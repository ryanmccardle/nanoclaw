# ABOUTME: Executes OmniFocus JavaScript via osascript with shared error handling.
# ABOUTME: Builds AppleScript wrappers for Omni Automation JavaScript payloads.

import json
import subprocess


def build_applescript(script: str) -> str:
    return f'tell application "OmniFocus" to evaluate javascript {json.dumps(script)}'


def run_omnifocus_js(script: str) -> str:
    result = subprocess.run(
        [
            "/usr/bin/osascript",
            "-l",
            "AppleScript",
            "-e",
            "on run argv",
            "-e",
            'tell application "OmniFocus" to evaluate javascript (item 1 of argv)',
            "-e",
            "end run",
            "--",
            script,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "OmniFocus JavaScript failed")
    return result.stdout
