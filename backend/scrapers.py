"""
Job board scrapers.
Sources: Adzuna API, Dice JSON API (near-real-time), Remotive RSS, Jobicy RSS,
         We Work Remotely RSS, Himalayas.app JSON API,
         Remote.co RSS, Working Nomads API, ZipRecruiter HTML,
         SimplyHired RSS, Arbeitnow (free), JSearch RapidAPI (optional),
         HN Who's Hiring.
Each scraper yields raw job dicts with keys:
  source, title, company, location, salary, posted, posted_raw, url, desc
"""

import os
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


# ── Dice.com JSON API (near-real-time) ───────────────────────────────────────

DICE_HEADERS = {
    **HEADERS,
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.dice.com",
    "Referer": "https://www.dice.com/",
}

DICE_QUERIES = [
    "AI engineer", "ML engineer", "machine learning engineer",
    "generative AI developer", "LLM engineer", "agentic AI",
    "data scientist", "MLOps engineer", "NLP engineer",
    "deep learning engineer", "computer vision engineer",
    "RAG developer", "LangChain developer", "AI architect",
    "data engineer AI", "GenAI developer", "vector database",
    "prompt engineer", "AI platform engineer", "Python ML",
]


def _dice_location(j: dict) -> str:
    loc = j.get("location", "")
    if isinstance(loc, dict):
        parts = [loc.get("city", ""), loc.get("state", "")]
        return ", ".join(p for p in parts if p) or "See posting"
    return str(loc) if loc else "See posting"


def _dice_url(j: dict) -> str:
    job_id = j.get("id", "")
    return (
        j.get("applyUrl", "")
        or j.get("jobDetailUrl", "")
        or (f"https://www.dice.com/job-detail/{job_id}" if job_id else "")
    )


def scrape_dice_api(queries=None, posted_date: str = "ONE") -> Generator:
    """Dice JSON search API. posted_date: ONE=24h, THREE=3d, SEVEN=7d."""
    if queries is None:
        queries = DICE_QUERIES
    for q in queries:
        url = (
            "https://job-search-api.scoobee.com/jobs/search"
            f"?q={urllib.parse.quote(q)}"
            "&countryCode2=US"
            f"&postedDate={posted_date}"
            "&pageSize=100"
            "&sort=-postedDate"
        )
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=DICE_HEADERS)
            r.raise_for_status()
            data = r.json()
            jobs_list = (
                data.get("data", {}).get("jobs", [])
                or data.get("jobs", [])
                or (data if isinstance(data, list) else [])
            )
            for j in jobs_list:
                pub = j.get("postedDate", j.get("modifiedDate", ""))
                desc = j.get("descriptionFragment", j.get("jobDescription", ""))
                yield {
                    "source":     "Dice.com",
                    "title":      j.get("title", ""),
                    "company":    j.get("companyName", ""),
                    "location":   _dice_location(j),
                    "salary":     "",
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub or "",
                    "url":        _dice_url(j),
                    "desc":       desc,
                }
            time.sleep(0.4)
        except Exception as e:
            print(f"  [Dice API] {q}: {e}")


DICE_RSS_QUERIES = [
    "machine+learning+engineer", "AI+engineer", "data+scientist",
    "GenAI+developer", "LLM+engineer", "MLOps+engineer",
    "data+engineer", "NLP+engineer", "deep+learning",
    "agentic+AI", "AI+architect", "computer+vision+engineer",
    "generative+AI+developer", "RAG+developer", "LangChain+developer",
    "AI+platform+engineer", "vector+database", "prompt+engineer",
    "AI+agent+developer", "foundation+model+engineer",
]


def scrape_dice_rss(queries=None) -> Generator:
    """Dice RSS feeds — expanded query set, ~15 min freshness."""
    if queries is None:
        queries = DICE_RSS_QUERIES
    for q in queries:
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
            print(f"  [Dice RSS] {q}: {e}")


def scrape_dice() -> Generator:
    """Dice scraper: tries JSON API (scoobee endpoint); RSS fallback removed
    as dice.com RSS feeds now return HTML. Fails gracefully if API is down."""
    yield from scrape_dice_api(posted_date="ONE")


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


# ── Jobicy.com ────────────────────────────────────────────────────────────────

JOBICY_QUERIES = [
    "machine+learning", "AI+engineer", "data+scientist",
    "generative+AI", "LLM", "data+engineer", "python+AI",
    "MLOps", "deep+learning", "NLP",
]


def scrape_jobicy() -> Generator:
    for q in JOBICY_QUERIES:
        # Note: job_types=contract filter returns 0 results — omit it
        url = f"https://jobicy.com/?feed=job_feed&search_keywords={urllib.parse.quote(q)}"
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


# ── The Muse (free API, no key needed) ───────────────────────────────────────

MUSE_CATEGORIES = [
    "Data Science", "Data Engineering & Warehouse",
    "Machine Learning", "Software Engineer",
]

MUSE_QUERIES = [
    "AI", "machine learning", "LLM", "data scientist",
    "generative AI", "MLOps", "NLP", "deep learning",
]


def scrape_the_muse() -> Generator:
    """The Muse public jobs API — free, no key required."""
    for q in MUSE_QUERIES:
        url = (
            f"https://www.themuse.com/api/public/jobs"
            f"?category=Computer+and+IT"
            f"&level=Senior+Level&level=Mid+Level"
            f"&page=0"
        )
        try:
            r    = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
            r.raise_for_status()
            for j in r.json().get("results", []):
                title = j.get("name", "")
                # Filter for AI/ML relevance in title
                if not any(kw.lower() in title.lower() for kw in [
                    "ai", "ml", "machine learning", "data", "nlp",
                    "llm", "python", "cloud", "engineer", "scientist"
                ]):
                    continue
                pub = j.get("publication_date", "")
                company = j.get("company", {})
                company_name = company.get("name", "") if isinstance(company, dict) else ""
                locations = j.get("locations", [])
                loc = locations[0].get("name", "") if locations else "See posting"
                url_apply = j.get("refs", {}).get("landing_page", "")
                yield {
                    "source":     "The Muse",
                    "title":      title,
                    "company":    company_name,
                    "location":   loc,
                    "salary":     "",
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub,
                    "url":        url_apply,
                    "desc":       j.get("contents", ""),
                }
            time.sleep(0.5)
        except Exception as e:
            print(f"  [The Muse] {q}: {e}")
            break


# ── Remotive additional feeds ─────────────────────────────────────────────────
# (SimplyHired and ZipRecruiter both return 403 anti-bot; removed)


# ── Arbeitnow (free, no key) ─────────────────────────────────────────────────

def scrape_arbeitnow() -> Generator:
    """Arbeitnow public job board API — completely free, no key needed."""
    import datetime as _dt
    url = "https://www.arbeitnow.com/api/job-board-api"
    try:
        r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
        for j in r.json().get("data", []):
            pub = j.get("created_at", "")
            # created_at is a Unix timestamp (int) — convert to ISO string
            if isinstance(pub, (int, float)) and pub > 0:
                pub_str = _dt.datetime.utcfromtimestamp(pub).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                pub_str = str(pub) if pub else ""
            yield {
                "source":     "Arbeitnow",
                "title":      j.get("title", ""),
                "company":    j.get("company_name", ""),
                "location":   j.get("location", "Remote"),
                "salary":     "",
                "posted":     pub_str[:10],
                "posted_raw": pub_str,
                "url":        j.get("url", ""),
                "desc":       j.get("description", ""),
            }
    except Exception as e:
        print(f"  [Arbeitnow]: {e}")


# ── JSearch via RapidAPI (optional — set JSEARCH_API_KEY env var) ─────────────

JSEARCH_QUERIES = [
    "AI engineer", "machine learning engineer",
    "generative AI developer", "LLM engineer",
    "data scientist AI", "MLOps engineer",
    "deep learning engineer", "AI architect",
    "RAG developer", "NLP engineer",
]


def scrape_jsearch() -> Generator:
    """JSearch RapidAPI — covers Dice, Indeed, Monster, Glassdoor, ZipRecruiter.
    Needs JSEARCH_API_KEY env var. Free tier: 200 req/month."""
    api_key = os.environ.get("JSEARCH_API_KEY", "")
    if not api_key:
        return
    headers = {
        "X-RapidAPI-Key":  api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    for q in JSEARCH_QUERIES:
        url = (
            f"https://jsearch.p.rapidapi.com/search"
            f"?query={urllib.parse.quote(q)}"
            f"&date_posted=today"
            f"&num_pages=2"
            f"&country=us"
        )
        try:
            r = requests.get(url, timeout=TIMEOUT, headers=headers)
            r.raise_for_status()
            for j in r.json().get("data", []):
                pub = j.get("job_posted_at_datetime_utc", "")
                loc_parts = [j.get("job_city", ""), j.get("job_state", "")]
                loc = ", ".join(p for p in loc_parts if p) or j.get("job_country", "")
                publisher = j.get("job_publisher", "JSearch")
                yield {
                    "source":     publisher,
                    "title":      j.get("job_title", ""),
                    "company":    j.get("employer_name", ""),
                    "location":   loc,
                    "salary":     "",
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub,
                    "url":        j.get("job_apply_link", j.get("job_google_link", "")),
                    "desc":       j.get("job_description", ""),
                }
            time.sleep(1.2)
        except Exception as e:
            print(f"  [JSearch] {q}: {e}")
            break


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
            full_text = BeautifulSoup(text, "html.parser").get_text()
            first_line = full_text[:120]
            yield {
                "source":     "HN Who's Hiring",
                "title":      first_line.strip(),
                "company":    "",
                "location":   "",
                "salary":     "",
                "posted":     "",
                "posted_raw": "",
                "url":        f"https://news.ycombinator.com/item?id={c.get('id', '')}",
                "desc":       full_text[:3000],
            }
        time.sleep(0.3)
    except Exception as e:
        print(f"  [HN Hiring]: {e}")


# ── Master runner ─────────────────────────────────────────────────────────────

SCRAPERS = [
    ("Adzuna",           scrape_adzuna),         # API, broad coverage
    ("Dice.com",         scrape_dice),           # JSON API (graceful fallback if down)
    ("Remotive",         scrape_remotive),       # RSS, remote tech jobs
    ("Jobicy",           scrape_jobicy),         # RSS, remote jobs
    ("WeWorkRemotely",   scrape_weworkremotely), # RSS, remote jobs
    ("Himalayas",        scrape_himalayas),      # JSON API, remote jobs
    ("WorkingNomads",    scrape_working_nomads), # JSON API, remote jobs
    ("The Muse",         scrape_the_muse),       # free API, tech jobs
    ("Arbeitnow",        scrape_arbeitnow),      # free API, no key
    ("JSearch",          scrape_jsearch),        # optional: set JSEARCH_API_KEY
    ("HN Hiring",        scrape_hn_hiring),
    # Remote.co: removed (consistent timeouts)
    # SimplyHired: removed (403 bot protection)
    # ZipRecruiter: removed (403 bot protection)
]


def run_all_scrapers() -> Generator:
    for name, fn in SCRAPERS:
        print(f"  Scraping {name}…")
        try:
            yield from fn()
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")
