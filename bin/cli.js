#!/usr/bin/env node
import { createServer } from '../src/server.js';
import { initStore } from '../src/store.js';
import { getLanIp, probeServer, detectVpn } from '../src/net.js';

const args = process.argv.slice(2);

function argValue(prefix, fallback) {
  const found = args.find(a => a.startsWith(prefix));
  return found ? found.split('=').slice(1).join('=') : fallback;
}

const port = parseInt(argValue('--port=', process.env.PORT || '3000'), 10);
const host = argValue('--host=', process.env.HOST || '0.0.0.0');
const dbPath = argValue('--db=', process.env.DB_PATH || undefined);

async function runDoctor() {
  const lanIp = getLanIp();
  const vpns = detectVpn();

  console.log('🔍 API Key Manager — Diagnosis\n');

  const loopback = await probeServer('127.0.0.1', port);
  console.log(`1. Loopback (127.0.0.1:${port})     : ${loopback.reachable ? '✅ OK' : `❌ FAIL (${loopback.error})`}`);

  if (lanIp) {
    const lan = await probeServer(lanIp, port);
    console.log(`2. LAN IP (${lanIp}:${port})  : ${lan.reachable ? '✅ OK' : `❌ FAIL (${lan.error})`}`);
  } else {
    console.log('2. LAN IP                          : ⚠️  tidak ditemukan');
  }

  if (vpns.length > 0) {
    console.log(`3. VPN aktif                       : ⚠️  ${vpns.map(v => v.name).join(', ')}`);
    console.log('   → Browser HP bisa gagal akses ke 192.168.x.x / 127.0.0.1');
    console.log('   → Solusi: bypass private IP di app VPN, atau matikan VPN sesaat');
  } else {
    console.log('3. VPN aktif                       : ✅ tidak ada');
  }

  console.log('\n📱 Buka di browser HP  : http://127.0.0.1:' + port);
  if (lanIp) console.log('💻 Buka di device lain : http://' + lanIp + ':' + port);
  console.log('\nCatatan: pakai 127.0.0.1 (bukan localhost) agar tidak kena DNS IPv6 / proxy.');
}

async function main() {
  if (args.includes('--doctor') || args.includes('doctor')) {
    await runDoctor();
    return;
  }

  try {
    await initStore(dbPath);

    const app = createServer({ dbPath });
    const server = app.listen(port, host, () => {
      const lanIp = getLanIp();
      console.log(`🚀 API Key Manager server running at http://127.0.0.1:${port}`);
      console.log(`📊 Dashboard (browser HP) : http://127.0.0.1:${port}`);
      if (lanIp) console.log(`🌐 Dashboard (device lain): http://${lanIp}:${port}`);
      console.log(`🔌 OpenAI API             : http://127.0.0.1:${port}/v1`);
      console.log(`💚 Health check           : http://127.0.0.1:${port}/health`);
      console.log('\nTekan Ctrl+C untuk berhenti');
    });

    const shutdown = () => {
      console.log('\n👋 Shutting down...');
      server.close(() => {
        console.log('Server closed');
        process.exit(0);
      });
    };

    process.on('SIGINT', shutdown);
    process.on('SIGTERM', shutdown);
  } catch (err) {
    console.error('❌ Failed to start server:', err.message);
    process.exit(1);
  }
}

main();
