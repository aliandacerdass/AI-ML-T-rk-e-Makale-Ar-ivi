"""Günlük özet dosyasını doğrular.

Kullanım: python scripts/validate_day.py ozetler/YYYY/MM/YYYY-MM-DD.md
Hata yoksa 0, varsa 1 ile çıkar ve hataları listeler.
"""
import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PAPERS_CSV = ROOT / "data" / "papers.csv"

WARNING = "🤖 Bu sayfa Claude tarafından otomatik hazırlanmıştır."
REQUIRED = {
    "gunluk": ["Tek cümlede", "Problem", "Yöntem", "Sonuçlar", "Neden önemli"],
    "haftalik": ["Tek cümlede", "Neden önemli"],
    "derin": ["Tek cümlede", "Problem", "Yöntem", "Sonuçlar", "Neden önemli"],
}
DERIN_HEADINGS = ["## Arka plan", "## Sınırlılıklar ve açık sorular"]
ID_RE = r"\d{4}\.\d{4,5}"


def parse_frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.split("#", 1)[0].strip()
    return fm, text[m.end():]


def validate(path):
    errors = []
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    if fm is None:
        return ["frontmatter bulunamadı (dosya '---' ile başlamalı)"]

    # Frontmatter
    for key in ("tarih", "tur", "makale_sayisi", "kaynak"):
        if not fm.get(key):
            errors.append(f"frontmatter: '{key}' eksik")
    tur = fm.get("tur")
    if tur and tur not in REQUIRED:
        errors.append(f"frontmatter: tur geçersiz: '{tur}' (gunluk | haftalik | derin)")
    try:
        tarih = date.fromisoformat(fm.get("tarih", ""))
        if path.stem != tarih.isoformat():
            errors.append(f"frontmatter: tarih ({tarih}) dosya adıyla ({path.stem}) uyuşmuyor")
    except ValueError:
        tarih = None
        errors.append(f"frontmatter: tarih geçersiz: '{fm.get('tarih')}'")
    try:
        declared = int(fm.get("makale_sayisi", ""))
    except ValueError:
        declared = None
        errors.append(f"frontmatter: makale_sayisi sayı değil: '{fm.get('makale_sayisi')}'")
    if errors and (tur not in REQUIRED or tarih is None):
        return errors

    # Uyarı
    if WARNING not in body:
        errors.append("otomatik üretim uyarısı eksik")

    # Makale bölümleri: "## 1. Başlık"
    sections = re.split(r"^## \d+\. ", body, flags=re.M)[1:]
    if tur == "gunluk" and not 3 <= len(sections) <= 5:
        errors.append(f"makale sayısı 3-5 olmalı, bulunan: {len(sections)}")
    if tur != "derin" and declared is not None and declared != len(sections):
        errors.append(f"makale_sayisi ({declared}) ile bölüm sayısı ({len(sections)}) uyuşmuyor")

    # Zorunlu başlıklar
    checks = [body] if tur == "derin" else sections
    for i, sec in enumerate(checks, 1):
        label = "dosya" if tur == "derin" else f"bölüm {i}"
        for h in REQUIRED[tur]:
            if f"**{h}:**" not in sec:
                errors.append(f"{label}: '**{h}:**' başlığı eksik")
        if tur != "derin" and not re.search(rf"\*\*arXiv:\*\* \[{ID_RE}\]\(https://arxiv\.org/abs/{ID_RE}\)", sec):
            errors.append(f"{label}: '**arXiv:** [id](https://arxiv.org/abs/id)' satırı eksik")
    if tur == "derin":
        for h in DERIN_HEADINGS:
            if not re.search(rf"^{re.escape(h)}\s*$", body, re.M):
                errors.append(f"dosya: '{h}' bölümü eksik")

    # arXiv ID'leri: link metni ile URL aynı olmalı, ID kaynakta bulunmalı
    for text_id, url_id in re.findall(rf"\[({ID_RE})\]\(https://arxiv\.org/abs/({ID_RE})\)", body):
        if text_id != url_id:
            errors.append(f"link metni ({text_id}) ile URL ({url_id}) farklı")
    ids = set(re.findall(rf"arxiv\.org/abs/({ID_RE})", body))
    if not ids:
        errors.append("dosyada hiç arXiv linki yok")
    if tur == "gunluk":
        raw_path = RAW_DIR / f"{tarih.isoformat()}.json"
        if not raw_path.exists():
            errors.append(f"ham veri yok: {raw_path.relative_to(ROOT)}")
        else:
            known = {p["arxiv_id"] for p in json.loads(raw_path.read_text())["papers"]}
            for i in sorted(ids - known):
                errors.append(f"arXiv ID {i} o günün ham verisinde ({raw_path.name}) yok — uydurma olabilir")
    else:
        with PAPERS_CSV.open(encoding="utf-8") as f:
            known = {row["arxiv_id"] for row in csv.DictReader(f)}
        for i in sorted(ids - known):
            errors.append(f"arXiv ID {i} papers.csv'de yok — hafta sonu yalnızca özetlenmiş makaleler kullanılır")
    if tur == "derin" and len(ids) != 1:
        errors.append(f"derin okuma tek makale olmalı, bulunan ID sayısı: {len(ids)}")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Kullanım: python scripts/validate_day.py <dosya>", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        print(f"HATA: dosya yok: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)
    errors = validate(path)
    if errors:
        print(f"GEÇERSİZ: {sys.argv[1]}")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    print(f"GEÇERLİ: {sys.argv[1]}")


if __name__ == "__main__":
    main()
