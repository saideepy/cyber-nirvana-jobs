"""
Shared utilities: role patterns, date helpers, C2C/vendor detection.
Carries over all patterns from the original c2c_job_scraper.py.
"""
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

# ── date config ────────────────────────────────────────────────────────────────
MAX_AGE_DAYS = 7
CUTOFF_DT = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)


def _refresh_cutoff():
    """Call at scrape-start so the cutoff stays current."""
    global CUTOFF_DT
    CUTOFF_DT = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)


def _parse_dt(s: str):
    if not s:
        return None
    s = s.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s[: len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        return parsedate_to_datetime(s)
    except Exception:
        pass
    return None


def _is_recent(raw: str) -> bool:
    dt = _parse_dt(raw)
    if dt is None:
        return True  # unknown date → keep
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= CUTOFF_DT


def _fmt_date(raw: str) -> str:
    dt = _parse_dt(raw)
    return dt.strftime("%Y-%m-%d") if dt else (raw[:10] if raw else "")


# ── role regex patterns ────────────────────────────────────────────────────────
ROLE_PATTERNS = [
    ("Agentic AI Engineer", re.compile(
        r"\b("
        r"agentic[\s\-]?ai"
        r"|ai[\s\-]?agent(s)?[\s\-]?(developer|engineer|architect)?"
        r"|autonomous[\s\-]?agent(s)?"
        r"|multi[\s\-]?agent[\s\-]?(system|framework|developer|engineer)?"
        r"|agent[\s\-]?(framework|developer|engineer|orchestration)"
        r"|crewai|autogen|langgraph|agentops|openagents"
        r")", re.IGNORECASE)),

    ("AI / ML Engineer", re.compile(
        r"\b("
        r"ai[\s/\-]?ml[\s\-]?engineer"
        r"|machine[\s\-]?learning[\s\-]?(engineer|developer|scientist|specialist|architect)"
        r"|ml[\s\-]?(engineer|developer|architect|specialist)"
        r"|artificial[\s\-]?intelligence[\s\-]?(engineer|developer|specialist|architect)"
        r"|ai[\s\-]?(engineer|developer|specialist|platform[\s\-]?engineer)"
        r")", re.IGNORECASE)),

    ("Generative AI / GenAI Engineer", re.compile(
        r"\b("
        r"gen[\s\-]?ai[\s\-]?(engineer|developer|architect|specialist)?"
        r"|generative[\s\-]?ai[\s\-]?(engineer|developer|architect|specialist)?"
        r"|genai[\s\-]?(engineer|developer)?"
        r")", re.IGNORECASE)),

    ("LLM Engineer", re.compile(
        r"\b("
        r"llm[\s\-]?(engineer|developer|architect|specialist|ops)?"
        r"|large[\s\-]?language[\s\-]?model[\s\-]?(engineer|developer|architect)?"
        r"|foundation[\s\-]?model[\s\-]?(engineer|developer)?"
        r"|llmops"
        r")", re.IGNORECASE)),

    ("Prompt Engineer", re.compile(
        r"\bprompt[\s\-]?engineer(ing|er)?\b", re.IGNORECASE)),

    ("Data Scientist", re.compile(
        r"\bdata[\s\-]?scien(tist|ce)[\s\-]?(sr\.?|senior|lead|principal|staff|mid)?\b",
        re.IGNORECASE)),

    ("Data Analyst", re.compile(
        r"\bdata[\s\-]?(anal(yst|ytics|ysis)|analytics[\s\-]?engineer)\b",
        re.IGNORECASE)),

    ("GCP / Google Cloud Data Engineer", re.compile(
        r"\b("
        r"gcp[\s\-]?(data[\s\-]?engineer|developer|architect|analyst|specialist)"
        r"|google[\s\-]?cloud[\s\-]?(data[\s\-]?engineer|developer|architect|platform)"
        r"|bigquery[\s\-]?(engineer|developer|analyst)?"
        r"|vertex[\s\-]?ai[\s\-]?(engineer|developer|architect)?"
        r")", re.IGNORECASE)),

    ("Azure AI / Foundry Developer", re.compile(
        r"\bazure[\s\-]?("
        r"ai[\s\-]?(engineer|developer|architect|foundry|studio|specialist)?"
        r"|openai[\s\-]?(developer|engineer|architect)?"
        r"|foundry[\s\-]?(developer|engineer)?"
        r"|machine[\s\-]?learning[\s\-]?(engineer|developer)?"
        r"|cognitive[\s\-]?(services|engineer|developer)?"
        r"|copilot[\s\-]?(developer|engineer)?"
        r"|ai[\s\-]?services"
        r"|bot[\s\-]?(framework|developer|engineer)?"
        r")", re.IGNORECASE)),

    ("Claude / Anthropic Developer", re.compile(
        r"\b("
        r"claude[\s\-]?(api|developer|engineer|ai|claude[\s\-]?\d)?"
        r"|anthropic[\s\-]?(developer|engineer|api)?"
        r")", re.IGNORECASE)),

    ("Python Developer (AI/ML)", re.compile(
        r"\bpython[\s\-]?(developer|engineer|programmer|architect|specialist)\b",
        re.IGNORECASE)),

    ("MLOps / LLMOps Engineer", re.compile(
        r"\b("
        r"mlops[\s\-]?(engineer|developer|architect|specialist)?"
        r"|llmops[\s\-]?(engineer|developer)?"
        r"|ml[\s\-]?ops[\s\-]?(engineer|developer)?"
        r"|model[\s\-]?ops([\s\-]?(engineer|developer))?"
        r"|kubeflow|mlflow[\s\-]?(engineer|developer)?"
        r"|sagemaker[\s\-]?(engineer|developer|mlops|pipeline)?"
        r"|vertex[\s\-]?ai[\s\-]?pipeline"
        r")", re.IGNORECASE)),

    ("NLP Engineer", re.compile(
        r"\b("
        r"nlp[\s\-]?(engineer|developer|scientist|specialist|architect)?"
        r"|natural[\s\-]?language[\s\-]?(processing|engineer|understanding|generation|inference)"
        r")", re.IGNORECASE)),

    ("AI / ML Architect", re.compile(
        r"\b("
        r"ai[\s\-]?(architect|solutions[\s\-]?architect|platform[\s\-]?architect)"
        r"|ml[\s\-]?architect"
        r"|machine[\s\-]?learning[\s\-]?architect"
        r")", re.IGNORECASE)),

    ("RAG / LangChain / Vector DB Developer", re.compile(
        r"\b("
        r"rag[\s\-]?(developer|engineer|architect|pipeline)?"
        r"|retrieval[\s\-]?augmented[\s\-]?generation"
        r"|langchain[\s\-]?(developer|engineer)?"
        r"|llamaindex[\s\-]?(developer|engineer)?"
        r"|vector[\s\-]?(db|database|store|search)[\s\-]?(engineer|developer)?"
        r"|pinecone|weaviate|chroma[\s\-]?db|qdrant|milvus"
        r")", re.IGNORECASE)),

    ("Copilot Developer", re.compile(
        r"\b("
        r"copilot[\s\-]?(developer|engineer|studio|specialist)?"
        r"|microsoft[\s\-]?copilot[\s\-]?(developer|engineer)?"
        r"|github[\s\-]?copilot[\s\-]?(developer|engineer)?"
        r"|m365[\s\-]?copilot|ms365[\s\-]?ai"
        r")", re.IGNORECASE)),

    ("Deep Learning / Computer Vision Engineer", re.compile(
        r"\b("
        r"deep[\s\-]?learning[\s\-]?(engineer|developer|scientist|researcher)?"
        r"|neural[\s\-]?network[\s\-]?(engineer|developer|architect)?"
        r"|transformer[\s\-]?model[\s\-]?(engineer|developer)?"
        r"|computer[\s\-]?vision[\s\-]?(engineer|developer|scientist)?"
        r"|cv[\s\-]?(engineer|developer|scientist)"
        r"|pytorch[\s\-]?(engineer|developer)?"
        r"|tensorflow[\s\-]?(engineer|developer)?"
        r"|hugging[\s\-]?face[\s\-]?(engineer|developer)?"
        r")", re.IGNORECASE)),

    ("Data Engineer (AI / Cloud)", re.compile(
        r"\bdata[\s\-]?engineer(ing)?[\s\-]?(sr\.?|senior|lead|principal|staff|cloud|ai)?\b",
        re.IGNORECASE)),
]


def match_role(title: str, desc: str):
    for category, pattern in ROLE_PATTERNS:
        if pattern.search(title):
            return category
    for category, pattern in ROLE_PATTERNS:
        if pattern.search(desc[:800]):
            return category
    return None


# ── C2C detection ──────────────────────────────────────────────────────────────
_C2C_RE = re.compile(
    r"\b(c2c|corp[\s\-]?to[\s\-]?corp|corp2corp|1099"
    r"|w2[\s/]?or[\s/]?c2c|c2c[\s/]?ok|c2c[\s/]?allowed"
    r"|contract[\s\-]?to[\s\-]?hire|independent[\s\-]?contractor"
    r"|contract[\s\-]?only|contract[\s\-]?position)\b",
    re.IGNORECASE,
)


def is_c2c(text: str) -> bool:
    return bool(_C2C_RE.search(text))


# ── vendor detection ───────────────────────────────────────────────────────────
VENDOR_KEYWORDS = [
    "brooksource", "beacon hill", "beaconhill", "york solutions",
    "garner resources", "insight global", "tek systems", "teksystems",
    "kforce", "motion recruitment", "apex systems", "infosys bpm",
    "cynet systems", "collabera", "mastech", "igate", "inforeliance",
    "softpath", "acs group", "staffigo", "cloud big data",
    "nityo infotech", "siri infosolutions", "synergistic it",
    "hcl", "wipro", "infosys", "cognizant", "tata consultancy",
    "diverse lynx", "iconma", "panzer solutions", "lancesoft",
    "artech", "smartit corp", "rangam", "talentburst",
    "vtech solution", "itbrainiac", "net2source", "vdart",
    "eteam", "genesis10", "mindlance", "signature consultants",
    "yoh services", "randstad", "robert half", "staffmark",
    "staffing solutions", "it staffing", "softchoice",
    "global consultants", "mvsoft", "techstar", "dexterous",
    "spruce infotech", "mps group", "futuresoft", "sysusa",
]


def is_vendor(company: str) -> bool:
    c = company.lower()
    return any(v in c for v in VENDOR_KEYWORDS)


# ── pay extraction ─────────────────────────────────────────────────────────────
def extract_pay(desc: str) -> str:
    for p in [
        r"\$(\d{2,3}(?:\.\d{2})?)\s*[-–to]+\s*\$?(\d{2,3}(?:\.\d{2})?)\s*/?\s*hr",
        r"\$(\d{2,3}(?:\.\d{2})?)\s*/\s*hr(?:our)?",
        r"(\d{2,3}(?:\.\d{2})?)\s*[-–]\s*(\d{2,3}(?:\.\d{2})?)\s*(?:per\s+hour|/hour|/hr)",
    ]:
        m = re.search(p, desc, re.IGNORECASE)
        if m:
            g = [x for x in m.groups() if x]
            return ("$" + "/hr–$".join(g) + "/hr") if len(g) > 1 else f"${g[0]}/hr"
    return ""
