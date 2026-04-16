import requests
import re
import os
import random
import time
import pandas as pd
import trafilatura
import unicodedata
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==========================================
# 1. KONFIGURASI GLOBAL (100M TOKENS EDITION)
# ==========================================
SITEMAP_SOURCES = [
    "https://www.kompas.com/sitemap.xml",
    "https://www.detik.com/sitemap.xml",
    "https://www.cnnindonesia.com/sitemap.xml",
    "https://tirto.id/sitemap.xml",
    "https://www.suara.com/sitemap.xml",
    "https://www.liputan6.com/sitemap.xml",
    "https://www.tribunnews.com/sitemap.xml",
    "https://www.jawapos.com/sitemap.xml",
    "https://www.pikiran-rakyat.com/sitemap.xml",
    "https://www.sindonews.com/sitemap.xml",
    "https://republika.co.id/sitemap.xml",
    "https://www.antaranews.com/sitemap.xml",
    "https://www.merdeka.com/sitemap.xml",
    "https://www.viva.co.id/sitemap.xml",
]

YEARS_TO_DIG = [str(y) for y in range(2014, 2027)]
MONTHS = [str(i).zfill(2) for i in range(1, 13)]

URL_DB_FILE = "url_mentah_100M.txt"
FINAL_DATASET = "dataset_pendidikan_100M.csv"
LEDGER_FILE = "riwayat_sukses.txt"

MAX_THREADS = 20
MAX_FOLDERS_PER_SITE = 6000

# HANYA akan mengambil artikel yang mengandung minimal salah satu kata ini
TARGET_KEYWORDS = [
    # 1. Core Sekolah Rakyat & Identitas Sekolah Menengah
    "sekolah rakyat", "srma", " sma ", " smp ", "sekolah menengah",
    "dinas pendidikan", "kemdikbud", "kemendikbudristek", "kementerian pendidikan",
    
    # 2. Sistem, Kebijakan & Struktur SMA
    "sistem pendidikan sma", "kebijakan pendidikan sma", "aturan sekolah sma",
    "akreditasi sma", "standar kelulusan sma", "standar kompetensi lulusan",
    "penjurusan sma", "peminatan sma", "lintas minat sma", "jurusan ipa ips", 
    "fase e sma", "fase f sma", "manajemen sekolah sma", "komite sekolah sma",
    "kepala sekolah sma", "waka kurikulum", "waka kesiswaan", "tata tertib sma",
    "mgmp sma", "musyawarah guru mata pelajaran", "kalender akademik sma",
    
    # 3. Kurikulum, Program & Pedoman Sekolah
    "kurikulum merdeka", "merdeka belajar", "profil pelajar pancasila",
    "sekolah penggerak", "guru penggerak", "capaian pembelajaran",
    "silabus sekolah", "rpp guru", "rencana pelaksanaan pembelajaran", "k-13",
    "modul ajar", "buku pedoman guru", "buku siswa", "buku teks", "ktsp", 
    "kurikulum 2013", "kurikulum 2013 revisi", "kurikulum 2013 edisi revisi",
    
    # 4. Pendanaan, Bantuan & Penerimaan 
    "dana bos", "bantuan operasional sekolah", "kip sekolah", 
    "pip kemdikbud", "program indonesia pintar", "ppdb sma", "ppdb smp", 
    "penerimaan peserta didik baru", "jalur zonasi sekolah", "zonasi sma",
    
    # 5. Ujian, Evaluasi & Rapor 
    "ujian nasional", "unbk", "ujian sekolah", "ujian akhir sekolah", 
    "try out sma", "try out smp", "kisi-kisi ujian", "soal latihan", 
    "ulangan harian", "penilaian tengah semester", "pts sma", "pts smp", 
    "penilaian akhir semester", "pas sma", "pas smp", "rapor siswa", 
    "kelulusan sekolah", "asesmen nasional", "anbk", 
    
    # 6. Ekosistem Siswa, Organisasi & Prestasi
    "siswa sma", "siswa smp", "guru sma", "guru smp", "pelajar sma", "pelajar smp",
    "anak sekolah", "osis", "ekstrakurikuler", "mpls", "mos sekolah",
    "pramuka sekolah", "paskibra sekolah", "paskibraka", "pmr sekolah", 
    "guru bk", "bimbingan konseling", "olimpiade sains", "osn", 
    "fls2n", "o2sn", "lomba cerdas cermat",
    
    # 7. Mata Pelajaran (Diikat agar tidak nyasar)
    "pelajaran matematika", "materi matematika", "soal matematika sma",
    "pelajaran fisika", "materi fisika", "praktikum fisika",
    "pelajaran kimia", "materi kimia", "praktikum kimia",
    "pelajaran biologi", "materi biologi", "praktikum biologi",
    "pelajaran ipa", "materi ipa",
    "pelajaran ips", "materi ips",
    "pelajaran sejarah", "materi sejarah",
    "pelajaran ekonomi", "materi ekonomi",
    "pelajaran sosiologi", "materi sosiologi", "materi antropologi",
    "pelajaran geografi", "materi geografi",
    "pelajaran bahasa", "materi bahasa", "pelajaran sastra",
    "pendidikan pancasila", "pelajaran pkn", "materi pkn",
    "pelajaran pjok", "pendidikan jasmani", "pelajaran seni",
    "pelajaran informatika", "materi tik", "prakarya", 
    "kewirausahaan sekolah", "ai untuk pendidikan", "literasi sekolah", "numerasi sekolah"
]

# ==========================================
# 2. UTILITY & THE SUPER SCRUB
# ==========================================
def clean_url(url):
    if not url: return ""
    return re.sub(r"<!\[CDATA\[|\]\]>", "", url).strip()

def get_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.google.com/",
    }

def clean_for_rag(text):
    if not text: return ""
    
    # 1. Normalisasi Unicode 
    text = unicodedata.normalize("NFKD", text)
    text = text.encode('ascii', 'ignore').decode('utf-8') 
    
    # 2. Pembersihan Boilerplate Berita 
    text = re.sub(r"(?i)Artikel ini merupakan bagian dari.*", "", text, flags=re.DOTALL)
    text = re.sub(r"(?i)(KOMPAS\.com|detikcom|CNN Indonesia|Tribunnews|JawaPos|Sindonews|Suara|Republika|Antara|Merdeka|VIVA) berkomitmen.*", "", text, flags=re.DOTALL)
    text = re.sub(r"(?i)Demikian informasi.*?(?=\n|$)", "", text)
    text = re.sub(r"(?i)baca juga:.*?(?=\n|$)", "", text)
    text = re.sub(r"(?i)^[a-zA-Z0-9.-]+\.(com|co\.id|ac\.id|id)\s+Ilustrasi.*?(?=\n|$)", "", text, flags=re.MULTILINE)
    text = re.sub(r"(?i)^.{0,80}?(kompas\.com|detikcom|tribunnews|cnn indonesia|suara\.com|liputan6\.com|tirto\.id|jawapos\.com|pikiran-rakyat\.com|republika\.co\.id|antaranews\.com|merdeka\.com|viva\.co\.id)[^a-zA-Z0-9]*-\s*", "", text)
    text = re.sub(r"(?i)^KOMPAS\.com\s*–\s*", "", text)
    
    # 3. Menghapus URL Liar & Email di dalam teks
    text = re.sub(r"http[s]?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    text = re.sub(r"\S+@\S+", "", text)
    
    # 4. Merapikan Noise Karakter 
    text = re.sub(r'\s+', ' ', text) 
    text = re.sub(r'([.?!])\s*([A-Z])', r'\1\n\n\2', text) 
    text = re.sub(r'[,;:]\s*[,;:]+', ',', text) 
    
    return text.strip()

# ==========================================
# 3. BUKU BESAR (THE LEDGER)
# ==========================================
def load_ledger():
    if not os.path.exists(LEDGER_FILE): return set()
    with open(LEDGER_FILE, "r", encoding="utf-8") as f:
        return set([line.strip() for line in f if line.strip()])

# ==========================================
# 4. RADAR & DISCOVERY
# ==========================================
def fetch_sub_sitemaps(main_url):
    print(f"\n🕵️ Menganalisis jaringan arsip di: {main_url}")
    all_subs = []
    try:
        res = requests.get(main_url, headers=get_headers(), timeout=20)
        raw_locs = re.findall(r"<loc>(.*?)</loc>", res.text)
        all_subs.extend([clean_url(loc) for loc in raw_locs if ".xml" in loc.lower()])
    except: pass

    base = main_url.replace("sitemap.xml", "")
    for y in YEARS_TO_DIG:
        for m in MONTHS:
            all_subs.append(f"{base}sitemap_{y}_{m}.xml")
            all_subs.append(f"{base}sitemap-{y}-{m}.xml")
            all_subs.append(f"{base}sitemap/archive/{y}/{m}.xml")
    return list(set(all_subs))

def fetch_article_links(sub_url, scraped_ledger):
    try:
        res = requests.get(sub_url, headers=get_headers(), timeout=15)
        raw_locs = re.findall(r"<loc>(.*?)</loc>", res.text)

        filtered_links = []
        for loc in raw_locs:
            link = clean_url(loc)
            if link and link not in scraped_ledger:
                filtered_links.append(link)
        return list(set(filtered_links))
    except:
        return []

# ==========================================
# 5. CONTENT HARVESTING (SMART SCORING EDITION)
# ==========================================
def harvest_content(url):
    try:
        session = requests.Session()
        res = session.get(url, headers=get_headers(), timeout=20)

        if res.status_code != 200: return None

        html_content = res.text
        soup = BeautifulSoup(html_content, "html.parser")

        # 1. Ekstraksi Judul yang lebih aman untuk Pylance
        h1_tag = soup.find("h1")
        title = h1_tag.text.strip() if h1_tag else "Tanpa Judul"

        # 2. Ekstraksi Tanggal pakai parameter attrs={}
        meta_date = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "pubdate"})
        
        # 3. Validasi isi content sebelum dipotong [:10]
        if meta_date and meta_date.get("content"):
            date = str(meta_date.get("content"))[:10]
        else:
            date = "Tidak diketahui"

        raw_text = trafilatura.extract(html_content, include_comments=False, include_tables=False, include_links=False)
        if not raw_text:
            paragraphs = soup.find_all("p")
            raw_text = "\n\n".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 30])

        if raw_text:
            clean_text = clean_for_rag(raw_text)
            if len(clean_text) > 300:
                text_to_check = (title + " " + clean_text).lower()
                
                # 🔥 THE NEW SCORING SYSTEM 🔥
                education_score = 0
                matched_keywords = set()

                for w in TARGET_KEYWORDS:
                    keyword = w.strip()
                    # Hitung frekuensi kemunculan setiap kata kunci di dalam teks
                    matches = re.findall(rf"\b{re.escape(keyword)}\b", text_to_check)
                    if matches:
                        education_score += len(matches)
                        matched_keywords.add(keyword)

                # SYARAT LOLOS SUPER KETAT:
                if education_score >= 4 or len(matched_keywords) >= 3:
                    return {
                        "metadata_url": url,
                        "metadata_title": title,
                        "metadata_date": date,
                        "content": clean_text,
                    }
                else:
                    return "SKIP_NOT_EDUCATION" 
    except Exception:
        pass
    return None

# ==========================================
# 6. PIPELINE UTAMA
# ==========================================
def run_full_pipeline():
    print("=" * 60)
    print("🚀 THE NEWS HARVESTER V5.1 (THE 100M JUGGERNAUT)")
    print("=" * 60)

    scraped_ledger = load_ledger()
    print(f"🧠 Memori Aktif: Mengingat {len(scraped_ledger)} artikel yang sudah sukses.")

    print("\n[FASE 1] Menyebar Radar Tanpa Batas ke 14 Portal Berita...")
    total_found = 0

    for main_site in SITEMAP_SOURCES:
        sub_sitemaps = fetch_sub_sitemaps(main_site)
        count_sub = 0

        for sub in sub_sitemaps:
            # 🔥 INDIKATOR PROGRESS (Anti-Silent) 🔥
            print(f"   🔍 Cek radar: {sub.split('/')[-1]}", end=" ")
            
            links = fetch_article_links(sub, scraped_ledger)
            if links:
                total_found += len(links)
                with open(URL_DB_FILE, "a", encoding="utf-8") as f:
                    for l in links:
                        f.write(l + "\n")
                # Beri tahu kalau sukses
                print(f"✅ DAPAT {len(links)} URL!")
            else:
                # Beri tahu kalau zonk/kosong
                print("❌ Kosong/Lewat")

            count_sub += 1
            if count_sub >= MAX_FOLDERS_PER_SITE:
                break
            time.sleep(random.uniform(0.5, 1.0))

    if not os.path.exists(URL_DB_FILE):
        return print("\n❌ Gagal: Tidak ada URL baru yang ditemukan.")

    with open(URL_DB_FILE, "r", encoding="utf-8") as f:
        urls_to_scrape = list(set([line.strip() for line in f if line.strip() and line.strip() not in scraped_ledger]))

    print(f"\n[FASE 2] Membedah {len(urls_to_scrape)} URL Target (Mencari Harta Karun Pendidikan)...")

    final_dataset = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = {executor.submit(harvest_content, url): url for url in urls_to_scrape}

        counter = 0
        with open(LEDGER_FILE, "a", encoding="utf-8") as ledger_file:
            for future in as_completed(futures):
                url_sukses = futures[future]
                try:
                    result = future.result()
                    
                    if result is not None:
                        ledger_file.write(url_sukses + "\n")
                        ledger_file.flush()
                        
                        if result != "SKIP_NOT_EDUCATION":
                            final_dataset.append(result)
                            counter += 1

                            if counter % 100 == 0:
                                print(f"   📥 PROGRESS: {counter} artikel pendidikan diamankan...")
                                df_new = pd.DataFrame(final_dataset)
                                df_new.to_csv(
                                    FINAL_DATASET, mode="a", header=not os.path.exists(FINAL_DATASET),
                                    index=False, encoding="utf-8",
                                )
                                final_dataset = []
                except:
                    pass

    if final_dataset:
        pd.DataFrame(final_dataset).to_csv(FINAL_DATASET, mode="a", header=not os.path.exists(FINAL_DATASET), index=False, encoding="utf-8")

    if os.path.exists(URL_DB_FILE):
        os.remove(URL_DB_FILE)

    print("\n" + "=" * 60)
    print("🏆 SESI PANEN SELESAI!")
    print(f"📂 Total artikel pendidikan MURNI: {counter}")
    print("=" * 60)

if __name__ == "__main__":
    run_full_pipeline()