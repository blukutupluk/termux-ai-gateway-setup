import os from 'node:os';

/**
 * Detect the LAN IP address of this device.
 * Used to print a reachable dashboard URL for other devices on the same WiFi.
 */
export function getLanIp() {
  const interfaces = os.networkInterfaces();
  const candidates = [];

  for (const [name, addresses] of Object.entries(interfaces)) {
    if (!addresses) continue;
    // Skip loopback and typical VPN tunnel interfaces
    if (name === 'lo' || name.startsWith('tun') || name.startsWith('ppp') || name.startsWith('wg')) {
      continue;
    }
    for (const addr of addresses) {
      if (addr.family === 'IPv4' && !addr.internal) {
        candidates.push({ name, address: addr.address });
      }
    }
  }

  // Prefer wlan interfaces (common on Android)
  const preferred = candidates.find(c => c.name.startsWith('wlan'));
  const chosen = preferred || candidates[0];
  return chosen ? chosen.address : null;
}

/**
 * Check whether the local server is reachable through a given address.
 * Returns { reachable, latencyMs, error }.
 */
export async function probeServer(address, port, timeoutMs = 3000) {
  const started = Date.now();
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const res = await fetch(`http://${address}:${port}/health`, { signal: controller.signal });
    clearTimeout(timer);
    return {
      reachable: res.ok,
      latencyMs: Date.now() - started,
      status: res.status,
      error: null
    };
  } catch (err) {
    return {
      reachable: false,
      latencyMs: Date.now() - started,
      status: null,
      error: err.message
    };
  }
}

/**
 * Detect whether a VPN tunnel interface is active.
 * Android VPNs (Clash/Shadowrocket TUN, WireGuard, etc.) often break LAN access
 * from the device browser unless private ranges are bypassed.
 */
export function detectVpn() {
  const interfaces = os.networkInterfaces();
  const vpnIfaces = [];

  for (const [name, addresses] of Object.entries(interfaces)) {
    if (!addresses) continue;
    const isTunnel = /^(tun|ppp|wg|ipsec|tap)/i.test(name);
    if (isTunnel) {
      const ipv4 = addresses.find(a => a.family === 'IPv4');
      vpnIfaces.push({ name, address: ipv4 ? ipv4.address : null });
    }
  }

  return vpnIfaces;
}
