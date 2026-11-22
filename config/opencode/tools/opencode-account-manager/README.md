# OpenCode Account Manager (lokal)

Dashboard web lokal untuk **melihat & mengganti akun aktif OpenCode Console**, plus **memo/catatan**, **status kuota free (manual)**, dan **backup data**.

## Fitur
- Menampilkan daftar akun OpenCode Console (label, email, status aktif, tipe)
- **Ganti akun aktif** dengan konfirmasi sebelum switch (`opencode auth switch opencode <id>`)
- **Filter status kuota** (Semua/Tersedia/Hampir habis/Habis/Tidak diketahui) + indikator visual pada kartu
- **Salin email / Salin ID** akun
- **Memo/Catatan Umum** — tersimpan otomatis, persisten antar sesi
- **Catatan per akun** — tersimpan otomatis
- **Status kuota free per akun (manual):** Tidak diketahui / Tersedia / Hampir habis / Habis + waktu terakhir dicek
- **Ekspor / Impor backup** (`data.json`) untuk memo/status
- **Multi-integrasi:** menampilkan & mengganti akun untuk semua integrasi yang tersimpan (opencode, freellmapi, google, nvidia) — bukan hanya OpenCode Console
- **Launcher otomatis:** `start.sh`/`start.bat` membuka dashboard, freellmapi (http://127.0.0.1:5173) dan openrouter.ai sekaligus

## Cara menjalankan

### Termux / Android (direktori ini)
```bash
bash ~/.config/opencode/tools/opencode-account-manager/start.sh
```
Lalu buka `http://127.0.0.1:8787`.

### Windows
1. Klik ganda `start.bat`, atau:
   ```powershell
   py C:\Users\<USERNAME>\.config\opencode\tools\opencode-account-manager\server.py
   ```
2. Buka: http://127.0.0.1:8787
3. Stop: `Ctrl+C`

## Lokasi data & database
- DB dibaca dari path dinamis `~/.local/share/opencode/opencode.db`
  (Windows: `C:\Users\<USERNAME>\.local\share\opencode\opencode.db`).
  Bila perlu, timpa dengan environment variable `OPENCODE_DB_PATH`.
- `data.json` dibuat otomatis di folder server saat memo/status pertama kali disimpan.
- Server membaca DB dalam mode **read-only** dan hanya mengambil field non-rahasia (id, label, email, org, tipe). Token/API key/password tidak pernah dikirim ke UI atau log.

## Catatan penting
- **Persisten:** memo/catatan/status disimpan ke `data.json`, tetap ada saat dibuka kembali.
- **Kuota free tidak dideteksi otomatis.** Status kuota adalah catatan manual; cek di https://opencode.ai/console lalu perbarui di dashboard.
- Setelah update file, **restart server** agar perubahan tampil.
- Server bind ke `127.0.0.1` saja. Jangan ekspos ke internet tanpa autentikasi.

## Troubleshooting
- **Port 8787 sudah dipakai:** `PORT=8888 python3 server.py` (Termux) atau `$env:PORT=8888; py server.py` (PowerShell).
- **`opencode` tidak dikenali:** pastikan OpenCode CLI terpasang dan ada di PATH.
- **Akun tidak muncul:** cek `OPENCODE_DB_PATH` / `~/.local/share/opencode/opencode.db` dan `opencode auth list`.
- **Perubahan UI tidak tampil:** restart server lalu hard refresh browser (Ctrl+F5).
- **Gagal ganti akun:** pastikan `opencode auth switch opencode <id>` bisa jalan di terminal; lihat pesan error di dashboard.
