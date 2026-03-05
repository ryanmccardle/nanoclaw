# ABOUTME: Deletes OmniFocus tags by ID using Omni Automation.
# ABOUTME: Resolves tags from flattened collections for removal.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id


def build_delete_tag_js(tag_id: str) -> str:
    tag_id_json = json.dumps(tag_id)
    return f'''
(function () {{
  var tagId = {tag_id_json};

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
  deleteObject(tag);
  return JSON.stringify({{ ok: true }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    args = parser.parse_args()

    try:
        tag_id = ensure_id(args.id)
        run_omnifocus_js(build_delete_tag_js(tag_id))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
