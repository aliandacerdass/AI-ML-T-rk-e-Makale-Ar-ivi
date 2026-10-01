# CLAUDE.md — Günlük Prosedür

Bu repo, arXiv'deki **cs.LG** ve **cs.AI** makalelerinden öne çıkanları her gün Türkçe özetler. Her gün 06:00'da (Europe/Istanbul) çalışan bir Claude scheduled task bu dosyayı okur ve aşağıdaki adımları **sırayla** uygular. Bu dosya tek başına yeterli olacak şekilde yazılmıştır.

## Değişmez kurallar

1. **Uydurma yok.** Yalnızca `data/raw/` altındaki JSON'da bulunan makaleler özetlenir. Sayı, oran ve iddialar yalnızca o makalenin `abstract` alanında geçiyorsa yazılır. Emin değilsen yazma.
2. **Şeffaflık.** Her sayfada otomatik üretim uyarısı bulunur. Commit mesajları `🤖` ile başlar.
3. **Başarısızlık sessiz geçmez.** Veri alınamazsa özet üretilmez. Yalnızca `data/runs.csv`'ye hata satırı eklenir ve o commit'lenir.
4. Script'lerin çıktısını elle düzenleme (`data/raw/*.json` dahil). Deterministik işleri script'ler yapar, sen yalnızca seçer ve yazarsın.

## Adımlar

### 1. Tarih ve gün tipi

```bash
TZ=Europe/Istanbul date +%F   # TARIH
TZ=Europe/Istanbul date +%u   # 1-5 hafta içi, 6 cumartesi, 7 pazar
```

- Hafta içi → `tur: gunluk`, adım 2'den devam et.
- Cumartesi → `tur: haftalik`, adım 2'yi atla ("Hafta sonu" bölümüne bak).
- Pazar → `tur: derin`, adım 2'yi atla ("Hafta sonu" bölümüne bak).

**Tekrar çalışma kontrolü:** `data/runs.csv`'de bugünün tarihiyle `basarili` satırı varsa bugünün işi zaten yapılmıştır. Hiçbir dosyayı değiştirme, commit atma ve "bugün zaten tamamlanmış" diyerek dur.

Önce `pip install -q -r requirements.txt` çalıştır.

### 2. Adayları çek (yalnızca hafta içi)

```bash
python scripts/fetch_candidates.py --date $TARIH
```

Script, HF Daily Papers'ın bir önceki gününü çeker (06:00'da o günün listesi henüz dolmamış olur), arXiv API'den metadata'yı tamamlar ve `data/raw/$TARIH.json`'u yazar. Sıfırdan farklı kodla çıkarsa **bir kez** tekrar dene. Yine başarısızsa aşağıdaki yedek yolu dene.

**Yedek yol (WebFetch):** Ortam shell üzerinden arXiv/Hugging Face'e erişemiyorsa (bağlantı reddi, proxy hatası, DNS hatası):
1. WebFetch ile `https://huggingface.co/api/daily_papers?date=<önceki gün>` adresini çek. Her makale için `paper.id` ve `paper.upvotes` değerlerini al.
2. WebFetch ile `https://export.arxiv.org/api/query?id_list=<virgülle ayrılmış ID'ler>&max_results=50` adresini çek. Her makale için başlık, yazarlar, kategoriler ve abstract'ı al.
3. Kategorilerinde `cs.LG` veya `cs.AI` olmayanları ve `data/seen.json`'daki ID'leri çıkar.
4. Sonucu script'in ürettiği formatla **birebir aynı** şekilde `data/raw/$TARIH.json`'a yaz: `run_date`, `hf_dates`, `sources` (`["huggingface", "webfetch"]`), `fetched_at`, `papers` (her biri: `arxiv_id, title, authors, categories, abstract, hf_upvotes, url, source`). Değerleri WebFetch çıktısından aynen aktar, hiçbir alanı tahminle doldurma.

Yedek yol da başarısızsa hata mesajını not al ve **adım 8'e geç**.

### 3. Makale seç

`data/raw/$TARIH.json` içindeki `papers` listesinden **3-5 makale** seç:

- `hf_upvotes` yüksek olanlar önceliklidir.
- Aynı alt konudan (ör. LLM ajanları, difüzyon, RL ile ince ayar) **en fazla 2** makale seç. Çeşitlilik hedefle.
- `data/seen.json`'daki ID'ler zaten filtrelenmiştir. Yine de kontrol et.
- Uygun aday 3'ten azsa listede `source: arxiv-rss` olanlardan kendi değerlendirmenle tamamla ve bunu sayfada belirt (ör. "Bugün HF'de yeterli aday olmadığı için 1 makale arXiv listesinden seçildi.").

### 4. Günlük dosyayı yaz

Yol: `ozetler/YYYY/MM/YYYY-MM-DD.md`. Şablon: `templates/gun.md`. Frontmatter'daki `kaynak` alanına JSON'daki `sources` değerlerini `+` ile birleştirerek yaz (ör. `huggingface+arxiv`; RSS kullanıldıysa `huggingface+arxiv-rss`).

Her makale için şu bölümler **zorunludur**, bu sırayla: **Tek cümlede**, **Problem**, **Yöntem**, **Sonuçlar**, **Neden önemli**, **Terimler**.

Yazım kuralları:
- Türkçe, sade, bir lisans öğrencisinin anlayacağı düzeyde.
- Makale başına yaklaşık 120-200 kelime.
- Abstract'tan cümle kopyalama. Anlayıp yeniden yaz.
- Teknik terim ilk geçtiğinde Türkçe karşılığı + parantez içinde İngilizcesi: ince ayar (*fine-tuning*). Karşılıkları `SOZLUK.md`'den al. Sözlükte olmayan yeni bir terim kullanırsan sözlüğe alfabetik sırayla ekle.
- **Sonuçlar** bölümünde yalnızca abstract'ta geçen sayıları kullan. Abstract sayı vermiyorsa sonucu niteliksel anlat.
- Yazarlar: ilk 3 yazar, fazlası varsa "ve diğerleri". **Kategori:** makalenin cs.LG/cs.AI kategorisi (ikisi de varsa ikisi). **HF oyu:** `hf_upvotes` (null ise "—").
- Başlık satırındaki tarih Türkçe yazılır: `# 1 Ekim 2026 — Günün AI/ML Makaleleri`.

### 5. Kayıtları güncelle

- `data/seen.json`: seçilen arXiv ID'lerini listeye ekle.
- `data/papers.csv`: her makale için bir satır: `arxiv_id,tarih,title,categories,hf_upvotes,dosya`. `categories` alanında `;` ile ayır, başlığı CSV kurallarına göre tırnakla. `dosya`, özet dosyasının repo köküne göre yoludur.

Python ile yap (ör. `csv` ve `json` modülleri). Elle yazınca biçim bozulabilir.

### 6. Doğrula

```bash
python scripts/validate_day.py ozetler/YYYY/MM/YYYY-MM-DD.md
```

Hata varsa dosyayı düzelt ve tekrar çalıştır. En fazla **2 düzeltme denemesi**. Hâlâ hata varsa özet dosyasını ve adım 5'teki değişiklikleri geri al, hatayı not al, adım 8'e geç.

### 7. İndeksi güncelle

```bash
python scripts/build_index.py
```

README'deki son 7 gün bölümünü ve `ARSIV.md`'yi yeniden üretir.

### 8. Çalışma kaydı

`data/runs.csv`'ye bir satır ekle: `tarih,durum,makale_sayisi,hata`

- Başarılı: `2026-10-01,basarili,4,`
- Başarısız: `2026-10-01,hata,0,"<kısa hata mesajı>"`

### 9. Commit ve push

```bash
git add -A
git -c user.name="Ali Andac Erdas" -c user.email="226695382+aliandacerdass@users.noreply.github.com" \
    commit -m "🤖 günlük: 2026-10-01 (4 makale)"
git push origin main
```

**Commit kimliği:** Commit'i her zaman yukarıdaki `-c user.name` / `-c user.email` ile at. Commit mesajına `Co-Authored-By`, `Claude-Session` veya benzeri bir trailer **ekleme**. Mesaj yalnızca aşağıdaki formattaki tek satırdır. Otomasyon zaten `🤖` öneki ve README ile açıkça belirtiliyor.

Mesaj formatları:
- Hafta içi: `🤖 günlük: YYYY-MM-DD (N makale)`
- Cumartesi: `🤖 haftalık: YYYY-MM-DD`
- Pazar: `🤖 derin okuma: YYYY-MM-DD`
- Başarısız gün: `🤖 çalışma kaydı: YYYY-MM-DD (veri alınamadı)`

Push reddedilirse `git pull --rebase origin main` yapıp tekrar push'la.

## Hafta sonu

arXiv cumartesi ve pazar duyuru yapmaz. Bu günlerde yeni veri çekilmez. Yalnızca **bu hafta (pazartesi-cuma) zaten özetlenmiş** makaleler kullanılır (`data/papers.csv`). Dosyadaki her arXiv ID'si `papers.csv`'de bulunmalıdır. Frontmatter'da `kaynak: papers.csv` yaz.

**Cumartesi — Haftanın özeti** (`tur: haftalik`):
- Başlık: `# 3 Ekim 2026 — Haftanın Özeti`
- Otomatik üretim uyarısı.
- `## Haftanın eğilimi`: hafta içi özetlerden çıkan genel tema (1-2 paragraf).
- Haftanın en önemli 3 makalesi: her biri için kısa bölüm (`## 1. <başlık>`, arXiv satırı, **Tek cümlede**, **Neden önemli**) ve o günün özet dosyasına link.
- Hafta içi hiç özet yoksa haftalık dosya yazma, adım 8'de `durum: atlandi` yaz.

**Pazar — Derin okuma** (`tur: derin`):
- Başlık: `# 4 Ekim 2026 — Derin Okuma: <makale başlığı>`
- Otomatik üretim uyarısı.
- Haftadan tek makale. Başlığın altında günlük formattaki `**arXiv:** ...` satırı, `makale_sayisi: 1`. Günlük formattaki tüm zorunlu bölümler + `## Arka plan` (konuyu anlamak için gereken temel bilgi) ve `## Sınırlılıklar ve açık sorular`. Yaklaşık 500-800 kelime.
- Ayrıntı için makalenin HTML sürümüne (`https://arxiv.org/html/<id>`) erişebiliyorsan kullan. Erişemiyorsan yalnızca abstract'a dayan ve bunu belirt. Sayı kuralı aynıdır: yalnızca kaynakta gördüğünü yaz.

Hafta sonu dosyaları da adım 5'i atlar (yeni makale yok), adım 6-9'u uygular.
