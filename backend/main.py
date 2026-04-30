"""
C2C AI Job Board — FastAPI backend
• Runs hourly scraping via APScheduler
• Stores jobs in SQLite with scraped_at + posted_date timestamps
• Serves REST API consumed by the React frontend
"""
import os
import threading
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import FastAPI, Depends, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Job, SessionLocal, create_tables
from scrapers import run_all_scrapers
from semantic import semantic_score, SEMANTIC_THRESHOLD, AI_RELATED_LABEL
from utils import match_role, is_c2c, is_vendor, extract_pay, _is_recent, _fmt_date, _refresh_cutoff, MAX_AGE_DAYS

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

app = FastAPI(title="C2C AI Job Board", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── global scrape state ───────────────────────────────────────────────────────
_state = {
    "is_scraping":  False,
    "last_scraped": None,
    "last_added":   0,
    "next_scrape":  None,
    "errors":       [],
}

if HAS_SCHEDULER:
    _scheduler = BackgroundScheduler(timezone="UTC")


# ── core scrape logic ─────────────────────────────────────────────────────────

def run_scrape():
    if _state["is_scraping"]:
        print("[Scraper] Already running, skipping.")
        return

    _state["is_scraping"] = True
    _state["errors"] = []
    _refresh_cutoff()
    print(f"\n[Scraper] Starting at {datetime.utcnow().isoformat()}Z")

    db = SessionLocal()
    try:
        # Purge jobs older than MAX_AGE_DAYS so the board stays fresh
        cutoff_str = (datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        deleted = db.query(Job).filter(
            Job.posted_date != "",
            Job.posted_date < cutoff_str,
        ).delete(synchronize_session=False)
        db.commit()
        if deleted:
            print(f"[Scraper] Purged {deleted} jobs older than {MAX_AGE_DAYS} days.")

        existing_urls = {row.url for row in db.query(Job.url).all()}
        # Title+company combo dedup — catches same job posted on multiple boards
        existing_combos = {
            (r.title.lower().strip(), r.company.lower().strip())
            for r in db.query(Job.title, Job.company).all()
        }
        seen_this_run: set[str] = set()
        added = 0

        for raw in run_all_scrapers():
            url = raw.get("url", "").strip()
            if not url or url in seen_this_run or url in existing_urls:
                continue
            seen_this_run.add(url)

            combo = (raw.get("title", "").lower().strip(), raw.get("company", "").lower().strip())
            if combo[0] and combo in existing_combos:
                continue
            existing_combos.add(combo)

            posted_raw = raw.get("posted_raw", raw.get("posted", ""))
            if not _is_recent(posted_raw):
                continue

            title = raw.get("title", "").strip()
            desc  = raw.get("desc",  "").strip()

            category = match_role(title, desc)
            score    = semantic_score(title, desc)

            if category is None and score < SEMANTIC_THRESHOLD:
                continue

            if category is None:
                category = AI_RELATED_LABEL

            salary = raw.get("salary", "") or extract_pay(desc)

            job = Job(
                url           = url,
                title         = title,
                company       = raw.get("company", ""),
                location      = raw.get("location", ""),
                salary        = salary,
                posted_date   = _fmt_date(posted_raw),
                scraped_at    = datetime.utcnow(),
                source        = raw.get("source", ""),
                role_category = category,
                description   = desc[:3000],
                is_c2c        = is_c2c(desc + " " + title),
                is_vendor     = is_vendor(raw.get("company", "")),
                semantic_score= round(score, 4),
            )
            db.add(job)
            existing_urls.add(url)
            added += 1

            if added % 50 == 0:
                db.commit()

        db.commit()
        _state["last_added"]   = added
        _state["last_scraped"] = datetime.utcnow().isoformat() + "Z"
        print(f"[Scraper] Done — {added} new jobs added.")

    except Exception as e:
        import traceback
        msg = str(e)
        _state["errors"].append(msg)
        print(f"[Scraper] Error: {msg}")
        traceback.print_exc()
    finally:
        db.close()
        _state["is_scraping"] = False
        if HAS_SCHEDULER:
            job = _scheduler.get_job("scraper")
            if job and job.next_run_time:
                _state["next_scrape"] = job.next_run_time.isoformat()


# ── startup / shutdown ────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    create_tables()

    if HAS_SCHEDULER:
        _scheduler.add_job(
            run_scrape,
            trigger=IntervalTrigger(hours=1),
            id="scraper",
            replace_existing=True,
            misfire_grace_time=300,
        )
        _scheduler.start()
        job = _scheduler.get_job("scraper")
        if job and job.next_run_time:
            _state["next_scrape"] = job.next_run_time.isoformat()

    # Initial scrape in background so startup doesn't block
    t = threading.Thread(target=run_scrape, daemon=True)
    t.start()


@app.on_event("shutdown")
def shutdown():
    if HAS_SCHEDULER:
        _scheduler.shutdown(wait=False)


# ── dependency ────────────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── helpers ───────────────────────────────────────────────────────────────────

def job_to_dict(j: Job) -> dict:
    return {
        "id":             j.id,
        "url":            j.url,
        "title":          j.title,
        "company":        j.company,
        "location":       j.location,
        "salary":         j.salary,
        "posted_date":    j.posted_date,
        "scraped_at":     j.scraped_at.isoformat() + "Z" if j.scraped_at else None,
        "source":         j.source,
        "role_category":  j.role_category,
        "is_c2c":         j.is_c2c,
        "is_vendor":      j.is_vendor,
        "semantic_score": j.semantic_score,
        "status":         j.status,
    }


# ── endpoints ─────────────────────────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs(
    db:          Session = Depends(get_db),
    page:        int     = Query(1, ge=1),
    per_page:    int     = Query(50, ge=1, le=200),
    search:      Optional[str] = None,
    category:    Optional[str] = None,
    source:      Optional[str] = None,
    c2c_only:    bool = False,
    vendor_only: bool = False,
    days:        Optional[int] = None,
    sort:        str  = "newest",
):
    q = db.query(Job)

    if search:
        term = f"%{search}%"
        q = q.filter(
            Job.title.ilike(term) |
            Job.company.ilike(term) |
            Job.description.ilike(term)
        )
    if category:
        q = q.filter(Job.role_category == category)
    if source:
        q = q.filter(Job.source == source)
    if c2c_only:
        q = q.filter(Job.is_c2c == True)
    if vendor_only:
        q = q.filter(Job.is_vendor == True)
    if days:
        cutoff = datetime.utcnow() - timedelta(days=days)
        q = q.filter(Job.scraped_at >= cutoff)

    if sort == "newest":
        q = q.order_by(Job.scraped_at.desc())
    elif sort == "oldest":
        q = q.order_by(Job.scraped_at.asc())
    elif sort == "score":
        q = q.order_by(Job.semantic_score.desc())
    elif sort == "posted":
        q = q.order_by(Job.posted_date.desc())

    total = q.count()
    jobs  = q.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "jobs":     [job_to_dict(j) for j in jobs],
        "total":    total,
        "page":     page,
        "per_page": per_page,
        "pages":    max(1, (total + per_page - 1) // per_page),
    }


@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    total  = db.query(Job).count()
    today  = db.query(Job).filter(
        Job.scraped_at >= datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    ).count()
    c2c    = db.query(Job).filter(Job.is_c2c   == True).count()
    vendor = db.query(Job).filter(Job.is_vendor == True).count()

    by_category = {
        k: v for k, v in
        db.query(Job.role_category, func.count(Job.id))
          .group_by(Job.role_category).all()
    }
    by_source = {
        k: v for k, v in
        db.query(Job.source, func.count(Job.id))
          .group_by(Job.source).all()
    }

    return {
        "total_jobs":    total,
        "jobs_today":    today,
        "c2c_jobs":      c2c,
        "vendor_jobs":   vendor,
        "by_category":   by_category,
        "by_source":     by_source,
        "all_categories": sorted(by_category.keys()),
        "all_sources":    sorted(by_source.keys()),
        **_state,
    }


@app.post("/api/scrape/trigger")
def trigger_scrape(background_tasks: BackgroundTasks):
    if _state["is_scraping"]:
        return {"message": "Scrape already running", "status": "busy"}
    background_tasks.add_task(run_scrape)
    return {"message": "Scrape triggered", "status": "started"}


@app.get("/api/scrape/status")
def scrape_status():
    return _state


@app.delete("/api/jobs/old")
def purge_old_jobs(db: Session = Depends(get_db), older_than_days: int = 30):
    """Remove jobs older than N days to keep the DB lean."""
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    deleted = db.query(Job).filter(Job.scraped_at < cutoff).delete()
    db.commit()
    return {"deleted": deleted}


# Serve React frontend for all non-API routes (production)
_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.isdir(_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
