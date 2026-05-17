"""Download the arXiv + NSF demo corpus to demo_corpus/.

Dev-set default is 50 documents (40 arXiv PDFs + 10 NSF grant abstracts) spanning
multiple disciplines. Scale up via --arxiv-n / --nsf-n once the agent loop is stable.

See docs/08-ops-and-demo.md §Data license notes and PRD §11.

Usage:
    python scripts/seed_corpus.py                     # default dev set: 40 arXiv + 10 NSF
    python scripts/seed_corpus.py --arxiv-n 500 --nsf-n 100
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARXIV_DIR = Path("demo_corpus/arxiv")
NSF_DIR = Path("demo_corpus/nsf")

ARXIV_API = "https://export.arxiv.org/api/query"
NSF_API = "https://api.nsf.gov/services/v1/awards.json"

ARXIV_NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

# Disciplines chosen for diverse compliance surface: CS (clean), q-bio (IRB-adjacent),
# physics (large collabs / funder mix), econ (human-subjects in empirical work).
ARXIV_CATEGORIES = ["cs.CL", "q-bio.QM", "physics.soc-ph", "econ.EM"]

# Be polite. arXiv asks for >=3s between API requests.
ARXIV_DELAY_SEC = 3.5
PDF_DELAY_SEC = 1.0

USER_AGENT = "Datalake-Hackathon/0.1 (nhnguyen@uchicago.edu)"


def _http_get(url: str, accept: str = "*/*", max_retries: int = 4) -> bytes:
    """GET with retry+backoff on 429 / transient 5xx. arXiv rate-limits aggressively."""
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 or 500 <= exc.code < 600:
                wait = 5 * (attempt + 1) ** 2  # 5s, 20s, 45s, 80s
                print(f"  HTTP {exc.code}; sleeping {wait}s before retry {attempt + 1}/{max_retries}")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError(f"giving up after {max_retries} retries: {last_exc}")


def fetch_arxiv(n_total: int, out_dir: Path) -> int:
    """Query arXiv across ARXIV_CATEGORIES, round-robin, until n_total PDFs are saved."""
    out_dir.mkdir(parents=True, exist_ok=True)
    per_category = max(1, n_total // len(ARXIV_CATEGORIES) + 2)  # over-fetch margin
    saved = 0

    for cat in ARXIV_CATEGORIES:
        if saved >= n_total:
            break
        params = {
            "search_query": f"cat:{cat}",
            "start": "0",
            "max_results": str(per_category),
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
        print(f"[arxiv] querying {cat} (have {saved}/{n_total})")
        body = _http_get(url, accept="application/atom+xml")
        time.sleep(ARXIV_DELAY_SEC)

        root = ET.fromstring(body)
        entries = root.findall("a:entry", ARXIV_NS)
        for entry in entries:
            if saved >= n_total:
                break
            arxiv_id = _arxiv_id_from_entry(entry)
            if not arxiv_id:
                continue
            pdf_path = out_dir / f"{arxiv_id}.pdf"
            meta_path = out_dir / f"{arxiv_id}.json"
            if pdf_path.exists() and meta_path.exists():
                saved += 1
                continue
            pdf_url = _arxiv_pdf_url_from_entry(entry)
            if not pdf_url:
                continue
            try:
                pdf_bytes = _http_get(pdf_url, accept="application/pdf")
            except Exception as exc:
                print(f"[arxiv]   skip {arxiv_id}: {exc}")
                time.sleep(PDF_DELAY_SEC)
                continue
            pdf_path.write_bytes(pdf_bytes)
            meta_path.write_text(json.dumps(_arxiv_entry_to_dict(entry), indent=2))
            saved += 1
            print(f"[arxiv]   saved {arxiv_id} ({len(pdf_bytes)//1024} KB)")
            time.sleep(PDF_DELAY_SEC)

    return saved


def _arxiv_id_from_entry(entry: ET.Element) -> str | None:
    id_el = entry.find("a:id", ARXIV_NS)
    if id_el is None or not id_el.text:
        return None
    # id looks like http://arxiv.org/abs/2401.12345v1
    return id_el.text.rsplit("/", 1)[-1].replace("/", "_")


def _arxiv_pdf_url_from_entry(entry: ET.Element) -> str | None:
    for link in entry.findall("a:link", ARXIV_NS):
        if link.get("title") == "pdf":
            return link.get("href")
    return None


def _arxiv_entry_to_dict(entry: ET.Element) -> dict:
    def _text(tag: str) -> str | None:
        el = entry.find(f"a:{tag}", ARXIV_NS)
        return el.text.strip() if el is not None and el.text else None

    authors = []
    for author in entry.findall("a:author", ARXIV_NS):
        name = author.find("a:name", ARXIV_NS)
        affiliation = author.find("arxiv:affiliation", ARXIV_NS)
        authors.append({
            "name": name.text if name is not None else None,
            "affiliation": affiliation.text if affiliation is not None else None,
        })
    categories = [c.get("term") for c in entry.findall("a:category", ARXIV_NS) if c.get("term")]
    return {
        "source": "arxiv",
        "arxiv_id": _arxiv_id_from_entry(entry),
        "title": _text("title"),
        "summary": _text("summary"),
        "published": _text("published"),
        "updated": _text("updated"),
        "authors": authors,
        "categories": categories,
    }


def fetch_nsf(n_total: int, out_dir: Path) -> int:
    """Pull recent NSF awards as JSON. One file per award."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fields = "id,title,abstractText,piFirstName,piLastName,awardeeName,fundsObligatedAmt,date"
    params = {
        "rpp": str(n_total),
        "printFields": fields,
    }
    url = f"{NSF_API}?{urllib.parse.urlencode(params)}"
    print(f"[nsf] querying {n_total} awards")
    body = _http_get(url, accept="application/json")
    data = json.loads(body)
    awards = data.get("response", {}).get("award", [])
    saved = 0
    for award in awards[:n_total]:
        award_id = str(award.get("id", "")).strip()
        if not award_id:
            continue
        path = out_dir / f"nsf_{award_id}.json"
        if path.exists():
            saved += 1
            continue
        payload = {"source": "nsf", **award}
        path.write_text(json.dumps(payload, indent=2))
        saved += 1
    print(f"[nsf] saved {saved} awards")
    return saved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arxiv-n", type=int, default=40, help="arXiv PDFs to fetch (default: 40)")
    parser.add_argument("--nsf-n", type=int, default=10, help="NSF awards to fetch (default: 10)")
    args = parser.parse_args()

    n_arxiv = fetch_arxiv(args.arxiv_n, ARXIV_DIR) if args.arxiv_n > 0 else 0
    n_nsf = fetch_nsf(args.nsf_n, NSF_DIR) if args.nsf_n > 0 else 0
    print(f"\ndone: {n_arxiv} arXiv + {n_nsf} NSF = {n_arxiv + n_nsf} dev docs")


if __name__ == "__main__":
    main()
