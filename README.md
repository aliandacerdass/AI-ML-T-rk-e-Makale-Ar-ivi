> 🤖 **Bu repo Claude (Anthropic) tarafından her gün otomatik olarak güncellenir.** Özetler bir yapay zekâ tarafından yazılır, insan tarafından tek tek kontrol edilmez.

# AI/ML Türkçe Makale Arşivi

arXiv'in **cs.LG** (makine öğrenmesi) ve **cs.AI** (yapay zekâ) kategorilerinden her gün öne çıkan **3-5 makalenin Türkçe özeti**. Her sabah 06:00'da (Türkiye saati) yeni sayfa eklenir.

## Son 7 gün

<!-- SON7 -->
Henüz özet yok.

Son başarılı çalışma: **—** · Tüm günler: [ARSIV.md](ARSIV.md)
<!-- /SON7 -->

## Nasıl çalışır?

```
Hugging Face Daily Papers ──┐
  (topluluk oyları)          ├─► aday listesi ─► seçim ─► Türkçe özet ─► doğrulama ─► commit
arXiv API / RSS ────────────┘   (script)        (Claude)  (Claude)      (script)
  (kategori, abstract)
```

1. **Veri çekme** (`scripts/fetch_candidates.py`): Hugging Face'te bir önceki gün en çok oy alan makaleler arXiv'den tamamlanır, cs.LG/cs.AI dışındakiler ve daha önce özetlenenler elenir. Sonuç `data/raw/` altına kaydedilir.
2. **Seçim ve özet** (Claude): Oylara ve konu çeşitliliğine göre 3-5 makale seçilir, her biri için *Problem → Yöntem → Sonuçlar → Neden önemli* yapısında özet yazılır. Terimler [`SOZLUK.md`](SOZLUK.md)'ye göre tutarlı çevrilir.
3. **Doğrulama** (`scripts/validate_day.py`): Sayfadaki her arXiv ID'si o günün ham verisinde var mı, zorunlu bölümler tam mı diye kontrol edilir. Uydurma makale bu adımda yakalanır.
4. **Kayıt**: Her çalışma, başarısız olsa bile `data/runs.csv`'ye yazılır. Veri alınamayan gün sahte içerik üretilmez.

Hafta sonu arXiv duyuru yapmaz: **cumartesi** haftanın özeti, **pazar** haftadan tek bir makalenin derin okuması yayınlanır.

Günlük görevin adım adım prosedürü [`CLAUDE.md`](CLAUDE.md)'de, proje planı [`PLAN.md`](PLAN.md)'de.

## Klasörler

| Yol | İçerik |
|---|---|
| [`ozetler/`](ozetler/) | Günlük özetler (`YYYY/MM/YYYY-MM-DD.md`) |
| [`ARSIV.md`](ARSIV.md) | Tüm günlerin ay ay indeksi |
| [`data/papers.csv`](data/papers.csv) | Özetlenen tüm makalelerin metadata'sı |
| [`data/raw/`](data/raw/) | Her günün ham aday listesi |
| [`data/runs.csv`](data/runs.csv) | Çalışma kayıtları (tarih, durum, hata) |

## Sınırlamalar

- Özetler yalnızca makalelerin **abstract'larına** dayanır. Makalenin tamamı okunmaz.
- Yapay zekâ özetleri **hata yapabilir**: yanlış yorum, eksik bağlam, kusurlu çeviri. Esas olan orijinal makaledir. Bir şeye dayanmadan önce makalenin kendisini okuyun.
- "Öne çıkan" seçimi Hugging Face topluluk oylarına dayanır. Bu, alanın tamamını temsil etmez.

## Lisans

- **Kod** (`scripts/`): [MIT](LICENSE)
- **Özet metinleri** (`ozetler/`, `SOZLUK.md`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.tr)
- Orijinal makalelerin hakları yazarlarına ve kendi lisanslarına aittir. Bu repo yalnızca özet ve bağlantı sunar.
