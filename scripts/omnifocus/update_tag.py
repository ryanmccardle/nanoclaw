# ABOUTME: Updates OmniFocus tags from JSON payloads using Omni Automation.
# ABOUTME: Supports renaming and note changes by ID.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id, load_data


def build_update_tag_js(tag_id: str, data: dict) -> str:
    tag_id_json = json.dumps(tag_id)
    name = json.dumps(data.get("name"))
    note = json.dumps(data.get("note"))

    return f'''
(function () {{
  var tagId = {tag_id_json};
  var name = {name};
  var note = {note};

  function findById(collection, identifier) {{
    if (collection.byId) {{
      return collection.byId(identifier);
    }}
    if (!collection.find) {{
      return null;
    }}
    return collection.find(function (item) {{ return item.id.primaryKey === identifier; }});
  }}

  var tag = findById(flattenedTags, tagId);
  if (!tag) {{
    throw new Error("Tag not found: " + tagId);
  }}
  if (name !== null && name !== undefined) {{
    tag.name = name;
  }}
  if (note !== null && note !== undefined) {{
    tag.note = note;
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
        tag_id = ensure_id(args.id)
        data = load_data(args.data)
        run_omnifocus_js(build_update_tag_js(tag_id, data))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
