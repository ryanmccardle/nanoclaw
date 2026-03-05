# ABOUTME: Updates OmniFocus folders from JSON payloads using Omni Automation.
# ABOUTME: Supports renaming, notes, and parent moves by ID.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id, load_data


def build_update_folder_js(folder_id: str, data: dict) -> str:
    folder_id_json = json.dumps(folder_id)
    name = json.dumps(data.get("name"))
    note = json.dumps(data.get("note"))
    parent_folder_id = json.dumps(data.get("parent_folder_id"))

    return f'''
(function () {{
  var folderId = {folder_id_json};
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

  var folder = requireById(flattenedFolders, folderId, "Folder");
  if (name !== null && name !== undefined) {{
    folder.name = name;
  }}
  if (note !== null && note !== undefined) {{
    folder.note = note;
  }}
  if (parentFolderId) {{
    var parent = requireById(flattenedFolders, parentFolderId, "Folder");
    folder.moveTo(parent);
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
        folder_id = ensure_id(args.id)
        data = load_data(args.data)
        run_omnifocus_js(build_update_folder_js(folder_id, data))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
