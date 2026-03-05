/**
 * OmniFocus MCP Proxy (stdio)
 * Runs inside the container, proxies tool calls to the host-side HTTP service
 * at http://host.docker.internal:3847/tool/<name>.
 */

import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';

const HOST_URL = 'http://host.docker.internal:3847';

async function callHost(toolName: string, body: Record<string, unknown>): Promise<string> {
  const res = await fetch(`${HOST_URL}/tool/${toolName}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await res.json() as { result?: string; error?: string };
  if (!res.ok || data.error) {
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data.result || '';
}

const server = new McpServer({
  name: 'omnifocus',
  version: '1.0.0',
});

// --- Tasks ---

server.tool(
  'list_tasks',
  'List OmniFocus tasks. Use mode to filter: "inbox" for inbox tasks, "project" for a specific project (requires project_name), "all" for all tasks (supports include_folders/exclude_folders).',
  {
    mode: z.enum(['inbox', 'project', 'all']).describe('Filter mode'),
    project_name: z.string().optional().describe('Project name (required when mode=project)'),
    include_folders: z.array(z.string()).optional().describe('Only show tasks in these folders (mode=all only)'),
    exclude_folders: z.array(z.string()).optional().describe('Hide tasks in these folders (mode=all only)'),
    refresh: z.boolean().optional().describe('Force cache refresh from OmniFocus'),
  },
  async (args) => {
    const text = await callHost('list_tasks', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'create_task',
  'Create a new OmniFocus task.',
  {
    name: z.string().describe('Task name'),
    note: z.string().optional().describe('Task note'),
    flagged: z.boolean().optional().describe('Flag the task'),
    due: z.string().optional().describe('Due date (e.g. "2026-03-10" or "tomorrow 5pm")'),
    defer: z.string().optional().describe('Defer date'),
    project_id: z.string().optional().describe('Project ID to add task to'),
    parent_task_id: z.string().optional().describe('Parent task ID (for subtasks)'),
    tag_ids: z.array(z.string()).optional().describe('Tag IDs to apply'),
  },
  async (args) => {
    const text = await callHost('create_task', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'update_task',
  'Update an existing OmniFocus task.',
  {
    id: z.string().describe('Task ID'),
    name: z.string().optional().describe('New name'),
    note: z.string().optional().describe('New note'),
    flagged: z.boolean().optional().describe('Set flagged state'),
    due: z.string().optional().describe('New due date'),
    defer: z.string().optional().describe('New defer date'),
    clear_due: z.boolean().optional().describe('Clear due date'),
    clear_defer: z.boolean().optional().describe('Clear defer date'),
    project_id: z.string().optional().describe('Move to project'),
    parent_task_id: z.string().optional().describe('Move under parent task'),
    tag_ids: z.array(z.string()).optional().describe('Replace tags'),
  },
  async (args) => {
    const text = await callHost('update_task', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'delete_task',
  'Delete an OmniFocus task.',
  { id: z.string().describe('Task ID') },
  async (args) => {
    const text = await callHost('delete_task', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'complete_task',
  'Mark an OmniFocus task as complete.',
  { id: z.string().describe('Task ID') },
  async (args) => {
    const text = await callHost('complete_task', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'uncomplete_task',
  'Mark a completed OmniFocus task as incomplete.',
  { id: z.string().describe('Task ID') },
  async (args) => {
    const text = await callHost('uncomplete_task', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

// --- Projects ---

server.tool(
  'list_projects',
  'List all OmniFocus projects.',
  { refresh: z.boolean().optional().describe('Force cache refresh') },
  async (args) => {
    const text = await callHost('list_projects', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'create_project',
  'Create a new OmniFocus project.',
  {
    name: z.string().describe('Project name'),
    note: z.string().optional().describe('Project note'),
    type: z.string().optional().describe('Project type (parallel or sequential)'),
    folder_id: z.string().optional().describe('Folder ID to place project in'),
  },
  async (args) => {
    const text = await callHost('create_project', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'update_project',
  'Update an existing OmniFocus project.',
  {
    id: z.string().describe('Project ID'),
    name: z.string().optional().describe('New name'),
    note: z.string().optional().describe('New note'),
    type: z.string().optional().describe('New type (parallel or sequential)'),
    folder_id: z.string().optional().describe('Move to folder'),
  },
  async (args) => {
    const text = await callHost('update_project', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'delete_project',
  'Delete an OmniFocus project.',
  { id: z.string().describe('Project ID') },
  async (args) => {
    const text = await callHost('delete_project', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

// --- Folders ---

server.tool(
  'list_folders',
  'List all OmniFocus folders.',
  { refresh: z.boolean().optional().describe('Force cache refresh') },
  async (args) => {
    const text = await callHost('list_folders', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'create_folder',
  'Create a new OmniFocus folder.',
  {
    name: z.string().describe('Folder name'),
    note: z.string().optional().describe('Folder note'),
    parent_folder_id: z.string().optional().describe('Parent folder ID'),
  },
  async (args) => {
    const text = await callHost('create_folder', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'update_folder',
  'Update an existing OmniFocus folder.',
  {
    id: z.string().describe('Folder ID'),
    name: z.string().optional().describe('New name'),
    note: z.string().optional().describe('New note'),
    parent_folder_id: z.string().optional().describe('Move to parent folder'),
  },
  async (args) => {
    const text = await callHost('update_folder', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'delete_folder',
  'Delete an OmniFocus folder.',
  { id: z.string().describe('Folder ID') },
  async (args) => {
    const text = await callHost('delete_folder', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

// --- Tags ---

server.tool(
  'list_tags',
  'List all OmniFocus tags.',
  { refresh: z.boolean().optional().describe('Force cache refresh') },
  async (args) => {
    const text = await callHost('list_tags', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'create_tag',
  'Create a new OmniFocus tag.',
  {
    name: z.string().describe('Tag name'),
    note: z.string().optional().describe('Tag note'),
  },
  async (args) => {
    const text = await callHost('create_tag', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'update_tag',
  'Update an existing OmniFocus tag.',
  {
    id: z.string().describe('Tag ID'),
    name: z.string().optional().describe('New name'),
    note: z.string().optional().describe('New note'),
  },
  async (args) => {
    const text = await callHost('update_tag', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

server.tool(
  'delete_tag',
  'Delete an OmniFocus tag.',
  { id: z.string().describe('Tag ID') },
  async (args) => {
    const text = await callHost('delete_tag', args);
    return { content: [{ type: 'text' as const, text }] };
  },
);

// Start
const transport = new StdioServerTransport();
await server.connect(transport);
