# ABOUTME: Updates OmniFocus projects from JSON payloads using Omni Automation.
# ABOUTME: Supports folder moves and type changes by ID.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id, load_data


def build_update_project_js(project_id: str, data: dict) -> str:
    project_id_json = json.dumps(project_id)
    name = json.dumps(data.get("name"))
    note = json.dumps(data.get("note"))
    folder_id = json.dumps(data.get("folder_id"))
    project_type = json.dumps(data.get("type"))

    return f'''
(function () {{
  var projectId = {project_id_json};
  var name = {name};
  var note = {note};
  var folderId = {folder_id};
  var projectType = {project_type};

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

  function applyType(project, type) {{
    if (!type) {{
      return;
    }}
    if (type === "single_action") {{
      project.containsSingletonActions = true;
      project.sequential = false;
      return;
    }}
    if (type === "sequential") {{
      project.containsSingletonActions = false;
      project.sequential = true;
      return;
    }}
    project.containsSingletonActions = false;
    project.sequential = false;
  }}

  var project = requireById(flattenedProjects, projectId, "Project");
  if (folderId) {{
    var folder = requireById(flattenedFolders, folderId, "Folder");
    project.parent = folder;
  }}
  if (name !== null && name !== undefined) {{
    project.name = name;
  }}
  if (note !== null && note !== undefined) {{
    project.note = note;
  }}
  applyType(project, projectType);

  return JSON.stringify({{ ok: true }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        project_id = ensure_id(args.id)
        data = load_data(args.data)
        run_omnifocus_js(build_update_project_js(project_id, data))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
