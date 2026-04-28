"""
Job board scrapers.
Sources: Adzuna API, Dice RSS, Remotive RSS, Jobicy RSS,
         We Work Remotely RSS, Himalayas.app JSON API,
         Remote.co RSS, Working Nomads API, ZipRecruiter HTML,
         SimplyHired RSS, LinkedIn (best-effort public feed).
Each scraper yields raw job dicts with keys:
  source, title, company, location, salary, posted, posted_raw, url, desc
"""

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Generator

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/2.0)"}
TIMEOUT = 20

# ── Adzuna ──────────────────────────────────────────────────────────────────

ADZUNA_APP_ID  = "67ecc1ab"
ADZUNA_APP_KEY = "932ed4fb93963c4021576e5e3d99d4a5"
ADZUNA_PAGES   = 3

ADZUNA_QUERIES = [
    "AI engineer", "ML engineer", "machine learning engineer",
    "generative AI engineer", "LLM engineer", "agentic AI",
    "AI agent developer", "data scientist", "data analyst",
    "GCP data engineer", "Google Cloud data engineer",
    "Azure AI engineer", "Azure OpenAI developer",
    "Python developer AI", "MLOps engineer", "NLP engineer",
    "AI architect", "RAG developer", "LangChain developer",
    "deep learning engineer", "computer vision engineer",
    "data engineer", "GenAI developer", "Copilot developer",
    "AI platform engineer", "foundation model engineer",
    "vector database engineer", "prompt engineer",
]


def _adzuna_salary(lo, hi) -> str:
    if lo and hi:
        h_lo = round(float(lo) / 2080)
        h_hi = round(float(hi) / 2080)
        if h_lo > 10:
            return f"~${h_lo}–${h_hi}/hr"
    return ""


def scrape_adzuna() -> Generator:
    for query in ADZUNA_QUERIES:
        for page in range(1, ADZUNA_PAGES + 1):
            url = (
                f"https://api.adzuna.com/v1/api/jobs/us/search/{page}"
                f"?app_id={ADZUNA_APP_ID}&app_key={ADZUNA_APP_KEY}"
                f"&results_per_page=20"
                f"&what={urllib.parse.quote(query)}"
                f"&sort_by=date"
                f"&content-type=application/json"
            )
            try:
                r = requests.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                results = r.json().get("results", [])
                if not results:
                    break
                for j in results:
                    raw = j.get("created", "")
                    yield {
                        "source":     "Adzuna",
                        "title":      j.get("title", ""),
                        "company":    j.get("company", {}).get("display_name", ""),
                        "location":   j.get("location", {}).get("display_name", ""),
                        "salary":     _adzuna_salary(j.get("salary_min"), j.get("salary_max")),
                        "posted":     raw[:10],
                        "posted_raw": raw,
                        "url":        j.get("redirect_url", ""),
                        "desc":       j.get("description", ""),
                    }
                time.sleep(0.35)
            except Exception as e:
                print(f"  [Adzuna] {query} p{page}: {e}")
                break


# ── Generic RSS helper ───────────────────────────────────────────────────────

def _clean_xml(content: bytes) -> bytes:
    content = re.sub(rb'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', b'', content)
    content = re.sub(
        rb'&(?!(?:amp|lt|gt|apos|quot|#\d+|#x[0-9a-fA-F]+);)',
        b'&amp;', content)
    return content


def _parse_rss(content: bytes):
    try:
        return ET.fromstring(content)
    except ET.ParseError:
        try:
            return ET.fromstring(_clean_xml(content))
        except ET.ParseError:
            return None


def _el(item, tag: str) -> str:
    el = item.find(tag)
    return (el.text or "").strip() if el is not None else ""


def _ns_el(item, tag: str, ns: dict) -> str:
    for prefix, uri in ns.items():
        el = item.find(f"{{{uri}}}{tag}")
        if el is not None and el.text:
            return el.text.strip()
    return ""


# ── Dice.com ─────────────────────────────────────────────────────────────────

DICE_QUERIES = [
    "machine+learning+engineer", "AI+engineer", "data+scientist",
    "GenAI+developer", "LLM+engineer", "MLOps+engineer",
    "data+engineer", "NLP+engineer", "deep+learning",
]


def scrape_dice() -> Generator:
    for q in DICE_QUERIES:
        url = f"https://www.dice.com/jobs/q-{q}-jobs.rss"
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            root = _parse_rss(r.content)
            if root is None:
                continue
            for item in root.findall(".//item")[:25]:
                pub = _el(item, "pubDate")
                yield {
                    "source":     "Dice.com",
                    "title":      _el(item, "title"),
                    "company":    _el(item, "author") or "",
                    "location":   _el(item, "location") or "See posting",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        _el(item, "link"),
                    "desc":       _el(item, "description"),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Dice] {q}: {e}")


# ── Remotive.com ─────────────────────────────────────────────────────────────

REMOTIVE_QUERIES = [
    "machine learning", "AI engineer", "data scientist",
    "generative AI", "LLM", "MLOps", "data engineer",
]


def scrape_remotive() -> Generator:
    for q in REMOTIVE_QUERIES:
        url = (
            f"https://remotive.com/remote-jobs/feed"
            f"?category=software-dev&search={urllib.parse.quote(q)}"
        )
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            root = _parse_rss(r.content)
            if root is None:
                continue
            for item in root.findall(".//item")[:20]:
                pub = _el(item, "pubDate")
                yield {
                    "source":     "Remotive.com",
                    "title":      _el(item, "title"),
                    "company":    _el(item, "company") or "",
                    "location":   "Remote",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        _el(item, "link"),
                    "desc":       _el(item, "description"),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Remotive] {q}: {e}")


# ── Jobicy.com (contract filter) ──────────────────────────────────────────────

JOBICY_QUERIES = [
    "machine+learning", "AI+engineer", "data+scientist",
    "generative+AI", "LLM", "data+engineer", "python+AI",
]


def scrape_jobicy() -> Generator:
    for q in JOBICY_QUERIES:
        url = (
            f"https://jobicy.com/?feed=job_feed"
            f"&job_types=contract"
            f"&search_keywords={urllib.parse.quote(q)}"
        )
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            root = _parse_rss(r.content)
            if root is None:
                continue
            for item in root.findall(".//item")[:15]:
                pub = _el(item, "pubDate")
                yield {
                    "source":     "Jobicy.com",
                    "title":      _el(item, "title"),
                    "company":    "",
                    "location":   "Remote",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        _el(item, "link"),
                    "desc":       _el(item, "description"),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Jobicy] {q}: {e}")


# ── We Work Remotely ──────────────────────────────────────────────────────────

WWR_FEEDS = [
    ("https://weworkremotely.com/remote-jobs.rss", "WeWorkRemotely"),
    ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "WeWorkRemotely"),
    ("https://weworkremotely.com/categories/remote-data-science-jobs.rss", "WeWorkRemotely"),
]


def scrape_weworkremotely() -> Generator:
    for feed_url, source in WWR_FEEDS:
        try:
            r    = requests.get(feed_url, timeout=TIMEOUT, headers=HEADERS)
            root = _parse_rss(r.content)
            if root is None:
                continue
            for item in root.findall(".//item")[:30]:
                pub     = _el(item, "pubDate")
                title   = _el(item, "title")
                company = ""
                # WWR encodes "Company: Title" in the title field
                if ": " in title:
                    parts   = title.split(": ", 1)
                    company = parts[0].strip()
                    title   = parts[1].strip()
                yield {
                    "source":     source,
                    "title":      title,
                    "company":    company,
                    "location":   "Remote",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        _el(item, "link"),
                    "desc":       _el(item, "description"),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [WWR] {feed_url}: {e}")


# ── Himalayas.app ─────────────────────────────────────────────────────────────

HIMALAYAS_QUERIES = [
    "machine-learning", "ai-engineer", "data-scientist",
    "generative-ai", "llm", "mlops", "data-engineer", "nlp",
]


def scrape_himalayas() -> Generator:
    for q in HIMALAYAS_QUERIES:
        url = f"https://himalayas.app/jobs/api?q={urllib.parse.quote(q)}&limit=25"
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            data = r.json()
            jobs = data if isinstance(data, list) else data.get("jobs", [])
            for j in jobs:
                pub = j.get("publishedAt", j.get("createdAt", ""))
                yield {
                    "source":     "Himalayas.app",
                    "title":      j.get("title", ""),
                    "company":    j.get("companyName", ""),
                    "location":   j.get("locationRestrictions", ["Remote"])[0] if j.get("locationRestrictions") else "Remote",
                    "salary":     j.get("salaryRange", ""),
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        j.get("applicationLink", j.get("url", "")),
                    "desc":       j.get("description", ""),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Himalayas] {q}: {e}")


# ── Working Nomads ────────────────────────────────────────────────────────────

WN_CATEGORIES = ["data", "programming", "developer"]


def scrape_working_nomads() -> Generator:
    for cat in WN_CATEGORIES:
        url = f"https://www.workingnomads.com/api/exposed_jobs/?category={cat}&limit=50"
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            jobs = r.json()
            if not isinstance(jobs, list):
                jobs = jobs.get("results", [])
            for j in jobs:
                pub = j.get("pub_date", "")
                yield {
                    "source":     "WorkingNomads",
                    "title":      j.get("title", ""),
                    "company":    j.get("company", ""),
                    "location":   "Remote",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        j.get("url", ""),
                    "desc":       j.get("description", ""),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [WorkingNomads] {cat}: {e}")


# ── Remote.co ────────────────────────────────────────────────────────────────

REMOTE_CO_FEEDS = [
    "https://remote.co/remote-jobs/developer/feed/",
    "https://remote.co/remote-jobs/data-science/feed/",
]


def scrape_remoteco() -> Generator:
    for feed_url in REMOTE_CO_FEEDS:
        try:
            r    = requests.get(feed_url, timeout=TIMEOUT, headers=HEADERS)
            root = _parse_rss(r.content)
            if root is None:
                continue
            for item in root.findall(".//item")[:20]:
                pub = _el(item, "pubDate")
                yield {
                    "source":     "Remote.co",
                    "title":      _el(item, "title"),
                    "company":    "",
                    "location":   "Remote",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        _el(item, "link"),
                    "desc":       _el(item, "description"),
                }
            time.sleep(0.3)
        except Exception as e:
            print(f"  [Remote.co] {feed_url}: {e}")


# ── SimplyHired (public search, first page) ───────────────────────────────────

SH_QUERIES = [
    "machine learning engineer", "AI engineer", "data scientist",
    "generative AI developer", "LLM engineer", "data engineer",
]


def scrape_simplyhired() -> Generator:
    for q in SH_QUERIES:
        url = (
            f"https://www.simplyhired.com/search"
            f"?q={urllib.parse.quote(q)}&fdb=7&job_type=contract"
        )
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            soup = BeautifulSoup(r.text, "lxml")
            for card in soup.select("[data-testid='searchSerpJob']")[:15]:
                title_el   = card.select_one("[data-testid='searchSerpJobTitle']")
                company_el = card.select_one("[data-testid='searchSerpJobCompanyName']")
                loc_el     = card.select_one("[data-testid='searchSerpJobLocation']")
                date_el    = card.select_one("time")
                link_el    = card.select_one("a[href]")
                desc_el    = card.select_one("[data-testid='searchSerpJobSnippet']")

                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.simplyhired.com" + href

                pub = date_el.get("datetime", "") if date_el else ""
                yield {
                    "source":     "SimplyHired",
                    "title":      title_el.get_text(strip=True) if title_el else "",
                    "company":    company_el.get_text(strip=True) if company_el else "",
                    "location":   loc_el.get_text(strip=True) if loc_el else "",
                    "salary":     "",
                    "posted":     pub[:10],
                    "posted_raw": pub,
                    "url":        href,
                    "desc":       desc_el.get_text(strip=True) if desc_el else "",
                }
            time.sleep(0.5)
        except Exception as e:
            print(f"  [SimplyHired] {q}: {e}")


# ── ZipRecruiter (public search HTML) ────────────────────────────────────────

ZR_QUERIES = [
    "machine learning engineer", "AI engineer", "generative AI developer",
    "data scientist", "LLM engineer", "data engineer",
]


def scrape_ziprecruiter() -> Generator:
    for q in ZR_QUERIES:
        url = (
            f"https://www.ziprecruiter.com/jobs-search"
            f"?search={urllib.parse.quote(q)}&location=&days=7"
        )
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers={**HEADERS, "Accept-Language": "en-US"})
            soup = BeautifulSoup(r.text, "lxml")
            for card in soup.select("article.job_result, [data-testid='job-card']")[:15]:
                title_el   = card.select_one("h2, [data-testid='job-title']")
                company_el = card.select_one("[class*='company'], [data-testid='job-company']")
                loc_el     = card.select_one("[class*='location'], [data-testid='job-location']")
                link_el    = card.select_one("a[href*='/jobs/']")
                desc_el    = card.select_one("[class*='snippet'], [data-testid='job-snippet']")

                href = link_el["href"] if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.ziprecruiter.com" + href

                yield {
                    "source":     "ZipRecruiter",
                    "title":      title_el.get_text(strip=True) if title_el else "",
                    "company":    company_el.get_text(strip=True) if company_el else "",
                    "location":   loc_el.get_text(strip=True) if loc_el else "",
                    "salary":     "",
                    "posted":     "",
                    "posted_raw": "",
                    "url":        href,
                    "desc":       desc_el.get_text(strip=True) if desc_el else "",
                }
            time.sleep(0.6)
        except Exception as e:
            print(f"  [ZipRecruiter] {q}: {e}")


# ── HN Who's Hiring (monthly thread) ─────────────────────────────────────────

def scrape_hn_hiring() -> Generator:
    """Parse the latest Hacker News 'Who's Hiring' thread."""
    try:
        # Find the latest hiring thread via Algolia search
        r = requests.get(
            "https://hn.algolia.com/api/v1/search?"
            "query=Ask+HN:+Who+is+hiring&tags=story,ask_hn&hitsPerPage=5",
            timeout=TIMEOUT,
        )
        hits = r.json().get("hits", [])
        thread_id = None
        for h in hits:
            if "who is hiring" in h.get("title", "").lower():
                thread_id = h.get("objectID")
                break
        if not thread_id:
            return

        items_r = requests.get(
            f"https://hn.algolia.com/api/v1/items/{thread_id}", timeout=TIMEOUT
        )
        children = items_r.json().get("children", [])
        for c in children[:80]:
            text = c.get("text", "")
            if not text or len(text) < 50:
                continue
            # Extract first line as title
            first_line = BeautifulSoup(text, "lxml").get_text()[:120]
            yield {
                "source":     "HN Who's Hiring",
                "title":      first_line.strip(),
                "company":    "",
                "location":   "",
                "salary":     "",
                "posted":     "",
                "posted_raw": "",
                "url":        f"https://news.ycombinator.com/item?id={c.get('id', '')}",
                "desc":       BeautifulSoup(text, "lxml").get_text()[:3000],
            }
        time.sleep(0.3)
    except Exception as e:
        print(f"  [HN Hiring]: {e}")


# ── Master runner ─────────────────────────────────────────────────────────────

SCRAPERS = [
    ("Adzuna",           scrape_adzuna),
    ("Dice.com",         scrape_dice),
    ("Remotive",         scrape_remotive),
    ("Jobicy",           scrape_jobicy),
    ("WeWorkRemotely",   scrape_weworkremotely),
    ("Himalayas",        scrape_himalayas),
    ("WorkingNomads",    scrape_working_nomads),
    ("Remote.co",        scrape_remoteco),
    ("SimplyHired",      scrape_simplyhired),
    ("ZipRecruiter",     scrape_ziprecruiter),
    ("HN Hiring",        scrape_hn_hiring),
]


def run_all_scrapers() -> Generator:
    for name, fn in SCRAPERS:
        print(f"  Scraping {name}…")
        try:
            yield from fn()
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
