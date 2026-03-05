# NanoClaw

Personal Claude assistant. See [README.md](README.md) for philosophy and setup. See [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) for architecture decisions.

## Quick Context

Single Node.js process with skill-based channel system. Channels (WhatsApp, Telegram, Slack, Discord, Gmail) are skills that self-register at startup. Messages route to Claude Agent SDK running in containers (Linux VMs). Each group has isolated filesystem and memory.

## Key Files

| File | Purpose |
|------|---------|
| `src/index.ts` | Orchestrator: state, message loop, agent invocation |
| `src/channels/registry.ts` | Channel registry (self-registration at startup) |
| `src/ipc.ts` | IPC watcher and task processing |
| `src/router.ts` | Message formatting and outbound routing |
| `src/config.ts` | Trigger pattern, paths, intervals |
| `src/container-runner.ts` | Spawns agent containers with mounts |
| `src/task-scheduler.ts` | Runs scheduled tasks |
| `src/db.ts` | SQLite operations |
| `groups/{name}/CLAUDE.md` | Per-group memory (isolated) |
| `container/skills/agent-browser.md` | Browser automation tool (available to all agents via Bash) |
| `src/browser-service.ts` | Browser sidecar lifecycle, Tailscale IP detection |

## Skills

| Skill | When to Use |
|-------|-------------|
| `/setup` | First-time installation, authentication, service configuration |
| `/customize` | Adding channels, integrations, changing behavior |
| `/debug` | Container issues, logs, troubleshooting |
| `/update-nanoclaw` | Bring upstream NanoClaw updates into a customized install |
| `/qodo-pr-resolver` | Fetch and fix Qodo PR review issues interactively or in batch |
| `/get-qodo-rules` | Load org- and repo-level coding rules from Qodo before code tasks |

## Development

Run commands directly—don't tell the user to run them.

```bash
npm run dev          # Run with hot reload
npm run build        # Compile TypeScript
./container/build.sh # Rebuild agent container
```

Service management:
```bash
# macOS (launchd)
launchctl load ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl unload ~/Library/LaunchAgents/com.nanoclaw.plist
launchctl kickstart -k gui/$(id -u)/com.nanoclaw  # restart

# Linux (systemd)
systemctl --user start nanoclaw
systemctl --user stop nanoclaw
systemctl --user restart nanoclaw
```

## Browser Sidecar

A persistent `nanoclaw-browser` container runs Chromium alongside the agent containers. Agents connect to it via `ws://nanoclaw-browser:9222` (passed as `BROWSER_CDP_URL` env var). The sidecar preserves cookies and login state across agent turns.

**Architecture:**
- Docker network `nanoclaw-net` connects the sidecar and all agent containers
- Chromium binds CDP internally on port 9221; a Python TCP proxy exposes it on `0.0.0.0:9222`
- Port 9222 is forwarded through Colima to Mac host on all interfaces (including Tailscale)
- Viewport: 1280×800

**User takeover flow (login/CAPTCHA):**
1. Andy navigates to the page and writes an IPC task (`browser_interactive` type)
2. NanoClaw sends a Telegram message with `chrome://inspect` + Tailscale IP instructions
3. User opens `chrome://inspect`, adds `<tailscale-ip>:9222`, clicks Inspect
4. User completes the action, replies "continue"
5. Andy resumes with session/cookies intact

**Inspect from Mac:**
```
chrome://inspect → Configure → add 100.106.88.38:9222
```

**Troubleshooting:**
- Check sidecar: `docker ps | grep nanoclaw-browser`
- Test CDP: `curl http://localhost:9222/json/version`
- View logs: `docker logs nanoclaw-browser`
- Chromium ignores `--remote-debugging-address=0.0.0.0` — the Python proxy inside the container is what makes external access work

## Troubleshooting

**WhatsApp not connecting after upgrade:** WhatsApp is now a separate skill, not bundled in core. Run `/add-whatsapp` (or `npx tsx scripts/apply-skill.ts .claude/skills/add-whatsapp && npm run build`) to install it. Existing auth credentials and groups are preserved.

## Container Build Cache

The container buildkit caches the build context aggressively. `--no-cache` alone does NOT invalidate COPY steps — the builder's volume retains stale files. To force a truly clean rebuild, prune the builder then re-run `./container/build.sh`.
