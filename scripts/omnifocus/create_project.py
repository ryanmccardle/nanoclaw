# ABOUTME: Creates OmniFocus projects from JSON payloads using Omni Automation.
# ABOUTME: Supports optional folder placement and project type configuration.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, load_data


def build_create_project_js(data: dict) -> str:
    if not data.get("name"):
        raise ValueError("Project name is required")

    props = {"name": data["name"]}
    if "note" in data:
        props["note"] = data["note"]

    props_json = json.dumps(props)
    folder_id = json.dumps(data.get("folder_id"))
    project_type = json.dumps(data.get("type"))

    return f'''
(function () {{
  var data = {props_json};
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

  var project = null;
  if (folderId) {{
    var folder = requireById(flattenedFolders, folderId, "Folder");
    project = new Project(data.name, folder);
  }} else {{
    project = new Project(data.name);
  }}
  if (data.note !== undefined) {{
    project.note = data.note;
  }}
  applyType(project, projectType);

  return JSON.stringify({{ id: project.id.primaryKey }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        data = load_data(args.data)
        output = run_omnifocus_js(build_create_project_js(data))
        payload = json.loads(output)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True, "id": payload.get("id", "")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
