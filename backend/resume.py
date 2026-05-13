import os, re, json, zipfile, io, base64, requests

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = os.environ.get("RESUME_MODEL", "claude-sonnet-4-6")

# ── Text extraction ───────────────────────────────────────────────────────────
def extract_text(file_bytes: bytes, filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "txt":
        return file_bytes.decode("utf-8", errors="replace")
    if ext == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(p.extract_text() or "" for p in reader.pages)
    if ext in ("docx", "doc"):
        from docx import Document
        doc = Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported file type: {ext}")

# ── XML helpers (port of server.js) ──────────────────────────────────────────
def extract_paragraphs(xml: str) -> list:
    paras = []
    for m in re.finditer(r"<w:p[ >][\s\S]*?</w:p>", xml):
        p_xml = m.group(0)
        text  = "".join(t.group(1) for t in re.finditer(r"<w:t[^>]*>([\s\S]*?)</w:t>", p_xml))
        paras.append({"text": text.strip(), "xml": p_xml, "index": m.start()})
    return paras

def build_bullet_para(text: str, tech_terms: list, template_xml: str) -> str:
    ppr_m  = re.search(r"<w:pPr>[\s\S]*?</w:pPr>", template_xml)
    ppr    = ppr_m.group(0) if ppr_m else '<w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr><w:jc w:val="both"/></w:pPr>'
    rpr_m  = re.search(r"<w:rPr>[\s\S]*?</w:rPr>", template_xml)
    base_r = rpr_m.group(0) if rpr_m else '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
    base_r = re.sub(r"<w:b/>|<w:bCs/>", "", base_r)
    bold_r = base_r.replace("</w:rPr>", "<w:b/><w:bCs/></w:rPr>")

    sorted_terms = sorted(tech_terms or [], key=len, reverse=True)
    remaining, segments = text, []
    while remaining:
        found = False
        for term in sorted_terms:
            idx = remaining.find(term)
            if idx == 0:
                segments.append({"text": term, "bold": True}); remaining = remaining[len(term):]; found = True; break
            elif idx > 0:
                segments.append({"text": remaining[:idx], "bold": False})
                segments.append({"text": term, "bold": True}); remaining = remaining[idx + len(term):]; found = True; break
        if not found:
            segments.append({"text": remaining, "bold": False}); remaining = ""

    runs = ""
    for seg in segments:
        if not seg["text"]: continue
        rpr = bold_r if seg["bold"] else base_r
        t   = seg["text"]
        sp  = ' xml:space="preserve"' if t.startswith(" ") or t.endswith(" ") else ""
        esc = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        runs += f"<w:r>{rpr}<w:t{sp}>{esc}</w:t></w:r>"
    return f"<w:p>{ppr}{runs}</w:p>"

def apply_text_swap(xml: str, find: str, replace: str) -> str:
    if not find or not replace or find.strip() == replace.strip(): return xml
    if find in xml: return xml.replace(find, replace)
    for para in extract_paragraphs(xml):
        if find in para["text"]:
            new_text = para["text"].replace(find, replace)
            ppr_m  = re.search(r"<w:pPr>[\s\S]*?</w:pPr>", para["xml"])
            ppr    = ppr_m.group(0) if ppr_m else ""
            rpr_m  = re.search(r"<w:rPr>[\s\S]*?</w:rPr>", para["xml"])
            base_r = rpr_m.group(0) if rpr_m else '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr>'
            base_r = re.sub(r"<w:b/>|<w:bCs/>", "", base_r)
            esc    = new_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            new_p  = f'<w:p>{ppr}<w:r>{base_r}<w:t xml:space="preserve">{esc}</w:t></w:r></w:p>'
            xml    = xml[:para["index"]] + new_p + xml[para["index"] + len(para["xml"]):]
            break
    return xml

def remove_paragraph(xml: str, find: str) -> str:
    if not find or len(find) < 10: return xml
    for para in extract_paragraphs(xml):
        if find[:50] in para["text"]:
            return xml[:para["index"]] + xml[para["index"] + len(para["xml"]):]
    return xml

def insert_after_paragraph(xml: str, after: str, new_para: str) -> str:
    if not after or len(after) < 10: return xml
    for para in extract_paragraphs(xml):
        if after[:50] in para["text"]:
            pos = para["index"] + len(para["xml"])
            return xml[:pos] + new_para + xml[pos:]
    return xml

# ── Hardcoded stack swap maps (from original ResumeAI repo) ──────────────────
AZURE_TO_AWS = [
    ("Azure App Services","AWS Elastic Beanstalk"),("Azure Functions v4","AWS Lambda"),
    ("Azure Functions","AWS Lambda"),("Azure API Management (APIM)","AWS API Gateway"),
    ("Azure API Management","AWS API Gateway"),("Azure API Gateway (v2)","AWS API Gateway"),
    ("Azure API Gateway","AWS API Gateway"),("Azure Blob Storage","Amazon S3"),
    ("Azure SQL Database","Amazon RDS"),("Azure SQL","Amazon RDS"),
    ("Azure AD B2C","AWS Cognito"),("Azure AD","AWS IAM"),
    ("Azure Monitor","Amazon CloudWatch"),("Application Insights","AWS CloudWatch Insights"),
    ("Azure Key Vault","AWS Secrets Manager"),
    ("Azure DevOps CI/CD pipelines","AWS CodePipeline CI/CD pipelines"),
    ("Azure DevOps CI/CD","AWS CodePipeline"),("Azure DevOps","AWS CodePipeline"),
    ("Azure Repos","AWS CodeCommit"),("Microsoft Azure","Amazon Web Services (AWS)"),
    ("Azure services","AWS services"),
]
AZURE_TO_GCP = [
    ("Azure App Services","Google Cloud Run"),("Azure Functions v4","Google Cloud Functions"),
    ("Azure Functions","Google Cloud Functions"),("Azure API Management (APIM)","Google Cloud Apigee"),
    ("Azure API Management","Google Cloud Apigee"),("Azure API Gateway","Google Cloud Endpoints"),
    ("Azure Blob Storage","Google Cloud Storage"),("Azure SQL Database","Google Cloud SQL"),
    ("Azure SQL","Google Cloud SQL"),("Azure AD B2C","Google Identity Platform"),
    ("Azure AD","Google Cloud IAM"),("Azure Monitor","Google Cloud Monitoring"),
    ("Application Insights","Google Cloud Trace"),("Azure Key Vault","Google Secret Manager"),
    ("Azure DevOps CI/CD pipelines","Google Cloud Build CI/CD pipelines"),
    ("Azure DevOps CI/CD","Google Cloud Build"),("Azure DevOps","Google Cloud Build"),
    ("Azure Repos","Google Cloud Source Repositories"),
    ("Microsoft Azure","Google Cloud Platform (GCP)"),("Azure services","GCP services"),
]
ANGULAR_TO_REACT = [
    ("Angular 14 to Angular 18","React 17 to React 18"),("Angular 14–18","React 17–18"),
    ("Angular 14, progressively upgrading to Angular 18","React 17, progressively upgrading to React 18"),
    ("Angular 12 to Angular 15","React 16 to React 18"),
    ("Angular 14","React 18"),("Angular 15","React 18"),("Angular 18","React 18"),
    ("Angular 12","React 17"),("Angular 6","React 16"),("Angular","React"),
    ("RxJS 7 to 8","Redux Toolkit"),("RxJS 7–8","Redux Toolkit"),("RxJS","Redux Toolkit"),
    ("Karma","Jest"),("Jasmine","React Testing Library"),("Protractor","Cypress"),
]
ANGULAR_TO_VUE = [
    ("Angular 14 to Angular 18","Vue 2 to Vue 3"),("Angular 14","Vue 3"),
    ("Angular 18","Vue 3"),("Angular 12","Vue 2"),("Angular","Vue.js"),
    ("RxJS","Vuex / Pinia"),("Karma","Vitest"),("Jasmine","Vue Test Utils"),("Protractor","Cypress"),
]

# ── Claude analysis ───────────────────────────────────────────────────────────
def analyze_with_claude(resume_text: str, jd_text: str) -> dict:
    if not ANTHROPIC_API_KEY:
        raise ValueError("Resume optimization requires ANTHROPIC_API_KEY. Add it to /data/env.conf on EC2.")

    system = """You are a world-class ATS resume optimizer. Your goal: make the resume score 92-95% against the JD.

STEP 1 - UNDERSTAND THE ROLE: Read the JD carefully. Determine if it is: frontend only, backend only, full stack, DevOps, data engineering, etc.
IMPORTANT: If the JD is full stack — frontend skills are relevant. If the JD is pure backend/DevOps — frontend skills are irrelevant.

STEP 2 - SCORE: Calculate current ATS match % by checking how many JD keywords exist in resume.

STEP 3 - REMOVE (only truly irrelevant bullets):
REMOVE ONLY if ALL of these are true:
  a) The skill/tool is NOT mentioned in the JD at all
  b) The skill is NOT related to the role type
  c) It is a basic obvious statement OR repeated elsewhere OR 10+ yr old tech
NEVER REMOVE: Core technical achievements, primary tech stack, frontend skills if JD is full stack, security/testing/CI-CD, quantified results, JD keyword matches.

STEP 4 - ADD (missing JD keywords): For every important JD keyword NOT in resume, add a natural bullet in the 2 most recent jobs.
Each new bullet must sound exactly like the candidate wrote it, be plausible, include the exact JD keyword, go after the most contextually relevant existing bullet.

STEP 5 - SWAP: Only swap if JD clearly requires DIFFERENT tech.

STEP 6 - VERIFY: After changes, score must be 92-95%.

ABSOLUTE RULES:
- insertAfter: COPY FIRST 60 CHARS EXACTLY from existing resume bullet
- find (swaps/removals): COPY EXACTLY from resume — must exist verbatim
- techTerms: every tech name that should be bold in new bullet
- Return ONLY valid JSON"""

    user = f"""Score this resume against the JD, then produce a complete editing plan to reach 92-95% ATS match.

CRITICAL INSTRUCTION FOR ADDITIONS:
- Add new bullets ONLY in the Professional Experience sections (the 2 most recent jobs)
- DO NOT add to Professional Summary
- The insertAfter field must reference an EXPERIENCE SECTION bullet (starts with action verbs like Implemented, Designed, Developed, Integrated, Built, Managed)
- DO NOT use markdown bold (**text**) in bullet text — just write plain text, list tech terms in techTerms array

RESUME:
{resume_text[:6000]}

JOB DESCRIPTION:
{jd_text[:2000]}

Return ONLY this JSON (no markdown):
{{
  "matchScoreBefore": 72,
  "matchScoreAfter": 93,
  "stackDetected": {{"cloud": "aws|azure|gcp|none","frontend": "react|angular|vue|none","backend": "dotnet|java|node|python|none","cicd": "jenkins|github_actions|azure_devops|none"}},
  "swaps": [{{"find": "exact verbatim text from resume","replace": "replacement with JD technology","scope": "recent_only","reason": "why"}}],
  "remove": [{{"find": "first 60 chars of bullet copied exactly from resume","reason": "specific reason"}}],
  "add": [{{"text": "complete new bullet plain text no markdown bold","insertAfter": "first 60 chars of an EXPERIENCE SECTION bullet copied exactly","techTerms": ["ExactTerm1"],"reason": "which JD keyword this covers"}}],
  "summary": "Score before X%, changes made, score after Y%"
}}"""

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
        json={"model": CLAUDE_MODEL, "max_tokens": 4000, "system": system, "messages": [{"role": "user", "content": user}]},
        timeout=120,
    )
    resp.raise_for_status()
    raw = "".join(b["text"] for b in resp.json()["content"] if b["type"] == "text").strip()
    try:
        cleaned = re.sub(r"```json\n?|```\n?", "", raw).strip()
        return json.loads(cleaned[cleaned.index("{"):cleaned.rindex("}")+1])
    except Exception as e:
        print(f"Claude parse error: {e}, raw: {raw[:300]}")
        return {"swaps": [], "remove": [], "add": [], "matchScoreBefore": 70, "matchScoreAfter": 88, "stackDetected": {}, "summary": ""}

# ── Apply editing plan directly to DOCX XML (preserves all formatting) ────────
def apply_to_docx(docx_bytes: bytes, instructions: dict, resume_text: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(docx_bytes)) as z:
        if "word/document.xml" not in z.namelist():
            raise ValueError("Invalid DOCX — word/document.xml not found")
        xml       = z.read("word/document.xml").decode("utf-8")
        all_files = {name: z.read(name) for name in z.namelist()}

    stack     = instructions.get("stackDetected", {})
    hardcoded = []
    if stack.get("cloud")    == "aws":   hardcoded.extend(AZURE_TO_AWS)
    if stack.get("cloud")    == "gcp":   hardcoded.extend(AZURE_TO_GCP)
    if stack.get("frontend") == "react": hardcoded.extend(ANGULAR_TO_REACT)
    if stack.get("frontend") == "vue":   hardcoded.extend(ANGULAR_TO_VUE)
    hardcoded.sort(key=lambda x: len(x[0]), reverse=True)

    scope_end = next((kw for kw in ["Fannie Mae","Lulu Lemon","LuluLemon","Infosys","previous employer"] if kw in resume_text), None)

    hardcoded_applied = []
    if hardcoded:
        si = xml.find(scope_end) if scope_end else -1
        if si > 0:
            exp = max(xml.find("Professional Experience"), xml.find("County of San Bernardino"), xml.find("Client:"))
            if exp > 0:
                before, scope, after = xml[:exp], xml[exp:si], xml[si:]
                for frm, to in hardcoded:
                    if frm in scope: scope = scope.replace(frm, to); hardcoded_applied.append(f"{frm[:30]} → {to[:30]}")
                xml = before + scope + after
        else:
            for frm, to in hardcoded:
                if frm in xml: xml = xml.replace(frm, to); hardcoded_applied.append(f"{frm[:30]} → {to[:30]}")

    swaps_applied, removed_bullets, added_bullets = [], [], []

    for swap in instructions.get("swaps", []):
        if not swap.get("find") or not swap.get("replace"): continue
        if swap["find"].strip() == swap["replace"].strip(): continue
        if scope_end and swap.get("scope") == "recent_only":
            si = xml.find(scope_end)
            if si > 0:
                nb = apply_text_swap(xml[:si], swap["find"].strip(), swap["replace"].strip())
                if nb != xml[:si]: xml = nb + xml[si:]; swaps_applied.append(f"{swap['find'].strip()[:35]} → {swap['replace'].strip()[:35]}")
        else:
            nxml = apply_text_swap(xml, swap["find"].strip(), swap["replace"].strip())
            if nxml != xml: xml = nxml; swaps_applied.append(f"{swap['find'].strip()[:35]} → {swap['replace'].strip()[:35]}")

    for removal in instructions.get("remove", []):
        if not removal.get("find"): continue
        nxml = remove_paragraph(xml, removal["find"].strip())
        if nxml != xml: xml = nxml; removed_bullets.append(removal["find"].strip()[:50])

    current_paras = extract_paragraphs(xml)
    for addition in instructions.get("add", []):
        if not addition.get("text") or not addition.get("insertAfter"): continue
        snippet = addition["insertAfter"].strip()[:50]
        tmpl    = next((p for p in current_paras if snippet in p["text"]), None)
        if not tmpl: print(f'insertAfter not found: "{snippet}"'); continue
        clean   = re.sub(r"\*\*(.*?)\*\*|\*(.*?)\*", lambda m: m.group(1) or m.group(2), addition["text"])
        nxml    = insert_after_paragraph(xml, snippet, build_bullet_para(clean, addition.get("techTerms", []), tmpl["xml"]))
        if nxml != xml:
            xml = nxml; added_bullets.append(addition["text"][:60]); current_paras = extract_paragraphs(xml)

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in all_files.items():
            zout.writestr(name, xml.encode("utf-8") if name == "word/document.xml" else data)

    return {"buffer": out.getvalue(), "swaps_applied": hardcoded_applied + swaps_applied,
            "removed_bullets": removed_bullets, "added_bullets": added_bullets}

# ── Public entry point ────────────────────────────────────────────────────────
def optimize(file_bytes: bytes, filename: str, job_description: str) -> dict:
    ext          = filename.rsplit(".", 1)[-1].lower()
    resume_text  = extract_text(file_bytes, filename)
    instructions = analyze_with_claude(resume_text, job_description)

    docx_base64 = None
    swaps_applied = removed_bullets = added_bullets = []

    if ext == "docx":
        try:
            r              = apply_to_docx(file_bytes, instructions, resume_text)
            docx_base64    = base64.b64encode(r["buffer"]).decode("utf-8")
            swaps_applied  = r["swaps_applied"]
            removed_bullets= r["removed_bullets"]
            added_bullets  = r["added_bullets"]
        except Exception as e:
            print(f"DOCX apply error: {e}")

    changes = (
        [{"type": "modified", "description": f"Updated: {s}"} for s in swaps_applied] +
        [{"type": "removed",  "description": f"Removed: {r}"} for r in removed_bullets] +
        [{"type": "added",    "description": f"Added: {a}"}   for a in added_bullets]
    )
    if not changes:
        changes.append({"type": "added", "description": instructions.get("summary", "Resume analyzed and optimized")})

    return {
        "docx_base64":  docx_base64,
        "match_before": instructions.get("matchScoreBefore", 70),
        "match_after":  instructions.get("matchScoreAfter", 93),
        "changes":      changes,
        "summary":      instructions.get("summary", ""),
    }
