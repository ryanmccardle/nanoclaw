# ABOUTME: Deletes OmniFocus folders by ID using Omni Automation.
# ABOUTME: Resolves folders from flattened collections for removal.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id


def build_delete_folder_js(folder_id: str) -> str:
    folder_id_json = json.dumps(folder_id)
    return f'''
(function () {{
  var folderId = {folder_id_json};

  function findById(collection, identifier) {{
    if (collection.byId) {{
      return collection.byId(identifier);
    }}
    if (!collection.find) {{
      return null;
    }}
    return collection.find(function (item) {{ return item.id.primaryKey === identifier; }});
  }}

  var folder = findById(flattenedFolders, folderId);
  if (!folder) {{
    throw new Error("Folder not found: " + folderId);
  }}
  deleteObject(folder);
  return JSON.stringify({{ ok: true }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    args = parser.parse_args()

    try:
        folder_id = ensure_id(args.id)
        run_omnifocus_js(build_delete_folder_js(folder_id))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
