"""README'deki son 7 gün bölümünü ve ARSIV.md'yi ozetler/ klasöründen üretir.

README'de şu işaretler bulunmalı:
<!-- SON7 -->
...otomatik içerik...
<!-- /SON7 -->
"""
import csv
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OZETLER = ROOT / "ozetler"
README = ROOT / "README.md"
ARSIV = ROOT / "ARSIV.md"
RUNS = ROOT / "data" / "runs.csv"

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
         "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TUR_ETIKET = {"gunluk": "Günlük", "haftalik": "Haftalık özet", "derin": "Derin okuma"}
START, END = "<!-- SON7 -->", "<!-- /SON7 -->"


def tr_date(d):
    return f"{d.day} {AYLAR[d.month - 1]} {d.year}"


def load_days():
    days = []
    for path in OZETLER.glob("*/*/*.md"):
        text = path.read_text(encoding="utf-8")
        fm = dict(re.findall(r"^(tarih|tur|makale_sayisi):\s*(\S+)", text, re.M))
        h1 = re.search(r"^# .+? — (.+)$", text, re.M)
        days.append({
            "date": date.fromisoformat(fm["tarih"]),
            "tur": fm.get("tur", "gunluk"),
            "count": fm.get("makale_sayisi", "?"),
            "title": h1.group(1) if h1 else "",
            "path": path.relative_to(ROOT).as_posix(),
        })
    return sorted(days, key=lambda d: d["date"], reverse=True)


def line(d):
    detail = f"{d['count']} makale" if d["tur"] == "gunluk" else d["title"]
    return f"- [{tr_date(d['date'])}]({d['path']}) · {TUR_ETIKET.get(d['tur'], d['tur'])} · {detail}"


def last_success():
    if not RUNS.exists():
        return None
    with RUNS.open(encoding="utf-8") as f:
        ok = [r["tarih"] for r in csv.DictReader(f) if r["durum"] == "basarili"]
    return max(ok) if ok else None


def build_arsiv(days):
    out = ["# Arşiv", "",
           "> Bu dosya `scripts/build_index.py` tarafından otomatik üretilir. Elle düzenlemeyin.", ""]
    by_month = defaultdict(list)
    for d in days:
        by_month[(d["date"].year, d["date"].month)].append(d)
    for (y, m) in sorted(by_month, reverse=True):
        out += [f"## {AYLAR[m - 1]} {y}", ""] + [line(d) for d in by_month[(y, m)]] + [""]
    if not days:
        out.append("Henüz özet yok.")
    ARSIV.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def build_readme(days):
    text = README.read_text(encoding="utf-8") if README.exists() else ""
    if START not in text or END not in text:
        print(f"HATA: README.md'de {START} / {END} işaretleri yok", file=sys.stderr)
        sys.exit(1)
    ls = last_success()
    block = [line(d) for d in days[:7]] or ["Henüz özet yok."]
    block += ["", f"Son başarılı çalışma: **{tr_date(date.fromisoformat(ls)) if ls else '—'}** · Tüm günler: [ARSIV.md](ARSIV.md)"]
    new = re.sub(re.escape(START) + r".*?" + re.escape(END),
                 lambda _: START + "\n" + "\n".join(block) + "\n" + END, text, flags=re.S)
    README.write_text(new, encoding="utf-8")


def main():
    days = load_days()
    build_arsiv(days)
    build_readme(days)
    print(f"İndeks güncellendi: {len(days)} gün")


if __name__ == "__main__":
    main()
