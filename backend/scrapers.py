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

import json
import os
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Generator

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobBot/2.0)"}
TIMEOUT = 20

# ── US-only location filter ───────────────────────────────────────────────────

_NON_US_KEYWORDS = frozenset([
    "united kingdom", "england", "scotland", "wales",
    "germany", "france", "netherlands", "india", "canada",
    "australia", "ireland", "poland", "spain", "italy",
    "portugal", "sweden", "norway", "denmark", "finland",
    "new zealand", "south africa", "brazil", "mexico",
    "singapore", "japan", "china", "hong kong", "philippines",
    "pakistan", "bangladesh", "ukraine", "romania", "czech",
    "hungary", "israel", "turkey", "egypt", "kenya", "nigeria",
])

def _is_us_or_remote(location: str) -> bool:
    """True if job location is US-based, remote, or unspecified."""
    if not location or location.lower() in ("", "remote", "see posting", "anywhere", "worldwide"):
        return True
    loc = location.lower()
    for kw in _NON_US_KEYWORDS:
        if kw in loc:
            return False
    return True

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
    # .NET domain
    ".NET developer", "C# developer", "ASP.NET developer",
    ".NET full stack developer", "React developer", "Angular developer",
    # SAP domain
    "SAP TM consultant", "SAP transport management", "SAP TM architect",
    "SAP SCM consultant", "S4HANA TM consultant",
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
    # .NET domain
    ".NET developer", "C# developer", "ASP.NET developer",
    "React developer", "Angular developer", ".NET full stack",
    # SAP domain
    "SAP TM", "SAP transport management", "SAP SCM consultant",
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
            loc = j.get("location", "Remote")
            if not _is_us_or_remote(loc):
                continue
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
                "location":   loc,
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
    # One broad query per domain — keeps within free tier (500 req/month)
    "AI ML engineer contract C2C USA",
    ".NET C# developer contract C2C USA",
    "SAP TM consultant contract C2C USA",
]


# Maps JSearch job_publisher values (lowercased) → UI platform label
_JSEARCH_PUB_MAP = {
    "linkedin":     "LinkedIn",
    "indeed":       "Indeed",
    "glassdoor":    "Glassdoor",
    "ziprecruiter": "ZipRecruiter",
    "monster":      "Monster",
    "dice":         "Dice.com",
    "dice.com":     "Dice.com",
}


def scrape_jsearch() -> Generator:
    """JSearch RapidAPI — covers Dice, Indeed, LinkedIn Jobs, Glassdoor, ZipRecruiter, Monster.
    Set RAPIDAPI_KEY (or JSEARCH_API_KEY). Free tier: 500 req/month."""
    api_key = os.environ.get("RAPIDAPI_KEY") or os.environ.get("JSEARCH_API_KEY", "")
    if not api_key:
        return
    headers = {
        "X-RapidAPI-Key":  api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }
    for q in JSEARCH_QUERIES:
        try:
            r = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                params={
                    "query":       q,
                    "date_posted": "today",
                    "num_pages":   "1",
                    "country":     "us",
                },
                timeout=35,
                headers=headers,
            )
            r.raise_for_status()
            for j in r.json().get("data", []):
                pub = j.get("job_posted_at_datetime_utc", "")
                loc_parts = [j.get("job_city", ""), j.get("job_state", "")]
                loc = ", ".join(p for p in loc_parts if p) or j.get("job_country", "Remote")
                publisher = j.get("job_publisher", "JSearch")
                publisher = _JSEARCH_PUB_MAP.get(publisher.lower(), publisher)
                yield {
                    "source":     publisher,
                    "title":      j.get("job_title", ""),
                    "company":    j.get("employer_name", ""),
                    "location":   loc,
                    "salary":     "",
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub,
                    "url":        j.get("job_apply_link") or j.get("job_google_link", ""),
                    "desc":       j.get("job_description", ""),
                }
            time.sleep(1.2)
        except Exception as e:
            print(f"  [JSearch] {q}: {e}")
            if "429" in str(e):
                time.sleep(10)
                break
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


# ── Jooble (aggregator API, 140+ countries) ───────────────────────────────────

JOOBLE_QUERIES = [
    "AI engineer C2C",
    "machine learning engineer contract",
    "LLM engineer C2C",
    "generative AI developer C2C",
    "data scientist C2C",
    "MLOps engineer C2C",
    "Python developer AI C2C",
    "NLP engineer contract",
    "deep learning engineer C2C",
    "AI architect C2C",
    "GenAI developer C2C",
    "RAG developer contract",
    "agentic AI engineer C2C",
    # .NET domain
    ".NET developer C2C",
    "C# developer contract",
    "React developer C2C",
    "Angular developer C2C",
    # SAP domain
    "SAP TM consultant C2C",
    "SAP transport management contract",
    "SAP SCM consultant C2C",
]


def scrape_jooble() -> Generator:
    """Jooble job aggregator — 140+ countries. Free key at jooble.org/api."""
    api_key = os.environ.get("JOOBLE_API_KEY", "")
    if not api_key:
        return
    for q in JOOBLE_QUERIES:
        try:
            resp = requests.post(
                f"https://jooble.org/api/{api_key}",
                json={"keywords": q, "location": "United States", "page": 1, "jobType": 4},
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            resp.raise_for_status()
            for j in resp.json().get("jobs", []):
                pub = j.get("updated", "")
                loc = j.get("location", "")
                if not _is_us_or_remote(loc):
                    continue
                title   = j.get("title", "")
                snippet = j.get("snippet", "")
                # Only keep contract/C2C jobs — Jooble jobType=4 helps but isn't strict
                _CONTRACT_RE = re.compile(
                    r"\b(contract|c2c|corp[\s\-]?to[\s\-]?corp|1099|w2|freelance"
                    r"|c2c[\s/]?ok|contract[\s\-]?to[\s\-]?hire|independent[\s\-]?contractor)\b",
                    re.IGNORECASE
                )
                if not _CONTRACT_RE.search(title + " " + snippet):
                    continue
                yield {
                    "source":     "Jooble",
                    "title":      title,
                    "company":    j.get("company", ""),
                    "location":   loc,
                    "salary":     j.get("salary", ""),
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub,
                    "url":        j.get("link", ""),
                    "desc":       snippet,
                }
            time.sleep(0.5)
        except Exception as e:
            print(f"  [Jooble] {q}: {e}")


# ── ScrapFly — LinkedIn Jobs + Indeed direct scraping ─────────────────────────
# Set SCRAPFLY_KEY. Scrapes public pages with anti-bot bypass.
# LinkedIn Jobs: public, no login. Contract filter, past 24h, sorted by date.
# Indeed: direct scraping with higher volume than JSearch rate limits allow.

_SCRAPFLY_QUERIES = [
    # Broad queries — one per domain to stay within concurrency limits
    "AI ML engineer contract C2C",
    ".NET C# developer contract C2C",
    "SAP TM consultant contract C2C",
]


def _scrapfly_get(api_key: str, url: str, render_js: bool = False) -> str:
    """Fetch a page via ScrapFly with anti-bot bypass. Returns HTML or ''."""
    try:
        resp = requests.get(
            "https://api.scrapfly.io/scrape",
            params={
                "key":       api_key,
                "url":       url,
                "asp":       "true",
                "render_js": "true" if render_js else "false",
                "country":   "us",
            },
            timeout=40,
        )
        resp.raise_for_status()
        return resp.json().get("result", {}).get("content", "")
    except Exception as e:
        print(f"  [ScrapFly] {url[:60]}… error: {e}")
        return ""


def scrape_linkedin_jobs_scrapfly() -> Generator:
    """Scrape LinkedIn public job listings via ScrapFly.
    Filters: Contract type, past 24h, US, sorted by date — no login required."""
    api_key = os.environ.get("SCRAPFLY_KEY", "")
    if not api_key:
        return

    for q in _SCRAPFLY_QUERIES:
        url = (
            "https://www.linkedin.com/jobs/search/"
            f"?keywords={urllib.parse.quote(q)}"
            "&location=United+States"
            "&f_TPR=r86400"   # past 24 hours
            "&sortBy=DD"       # date descending
            "&f_JT=C"          # Contract job type
        )
        html = _scrapfly_get(api_key, url, render_js=False)
        if not html:
            time.sleep(3)
            continue

        soup = BeautifulSoup(html, "lxml")
        found = 0

        # LinkedIn embeds job data as JSON-LD in public search results
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if item.get("@type") != "JobPosting":
                        continue
                    pub = item.get("datePosted", "")
                    loc_obj = item.get("jobLocation", {})
                    if isinstance(loc_obj, list):
                        loc_obj = loc_obj[0] if loc_obj else {}
                    addr = loc_obj.get("address", {})
                    loc = ", ".join(filter(None, [
                        addr.get("addressLocality", ""),
                        addr.get("addressRegion", ""),
                    ])) or "United States"
                    apply_url = item.get("url") or item.get("sameAs", "")
                    title = item.get("title", "")
                    if title and apply_url:
                        yield {
                            "source":     "LinkedIn",
                            "title":      title,
                            "company":    item.get("hiringOrganization", {}).get("name", ""),
                            "location":   loc,
                            "salary":     "",
                            "posted":     pub[:10] if pub else "",
                            "posted_raw": pub,
                            "url":        apply_url,
                            "desc":       item.get("description", "")[:500],
                        }
                        found += 1
            except (json.JSONDecodeError, AttributeError):
                continue

        print(f"  [LinkedIn/ScrapFly] '{q}' → {found} jobs")
        time.sleep(3)


def scrape_indeed_scrapfly() -> Generator:
    """Scrape Indeed job listings via ScrapFly — higher volume than JSearch limits.
    Parses embedded mosaic JSON (fast, reliable). Falls back to HTML card parsing."""
    api_key = os.environ.get("SCRAPFLY_KEY", "")
    if not api_key:
        return

    for q in _SCRAPFLY_QUERIES:
        url = (
            "https://www.indeed.com/jobs"
            f"?q={urllib.parse.quote(q)}"
            "&l=United+States"
            "&sort=date"
            "&fromage=1"   # past 24 hours
        )
        html = _scrapfly_get(api_key, url, render_js=False)
        if not html:
            time.sleep(3)
            continue

        found = 0

        # Indeed embeds all job card data as window.mosaic JSON
        match = re.search(
            r'window\.mosaic\.providerData\["mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});\s*(?:window|$)',
            html, re.DOTALL,
        )
        if match:
            try:
                data = json.loads(match.group(1))
                results = (
                    data.get("metaData", {})
                        .get("mosaicProviderJobCardsModel", {})
                        .get("results", [])
                )
                import datetime as _idt
                for j in results:
                    pub_ms = j.get("pubDate", 0)
                    pub = (
                        _idt.datetime.utcfromtimestamp(pub_ms / 1000).strftime("%Y-%m-%dT%H:%M:%SZ")
                        if pub_ms else ""
                    )
                    sal = j.get("extractedSalary", {})
                    salary = f"${sal.get('max', '')}" if isinstance(sal, dict) and sal.get("max") else ""
                    yield {
                        "source":     "Indeed",
                        "title":      j.get("title", ""),
                        "company":    j.get("company", ""),
                        "location":   j.get("formattedLocation", ""),
                        "salary":     salary,
                        "posted":     pub[:10] if pub else "",
                        "posted_raw": pub,
                        "url":        f"https://www.indeed.com/viewjob?jk={j.get('jobkey', '')}",
                        "desc":       j.get("snippet", ""),
                    }
                    found += 1
            except (json.JSONDecodeError, KeyError):
                pass

        # HTML fallback if mosaic JSON not found
        if found == 0:
            soup = BeautifulSoup(html, "lxml")
            for card in soup.find_all("td", class_="resultContent"):
                title_el = card.find("h2", class_=lambda c: c and "jobTitle" in c)
                company_el = card.find("span", attrs={"data-testid": "company-name"})
                loc_el = card.find("div", attrs={"data-testid": "text-location"})
                link_el = card.find("a", href=re.compile(r"/rc/clk|/pagead/clk|/viewjob"))
                if title_el and link_el:
                    href = link_el.get("href", "")
                    full_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                    yield {
                        "source":     "Indeed",
                        "title":      title_el.get_text(strip=True),
                        "company":    company_el.get_text(strip=True) if company_el else "",
                        "location":   loc_el.get_text(strip=True) if loc_el else "",
                        "salary":     "",
                        "posted":     "",
                        "posted_raw": "",
                        "url":        full_url,
                        "desc":       "",
                    }
                    found += 1

        print(f"  [Indeed/ScrapFly] '{q}' → {found} jobs")
        time.sleep(2)


# ── LinkedIn Jobs (free guest API — no API key required) ─────────────────────
# Uses LinkedIn's public job search guest endpoint. No login, no API key.
# Returns up to 30 results per query (3 pages × 10 results).

# All queries run together — match_role() routes each job to the right domain tab.
_LI_FREE_ALL_QUERIES = [
    # ── .NET domain ───────────────────────────────────────────────────────────
    "C# developer C2C contract",
    "ASP.NET developer contract",
    ".NET architect contract",
    ".NET software engineer C2C",
    ".NET full stack developer contract",
    ".NET microservices developer C2C",
    "dotNet developer contract",
    ".NET developer remote contract",
    ".NET developer W2 contract",
    "dotnet C# developer contract",
    ".NET web API developer contract",
    ".NET MVC developer contract",
    # ── AI / ML domain ────────────────────────────────────────────────────────
    "AI engineer C2C contract",
    "machine learning engineer C2C",
    "LLM engineer contract C2C",
    "generative AI developer C2C",
    "MLOps engineer contract",
    "data scientist C2C",
    "NLP engineer contract C2C",
    "agentic AI developer C2C",
    "AI ML engineer contract",
    "deep learning engineer C2C",
    "RAG developer contract",
    "GenAI engineer C2C",
    # ── SAP domain ────────────────────────────────────────────────────────────
    "SAP TM consultant contract",
    "SAP transport management C2C",
    "SAP SCM consultant contract",
    "S4HANA TM consultant C2C",
]

_NO_C2C_TITLE_RE = re.compile(
    r"\bno[\s\-]c2c\b|\bnot[\s\-]c2c\b|no[\s\-]corp[\s\-]to[\s\-]corp",
    re.IGNORECASE,
)

# Companies whose LinkedIn postings are actually sourced from Dice.com
_DICE_COMPANY_RE = re.compile(r"jobs\s+via\s+dice|dice\.com", re.IGNORECASE)


def scrape_linkedin_jobs_free() -> Generator:
    """Scrape LinkedIn public jobs via the free guest API — no API key needed.
    Covers AI/ML, .NET, and SAP C2C/contract positions posted in the last 24 hours.
    Jobs from 'Jobs via Dice' are re-attributed to source='Dice.com'."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.linkedin.com/",
    }
    for q in _LI_FREE_ALL_QUERIES:
        found = 0
        for start in (0, 10, 20):
            try:
                r = requests.get(
                    "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search",
                    params={
                        "keywords": q,
                        "location": "United States",
                        "f_TPR":    "r86400",   # past 24 hours — strict
                        "start":    start,
                    },
                    headers=headers,
                    timeout=15,
                )
                if r.status_code != 200:
                    break
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.find_all("li")
                if not cards:
                    break
                for card in cards:
                    title_el = card.find("h3", class_="base-search-card__title")
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    if _NO_C2C_TITLE_RE.search(title):
                        continue
                    company_el = card.find("h4", class_="base-search-card__subtitle")
                    company = company_el.get_text(strip=True) if company_el else ""
                    loc_el = card.find("span", class_="job-search-card__location")
                    location = loc_el.get_text(strip=True) if loc_el else "United States"
                    if not _is_us_or_remote(location):
                        continue
                    time_el = card.find("time")
                    posted_raw = time_el.get("datetime", "") if time_el else ""
                    link_el = card.find("a", class_="base-card__full-link")
                    job_url = link_el.get("href", "").split("?")[0] if link_el else ""
                    if not title or not job_url:
                        continue
                    source = "LinkedIn"
                    yield {
                        "source":     source,
                        "title":      title,
                        "company":    company,
                        "location":   location,
                        "salary":     "",
                        "posted":     posted_raw[:10] if posted_raw else "",
                        "posted_raw": posted_raw,
                        "url":        job_url,
                        "desc":       "",
                    }
                    found += 1
                time.sleep(2)
                if len(cards) < 10:
                    break
            except Exception as e:
                print(f"  [LinkedIn/Free] '{q}' start={start}: {e}")
                break
        print(f"  [LinkedIn/Free] '{q}' → {found} jobs")
        time.sleep(1)


def scrape_dice_scrapfly() -> Generator:
    """Scrape Dice.com job listings via ScrapFly with JS rendering."""
    api_key = os.environ.get("SCRAPFLY_KEY", "")
    if not api_key:
        return
    queries = [
        "AI ML engineer C2C contract",
        ".NET C# developer C2C contract",
        "SAP TM consultant C2C contract",
    ]
    for q in queries:
        url = (
            f"https://www.dice.com/jobs?q={urllib.parse.quote(q)}"
            "&countryCode2=US&filters.postedDate=ONE&pageSize=20&sort=-postedDate"
        )
        html = _scrapfly_get(api_key, url, render_js=True)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        found = 0
        for card in soup.select("dhi-search-card, [data-cy='card-title-link'], a[id^='card-title-link']"):
            title_el = card.select_one("a[id^='card-title-link'], [data-cy='card-title-link']") or card
            title = title_el.get_text(strip=True)
            if not title:
                continue
            href = title_el.get("href", "")
            job_url = f"https://www.dice.com{href}" if href.startswith("/") else href
            company_el = card.select_one("[data-cy='search-result-company-name'], .company-name")
            company = company_el.get_text(strip=True) if company_el else ""
            loc_el = card.select_one("[data-cy='search-result-location'], .location")
            location = loc_el.get_text(strip=True) if loc_el else "United States"
            if job_url and title:
                yield {
                    "source":     "Dice.com",
                    "title":      title,
                    "company":    company,
                    "location":   location,
                    "salary":     "",
                    "posted":     "",
                    "posted_raw": "",
                    "url":        job_url,
                    "desc":       "",
                }
                found += 1
        print(f"  [Dice/ScrapFly] '{q}' → {found} jobs")
        time.sleep(2)


_DICE_APIFY_QUERIES = [
    "AI ML engineer contract C2C",
    "machine learning engineer C2C contract",
    "LLM engineer C2C",
    "generative AI developer contract",
    "data scientist C2C",
    "Python developer AI C2C",
    ".NET developer C2C contract",
    "C# developer C2C",
    "SAP TM consultant C2C contract",
    "SAP SCM consultant C2C",
]


def scrape_dice_apify() -> Generator:
    """Scrape Dice.com via Apify actor shahidirfan~Dice-Job-Scraper.
    Requires APIFY_TOKEN. Falls back silently if limit exceeded."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        return
    actor = "shahidirfan~Dice-Job-Scraper"
    for q in _DICE_APIFY_QUERIES:
        try:
            resp = requests.post(
                f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
                params={"token": token, "timeout": 90, "memory": 1024},
                json={"keyword": q, "maxItems": 20, "datePosted": "1"},
                timeout=120,
            )
            if resp.status_code == 403:
                err = resp.json().get("error", {}).get("type", "")
                if "limit" in err:
                    print(f"  [Dice/Apify] Monthly limit exceeded — upgrade Apify plan")
                    return
            resp.raise_for_status()
            data  = resp.json()
            items = data if isinstance(data, list) else data.get("items", [])
            cutoff = datetime.utcnow() - timedelta(hours=24)
            kept = 0
            for j in items:
                title   = j.get("title") or j.get("jobTitle") or j.get("name") or ""
                company = j.get("company") or j.get("companyName") or j.get("employer") or ""
                loc     = j.get("location") or j.get("city") or "United States"
                url     = j.get("url") or j.get("jobUrl") or j.get("link") or ""
                desc    = j.get("description") or j.get("jobDescription") or j.get("summary") or ""
                pub     = j.get("postedDate") or j.get("datePosted") or j.get("date") or ""
                if not url or not title:
                    continue
                if not _is_us_or_remote(loc):
                    continue
                # Drop anything older than 24 hours
                if pub:
                    try:
                        dt = datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                        dt_utc = dt.replace(tzinfo=None) if dt.tzinfo else dt
                        if dt_utc < cutoff:
                            continue
                    except Exception:
                        pass
                yield {
                    "source":     "Dice.com",
                    "title":      title,
                    "company":    company,
                    "location":   loc,
                    "salary":     j.get("salary") or j.get("pay") or "",
                    "posted":     pub[:10] if pub else "",
                    "posted_raw": pub,
                    "url":        url,
                    "desc":       str(desc)[:3000],
                }
                kept += 1
            print(f"  [Dice/Apify] '{q}' → {kept}/{len(items)} jobs (past 24h)")
            time.sleep(1)
        except Exception as e:
            print(f"  [Dice/Apify] '{q}' error: {e}")
            if "429" in str(e):
                time.sleep(10)
                break


# ── Master runner ─────────────────────────────────────────────────────────────

SCRAPERS = [
    ("Adzuna",             scrape_adzuna),                 # API, US only
    ("Remotive",           scrape_remotive),               # RSS, remote tech jobs
    ("Jobicy",             scrape_jobicy),                 # RSS, remote jobs
    ("WeWorkRemotely",     scrape_weworkremotely),         # RSS, remote jobs
    ("Himalayas",          scrape_himalayas),              # JSON API, remote jobs
    ("WorkingNomads",      scrape_working_nomads),         # JSON API, remote jobs
    ("The Muse",           scrape_the_muse),               # free API, tech jobs
    ("Arbeitnow",          scrape_arbeitnow),              # free API, US-filtered
    ("LinkedIn/Free",      scrape_linkedin_jobs_free),     # FREE — no key, LinkedIn guest API, .NET C2C, past 24h
    ("JSearch",            scrape_jsearch),                # RAPIDAPI_KEY — Dice/Indeed/LinkedIn/Glassdoor/ZipRecruiter
    ("Jooble",             scrape_jooble),                 # JOOBLE_API_KEY — 140-country aggregator
    ("Dice/ScrapFly",      scrape_dice_scrapfly),          # SCRAPFLY_KEY — Dice.com, contract jobs
    ("LinkedIn/ScrapFly",  scrape_linkedin_jobs_scrapfly), # SCRAPFLY_KEY — LinkedIn Jobs, contract, past 24h
    ("Indeed/ScrapFly",    scrape_indeed_scrapfly),        # SCRAPFLY_KEY — Indeed, past 24h, high volume
    ("HN Hiring",          scrape_hn_hiring),
]


def run_all_scrapers() -> Generator:
    for name, fn in SCRAPERS:
        print(f"  Scraping {name}…")
        try:
            yield from fn()
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")


# ── LinkedIn Posts (no-login, multi-API) ─────────────────────────────────────
#
# Sources (configure via env vars — all optional, DuckDuckGo always runs):
#   SERPAPI_KEY     → SerpAPI  (Google search, ~100 free/mo, paid plans)
#   SERPER_API_KEY  → Serper.dev (Google search, cheaper alternative)
#   APIFY_TOKEN     → Apify LinkedIn Post Search actor
# DuckDuckGo requires no key and is always used as a supplement/fallback.
#
# All results are merged and deduplicated by URL.

_LI_BASE = "#c2c #Hiring"

AIML_POST_QUERIES = [
    f"{_LI_BASE} AI Engineer",
    f"{_LI_BASE} ML Engineer",
    f"{_LI_BASE} Machine Learning Engineer",
    f"{_LI_BASE} LLM Engineer",
    f"{_LI_BASE} GenAI Engineer",
    f"{_LI_BASE} Data Scientist",
    f"{_LI_BASE} Python Developer",
    f"{_LI_BASE} MLOps Engineer",
    f"{_LI_BASE} NLP Engineer",
    f"{_LI_BASE} Deep Learning Engineer",
    f"{_LI_BASE} RAG Developer",
    f"{_LI_BASE} Agentic AI",
    f"{_LI_BASE} AI/ML Engineer",
    f"{_LI_BASE} Python Engineer",
]

DOTNET_POST_QUERIES = [
    f"{_LI_BASE} .NET Developer",
    f"{_LI_BASE} Senior .NET Developer",
    f"{_LI_BASE} .NET Software Engineer",
    f"{_LI_BASE} .NET Full Stack Developer",
    f"{_LI_BASE} .NET Backend Developer",
    f"{_LI_BASE} C# Developer",
    f"{_LI_BASE} ASP.NET Developer",
    f"{_LI_BASE} React Developer",
    f"{_LI_BASE} Angular Developer",
]

SAP_POST_QUERIES = [
    f"{_LI_BASE} SAP TM",
    f"{_LI_BASE} SAP Transport Management",
    f"{_LI_BASE} SAP TM Architect",
    f"{_LI_BASE} SAP TM Functional Consultant",
    f"{_LI_BASE} SAP TM Solution Consultant",
    f"{_LI_BASE} SAP SCM Consultant",
    f"{_LI_BASE} S4HANA TM",
]

_DOMAIN_POST_QUERIES = {
    "AIML":   AIML_POST_QUERIES,
    "DOTNET": DOTNET_POST_QUERIES,
    "SAP":    SAP_POST_QUERIES,
}

# Keep legacy alias for compatibility
LINKEDIN_POST_QUERIES = AIML_POST_QUERIES

_LI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    )
}


def _norm_li_url(url: str) -> str:
    """Strip tracking params and trailing slash for dedup."""
    return url.split("?")[0].rstrip("/")


def _is_li_post_url(url: str) -> bool:
    return "linkedin.com" in url and (
        "/posts/" in url or "/feed/update/" in url
    )


def _build_li_post(url: str, title: str, snippet: str, date: str, query: str) -> dict:
    url = _norm_li_url(url)
    # "John Doe on LinkedIn: post text…" → extract author before " on LinkedIn"
    author_name = re.sub(r"\s+on LinkedIn.*", "", title, flags=re.IGNORECASE).strip()
    if not author_name or len(author_name) > 80:
        author_name = ""
    role_keyword = re.sub(r"^#c2c\s+#Hiring\s*", "", query, flags=re.IGNORECASE).strip()
    return {
        "post_url":       url,
        "author_name":    author_name,
        "author_title":   "",
        "author_url":     "",
        "content":        snippet[:2000],
        "posted_at":      date,
        "likes_count":    0,
        "comments_count": 0,
        "search_query":   query,
        "role_keyword":   role_keyword,
    }


# ── Source 1: SerpAPI (Google) ───────────────────────────────────────────────

def _li_serpapi(query: str) -> list[dict]:
    api_key = os.environ.get("SERPAPI_KEY", "")
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "engine":  "google",
                "q":       f'site:linkedin.com/posts {query}',
                "tbs":     "qdr:d,sbd:1",   # past 24 hours, sorted by date (most recent first)
                "num":     20,
                "api_key": api_key,
            },
            timeout=20,
        )
        resp.raise_for_status()
        posts = []
        for r in resp.json().get("organic_results", []):
            url = r.get("link", "")
            if not _is_li_post_url(url):
                continue
            posts.append(_build_li_post(
                url, r.get("title", ""), r.get("snippet", ""), r.get("date", ""), query
            ))
        print(f"[LinkedIn/SerpAPI] '{query}' → {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[LinkedIn/SerpAPI] '{query}' error: {e}")
        return []


# ── Source 2: Serper.dev (Google, cheaper) ───────────────────────────────────

def _li_serper(query: str) -> list[dict]:
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        return []
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": f'site:linkedin.com/posts {query}', "tbs": "qdr:d,sbd:1", "num": 20},
            timeout=15,
        )
        resp.raise_for_status()
        posts = []
        for r in resp.json().get("organic", []):
            url = r.get("link", "")
            if not _is_li_post_url(url):
                continue
            posts.append(_build_li_post(
                url, r.get("title", ""), r.get("snippet", ""), r.get("date", ""), query
            ))
        print(f"[LinkedIn/Serper] '{query}' → {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[LinkedIn/Serper] '{query}' error: {e}")
        return []


# ── Source 3: Apify LinkedIn Post Scraper ────────────────────────────────────
# Set APIFY_TOKEN. Recommended actor: bebity/linkedin-posts-scraper
# (sign up at apify.com → get API token → set APIFY_ACTOR_ID if using a different actor)

def _li_apify(query: str) -> list[dict]:
    """Run Apify LinkedIn post scraper for one query.
    Uses real browser sessions — the only reliable source for recent posts."""
    token = os.environ.get("APIFY_TOKEN", "")
    if not token:
        return []
    actor = os.environ.get("APIFY_ACTOR_ID", "buIWk2uOUzTmcLsuB")
    try:
        resp = requests.post(
            f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
            params={"token": token, "timeout": 120, "memory": 512},
            json={
                "searchQueries": [query],
                "resultsLimit":  25,
                "datePosted":    "past-24h",
                "sortBy":        "date",
            },
            timeout=150,
        )
        resp.raise_for_status()
        data  = resp.json()
        items = data if isinstance(data, list) else data.get("items", data.get("results", []))

        posts = []
        for item in items:
            # harvestapi~linkedin-post-search schema
            url = _norm_li_url(
                item.get("linkedinUrl") or item.get("shareLinkedinUrl") or
                item.get("url") or item.get("postUrl") or item.get("link", "")
            )
            if not _is_li_post_url(url):
                continue

            author_obj = item.get("author") or {}
            if isinstance(author_obj, dict):
                author       = author_obj.get("name", "")
                author_title = author_obj.get("info", "")
                author_url   = author_obj.get("linkedinUrl", "")
            else:
                author       = str(author_obj)
                author_title = ""
                author_url   = ""

            content    = item.get("content") or item.get("text") or item.get("postText") or ""

            posted_raw = item.get("postedAt") or {}
            if isinstance(posted_raw, dict):
                posted_at = posted_raw.get("date") or posted_raw.get("postedAgoText", "")
            else:
                posted_at = str(posted_raw)

            engagement = item.get("engagement") or item.get("socialContent") or {}
            likes    = int(item.get("reactions") or (engagement.get("likes") if isinstance(engagement, dict) else 0) or 0)
            comments = int(item.get("comments") or (engagement.get("comments") if isinstance(engagement, dict) else 0) or 0)

            q_obj      = item.get("query") or {}
            item_query = (q_obj.get("search") if isinstance(q_obj, dict) else str(q_obj)) or query

            posts.append({
                "post_url":       url,
                "author_name":    str(author)[:200],
                "author_title":   str(author_title)[:300],
                "author_url":     str(author_url)[:500],
                "content":        str(content)[:2000],
                "posted_at":      str(posted_at)[:100],
                "likes_count":    likes,
                "comments_count": comments,
                "search_query":   item_query,
                "role_keyword":   re.sub(r"^#c2c\s+#Hiring\s*", "", item_query, flags=re.IGNORECASE).strip(),
            })

        print(f"[LinkedIn/Apify] '{query}' → {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[LinkedIn/Apify] '{query}' error: {e}")
        return []


# ── Source 4: DuckDuckGo — NOTE: returns 0 results for LinkedIn posts ─────────
# LinkedIn blocks all search engine indexing of their posts.
# DuckDuckGo, Google scraping, and Bing all return 0 LinkedIn post results.
# This function is kept as a stub; real results require a paid API key:
#   SERPAPI_KEY    → SerpAPI  (serpapi.com — 100 free/month, no credit card)
#   SERPER_API_KEY → Serper.dev
#   APIFY_TOKEN    → Apify LinkedIn Post scraper

def _li_duckduckgo(query: str) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            return []
    try:
        with DDGS() as ddgs:
            raw = list(ddgs.text(
                keywords=f'site:linkedin.com/posts {query}',
                max_results=15,
                timelimit="d",   # past 24 hours
                # note: sort="date" is not a valid param — removed
            ))
        posts = []
        for r in raw:
            url = r.get("href", "")
            if not _is_li_post_url(url):
                continue
            posts.append(_build_li_post(
                url, r.get("title", ""), r.get("body", ""), "", query
            ))
        print(f"[LinkedIn/DDG] '{query}' → {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[LinkedIn/DDG] '{query}' error: {e}")
        return []


# ── Main entry point ──────────────────────────────────────────────────────────

def scrape_linkedin_posts(domain: str = "AIML") -> list[dict]:
    """Pull LinkedIn posts for a domain from all configured no-login APIs and deduplicate.

    domain: 'AIML' | 'DOTNET' | 'SAP'
    Source priority (configure via env vars):
      APIFY_TOKEN     → Apify (real browser, most reliable — recommended)
      SERPAPI_KEY     → SerpAPI Google search (indexes ~1-6h old posts)
      SERPER_API_KEY  → Serper.dev Google search (cheaper alternative)
    Note: DuckDuckGo/Google direct scraping return 0 results — LinkedIn blocks indexing.
    """
    all_posts: list[dict] = []
    seen_urls: set[str]   = set()

    has_serpapi = bool(os.environ.get("SERPAPI_KEY"))
    has_serper  = bool(os.environ.get("SERPER_API_KEY"))
    has_apify   = bool(os.environ.get("APIFY_TOKEN"))

    if not (has_apify or has_serpapi or has_serper):
        print(f"[LinkedIn Posts/{domain}] No API keys configured — set APIFY_TOKEN for best results.")
        return []

    queries = _DOMAIN_POST_QUERIES.get(domain, AIML_POST_QUERIES)

    def _add(posts: list[dict]):
        for p in posts:
            url = _norm_li_url(p.get("post_url", ""))
            if url and url not in seen_urls:
                seen_urls.add(url)
                p["post_url"] = url
                p["domain"]   = domain
                all_posts.append(p)

    for query in queries:
        if has_apify:
            _add(_li_apify(query))
            time.sleep(1.0)

        if has_serpapi:
            _add(_li_serpapi(query))
            time.sleep(0.5)

        if has_serper:
            _add(_li_serper(query))
            time.sleep(0.5)

        already = sum(1 for p in all_posts if p.get("search_query") == query)
        if already == 0:
            _add(_li_duckduckgo(query))
            time.sleep(1.2)

    # Drop anything older than 24 hours
    cutoff = datetime.utcnow() - timedelta(hours=24)
    filtered = []
    for p in all_posts:
        ts = p.get("posted_at", "")
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            dt_utc = dt.replace(tzinfo=None) if dt.tzinfo else dt
            if dt_utc < cutoff:
                continue
        except Exception:
            pass  # can't parse → keep it
        filtered.append(p)

    print(f"[LinkedIn Posts/{domain}] Done — {len(filtered)}/{len(all_posts)} posts within 24h from {len(queries)} queries.")
    return filtered
