"""
C2C AI Job Board — FastAPI backend
• Runs hourly scraping via APScheduler
• Stores jobs in SQLite with scraped_at + posted_date timestamps
• Serves REST API consumed by the React frontend
• Auth: session-token based (Bearer), admin-managed users
"""
import os
import uuid
import threading
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import FastAPI, Depends, Query, BackgroundTasks, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import (
    Job, User, UserSession, JobApplication,
    SessionLocal, create_tables
)
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

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

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


# ── password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


# ── auth dependency ───────────────────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ", 1)[1]
    session = db.query(UserSession).filter(
        UserSession.token == token,
        UserSession.is_active == True,
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.query(User).filter(User.id == session.user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    session.last_seen = datetime.utcnow()
    db.commit()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── pydantic schemas ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None

class ApplyRequest(BaseModel):
    job_title: str = ""
    job_category: str = ""
    job_url: str = ""


# ── seed admin ────────────────────────────────────────────────────────────────

def seed_admin(db: Session):
    admin_username = os.environ.get("ADMIN_USERNAME", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "CyberNirvana@2024!")
    existing = db.query(User).filter(User.username == admin_username).first()
    if not existing:
        admin = User(
            username=admin_username,
            password_hash=hash_password(admin_password),
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"[Auth] Admin user '{admin_username}' created with default password.")
    elif not existing.is_admin:
        existing.is_admin = True
        db.commit()


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
        cutoff_str = (datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")
        deleted = db.query(Job).filter(
            Job.posted_date != "",
            Job.posted_date < cutoff_str,
        ).delete(synchronize_session=False)
        db.commit()
        if deleted:
            print(f"[Scraper] Purged {deleted} jobs older than {MAX_AGE_DAYS} days.")

        existing_urls = {row.url for row in db.query(Job.url).all()}
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

    db = SessionLocal()
    try:
        seed_admin(db)
    finally:
        db.close()

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

    t = threading.Thread(target=run_scrape, daemon=True)
    t.start()


@app.on_event("shutdown")
def shutdown():
    if HAS_SCHEDULER:
        _scheduler.shutdown(wait=False)


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


def user_to_dict(u: User) -> dict:
    return {
        "id":         u.id,
        "username":   u.username,
        "is_admin":   u.is_admin,
        "is_active":  u.is_active,
        "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
    }


# ── auth endpoints ────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = str(uuid.uuid4())
    session = UserSession(
        user_id    = user.id,
        token      = token,
        created_at = datetime.utcnow(),
        last_seen  = datetime.utcnow(),
        is_active  = True,
    )
    db.add(session)
    db.commit()

    return {
        "token": token,
        "user":  user_to_dict(user),
    }


@app.post("/api/auth/logout")
def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        return {"message": "ok"}
    token = authorization.split(" ", 1)[1]
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        session.is_active     = False
        session.logged_out_at = datetime.utcnow()
        db.commit()
    return {"message": "Logged out"}


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)):
    return user_to_dict(current_user)


# ── job application endpoints ─────────────────────────────────────────────────

@app.post("/api/jobs/{job_id}/apply")
def apply_job(
    job_id: int,
    body: ApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(JobApplication).filter(
        JobApplication.user_id  == current_user.id,
        JobApplication.job_id   == job_id,
        JobApplication.is_active == True,
    ).first()
    if existing:
        return {"message": "Already applied", "applied": True}

    app_record = JobApplication(
        user_id      = current_user.id,
        job_id       = job_id,
        job_title    = body.job_title,
        job_category = body.job_category,
        job_url      = body.job_url,
        applied_at   = datetime.utcnow(),
        is_active    = True,
    )
    db.add(app_record)
    db.commit()
    return {"message": "Applied", "applied": True}


@app.delete("/api/jobs/{job_id}/apply")
def unapply_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(JobApplication).filter(
        JobApplication.user_id  == current_user.id,
        JobApplication.job_id   == job_id,
        JobApplication.is_active == True,
    ).first()
    if record:
        record.is_active = False
        db.commit()
    return {"message": "Unapplied", "applied": False}


@app.get("/api/user/applications")
def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    apps = db.query(JobApplication).filter(
        JobApplication.user_id  == current_user.id,
        JobApplication.is_active == True,
    ).all()
    return {
        "applied_job_ids": [a.job_id for a in apps],
        "applications": [
            {
                "job_id":      a.job_id,
                "job_title":   a.job_title,
                "job_category":a.job_category,
                "job_url":     a.job_url,
                "applied_at":  a.applied_at.isoformat() + "Z",
            }
            for a in apps
        ],
    }


# ── admin endpoints ───────────────────────────────────────────────────────────

ONLINE_THRESHOLD = timedelta(minutes=5)
TODAY_START = lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


@app.get("/api/admin/dashboard")
def admin_dashboard(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_users  = db.query(User).filter(User.is_admin == False).count()
    active_users = db.query(User).filter(User.is_admin == False, User.is_active == True).count()
    online_cutoff = datetime.utcnow() - ONLINE_THRESHOLD
    online_now = db.query(UserSession).filter(
        UserSession.is_active == True,
        UserSession.last_seen >= online_cutoff,
    ).count()
    apps_today = db.query(JobApplication).filter(
        JobApplication.applied_at >= TODAY_START(),
        JobApplication.is_active  == True,
    ).count()

    return {
        "total_users":  total_users,
        "active_users": active_users,
        "online_now":   online_now,
        "apps_today":   apps_today,
    }


@app.get("/api/admin/users")
def admin_list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.query(User).filter(User.is_admin == False).order_by(User.created_at.desc()).all()
    online_cutoff = datetime.utcnow() - ONLINE_THRESHOLD
    today_start   = TODAY_START()
    result = []

    for u in users:
        latest_session = (
            db.query(UserSession)
            .filter(UserSession.user_id == u.id)
            .order_by(UserSession.created_at.desc())
            .first()
        )
        is_online = (
            latest_session is not None
            and latest_session.is_active
            and latest_session.last_seen >= online_cutoff
        )
        apps_today = db.query(JobApplication).filter(
            JobApplication.user_id  == u.id,
            JobApplication.applied_at >= today_start,
            JobApplication.is_active  == True,
        ).all()

        categories_today = list({a.job_category for a in apps_today if a.job_category})

        result.append({
            **user_to_dict(u),
            "is_online":        is_online,
            "last_login":       latest_session.created_at.isoformat() + "Z" if latest_session else None,
            "last_seen":        latest_session.last_seen.isoformat() + "Z" if latest_session else None,
            "apps_today_count": len(apps_today),
            "categories_today": categories_today,
        })

    return result


@app.post("/api/admin/users")
def admin_create_user(
    body: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    user = User(
        username      = body.username,
        password_hash = hash_password(body.password),
        is_admin      = body.is_admin,
        is_active     = True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@app.put("/api/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    body: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.username is not None:
        existing = db.query(User).filter(User.username == body.username, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = body.username
    if body.password is not None:
        if len(body.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        user.password_hash = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
        if not body.is_active:
            db.query(UserSession).filter(
                UserSession.user_id == user_id,
                UserSession.is_active == True,
            ).update({"is_active": False, "logged_out_at": datetime.utcnow()})
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    db.commit()
    db.refresh(user)
    return user_to_dict(user)


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.query(UserSession).filter(UserSession.user_id == user_id).delete()
    db.query(JobApplication).filter(JobApplication.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


# ── public health endpoint (no auth — used by Railway healthcheck) ───────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


# ── job endpoints (require auth) ──────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs(
    db:          Session = Depends(get_db),
    _:           User    = Depends(get_current_user),
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
def get_stats(
    db: Session = Depends(get_db),
    _:  User    = Depends(get_current_user),
):
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
def trigger_scrape(
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_user),
):
    if _state["is_scraping"]:
        return {"message": "Scrape already running", "status": "busy"}
    background_tasks.add_task(run_scrape)
    return {"message": "Scrape triggered", "status": "started"}


@app.get("/api/scrape/status")
def scrape_status(_: User = Depends(get_current_user)):
    return _state


@app.delete("/api/jobs/old")
def purge_old_jobs(
    db: Session = Depends(get_db),
    _:  User    = Depends(require_admin),
    older_than_days: int = 30,
):
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    deleted = db.query(Job).filter(Job.scraped_at < cutoff).delete()
    db.commit()
    return {"deleted": deleted}


# Serve React frontend — mount assets dir for hashed JS/CSS, catch-all for SPA routes
_dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
if os.path.isdir(_dist):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse as _FileResponse

    app.mount("/assets", StaticFiles(directory=os.path.join(_dist, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return _FileResponse(os.path.join(_dist, "index.html"))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
