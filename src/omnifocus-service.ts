import http from 'http';
import path from 'path';
import { execFile } from 'child_process';
import { fileURLToPath } from 'url';

import { logger } from './logger.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPTS_DIR = path.resolve(__dirname, '..', 'scripts', 'omnifocus');
const PORT = 3847;
const HOST = '127.0.0.1';

let server: http.Server | null = null;

interface ToolArgs {
  [key: string]: unknown;
}

/**
 * Map MCP tool name + JSON body → python3 omnifocus_cli.py CLI args.
 */
function buildCliArgs(toolName: string, body: ToolArgs): string[] {
  switch (toolName) {
    case 'list_tasks': {
      const args = ['tasks', 'list'];
      const mode = body.mode as string | undefined;
      if (mode === 'inbox') args.push('--inbox');
      else if (mode === 'project') {
        args.push('--project', body.project_name as string);
      } else if (mode === 'all') {
        args.push('--all');
        const include = body.include_folders as string[] | undefined;
        if (include) for (const f of include) args.push('--include-folder', f);
        const exclude = body.exclude_folders as string[] | undefined;
        if (exclude) for (const f of exclude) args.push('--exclude-folder', f);
      }
      if (body.refresh) args.push('--refresh');
      return args;
    }
    case 'list_projects': {
      const args = ['projects', 'list'];
      if (body.refresh) args.push('--refresh');
      return args;
    }
    case 'list_folders': {
      const args = ['folders', 'list'];
      if (body.refresh) args.push('--refresh');
      return args;
    }
    case 'list_tags': {
      const args = ['tags', 'list'];
      if (body.refresh) args.push('--refresh');
      return args;
    }
    case 'create_task': {
      const args = ['tasks', 'create'];
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.flagged !== undefined)
        args.push('--flagged', String(body.flagged));
      if (body.due) args.push('--due', body.due as string);
      if (body.defer) args.push('--defer', body.defer as string);
      if (body.project_id) args.push('--project-id', body.project_id as string);
      if (body.parent_task_id)
        args.push('--parent-task-id', body.parent_task_id as string);
      const tagIds = body.tag_ids as string[] | undefined;
      if (tagIds) for (const id of tagIds) args.push('--tag-id', id);
      return args;
    }
    case 'update_task': {
      const args = ['tasks', 'update'];
      args.push('--id', body.id as string);
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.flagged !== undefined)
        args.push('--flagged', String(body.flagged));
      if (body.due) args.push('--due', body.due as string);
      if (body.defer) args.push('--defer', body.defer as string);
      if (body.clear_due) args.push('--clear-due');
      if (body.clear_defer) args.push('--clear-defer');
      if (body.project_id) args.push('--project-id', body.project_id as string);
      if (body.parent_task_id)
        args.push('--parent-task-id', body.parent_task_id as string);
      const tagIds = body.tag_ids as string[] | undefined;
      if (tagIds) for (const id of tagIds) args.push('--tag-id', id);
      return args;
    }
    case 'delete_task':
      return ['tasks', 'delete', '--id', body.id as string];
    case 'complete_task':
      return ['tasks', 'complete', '--id', body.id as string];
    case 'uncomplete_task':
      return ['tasks', 'uncomplete', '--id', body.id as string];
    case 'create_project': {
      const args = ['projects', 'create'];
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.type) args.push('--type', body.type as string);
      if (body.folder_id) args.push('--folder-id', body.folder_id as string);
      return args;
    }
    case 'update_project': {
      const args = ['projects', 'update'];
      args.push('--id', body.id as string);
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.type) args.push('--type', body.type as string);
      if (body.folder_id) args.push('--folder-id', body.folder_id as string);
      return args;
    }
    case 'delete_project':
      return ['projects', 'delete', '--id', body.id as string];
    case 'create_folder': {
      const args = ['folders', 'create'];
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.parent_folder_id)
        args.push('--parent-folder-id', body.parent_folder_id as string);
      return args;
    }
    case 'update_folder': {
      const args = ['folders', 'update'];
      args.push('--id', body.id as string);
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      if (body.parent_folder_id)
        args.push('--parent-folder-id', body.parent_folder_id as string);
      return args;
    }
    case 'delete_folder':
      return ['folders', 'delete', '--id', body.id as string];
    case 'create_tag': {
      const args = ['tags', 'create'];
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      return args;
    }
    case 'update_tag': {
      const args = ['tags', 'update'];
      args.push('--id', body.id as string);
      if (body.name) args.push('--name', body.name as string);
      if (body.note) args.push('--note', body.note as string);
      return args;
    }
    case 'delete_tag':
      return ['tags', 'delete', '--id', body.id as string];
    default:
      throw new Error(`Unknown tool: ${toolName}`);
  }
}

function runCli(
  args: string[],
): Promise<{ stdout: string; stderr: string; code: number }> {
  return new Promise((resolve) => {
    execFile(
      'python3',
      ['omnifocus_cli.py', ...args],
      { cwd: SCRIPTS_DIR, timeout: 30000 },
      (err, stdout, stderr) => {
        const code =
          err && 'code' in err ? (err as { code: number }).code : err ? 1 : 0;
        resolve({ stdout: stdout.toString(), stderr: stderr.toString(), code });
      },
    );
  });
}

export function startOmniFocusService(): void {
  if (server) return;

  server = http.createServer(async (req, res) => {
    // POST /tool/:toolName
    const match = req.url?.match(/^\/tool\/([a-z_]+)$/);
    if (req.method !== 'POST' || !match) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not found' }));
      return;
    }

    const toolName = match[1];
    let bodyStr = '';
    for await (const chunk of req) bodyStr += chunk;

    let body: ToolArgs = {};
    try {
      if (bodyStr.trim()) body = JSON.parse(bodyStr);
    } catch {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON' }));
      return;
    }

    try {
      const args = buildCliArgs(toolName, body);
      logger.debug({ toolName, args }, 'OmniFocus CLI call');

      const result = await runCli(args);

      if (result.code !== 0) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(
          JSON.stringify({
            error: result.stderr || `Exit code ${result.code}`,
          }),
        );
        return;
      }

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ result: result.stdout }));
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: msg }));
    }
  });

  server.listen(PORT, HOST, () => {
    logger.info({ port: PORT }, 'OmniFocus service started');
  });
}

export function stopOmniFocusService(): void {
  if (!server) return;
  server.close();
  server = null;
  logger.info('OmniFocus service stopped');
}
