# ABOUTME: Creates OmniFocus tasks from JSON payloads using Omni Automation.
# ABOUTME: Supports inbox, project, or parent task placement and optional tags.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, load_data


def build_create_task_js(data: dict) -> str:
    if not data.get("name"):
        raise ValueError("Task name is required")

    props = {"name": data["name"]}
    if "note" in data:
        props["note"] = data["note"]
    if "flagged" in data:
        props["flagged"] = data["flagged"]

    props_json = json.dumps(props)
    project_id = json.dumps(data.get("project_id"))
    parent_task_id = json.dumps(data.get("parent_task_id"))
    due = json.dumps(data.get("due"))
    defer = json.dumps(data.get("defer"))
    tag_ids = json.dumps(data.get("tag_ids", []))

    return f'''
(function () {{
  var data = {props_json};
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

  var location = inbox.beginning;
  if (projectId) {{
    location = requireById(flattenedProjects, projectId, "Project");
  }}
  if (parentTaskId) {{
    location = requireById(flattenedTasks, parentTaskId, "Task");
  }}

  var task = new Task(data.name, location);
  if (data.note !== undefined) {{
    task.note = data.note;
  }}
  if (data.flagged !== undefined) {{
    task.flagged = data.flagged;
  }}

  if (due !== null && due !== undefined) {{
    task.dueDate = due ? new Date(due) : null;
  }}
  if (defer !== null && defer !== undefined) {{
    task.deferDate = defer ? new Date(defer) : null;
  }}
  if (tagIds && tagIds.length) {{
    var tags = tagIds.map(function (tagId) {{
      return requireById(flattenedTags, tagId, "Tag");
    }});
    task.addTags(tags);
  }}

  return JSON.stringify({{ id: task.id.primaryKey }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        data = load_data(args.data)
        output = run_omnifocus_js(build_create_task_js(data))
        payload = json.loads(output)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True, "id": payload.get("id", "")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
