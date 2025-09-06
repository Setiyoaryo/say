# Prerequisites

Linux/macOS/Windows

Python 3.10+

Git

Akses RPC chain Pharos (testnet/mainnet sesuai kebutuhan)

Paket dependensi akan terpasang lewat requirements.txt (termasuk dukungan SOCKS/HTTP proxy).

# 1) Clone repo
```bash
git clone https://github.com/Setiyoaryo/PharosAutoTask.git
cd PharosAutoTask
```
# 2) Buat & aktifkan virtual environment
```bash
python3 -m venv .venv
```
# Linux/macOS:
```bash
source .venv/bin/activate
```
# Windows (PowerShell):
```bash
 .\.venv\Scripts\Activate.ps1
```
# 3) Upgrade pip & install dependensi
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```
# Konfigurasi

# 1) wallets.txt (wajib, bisa multi-akun)

Buat file wallets.txt di root project. Satu akun per baris:

Format umum:

PRIVATE_KEY_HEX[,NAMA_AKUN][,PROXY_ID]


PRIVATE_KEY_HEX bisa dengan atau tanpa 0x (64 hex).

NAMA_AKUN opsional untuk label log.

PROXY_ID opsional, mengacu ke proxies.txt (lihat di bawah).

Contoh:

0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,akun-1,proxy-1
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,akun-2
0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc

# 2) proxies.txt (opsional)

Jika ingin pakai proxy per akun, buat proxies.txt. Bila file ini tidak ada, bot jalan normal tanpa proxy.

Format CSV per baris:

id,type,host,port[,username,password]


type: HTTP atau SOCKS5 (tanpa spasi).

username/password opsional.

Contoh:

proxy-1,HTTP,127.0.0.1,8080
proxy-2,SOCKS5,10.0.0.5,1080,user1,pass1


Lalu hubungkan akun ke proxy dengan menaruh proxy-1 atau proxy-2 di kolom ketiga wallets.txt.

# 3) runner_config.json (otomatis)

File runner_config.json dibuat otomatis saat Anda mengubah Set Default Config dari menu. File ini menyimpan:

Default amount (kecuali Program 2 “Add Domain” yang tidak punya amount),

Jumlah perulangan,

Jeda transaksi,

Pengaturan global (mis. all-in-one sleep 24h).

Anda bisa mengedit lewat menu; tidak wajib mengubah file ini manual.

# Menjalankan

Aktifkan venv (jika belum), lalu:

python main.py


# Menu utama:

All in One Run — Menjalankan P1→P6 sesuai default config, lalu tidur 24 jam dan mengulang (Ctrl+C untuk berhenti aman).

Set Default Config — Ubah konfigurasi default per program (jumlah & jeda; plus amount untuk semua program kecuali P2).

Individual Run — Jalankan satu program untuk satu/semua akun.

Keluar

# Logging:

Hijau = sukses, Merah = gagal/revert/error.

Saat jeda, ada progress bar agar mudah dipantau.

# Format File Contoh

.env

RPC_URL=https://testnet.dplabs-internal.com
CHAIN_ID=688688
EXPLORER_BASE=https://testnet.pharosscan.xyz


wallets.txt

0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa,utama,proxy-1
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb,backup


proxies.txt (opsional)

proxy-1,HTTP,127.0.0.1,8080
proxy-2,SOCKS5,10.0.0.5,1080,user1,pass1

# Tips & Troubleshooting

Revert deposit/trade: biasanya karena saldo/allowance kurang. Kurangi amount di “Set Default Config” atau isi saldo.

Program 2 (Add Domain): tidak memiliki pengaturan amount (hanya jumlah & jeda).

Proxy: pastikan type benar (HTTP/SOCKS5) dan kredensial valid. Jika tidak butuh proxy, jangan buat proxies.txt.

Keamanan: jangan commit wallets.txt, .env, atau file berisi kunci ke repository publik.

Uninstall venv (opsional)
deactivate  # jika masih aktif
rm -rf .venv
