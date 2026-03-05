# ABOUTME: Reads OmniFocus cache data and renders list outputs.
# ABOUTME: Refreshes cache via AppleScript for list operations.

import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Tuple

CACHE_TTL_SECONDS = 120
CACHE_PATH = os.path.expanduser("~/Library/Caches/omnifocus-skill/omnifocus.json")


def ensure_cache_dir() -> None:
    cache_dir = os.path.dirname(CACHE_PATH)
    os.makedirs(cache_dir, exist_ok=True)


def cache_is_stale() -> bool:
    if not os.path.exists(CACHE_PATH):
        return True
    age = time.time() - os.path.getmtime(CACHE_PATH)
    return age > CACHE_TTL_SECONDS


def run_omnifocus_js(script: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/osascript",
            "-l",
            "AppleScript",
            "-e",
            "on run argv",
            "-e",
            'tell application "OmniFocus" to evaluate javascript (item 1 of argv)',
            "-e",
            "end run",
            "--",
            script,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "OmniFocus JavaScript failed")
    return result.stdout


def build_omnifocus_js() -> str:
    return r"""
(function () {
  var tasks = flattenedTasks
    .filter(function (task) {
      return task.taskStatus !== Task.Status.Completed &&
        task.taskStatus !== Task.Status.Dropped;
    })
    .map(function (task) {
      return {
        id: task.id.primaryKey,
        name: task.name,
        inbox: task.inInbox,
        status_raw: task.taskStatus.name,
        note: task.note,
        flagged: task.flagged,
        parent_task_id: task.parent && task.parent.constructor.name === "Task"
          ? task.parent.id.primaryKey
          : "",
        project_id: task.project ? task.project.id.primaryKey : "",
        tag_ids: task.tags.map(function (tag) { return tag.id.primaryKey; }),
        due: task.dueDate ? task.dueDate.toISOString() : "",
        defer: task.deferDate ? task.deferDate.toISOString() : ""
      };
    });

  var projects = flattenedProjects.map(function (project) {
    return {
      id: project.id.primaryKey,
      name: project.name,
      parent_project_id: "",
      folder_id: project.parentFolder ? project.parentFolder.id.primaryKey : "",
      type: project.containsSingletonActions
        ? "single_action"
        : (project.sequential ? "sequential" : "parallel")
    };
  });

  var folders = flattenedFolders.map(function (folder) {
    return {
      id: folder.id.primaryKey,
      name: folder.name,
      parent_folder_id: folder.parent ? folder.parent.id.primaryKey : ""
    };
  });

  var tags = flattenedTags.map(function (tag) {
    return {
      id: tag.id.primaryKey,
      name: tag.name
    };
  });

  return JSON.stringify({ tasks: tasks, projects: projects, folders: folders, tags: tags });
})();
"""


def refresh_cache() -> None:
    ensure_cache_dir()
    script = build_omnifocus_js()
    output = run_omnifocus_js(script)
    data = json.loads(output)
    tmp_path = f"{CACHE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)
    os.replace(tmp_path, CACHE_PATH)


def load_cache() -> Dict[str, List[Dict[str, object]]]:
    with open(CACHE_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def path_has_prefix(path: str, prefix: str) -> bool:
    if path == prefix:
        return True
    return path.startswith(prefix + " > ")


def build_folder_paths(folders: List[Dict[str, object]]) -> Dict[str, str]:
    by_id = {folder["id"]: folder for folder in folders}
    cache: Dict[str, str] = {}

    def compute(folder_id: str) -> str:
        if folder_id in cache:
            return cache[folder_id]
        folder = by_id.get(folder_id)
        if not folder:
            cache[folder_id] = ""
            return ""
        name = folder["name"]
        parent_id = folder.get("parent_folder_id") or ""
        if parent_id:
            parent_path = compute(parent_id)
            if parent_path:
                value = parent_path + " > " + name
            else:
                value = name
        else:
            value = name
        cache[folder_id] = value
        return value

    for folder_id in by_id:
        compute(folder_id)

    return cache


def build_project_paths(
    projects: List[Dict[str, object]],
    folder_paths: Dict[str, str],
) -> Dict[str, str]:
    by_id = {project["id"]: project for project in projects}
    cache: Dict[str, str] = {}

    def compute(project_id: str) -> str:
        if project_id in cache:
            return cache[project_id]
        project = by_id.get(project_id)
        if not project:
            cache[project_id] = ""
            return ""
        name = project["name"]
        parent_id = project.get("parent_project_id") or ""
        if parent_id:
            parent_path = compute(parent_id)
            project_path = parent_path + " > " + name if parent_path else name
        else:
            project_path = name
        folder_id = project.get("folder_id") or ""
        folder_path = folder_paths.get(folder_id, "")
        if folder_path:
            full = folder_path + " > " + project_path
        else:
            full = project_path
        cache[project_id] = full
        return full

    for project_id in by_id:
        compute(project_id)

    return cache


def select_project_by_name(
    projects: List[Dict[str, object]], name: str
) -> Optional[Dict[str, object]]:
    for project in projects:
        if project["name"] == name:
            return project
    return None


def collect_descendant_projects(
    projects: List[Dict[str, object]], root_id: str
) -> List[str]:
    children: Dict[str, List[str]] = {}
    for project in projects:
        parent_id = project.get("parent_project_id") or ""
        children.setdefault(parent_id, []).append(project["id"])

    result: List[str] = []
    stack = [root_id]
    while stack:
        current = stack.pop()
        result.append(current)
        stack.extend(children.get(current, []))
    return result


def build_folder_children(folders: List[Dict[str, object]]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {}
    for folder in folders:
        parent_id = folder.get("parent_folder_id") or ""
        children.setdefault(parent_id, []).append(folder["id"])
    return children


def build_project_children(projects: List[Dict[str, object]]) -> Dict[str, List[str]]:
    children: Dict[str, List[str]] = {}
    for project in projects:
        parent_id = project.get("parent_project_id") or ""
        children.setdefault(parent_id, []).append(project["id"])
    return children


def indent(level: int) -> str:
    return "  " * level


def build_task_children(
    tasks: List[Dict[str, object]],
) -> Dict[str, List[Dict[str, object]]]:
    children: Dict[str, List[Dict[str, object]]] = {}
    for task in tasks:
        parent_id = task.get("parent_task_id") or ""
        if parent_id:
            children.setdefault(parent_id, []).append(task)
    return children


def collect_task_roots(
    tasks: List[Dict[str, object]],
) -> Tuple[List[Dict[str, object]], Dict[str, List[Dict[str, object]]]]:
    task_ids = {task.get("id") for task in tasks}
    inbox_roots: List[Dict[str, object]] = []
    project_roots: Dict[str, List[Dict[str, object]]] = {}
    for task in tasks:
        parent_id = task.get("parent_task_id") or ""
        if parent_id and parent_id in task_ids:
            continue
        if task.get("inbox"):
            inbox_roots.append(task)
            continue
        project_id = task.get("project_id") or ""
        project_roots.setdefault(project_id, []).append(task)
    return inbox_roots, project_roots


def emit_task(
    lines: List[str],
    task: Dict[str, object],
    level: int,
    task_children: Dict[str, List[Dict[str, object]]],
) -> None:
    lines.append(indent(level) + "- " + task["name"])
    for child in task_children.get(task["id"], []):
        emit_task(lines, child, level + 1, task_children)


def render_inbox_lines(tasks: List[Dict[str, object]]) -> List[str]:
    task_children = build_task_children(tasks)
    inbox_roots, _ = collect_task_roots(tasks)
    lines = ["Inbox"]
    for task in inbox_roots:
        emit_task(lines, task, 1, task_children)
    return lines


def normalize_paths(paths: List[str]) -> List[str]:
    return [path.strip() for path in paths if path.strip()]


def path_equals_or_child(path: str, candidate: str) -> bool:
    return candidate == path or candidate.startswith(path + " > ")


def folder_matches(path: str, includes: List[str], excludes: List[str]) -> bool:
    path = path.strip()
    includes = normalize_paths(includes)
    excludes = normalize_paths(excludes)
    if includes:
        if path and not any(path_equals_or_child(path, inc) for inc in includes):
            return False
    if path and any(path_has_prefix(path, exc) for exc in excludes):
        return False
    return True


def render_tree(
    tasks: List[Dict[str, object]],
    projects: List[Dict[str, object]],
    folders: List[Dict[str, object]],
    folder_paths: Dict[str, str],
    includes: List[str],
    excludes: List[str],
) -> List[str]:
    task_children = build_task_children(tasks)
    _, project_roots = collect_task_roots(tasks)

    folder_children = build_folder_children(folders)
    project_children = build_project_children(projects)
    projects_by_id = {project["id"]: project for project in projects}
    folders_by_id = {folder["id"]: folder for folder in folders}

    includes = normalize_paths(includes)
    excludes = normalize_paths(excludes)
    include_inbox = "Inbox" in includes if includes else True
    lines: List[str] = render_inbox_lines(tasks) if include_inbox else []

    def emit_project(project_id: str, level: int) -> None:
        project = projects_by_id.get(project_id)
        if not project:
            return
        lines.append(indent(level) + project["name"])
        for task in project_roots.get(project_id, []):
            emit_task(lines, task, level + 1, task_children)
        for child_id in project_children.get(project_id, []):
            if child_id != project_id:
                emit_project(child_id, level + 1)

    def emit_folder(folder_id: str, level: int) -> None:
        folder = folders_by_id.get(folder_id)
        if not folder:
            return
        path = folder_paths.get(folder_id, "")
        if not folder_matches(path, includes, excludes):
            return
        next_level = level
        if includes:
            if not any(path_equals_or_child(path, inc) for inc in includes):
                return
            if path in includes:
                lines.append(indent(level) + folder["name"])
                next_level = level + 1
        else:
            lines.append(indent(level) + folder["name"])
            next_level = level + 1
        for child_folder_id in folder_children.get(folder_id, []):
            emit_folder(child_folder_id, next_level)
        if not includes or path in includes:
            for project in projects:
                if (project.get("folder_id") or "") == folder_id and not project.get(
                    "parent_project_id"
                ):
                    emit_project(project["id"], next_level)

    for folder_id in folder_children.get("", []):
        emit_folder(folder_id, 0)

    return lines

