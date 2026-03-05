# ABOUTME: Updates OmniFocus tasks from JSON payloads using Omni Automation.
# ABOUTME: Supports property changes, moves, and tag assignment by ID.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id, load_data


def build_update_task_js(task_id: str, data: dict) -> str:
    task_id_json = json.dumps(task_id)
    name = json.dumps(data.get("name"))
    note = json.dumps(data.get("note"))
    flagged = json.dumps(data.get("flagged"))
    project_id = json.dumps(data.get("project_id"))
    parent_task_id = json.dumps(data.get("parent_task_id"))
    due = json.dumps(data.get("due"))
    defer = json.dumps(data.get("defer"))
    tag_ids = json.dumps(data.get("tag_ids"))

    return f'''
(function () {{
  var taskId = {task_id_json};
  var name = {name};
  var note = {note};
  var flagged = {flagged};
  var projectId = {project_id};
  var parentTaskId = {parent_task_id};
  var due = {due};
  var defer = {defer};
  var tagIds = {tag_ids};

  function findById(collection, identifier) {{
    if (collection.byId) {{
      return collection.byId(identifier);
    }}
    if (!collection.find) {{
      return null;
    }}
    return collection.find(function (item) {{ return item.id.primaryKey === identifier; }});
  }}

  function requireById(collection, identifier, label) {{
    var item = findById(collection, identifier);
    if (!item) {{
      throw new Error(label + " not found: " + identifier);
    }}
    return item;
  }}

  var task = requireById(flattenedTasks, taskId, "Task");

  if (parentTaskId) {{
    var parentTask = requireById(flattenedTasks, parentTaskId, "Task");
    task.parent = parentTask;
  }} else if (projectId) {{
    var project = requireById(flattenedProjects, projectId, "Project");
    task.project = project;
  }}

  if (name !== null && name !== undefined) {{
    task.name = name;
  }}
  if (note !== null && note !== undefined) {{
    task.note = note;
  }}
  if (flagged !== null && flagged !== undefined) {{
    task.flagged = flagged;
  }}
  if (due !== null && due !== undefined) {{
    task.dueDate = due ? new Date(due) : null;
  }}
  if (defer !== null && defer !== undefined) {{
    task.deferDate = defer ? new Date(defer) : null;
  }}
  if (tagIds !== null && tagIds !== undefined) {{
    var tags = tagIds.map(function (tagId) {{
      return requireById(flattenedTags, tagId, "Tag");
    }});
    task.clearTags();
    task.addTags(tags);
  }}

  return JSON.stringify({{ ok: true }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        task_id = ensure_id(args.id)
        data = load_data(args.data)
        run_omnifocus_js(build_update_task_js(task_id, data))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
