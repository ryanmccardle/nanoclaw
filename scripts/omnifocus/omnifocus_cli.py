# ABOUTME: Provides the unified OmniFocus CLI with subcommands.
# ABOUTME: Routes read and write operations to helper modules.

import argparse
import json
import sys
from typing import Optional

import create_folder
import create_project
import create_tag
import create_task
import delete_folder
import delete_project
import delete_tag
import delete_task
import omnifocus_js
import omnifocus_read
import task_completion
import update_folder
import update_project
import update_tag
import update_task


def load_cache(refresh: bool) -> dict:
    if refresh or omnifocus_read.cache_is_stale():
        omnifocus_read.refresh_cache()
    return omnifocus_read.load_cache()


def parse_optional_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    raise ValueError("Flagged must be true or false")


def handle_tasks_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.project and (args.inbox or args.projects or args.all_tasks):
        parser.print_usage(sys.stderr)
        return 2

    if (args.include_folder or args.exclude_folder) and not args.all_tasks:
        parser.print_usage(sys.stderr)
        return 2

    if not (args.inbox or args.project or args.projects or args.all_tasks):
        parser.print_usage(sys.stderr)
        return 2

    data = load_cache(args.refresh)
    tasks = data.get("tasks", [])
    projects = data.get("projects", [])
    folders = data.get("folders", [])

    folder_paths = omnifocus_read.build_folder_paths(folders)
    project_paths = omnifocus_read.build_project_paths(projects, folder_paths)

    if args.inbox:
        inbox_tasks = [task for task in tasks if task.get("inbox")]
        lines = omnifocus_read.render_inbox_lines(inbox_tasks)
        for line in lines:
            print(line)
        return 0

    if args.project:
        project = omnifocus_read.select_project_by_name(projects, args.project)
        if not project:
            return 0
        project_ids = set(
            omnifocus_read.collect_descendant_projects(projects, project["id"])
        )
        for task in tasks:
            if task.get("project_id") in project_ids:
                print(task["name"])
        return 0

    if args.projects:
        for project in projects:
            path = project_paths.get(project["id"], "")
            if path:
                print(path)
        return 0

    if args.all_tasks:
        lines = omnifocus_read.render_tree(
            tasks,
            projects,
            folders,
            folder_paths,
            args.include_folder,
            args.exclude_folder,
        )
        for line in lines:
            print(line)
        return 0

    return 0


def build_task_payload(args: argparse.Namespace) -> dict:
    payload: dict = {}
    if getattr(args, "name", None) is not None:
        payload["name"] = args.name
    if getattr(args, "note", None) is not None:
        payload["note"] = args.note

    flagged = parse_optional_bool(getattr(args, "flagged", None))
    if flagged is not None:
        payload["flagged"] = flagged

    if getattr(args, "project_id", None) and getattr(args, "parent_task_id", None):
        raise ValueError("Only one of project_id or parent_task_id is allowed")
    if getattr(args, "project_id", None):
        payload["project_id"] = args.project_id
    if getattr(args, "parent_task_id", None):
        payload["parent_task_id"] = args.parent_task_id

    if getattr(args, "due", None) is not None or getattr(args, "clear_due", False):
        payload["due"] = None if args.clear_due else args.due
    if getattr(args, "defer", None) is not None or getattr(args, "clear_defer", False):
        payload["defer"] = None if args.clear_defer else args.defer

    if getattr(args, "tag_id", None) is not None:
        payload["tag_ids"] = args.tag_id

    return payload


def handle_tasks_create(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.name:
        parser.print_usage(sys.stderr)
        return 2
    payload = build_task_payload(args)
    script = create_task.build_create_task_js(payload)
    output = omnifocus_js.run_omnifocus_js(script)
    data = json.loads(output)
    print(json.dumps({"ok": True, "id": data.get("id", "")}))
    return 0


def handle_tasks_update(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    payload = build_task_payload(args)
    script = update_task.build_update_task_js(args.id, payload)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_tasks_delete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = delete_task.build_delete_task_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_tasks_complete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = task_completion.build_complete_task_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_tasks_uncomplete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = task_completion.build_uncomplete_task_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_projects_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    data = load_cache(args.refresh)
    projects = data.get("projects", [])
    folders = data.get("folders", [])
    folder_paths = omnifocus_read.build_folder_paths(folders)
    project_paths = omnifocus_read.build_project_paths(projects, folder_paths)
    for project in projects:
        path = project_paths.get(project["id"], "")
        if path:
            print(path)
    return 0


def handle_projects_create(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.name:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {"name": args.name}
    if args.note is not None:
        payload["note"] = args.note
    if args.type is not None:
        payload["type"] = args.type
    if args.folder_id is not None:
        payload["folder_id"] = args.folder_id
    output = omnifocus_js.run_omnifocus_js(create_project.build_create_project_js(payload))
    data = json.loads(output)
    print(json.dumps({"ok": True, "id": data.get("id", "")}))
    return 0


def handle_projects_update(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.note is not None:
        payload["note"] = args.note
    if args.type is not None:
        payload["type"] = args.type
    if args.folder_id is not None:
        payload["folder_id"] = args.folder_id
    script = update_project.build_update_project_js(args.id, payload)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_projects_delete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = delete_project.build_delete_project_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_tags_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    data = load_cache(args.refresh)
    tags = data.get("tags", [])
    for tag in tags:
        name = tag.get("name", "")
        if name:
            print(name)
    return 0


def handle_tags_create(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.name:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {"name": args.name}
    if args.note is not None:
        payload["note"] = args.note
    output = omnifocus_js.run_omnifocus_js(create_tag.build_create_tag_js(payload))
    data = json.loads(output)
    print(json.dumps({"ok": True, "id": data.get("id", "")}))
    return 0


def handle_tags_update(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.note is not None:
        payload["note"] = args.note
    script = update_tag.build_update_tag_js(args.id, payload)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_tags_delete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = delete_tag.build_delete_tag_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_folders_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    data = load_cache(args.refresh)
    folders = data.get("folders", [])
    folder_paths = omnifocus_read.build_folder_paths(folders)
    for folder in folders:
        path = folder_paths.get(folder["id"], "")
        if path:
            print(path)
    return 0


def handle_folders_create(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.name:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {"name": args.name}
    if args.note is not None:
        payload["note"] = args.note
    if args.parent_folder_id is not None:
        payload["parent_folder_id"] = args.parent_folder_id
    output = omnifocus_js.run_omnifocus_js(create_folder.build_create_folder_js(payload))
    data = json.loads(output)
    print(json.dumps({"ok": True, "id": data.get("id", "")}))
    return 0


def handle_folders_update(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    payload: dict = {}
    if args.name is not None:
        payload["name"] = args.name
    if args.note is not None:
        payload["note"] = args.note
    if args.parent_folder_id is not None:
        payload["parent_folder_id"] = args.parent_folder_id
    script = update_folder.build_update_folder_js(args.id, payload)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def handle_folders_delete(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.id:
        parser.print_usage(sys.stderr)
        return 2
    script = delete_folder.build_delete_folder_js(args.id)
    omnifocus_js.run_omnifocus_js(script)
    print(json.dumps({"ok": True}))
    return 0


def build_tasks_subparser(subparsers: argparse._SubParsersAction) -> None:
    tasks_parser = subparsers.add_parser("tasks")
    task_actions = tasks_parser.add_subparsers(dest="action")
    task_actions.required = True

    list_parser = task_actions.add_parser("list")
    list_parser.add_argument("--inbox", action="store_true")
    list_parser.add_argument("--project")
    list_parser.add_argument("--projects", action="store_true")
    list_parser.add_argument("--all", dest="all_tasks", action="store_true")
    list_parser.add_argument("--include-folder", action="append", default=[])
    list_parser.add_argument("--exclude-folder", action="append", default=[])
    list_parser.add_argument("--refresh", action="store_true")
    list_parser.set_defaults(handler=handle_tasks_list, handler_parser=list_parser)

    create_parser = task_actions.add_parser("create")
    create_parser.add_argument("--name")
    create_parser.add_argument("--note")
    create_parser.add_argument("--flagged")
    create_parser.add_argument("--due")
    create_parser.add_argument("--defer")
    create_parser.add_argument("--clear-due", action="store_true")
    create_parser.add_argument("--clear-defer", action="store_true")
    create_parser.add_argument("--project-id")
    create_parser.add_argument("--parent-task-id")
    create_parser.add_argument("--tag-id", action="append")
    create_parser.set_defaults(handler=handle_tasks_create, handler_parser=create_parser)

    update_parser = task_actions.add_parser("update")
    update_parser.add_argument("--id")
    update_parser.add_argument("--name")
    update_parser.add_argument("--note")
    update_parser.add_argument("--flagged")
    update_parser.add_argument("--due")
    update_parser.add_argument("--defer")
    update_parser.add_argument("--clear-due", action="store_true")
    update_parser.add_argument("--clear-defer", action="store_true")
    update_parser.add_argument("--project-id")
    update_parser.add_argument("--parent-task-id")
    update_parser.add_argument("--tag-id", action="append")
    update_parser.set_defaults(handler=handle_tasks_update, handler_parser=update_parser)

    delete_parser = task_actions.add_parser("delete")
    delete_parser.add_argument("--id")
    delete_parser.set_defaults(handler=handle_tasks_delete, handler_parser=delete_parser)

    complete_parser = task_actions.add_parser("complete")
    complete_parser.add_argument("--id")
    complete_parser.set_defaults(handler=handle_tasks_complete, handler_parser=complete_parser)

    uncomplete_parser = task_actions.add_parser("uncomplete")
    uncomplete_parser.add_argument("--id")
    uncomplete_parser.set_defaults(handler=handle_tasks_uncomplete, handler_parser=uncomplete_parser)


def build_projects_subparser(subparsers: argparse._SubParsersAction) -> None:
    projects_parser = subparsers.add_parser("projects")
    project_actions = projects_parser.add_subparsers(dest="action")
    project_actions.required = True

    list_parser = project_actions.add_parser("list")
    list_parser.add_argument("--refresh", action="store_true")
    list_parser.set_defaults(handler=handle_projects_list, handler_parser=list_parser)

    create_parser = project_actions.add_parser("create")
    create_parser.add_argument("--name")
    create_parser.add_argument("--note")
    create_parser.add_argument("--type")
    create_parser.add_argument("--folder-id")
    create_parser.set_defaults(handler=handle_projects_create, handler_parser=create_parser)

    update_parser = project_actions.add_parser("update")
    update_parser.add_argument("--id")
    update_parser.add_argument("--name")
    update_parser.add_argument("--note")
    update_parser.add_argument("--type")
    update_parser.add_argument("--folder-id")
    update_parser.set_defaults(handler=handle_projects_update, handler_parser=update_parser)

    delete_parser = project_actions.add_parser("delete")
    delete_parser.add_argument("--id")
    delete_parser.set_defaults(handler=handle_projects_delete, handler_parser=delete_parser)


def build_tags_subparser(subparsers: argparse._SubParsersAction) -> None:
    tags_parser = subparsers.add_parser("tags")
    tag_actions = tags_parser.add_subparsers(dest="action")
    tag_actions.required = True

    list_parser = tag_actions.add_parser("list")
    list_parser.add_argument("--refresh", action="store_true")
    list_parser.set_defaults(handler=handle_tags_list, handler_parser=list_parser)

    create_parser = tag_actions.add_parser("create")
    create_parser.add_argument("--name")
    create_parser.add_argument("--note")
    create_parser.set_defaults(handler=handle_tags_create, handler_parser=create_parser)

    update_parser = tag_actions.add_parser("update")
    update_parser.add_argument("--id")
    update_parser.add_argument("--name")
    update_parser.add_argument("--note")
    update_parser.set_defaults(handler=handle_tags_update, handler_parser=update_parser)

    delete_parser = tag_actions.add_parser("delete")
    delete_parser.add_argument("--id")
    delete_parser.set_defaults(handler=handle_tags_delete, handler_parser=delete_parser)


def build_folders_subparser(subparsers: argparse._SubParsersAction) -> None:
    folders_parser = subparsers.add_parser("folders")
    folder_actions = folders_parser.add_subparsers(dest="action")
    folder_actions.required = True

    list_parser = folder_actions.add_parser("list")
    list_parser.add_argument("--refresh", action="store_true")
    list_parser.set_defaults(handler=handle_folders_list, handler_parser=list_parser)

    create_parser = folder_actions.add_parser("create")
    create_parser.add_argument("--name")
    create_parser.add_argument("--note")
    create_parser.add_argument("--parent-folder-id")
    create_parser.set_defaults(handler=handle_folders_create, handler_parser=create_parser)

    update_parser = folder_actions.add_parser("update")
    update_parser.add_argument("--id")
    update_parser.add_argument("--name")
    update_parser.add_argument("--note")
    update_parser.add_argument("--parent-folder-id")
    update_parser.set_defaults(handler=handle_folders_update, handler_parser=update_parser)

    delete_parser = folder_actions.add_parser("delete")
    delete_parser.add_argument("--id")
    delete_parser.set_defaults(handler=handle_folders_delete, handler_parser=delete_parser)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="entity")
    subparsers.required = True

    build_tasks_subparser(subparsers)
    build_projects_subparser(subparsers)
    build_tags_subparser(subparsers)
    build_folders_subparser(subparsers)

    args = parser.parse_args()
    handler = getattr(args, "handler", None)
    handler_parser = getattr(args, "handler_parser", None)
    if not handler or not handler_parser:
        parser.print_usage(sys.stderr)
        return 2
    try:
        return handler(args, handler_parser)
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
