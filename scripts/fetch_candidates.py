"""Aday makaleleri çeker → data/raw/YYYY-MM-DD.json

Kaynak 1: Hugging Face Daily Papers (upvote sinyali)
Kaynak 2: arXiv API (kategori, abstract, yazarlar) — HF yetersizse arXiv RSS yedek

Not: Görev 06:00 (Europe/Istanbul) çalışır. O saatte HF'nin "bugün" listesi
henüz dolmamıştır, bu yüzden varsayılan HF tarihi bir önceki gündür.
"""
import argparse
import json
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SEEN_FILE = ROOT / "data" / "seen.json"

HF_URL = "https://huggingface.co/api/daily_papers"
ARXIV_API = "https://export.arxiv.org/api/query"
RSS_URLS = ["https://rss.arxiv.org/rss/cs.LG", "https://rss.arxiv.org/rss/cs.AI"]
TARGET_CATS = {"cs.LG", "cs.AI"}
ARXIV_DELAY = 3  # arXiv kuralı: istekler arası en az 3 sn
MIN_CANDIDATES = 5
MAX_HF_LOOKBACK = 3  # HF yetersizse en fazla kaç gün geriye bakılır
HEADERS = {"User-Agent": "arxiv-turkce-gunluk/1.0 (github.com/aliandacerdass)"}
ATOM = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


class FetchError(Exception):
    pass


def get(url, params=None, retries=3):
    """arXiv'in 503/429 dönebildiği durumlar için artan beklemeyle tekrar dener."""
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=90)
            if r.status_code == 200 and "Rate exceeded" not in r.text[:100]:
                return r
            last = f"HTTP {r.status_code}: {r.text[:80].strip()}"
        except requests.RequestException as e:
            last = str(e)
        time.sleep(ARXIV_DELAY * (i + 2) * 2)
    raise FetchError(f"{url} → {last}")


def fetch_hf(day):
    r = get(HF_URL, params={"date": day.isoformat()})
    out = {}
    for item in r.json():
        p = item["paper"]
        out[p["id"]] = p.get("upvotes", 0)
    return out


def fetch_arxiv_meta(ids):
    """ids için arXiv API'den metadata; 25lik gruplar halinde, aralarında 3 sn."""
    meta = {}
    ids = list(ids)
    for i in range(0, len(ids), 25):
        if i:
            time.sleep(ARXIV_DELAY)
        chunk = ids[i:i + 25]
        r = get(ARXIV_API, params={"id_list": ",".join(chunk), "max_results": len(chunk)})
        root = ET.fromstring(r.content)
        for e in root.findall("a:entry", ATOM):
            raw_id = e.findtext("a:id", "", ATOM).rsplit("/", 1)[-1]
            aid = raw_id.split("v")[0] if "v" in raw_id else raw_id
            title = e.findtext("a:title", "", ATOM)
            if not title or title.strip() == "Error":
                continue
            meta[aid] = {
                "arxiv_id": aid,
                "title": " ".join(title.split()),
                "authors": [a.findtext("a:name", "", ATOM) for a in e.findall("a:author", ATOM)],
                "categories": [c.get("term") for c in e.findall("a:category", ATOM)],
                "abstract": " ".join(e.findtext("a:summary", "", ATOM).split()),
                "url": f"https://arxiv.org/abs/{aid}",
            }
    return meta


def fetch_rss():
    out = {}
    for url in RSS_URLS:
        feed = feedparser.parse(get(url).content)
        for it in feed.entries:
            desc = it.get("description", "")
            if "Announce Type: new" not in desc and "Announce Type: cross" not in desc:
                continue
            aid = it.link.rsplit("/", 1)[-1]
            abstract = desc.split("Abstract:", 1)[-1]
            out[aid] = {
                "arxiv_id": aid,
                "title": " ".join(it.title.split()),
                "authors": [a.strip() for a in it.get("author", "").split(",") if a.strip()],
                "categories": [t.term for t in it.get("tags", [])],
                "abstract": " ".join(abstract.split()),
                "url": f"https://arxiv.org/abs/{aid}",
            }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="Çalışma tarihi YYYY-MM-DD (varsayılan: bugün, Europe/Istanbul)")
    ap.add_argument("--hf-date", help="HF Daily Papers tarihi (varsayılan: --date'in bir önceki günü)")
    args = ap.parse_args()

    run_day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Europe/Istanbul")).date()
    hf_day = date.fromisoformat(args.hf_date) if args.hf_date else run_day - timedelta(days=1)
    seen = set(json.loads(SEEN_FILE.read_text()))

    try:
        # 1) HF: hedef sayıya ulaşana kadar en fazla MAX_HF_LOOKBACK gün geriye git
        upvotes, hf_dates = {}, []
        candidates = {}
        for back in range(MAX_HF_LOOKBACK):
            d = hf_day - timedelta(days=back)
            new = {k: v for k, v in fetch_hf(d).items() if k not in seen and k not in upvotes}
            hf_dates.append(d.isoformat())
            if not new:
                continue
            upvotes.update(new)
            time.sleep(ARXIV_DELAY)
            for aid, m in fetch_arxiv_meta(new).items():
                if TARGET_CATS & set(m["categories"]):
                    candidates[aid] = {**m, "hf_upvotes": upvotes.get(aid), "source": "huggingface"}
            if len(candidates) >= MIN_CANDIDATES:
                break

        # 2) Yedek: arXiv RSS
        sources = ["huggingface"]
        if len(candidates) < MIN_CANDIDATES:
            sources.append("arxiv-rss")
            for aid, m in fetch_rss().items():
                if aid in seen or aid in candidates:
                    continue
                if TARGET_CATS & set(m["categories"]):
                    candidates[aid] = {**m, "hf_upvotes": None, "source": "arxiv-rss"}
    except (FetchError, ET.ParseError, ValueError) as e:
        print(f"HATA: veri çekilemedi: {e}", file=sys.stderr)
        sys.exit(2)

    if not candidates:
        print("HATA: hiç uygun aday bulunamadı", file=sys.stderr)
        sys.exit(3)

    papers = sorted(candidates.values(), key=lambda p: -(p["hf_upvotes"] or -1))
    out = {
        "run_date": run_day.isoformat(),
        "hf_dates": hf_dates,
        "sources": sources,
        "fetched_at": datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(timespec="seconds"),
        "papers": papers,
    }
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{run_day.isoformat()}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(f"{path.relative_to(ROOT)}: {len(papers)} aday ({', '.join(sources)})")


if __name__ == "__main__":
    main()
