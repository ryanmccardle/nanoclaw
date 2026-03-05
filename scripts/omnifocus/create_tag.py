# ABOUTME: Creates OmniFocus tags from JSON payloads using Omni Automation.
# ABOUTME: Supports optional note assignment.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, load_data


def build_create_tag_js(data: dict) -> str:
    if not data.get("name"):
        raise ValueError("Tag name is required")

    name = json.dumps(data["name"])
    note = json.dumps(data.get("note"))

    return f'''
(function () {{
  var name = {name};
  var note = {note};

  var tag = new Tag(name);
  if (note !== null && note !== undefined) {{
    tag.note = note;
  }}

  return JSON.stringify({{ id: tag.id.primaryKey }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    args = parser.parse_args()

    try:
        data = load_data(args.data)
        output = run_omnifocus_js(build_create_tag_js(data))
        payload = json.loads(output)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True, "id": payload.get("id", "")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
