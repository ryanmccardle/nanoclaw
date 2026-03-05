import { execSync, spawnSync } from 'child_process';

import { logger } from './logger.js';

export const BROWSER_NETWORK = 'nanoclaw-net';
export const BROWSER_CONTAINER_NAME = 'nanoclaw-browser';
export const BROWSER_CDP_PORT = 9222;
export const BROWSER_CDP_URL = `ws://nanoclaw-browser:${BROWSER_CDP_PORT}`;

export function ensureBrowserNetwork(): void {
  try {
    execSync(`docker network inspect ${BROWSER_NETWORK}`, { stdio: 'ignore' });
    logger.debug(
      { network: BROWSER_NETWORK },
      'Browser network already exists',
    );
  } catch {
    logger.info({ network: BROWSER_NETWORK }, 'Creating browser network');
    execSync(`docker network create ${BROWSER_NETWORK}`);
  }
}

export function startBrowserSidecar(): void {
  // Remove any existing sidecar (ignore error if not running).
  // Use rm -f rather than stop to avoid race where --rm container is stopped
  // but not yet removed when docker run tries to reuse the name.
  spawnSync('docker', ['rm', '-f', BROWSER_CONTAINER_NAME], {
    stdio: 'ignore',
  });

  logger.info(
    { container: BROWSER_CONTAINER_NAME },
    'Starting browser sidecar',
  );

  // Chromium only binds CDP to loopback (127.0.0.1) regardless of
  // --remote-debugging-address. Use an internal port (9221) for Chromium and a
  // Python TCP proxy to expose it on 0.0.0.0:9222 so Docker's port forwarding
  // can reach it.
  const internalPort = BROWSER_CDP_PORT - 1; // 9221
  const proxyScript =
    'import socket,threading\n' +
    'def fwd(s,d):\n' +
    ' try:\n' +
    '  while True:\n' +
    '   b=s.recv(4096)\n' +
    '   if not b:break\n' +
    '   d.sendall(b)\n' +
    ' except:pass\n' +
    ' finally:\n' +
    '  try:s.close()\n' +
    '  except:pass\n' +
    '  try:d.close()\n' +
    '  except:pass\n' +
    `srv=socket.socket()\n` +
    `srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)\n` +
    `srv.bind(("0.0.0.0",${BROWSER_CDP_PORT}))\n` +
    `srv.listen(128)\n` +
    `while True:\n` +
    ` c,_=srv.accept()\n` +
    ` b=socket.socket()\n` +
    ` b.connect(("127.0.0.1",${internalPort}))\n` +
    ` threading.Thread(target=fwd,args=(c,b),daemon=True).start()\n` +
    ` threading.Thread(target=fwd,args=(b,c),daemon=True).start()`;

  const shellCmd =
    `chromium --headless=new --remote-debugging-port=${internalPort} ` +
    `--no-sandbox --disable-dev-shm-usage --user-data-dir=/tmp/chrome-data ` +
    `--window-size=1280,800 about:blank & ` +
    `CPID=$!; ` +
    `i=0; while [ $i -lt 40 ]; do ` +
    `  curl -sf http://127.0.0.1:${internalPort}/json/version >/dev/null 2>&1 && break; ` +
    `  sleep 0.5; i=$((i+1)); ` +
    `done; ` +
    `python3 -c '${proxyScript}' & ` +
    `wait $CPID`;

  const result = spawnSync(
    'docker',
    [
      'run',
      '-d',
      '--rm',
      '--name',
      BROWSER_CONTAINER_NAME,
      '--network',
      BROWSER_NETWORK,
      '-p',
      `${BROWSER_CDP_PORT}:${BROWSER_CDP_PORT}`,
      '--entrypoint',
      'sh',
      'nanoclaw-agent:latest',
      '-c',
      shellCmd,
    ],
    { stdio: 'pipe' },
  );

  if (result.status !== 0) {
    logger.error(
      { stderr: result.stderr?.toString() },
      'Failed to start browser sidecar',
    );
  } else {
    logger.info(
      { container: BROWSER_CONTAINER_NAME },
      'Browser sidecar started',
    );
  }
}

export function stopBrowserSidecar(): void {
  spawnSync('docker', ['stop', BROWSER_CONTAINER_NAME], { stdio: 'ignore' });
  logger.info({ container: BROWSER_CONTAINER_NAME }, 'Browser sidecar stopped');
}

export function getTailscaleIp(): string {
  // Try Tailscale CLI first
  try {
    const ip = execSync(
      '/Applications/Tailscale.app/Contents/MacOS/tailscale ip -4',
      {
        stdio: 'pipe',
        timeout: 3000,
      },
    )
      .toString()
      .trim();
    if (ip) return ip;
  } catch {
    // fall through
  }

  // Fallback: parse ifconfig for Tailscale CGNAT range (100.x.x.x)
  try {
    const ifconfig = execSync('ifconfig', {
      stdio: 'pipe',
      timeout: 3000,
    }).toString();
    const match = ifconfig.match(/inet (100\.\d+\.\d+\.\d+)/);
    if (match) return match[1];
  } catch {
    // fall through
  }

  return 'YOUR_TAILSCALE_IP';
}
