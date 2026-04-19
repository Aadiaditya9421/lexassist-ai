"""
knowledge_base/scraper.py
─────────────────────────
Scrapes full legal text for all 12 LexAssist documents from public
Government of India sources and saves them as YAML-frontmatted .txt files.

Sources (all public domain / Government of India):
  • IndiaCode      : https://indiacode.nic.in
  • Legislative Dept: https://legislative.gov.in
  • Indian Kanoon  : https://indiankanoon.org (fallback)

Usage:
    pip install requests beautifulsoup4 lxml
    python knowledge_base/scraper.py

Output:
    knowledge_base/docs/<filename>.txt   (12 files)

Run time: ~3–5 minutes on a normal connection.
"""

import os
import re
import time
import random
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scraper")

# ── Config ────────────────────────────────────────────────────────────────────
DOCS_DIR = Path(__file__).parent / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ── Document targets ──────────────────────────────────────────────────────────

@dataclass
class DocTarget:
    filename: str
    title: str
    category: str
    subcategory: str
    source_name: str
    year: int
    primary_url: str
    fallback_url: str
    content_selector: str          # CSS selector for main content div
    section_pattern: str           # regex to identify section headings


TARGETS = [
    DocTarget(
        filename="01_ipc_sections_1_to_120.txt",
        title="Indian Penal Code — Sections 1 to 120",
        category="criminal_law",
        subcategory="ipc_general",
        source_name="Government of India — Indian Penal Code, 1860",
        year=1860,
        primary_url="https://indiacode.nic.in/handle/123456789/2263",
        fallback_url="https://indiankanoon.org/doc/1569253/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="02_ipc_sections_121_to_300.txt",
        title="Indian Penal Code — Sections 121 to 300",
        category="criminal_law",
        subcategory="ipc_offences_state",
        source_name="Government of India — Indian Penal Code, 1860",
        year=1860,
        primary_url="https://indiacode.nic.in/handle/123456789/2263",
        fallback_url="https://indiankanoon.org/doc/1569253/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="03_ipc_sections_301_to_511.txt",
        title="Indian Penal Code — Sections 301 to 511",
        category="criminal_law",
        subcategory="ipc_offences_body_property",
        source_name="Government of India — Indian Penal Code, 1860",
        year=1860,
        primary_url="https://indiacode.nic.in/handle/123456789/2263",
        fallback_url="https://indiankanoon.org/doc/1569253/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="04_crpc_arrest_bail_trial.txt",
        title="Code of Criminal Procedure — Arrest, Bail and Trial",
        category="criminal_law",
        subcategory="crpc_procedure",
        source_name="Government of India — CrPC, 1973",
        year=1973,
        primary_url="https://indiacode.nic.in/handle/123456789/1362",
        fallback_url="https://indiankanoon.org/doc/1201279/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="05_constitution_fundamental_rights.txt",
        title="Constitution of India — Fundamental Rights (Articles 12–35)",
        category="constitutional_law",
        subcategory="fundamental_rights",
        source_name="Government of India — Constitution of India, 1950",
        year=1950,
        primary_url="https://legislative.gov.in/constitution-of-india/",
        fallback_url="https://indiankanoon.org/doc/609295/",
        content_selector="div.field-items",
        section_pattern=r"Article\s+\d+",
    ),
    DocTarget(
        filename="06_constitution_dpsp_amendments.txt",
        title="Constitution of India — DPSP, Fundamental Duties and Key Amendments",
        category="constitutional_law",
        subcategory="dpsp_duties",
        source_name="Government of India — Constitution of India, 1950",
        year=1950,
        primary_url="https://legislative.gov.in/constitution-of-india/",
        fallback_url="https://indiankanoon.org/doc/609295/",
        content_selector="div.field-items",
        section_pattern=r"Article\s+\d+",
    ),
    DocTarget(
        filename="07_consumer_protection_act_2019.txt",
        title="Consumer Protection Act, 2019",
        category="civil_law",
        subcategory="consumer_rights",
        source_name="Government of India — Consumer Protection Act, 2019",
        year=2019,
        primary_url="https://indiacode.nic.in/handle/123456789/14587",
        fallback_url="https://indiankanoon.org/doc/116888116/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="08_rti_act_2005.txt",
        title="Right to Information Act, 2005",
        category="special_law",
        subcategory="rti",
        source_name="Government of India — RTI Act, 2005",
        year=2005,
        primary_url="https://indiacode.nic.in/handle/123456789/2055",
        fallback_url="https://indiankanoon.org/doc/1371676/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="09_labour_law_pf_gratuity.txt",
        title="Labour Law — EPF Act 1952 and Payment of Gratuity Act 1972",
        category="civil_law",
        subcategory="labour_law",
        source_name="Government of India — EPF Act 1952 & Gratuity Act 1972",
        year=1952,
        primary_url="https://indiacode.nic.in/handle/123456789/1357",
        fallback_url="https://indiankanoon.org/doc/1917686/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="10_it_act_2000_cyber_offences.txt",
        title="Information Technology Act, 2000 — Cyber Offences",
        category="special_law",
        subcategory="cyber_law",
        source_name="Government of India — IT Act, 2000",
        year=2000,
        primary_url="https://indiacode.nic.in/handle/123456789/1999",
        fallback_url="https://indiankanoon.org/doc/1368458/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="11_domestic_violence_pocso.txt",
        title="Protection of Women from Domestic Violence Act 2005 and POCSO Act 2012",
        category="special_law",
        subcategory="domestic_violence_child_protection",
        source_name="Government of India — PWDVA 2005 & POCSO 2012",
        year=2005,
        primary_url="https://indiacode.nic.in/handle/123456789/2021",
        fallback_url="https://indiankanoon.org/doc/542273/",
        content_selector="div.akn-act",
        section_pattern=r"Section\s+\d+",
    ),
    DocTarget(
        filename="12_limitation_act_glossary.txt",
        title="Limitation Act 1963 and Legal Glossary",
        category="reference",
        subcategory="limitation_periods",
        source_name="Government of India — Limitation Act, 1963",
        year=1963,
        primary_url="https://indiacode.nic.in/handle/123456789/1565",
        fallback_url="https://indiankanoon.org/doc/1357604/",
        content_selector="div.akn-act",
        section_pattern=r"(?:Section|Article)\s+\d+",
    ),
]


# ── Scraper functions ─────────────────────────────────────────────────────────

def fetch_page(url: str, retries: int = 3) -> Optional[str]:
    """Fetch a page with retries and polite delays."""
    for attempt in range(retries):
        try:
            delay = random.uniform(2, 5)
            log.info(f"  Fetching (attempt {attempt+1}): {url[:70]}...")
            time.sleep(delay)
            resp = SESSION.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.text
            elif resp.status_code == 429:
                wait = (attempt + 1) * 10
                log.warning(f"  Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"  HTTP {resp.status_code} for {url}")
        except requests.RequestException as e:
            log.warning(f"  Request failed: {e}")
            time.sleep(5)
    return None


def extract_text(html: str, selector: str) -> str:
    """Extract and clean main content text from HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Try the primary selector
    container = soup.select_one(selector)

    # Fallback selectors in order of preference
    if not container:
        for fallback in ["main", "article", "#content", ".content",
                         "div.container", "body"]:
            container = soup.select_one(fallback)
            if container:
                break

    if not container:
        container = soup

    # Remove navigation, scripts, styles, headers, footers
    for tag in container.find_all(["nav", "script", "style", "footer",
                                   "header", "aside", "button", "form"]):
        tag.decompose()

    # Extract text preserving structure
    lines = []
    for elem in container.find_all(["h1", "h2", "h3", "h4", "p",
                                    "li", "td", "th", "section"]):
        text = elem.get_text(separator=" ", strip=True)
        if text and len(text) > 10:
            # Add dividers before headings
            if elem.name in ["h1", "h2"]:
                lines.append("\n" + "=" * 72)
                lines.append(text.upper())
                lines.append("=" * 72)
            elif elem.name in ["h3", "h4"]:
                lines.append("\n" + text)
                lines.append("-" * 40)
            else:
                lines.append(text)

    return "\n".join(lines)


def clean_text(text: str) -> str:
    """Normalise whitespace and remove junk characters."""
    # Collapse multiple blank lines to max 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove non-printable characters except newline and tab
    text = re.sub(r"[^\x09\x0A\x20-\x7E\u00A0-\uFFFF]", "", text)
    # Normalise section headings
    text = re.sub(r"\bSec\.\s*(\d+)", r"Section \1", text)
    # Strip trailing whitespace per line
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def build_frontmatter(target: DocTarget, word_count: int) -> str:
    """Build YAML frontmatter block for the document."""
    return f"""---
title: {target.title}
category: {target.category}
subcategory: {target.subcategory}
source: {target.source_name}
year: {target.year}
scraped_from: {target.primary_url}
scraped_at: {datetime.now().strftime('%Y-%m-%d')}
word_count: {word_count}
---"""


def add_practical_notes_prompt(target: DocTarget) -> str:
    """
    Adds a footer note pointing to the official source.
    In production, you can replace this with LLM-generated practical notes.
    """
    return f"""

================================================================================
OFFICIAL SOURCE
================================================================================

This document was sourced from the Government of India's official legal
repository. For the most current and authoritative text, refer to:

Primary source   : {target.primary_url}
Alternative      : {target.fallback_url}
Last verified    : {datetime.now().strftime('%B %Y')}

DISCLAIMER: This text is provided for informational purposes only and
constitutes legal information, not legal advice. Always consult a qualified
advocate for advice specific to your situation.
"""


def scrape_document(target: DocTarget) -> bool:
    """Scrape one document and save it. Returns True on success."""
    output_path = DOCS_DIR / target.filename
    log.info(f"\n{'='*60}")
    log.info(f"Document : {target.filename}")
    log.info(f"Title    : {target.title[:55]}")

    # ── Try primary URL ───────────────────────────────────────────────────────
    html = fetch_page(target.primary_url)
    source_used = target.primary_url

    # ── Try fallback if primary fails ─────────────────────────────────────────
    if not html:
        log.warning(f"  Primary failed — trying fallback: {target.fallback_url}")
        html = fetch_page(target.fallback_url)
        source_used = target.fallback_url

    if not html:
        log.error(f"  Both URLs failed for {target.filename} — skipping.")
        return False

    log.info(f"  Fetched {len(html):,} bytes from {source_used[:50]}")

    # ── Extract and clean text ────────────────────────────────────────────────
    raw_text = extract_text(html, target.content_selector)
    clean = clean_text(raw_text)

    if len(clean.split()) < 200:
        log.warning(
            f"  Extracted text too short ({len(clean.split())} words) — "
            f"selector may not match. Consider inspecting manually."
        )

    # ── Build final document ──────────────────────────────────────────────────
    word_count = len(clean.split())
    frontmatter = build_frontmatter(target, word_count)
    footer = add_practical_notes_prompt(target)
    final_text = f"{frontmatter}\n\n{clean}\n{footer}"

    # ── Write to disk ─────────────────────────────────────────────────────────
    output_path.write_text(final_text, encoding="utf-8")
    log.info(f"  Saved  → {output_path.name}  ({word_count:,} words)")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("LexAssist AI — Legal Document Scraper")
    log.info(f"Output directory: {DOCS_DIR}")
    log.info(f"Documents to scrape: {len(TARGETS)}")
    log.info("Estimated time: 3–6 minutes (polite rate limiting)\n")

    results = {"success": [], "failed": []}

    for i, target in enumerate(TARGETS, 1):
        log.info(f"[{i}/{len(TARGETS)}] Starting...")
        ok = scrape_document(target)
        if ok:
            results["success"].append(target.filename)
        else:
            results["failed"].append(target.filename)
        # Polite delay between documents
        if i < len(TARGETS):
            wait = random.uniform(3, 7)
            log.info(f"  Waiting {wait:.1f}s before next document...")
            time.sleep(wait)

    # ── Summary ───────────────────────────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info("SCRAPING COMPLETE")
    log.info(f"  Success : {len(results['success'])}/{len(TARGETS)}")
    log.info(f"  Failed  : {len(results['failed'])}/{len(TARGETS)}")

    if results["failed"]:
        log.warning("  Failed files (generate manually or retry):")
        for f in results["failed"]:
            log.warning(f"    - {f}")

    if results["success"]:
        log.info("  Successful files:")
        for f in results["success"]:
            size = (DOCS_DIR / f).stat().st_size
            log.info(f"    ✓ {f}  ({size:,} bytes)")

    log.info(f"\nNext step: python -m knowledge_base.ingest")


if __name__ == "__main__":
    main()
