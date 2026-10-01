# Proje Planı: arXiv Türkçe Günlük

Her gün arXiv'deki **cs.LG** ve **cs.AI** kategorilerinden öne çıkan 3-5 makaleyi seçip Türkçe özetleyen ve GitHub'a commit'leyen, Claude scheduled task ile çalışan otomatik bir repo.

> Bu dosyayı repo köküne koy ve Claude Code'a şunu söyle:
> **"PLAN.md'yi oku ve Faz 1'den başlayarak uygula. Her fazın sonunda kabul kriterlerini kontrol et ve bana rapor ver, onayım olmadan bir sonraki faza geçme."**

---

## 1. Temel ilkeler

1. **Şeffaflık.** README'nin ilk satırı repo'nun Claude tarafından otomatik güncellendiğini söyler. Commit mesajları `🤖` ile başlar. Hiçbir şey insan yazmış gibi sunulmaz.
2. **Uydurma yok.** Her özet, o gün çekilmiş gerçek bir arXiv kaydına dayanır. Sayılar ve iddialar yalnızca abstract'ta (veya erişilebiliyorsa makalenin HTML sürümünde) geçiyorsa yazılır.
3. **Deterministik işler script'te, yorum işi Claude'da.** Veri çekme, filtreleme, doğrulama ve indeksleme Python script'leriyle yapılır. Claude yalnızca seçim ve özetleme yapar.
4. **Başarısızlık sessiz geçmez.** Veri çekilemezse sahte içerik üretilmez. Hata `data/runs.csv`'ye kaydedilir.

---

## 2. Repo yapısı

```
AI-ML-T-rk-e-Makale-Ar-ivi/   (plan adı: arxiv-turkce-gunluk)
├── README.md                  # Tanıtım + son 7 günün linkleri (otomatik güncellenir)
├── CLAUDE.md                  # Günlük görevin adım adım prosedürü (scheduled task bunu okur)
├── PLAN.md                    # Bu dosya
├── SOZLUK.md                  # Terim sözlüğü (İngilizce → Türkçe), tutarlılık için
├── requirements.txt
├── templates/
│   └── gun.md                 # Günlük özet dosyasının şablonu
├── scripts/
│   ├── fetch_candidates.py    # Aday makaleleri çeker → data/raw/YYYY-MM-DD.json
│   ├── validate_day.py        # Günlük dosyayı doğrular
│   └── build_index.py         # README'deki "son 7 gün" + arşiv indeksini üretir
├── ozetler/
│   └── 2026/
│       └── 10/
│           └── 2026-10-01.md  # Günlük özet
├── data/
│   ├── raw/2026-10-01.json    # O günün ham aday listesi (zamanla veri setine dönüşür)
│   ├── papers.csv             # Özetlenen tüm makalelerin metadata'sı
│   ├── seen.json              # Daha önce özetlenen arXiv ID'leri (tekrarı önler)
│   └── runs.csv               # Her çalışmanın tarihi, durumu, hata mesajı
└── ARSIV.md                   # Tüm günlerin indeksi (otomatik)
```

---

## 3. Veri kaynakları ve seçim mantığı

**"Öne çıkan" nasıl belirlenir:** arXiv'e günde yüzlerce makale düşer. Ham listeden seçim yapmak keyfi olur. Bu yüzden iki kaynak birlikte kullanılır:

| Öncelik | Kaynak | Ne sağlar |
|---|---|---|
| 1 | Hugging Face Daily Papers API (`https://huggingface.co/api/daily_papers?date=YYYY-MM-DD`) | Topluluk oyları (upvote) ile popülerlik sinyali |
| 2 | arXiv API (`http://export.arxiv.org/api/query`) veya RSS (`https://rss.arxiv.org/rss/cs.LG`, `cs.AI`) | Kategori bilgisi, tam abstract, yazarlar; HF boş kalırsa yedek kaynak |

**Filtre:** Makalenin kategorilerinden en az biri `cs.LG` veya `cs.AI` olmalı.

**Seçim kuralları (Claude uygular):**
- HF upvote sayısı yüksek olanlar öncelikli.
- Aynı alt konudan (ör. üç tane LLM ajan makalesi) en fazla 2 makale. Çeşitlilik hedeflenir.
- `data/seen.json`'daki ID'ler atlanır.
- 3'ten az uygun aday varsa: arXiv listesinden Claude kendi değerlendirmesiyle tamamlar ve dosyada bunu belirtir.

**Hafta sonu:** arXiv cumartesi ve pazar duyuru yapmaz. Bu günlerde:
- **Cumartesi:** "Haftanın özeti": hafta içinde özetlenenlerden en önemli 3'ü + haftanın genel eğilimi.
- **Pazar:** "Derin okuma": haftadan tek bir makale, daha uzun ve detaylı anlatım.

---

## 4. Günlük dosya formatı

`templates/gun.md`:

```markdown
---
tarih: 2026-10-01
tur: gunluk            # gunluk | haftalik | derin
makale_sayisi: 4
kaynak: huggingface+arxiv
---

# 1 Ekim 2026 — Günün AI/ML Makaleleri

> 🤖 Bu sayfa Claude tarafından otomatik hazırlanmıştır. Özetler makalelerin abstract'larına dayanır; ayrıntı için orijinal makaleyi okuyun.

## 1. <Orijinal makale başlığı>

**arXiv:** [2510.xxxxx](https://arxiv.org/abs/2510.xxxxx) · **Kategori:** cs.LG · **Yazarlar:** A, B, C ve diğerleri · **HF oyu:** 123

**Tek cümlede:** ...

**Problem:** ...

**Yöntem:** ...

**Sonuçlar:** ... (yalnızca abstract'ta geçen sayılar)

**Neden önemli:** ...

**Terimler:** ince ayar (*fine-tuning*), çıkarım (*inference*)

---
## 2. ...
```

**Yazım kuralları:**
- Türkçe, sade, bir lisans öğrencisinin anlayacağı düzeyde.
- Teknik terim ilk geçtiğinde Türkçe karşılığı + parantez içinde İngilizcesi. Karşılıklar `SOZLUK.md`'den alınır. Yeni terim çıkarsa sözlüğe eklenir.
- Abstract'tan cümle kopyalanmaz, yeniden yazılır.
- Her makale bölümü yaklaşık 120-200 kelime.

---

## 5. Fazlar

### Faz 1 — İskelet ve veri çekme
- Klasör yapısını, `requirements.txt`'i (yalnızca gerekli paketler: `requests`, `feedparser` vb.) ve boş `data/` dosyalarını oluştur.
- `scripts/fetch_candidates.py`:
  - Argüman: `--date YYYY-MM-DD` (varsayılan: bugün, Europe/Istanbul).
  - HF Daily Papers'ı çeker; her makale için arXiv API'den kategori, abstract ve yazarları tamamlar.
  - cs.LG / cs.AI filtresini ve `seen.json` filtresini uygular.
  - Çıktı: `data/raw/YYYY-MM-DD.json` (alanlar: `arxiv_id, title, authors, categories, abstract, hf_upvotes, url`).
  - arXiv API'ye istekler arasında en az 3 saniye bekler (arXiv'in kuralı).
  - Ağ hatasında anlamlı hata mesajıyla sıfırdan farklı kodla çıkar.
- **Endpoint doğrulaması (2026-10-01):** HF API aynı şekilde çalışıyor. arXiv API `http://` → `https://` yönlendiriyor; script doğrudan `https://export.arxiv.org` kullanır. arXiv API yavaş (tek istek ~27 sn) ve art arda isteklerde `Rate exceeded`/503 dönebiliyor → 90 sn timeout, 25'lik gruplar, artan beklemeyle 3 deneme.
- **Önce endpoint'leri doğrula:** HF ve arXiv uç noktalarının şu an hâlâ bu şekilde çalıştığını gerçek bir istekle test et. Değiştiyse planı güncelle ve bana bildir.

**Kabul kriteri:** `python scripts/fetch_candidates.py --date <dünün tarihi>` çalışıyor ve en az 5 aday içeren geçerli bir JSON üretiyor.

### Faz 2 — Şablon, sözlük ve günlük prosedür
- `templates/gun.md`'yi bölüm 4'e göre oluştur.
- `SOZLUK.md`'yi 30-40 temel terimle başlat (fine-tuning, inference, transformer, attention, benchmark, reinforcement learning, diffusion, embedding, agent, retrieval vb.).
- `CLAUDE.md`'yi yaz. Scheduled task her gün yalnızca bunu okuyacak, o yüzden tek başına anlaşılır olmalı:
  1. Bugünün tarihini Europe/Istanbul'a göre belirle; gün tipini (hafta içi / cumartesi / pazar) belirle.
  2. Hafta içiyse `fetch_candidates.py`'yi çalıştır. Hata verirse adım 8'e geç.
  3. `data/raw/<tarih>.json`'u oku, bölüm 3'teki kurallarla 3-5 makale seç.
  4. Şablona göre `ozetler/YYYY/MM/YYYY-MM-DD.md`'yi yaz. Gerekirse `SOZLUK.md`'yi güncelle.
  5. `seen.json` ve `papers.csv`'yi güncelle.
  6. `validate_day.py`'yi çalıştır; hata varsa düzelt ve tekrar çalıştır (en fazla 2 deneme).
  7. `build_index.py`'yi çalıştır.
  8. `runs.csv`'ye satır ekle (`tarih, durum, makale_sayisi, hata`).
  9. Commit at ve push'la. Mesaj formatı: `🤖 günlük: 2026-10-01 (4 makale)`. Başarısız günde: `🤖 çalışma kaydı: 2026-10-01 (veri alınamadı)`.
- Prosedürü bugünün (veya dünün) verisiyle **elle bir kez çalıştır.**

**Kabul kriteri:** Bir günlük dosya oluştu, okunuşu doğal Türkçe, tüm linkler gerçek arXiv sayfalarına gidiyor.

### Faz 3 — Doğrulama ve indeks
- `scripts/validate_day.py <dosya>` şunları kontrol eder:
  - Frontmatter alanları eksiksiz ve geçerli.
  - Makale sayısı 3-5 arası (hafta sonu türleri hariç).
  - **Dosyadaki her arXiv ID'si o günün `data/raw/` JSON'unda var.** (Uydurma makaleyi engelleyen ana kontrol.)
  - Her bölümde zorunlu başlıklar (Tek cümlede, Problem, Yöntem, Sonuçlar, Neden önemli) mevcut.
  - Otomatik üretim uyarısı sayfada var.
- `scripts/build_index.py`: README'deki `<!-- SON7 -->` işaretleri arasına son 7 günün linklerini, `ARSIV.md`'ye ay ay tüm günleri yazar.

**Kabul kriteri:** Kasıtlı bozulmuş bir dosyada (sahte arXiv ID, eksik başlık) validator hata veriyor; düzgün dosyada geçiyor.

### Faz 4 — README
- İlk satır: otomatik güncellendiğine dair açık ifade.
- Projenin ne olduğu, nasıl çalıştığı (kısa mimari: kaynaklar → seçim → özet → doğrulama → commit).
- Son 7 gün listesi (otomatik bölüm).
- Sınırlamalar: özetler abstract'a dayanır, hata yapabilir, orijinal makale esastır.
- Lisans: kod MIT, özet metinleri CC BY 4.0 önerisi. Orijinal makalelerin lisansları kendi sahiplerine aittir.

**Kabul kriteri:** Repoyu ilk kez gören biri 30 saniyede ne olduğunu ve otomatik olduğunu anlıyor.

### Faz 5 — Scheduled task
- Repoyu GitHub'a push'la.
- Scheduled task kur:
  - **Saat:** her gün 06:00 (Europe/Istanbul). arXiv duyuruları Türkiye saatiyle gece 03:00 civarı çıkar.
  - **06:00 notu:** O saatte HF Daily Papers'ın "bugün" listesi henüz dolmamış olur ve arXiv RSS 07:00 TR'de yenilenir. Bu yüzden `fetch_candidates.py` varsayılan olarak HF'nin **bir önceki gününü** (oylaması tamamlanmış liste) çeker; yetersizse en fazla 3 gün geriye bakar, sonra RSS'e düşer.
  - **Prompt:**
    > `aliandacerdass/AI-ML-T-rk-e-Makale-Ar-ivi` reposunda çalış. Repo kökündeki CLAUDE.md dosyasını oku ve oradaki günlük prosedürü baştan sona uygula. Uydurma içerik üretme; veri alınamazsa yalnızca çalışma kaydını commit'le.
  - Repo'ya **push** yetkisi olduğundan emin ol.
- Ağ erişimini kontrol et: scheduled task'ın ortamı arXiv ve Hugging Face'e shell üzerinden erişemeyebilir. Erişemiyorsa iki seçenek: (a) ortamın ağ izinlerine bu alan adlarını eklemek, (b) `CLAUDE.md`'ye yedek yol yazmak: script başarısız olursa Claude veriyi WebFetch ile çeker ve aynı JSON formatında `data/raw/`'a kaydeder.
- İlk otomatik çalışmayı manuel tetikle ve sonucu kontrol et.

**Kabul kriteri:** Scheduled task insan müdahalesi olmadan bir günlük dosya üretip push'ladı.

---

## 6. Riskler ve önlemler

| Risk | Önlem |
|---|---|
| Claude olmayan bir makale veya sayı uydurur | `validate_day.py` ID kontrolü + "yalnızca abstract'taki sayılar" kuralı |
| HF API değişir veya boş döner | arXiv RSS/API yedek kaynak |
| Aynı makale iki kez özetlenir | `seen.json` |
| Terimler günden güne farklı çevrilir | `SOZLUK.md` |
| Scheduled task ortamı dış sitelere erişemez | Faz 5'teki ağ kontrolü + WebFetch yedeği |
| Task sessizce çalışmayı bırakır | `runs.csv` + README'de "son başarılı çalışma" tarihi |

---

## 7. Sonraki adımlar (opsiyonel, şimdilik yapma)

- `data/papers.csv` birkaç ay dolunca: hangi konuların yükseldiğini gösteren bir trend analizi notebook'u. **Bu kısmı kendin yaz**, repodaki tek "senin" işin bu olur ve ondan bahsedebilirsin.
- Haftalık özetleri e-posta bülteni veya bir Telegram kanalına göndermek.
- GitHub Pages ile basit bir web arayüzü.
