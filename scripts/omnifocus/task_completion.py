# ABOUTME: Builds OmniFocus JavaScript for task completion changes.
# ABOUTME: Resolves tasks by ID and marks them complete or incomplete.

import json


def build_complete_task_js(task_id: str) -> str:
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
  task.markComplete();
  return JSON.stringify({{ ok: true }});
}})();
'''


def build_uncomplete_task_js(task_id: str) -> str:
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
  task.markIncomplete();
  return JSON.stringify({{ ok: true }});
}})();
'''
