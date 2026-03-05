# ABOUTME: Creates OmniFocus folders from JSON payloads using Omni Automation.
# ABOUTME: Supports optional parent placement and note assignment.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, load_data


def build_create_folder_js(data: dict) -> str:
    if not data.get("name"):
        raise ValueError("Folder name is required")

    name = json.dumps(data["name"])
    note = json.dumps(data.get("note"))
    parent_folder_id = json.dumps(data.get("parent_folder_id"))

    return f'''
(function () {{
  var name = {name};
  var note = {note};
  var parentFolderId = {parent_folder_id};

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

  var folder = new Folder(name);
  if (note !== null && note !== undefined) {{
    folder.note = note;
  }}
  if (parentFolderId) {{
    var parent = requireById(flattenedFolders, parentFolderId, "Folder");
    folder.moveTo(parent);
  }}

  return JSON.stringify({{ id: folder.id.primaryKey }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        data = load_data(args.data)
        output = run_omnifocus_js(build_create_folder_js(data))
        payload = json.loads(output)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True, "id": payload.get("id", "")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
