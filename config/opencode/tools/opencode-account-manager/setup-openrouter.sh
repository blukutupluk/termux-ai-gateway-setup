#!/usr/bin/env bash
# Tambahkan provider OpenRouter (HANYA model free) ke config OpenCode.
# Pakai:
#   export OPENROUTER_API_KEY='...'   # atau simpan di ~/.bashrc
#   bash setup-openrouter.sh
set -euo pipefail

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "OPENROUTER_API_KEY belum diset. Jalankan: export OPENROUTER_API_KEY='...' dulu."
  exit 1
fi

python3 - <<'PY'
import json, os, urllib.request
path = os.path.expanduser('~/.config/opencode/opencode.json')
try:
    with open(path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
cfg.setdefault('$schema', 'https://opencode.ai/config.json')
cfg.setdefault('provider', {})

# Ambil daftar model gratis dari OpenRouter
with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=30) as r:
    data = json.load(r).get('data', [])
free = [m for m in data if m.get('id','').endswith(':free') or (m.get('pricing',{}).get('prompt') in ('0','0.0','0.00'))]
free_ids = sorted({m['id'] for m in free})

# Hapus provider openrouter lama (full catalog) agar tidak tampil
cfg['provider'].pop('openrouter', None)

models = {}
for mid in free_ids:
    orig = next((m for m in free if m['id'] == mid), {})
    ctx = orig.get('context_length') or 32768
    models[mid] = {
        'name': orig.get('name') or mid,
        'limit': {'context': ctx, 'output': min(8192, ctx)},
    }

cfg['provider']['openrouter-free'] = {
    'npm': '@ai-sdk/openai-compatible',
    'name': 'OpenRouter (free only)',
    'options': {
        'baseURL': 'https://openrouter.ai/api/v1',
        'apiKey': os.environ['OPENROUTER_API_KEY'],
    },
    'models': models,
}
tmp = path + '.tmp'
with open(tmp, 'w', encoding='utf-8') as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
os.replace(tmp, path)
print(f'OpenRouter free-only ditambahkan: {len(free_ids)} model gratis.')
PY

echo 'Cek: opencode models | grep openrouter-free'