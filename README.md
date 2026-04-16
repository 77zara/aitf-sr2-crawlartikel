# 🚀 AI Sekolah Rakyat - Mass Article Crawler V5.1

Script ini berfungsi untuk memanen jutaan data teks (100M Tokens Target) dari 14 portal berita nasional Indonesia pada rentang tahun 2014-2027. Data akan difilter secara ketat menggunakan *Smart Scoring* khusus untuk ekosistem pendidikan (K-12/SMA).

## 🛠️ Cara Penggunaan di Server
1. Clone repository ini:
   `git clone https://github.com/77zara/aitf-sr2-crawlartikel.git`
2. Masuk ke folder:
   `cd aitf-sr2-crawlartikel`
3. Install dependencies:
   `pip install requests pandas trafilatura beautifulsoup4`
4. Jalankan mesin:
   `python KODE_MASIF_HARVEST.py`

**⚠️ PERHATIAN:** Jangan hapus file `riwayat_sukses.txt` karena file tersebut adalah "buku besar" agar server tidak mendownload ulang artikel yang sudah pernah diambil sebelumnya.
