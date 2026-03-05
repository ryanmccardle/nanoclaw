# ABOUTME: Deletes OmniFocus tasks by ID using Omni Automation.
# ABOUTME: Resolves tasks from flattened collections for removal.

import argparse
import json
import sys

from omnifocus_js import run_omnifocus_js
from write_cli import emit_json, ensure_id


def build_delete_task_js(task_id: str) -> str:
    task_id_json = json.dumps(task_id)
    return f'''
(function () {{
  var taskId = {task_id_json};

  function findById(collection, identifier) {{
    if (collection.byId) {{
      return collection.byId(identifier);
    }}
    if (!collection.find) {{
      return null;
    }}
    return collection.find(function (item) {{ return item.id.primaryKey === identifier; }});
  }}

  var task = findById(flattenedTasks, taskId);
  if (!task) {{
    throw new Error("Task not found: " + taskId);
  }}
  deleteObject(task);
  return JSON.stringify({{ ok: true }});
}})();
'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    args = parser.parse_args()

    try:
        task_id = ensure_id(args.id)
        run_omnifocus_js(build_delete_task_js(task_id))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    emit_json({"ok": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
