import os
import re
import sys
import json
import time
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup
load_dotenv()
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SEEN_JOBS_FILE    = os.path.join(os.path.dirname(__file__), "seen_jobs.json")
SEEN_JOBS_TTL_DAYS = 7
TOP_N = 10
LINKEDIN_SEARCHES = [
    # Turkey (English & Turkish)
    {"keywords": "React Developer",          "location": "Turkey"},
    {"keywords": "Next.js Developer",        "location": "Turkey"},
    {"keywords": "Frontend Developer",       "location": "Turkey"},
    {"keywords": "Frontend Engineer",        "location": "Turkey"},
    {"keywords": "Senior React Developer",   "location": "Turkey"},
    {"keywords": "Senior Frontend Engineer", "location": "Turkey"},
    {"keywords": "Junior React Developer",   "location": "Turkey"},
    {"keywords": "Junior Frontend",          "location": "Turkey"},
    {"keywords": "React Intern",             "location": "Turkey"},
    {"keywords": "Frontend Intern",          "location": "Turkey"},
    {"keywords": "React Stajyer",            "location": "Turkey"},
    {"keywords": "Frontend Stajyer",         "location": "Turkey"},
    {"keywords": "Web Geliştirici Stajyer",  "location": "Turkey"},
    {"keywords": "Frontend Geliştirici",     "location": "Turkey"},
    # UAE
    {"keywords": "React Developer",          "location": "United Arab Emirates"},
    {"keywords": "Next.js Developer",        "location": "United Arab Emirates"},
    {"keywords": "Frontend Developer",       "location": "United Arab Emirates"},
    {"keywords": "Senior React Developer",   "location": "United Arab Emirates"},
    {"keywords": "Junior Frontend",          "location": "United Arab Emirates"},
    {"keywords": "React Intern",             "location": "United Arab Emirates"},
    # Saudi Arabia
    {"keywords": "React Developer",          "location": "Saudi Arabia"},
    {"keywords": "Next.js Developer",        "location": "Saudi Arabia"},
    {"keywords": "Frontend Developer",       "location": "Saudi Arabia"},
    {"keywords": "Senior Frontend",          "location": "Saudi Arabia"},
    {"keywords": "Junior React Developer",   "location": "Saudi Arabia"},
    {"keywords": "React Intern",             "location": "Saudi Arabia"},
    # Qatar
    {"keywords": "React Developer",          "location": "Qatar"},
    {"keywords": "Next.js Developer",        "location": "Qatar"},
    {"keywords": "Frontend Developer",       "location": "Qatar"},
    # Kuwait
    {"keywords": "React Developer",          "location": "Kuwait"},
    {"keywords": "Frontend Developer",       "location": "Kuwait"},
    # Bahrain
    {"keywords": "React Developer",          "location": "Bahrain"},
    {"keywords": "Frontend Developer",       "location": "Bahrain"},
    # Oman
    {"keywords": "React Developer",          "location": "Oman"},
    {"keywords": "Frontend Developer",       "location": "Oman"},
    # Egypt
    {"keywords": "React Developer",          "location": "Egypt"},
    {"keywords": "Next.js Developer",        "location": "Egypt"},
    {"keywords": "Frontend Developer",       "location": "Egypt"},
    {"keywords": "Senior React Developer",   "location": "Egypt"},
    {"keywords": "Junior React Developer",   "location": "Egypt"},
    {"keywords": "React Intern",             "location": "Egypt"},
    {"keywords": "Frontend Intern",          "location": "Egypt"},
]
LINKEDIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}
# ── حساب النقاط (يشمل جميع المستويات) ──────────────────────────────────────────
ROLE_SCORES = {
    # Senior / Lead
    "senior react developer": 55,
    "senior next.js developer": 55,
    "senior frontend engineer": 55,
    "senior frontend developer": 55,
    "lead frontend engineer": 52,
    "tech lead frontend": 52,
    # Mid / General
    "next.js developer": 50,
    "nextjs developer": 50,
    "next.js engineer": 50,
    "react developer": 48,
    "react engineer": 46,
    "frontend developer": 44,
    "front end developer": 44,
    "frontend engineer": 42,
    "mid-level frontend developer": 45,
    # Junior / Entry
    "junior react developer": 45,
    "junior next.js developer": 45,
    "junior frontend developer": 42,
    "junior front end developer": 42,
    "entry level react developer": 40,
    # التدريب بالإنجليزية والتركية
    "react intern": 40,
    "react internship": 40,
    "frontend intern": 38,
    "frontend internship": 38,
    "next.js intern": 40,
    "react stajyer": 40,
    "react staj": 40,
    "frontend stajyer": 38,
    "frontend staj": 38,
    "web geliştirici stajyer": 35,
    "next.js stajyer": 40,
    "frontend geliştirici": 44,
    "react geliştirici": 46,
    "yazılım stajyeri": 35,
    "stajyer": 30,
    "staj": 30,
    "trainee": 30,
    "web developer": 25,
}
SKILL_SCORES = {
    "react": 25,
    "next.js": 25,
    "nextjs": 25,
    "typescript": 20,
    "javascript": 15,
    "tailwind": 10,
    "redux": 10,
    "html": 8,
    "css": 8,
    "rest api": 7,
    "rest": 6,
}
# الأنماط المسموحة
ALLOWED_ROLE_PATTERNS = [
    r"\breact developer\b",
    r"\breact engineer\b",
    r"\bnext\.?js developer\b",
    r"\bnext\.?js engineer\b",
    r"\bfrontend developer\b",
    r"\bfront[- ]end developer\b",
    r"\bfrontend engineer\b",
    r"\bfront[- ]end engineer\b",
    r"\bsenior\b",
    r"\blead\b",
    r"\bjunior\b",
    r"\bentry level\b",
    r"\bintern\b",
    r"\binternship\b",
    r"\btrainee\b",
    r"\bstajyer\b",
    r"\bstaj\b",
    r"\bgeliştirici\b",
]
EXCLUDED_ROLE_PATTERNS = [
    # استبعاد تطوير الألعاب
    r"\bgame\b",
    r"\bgaming\b",
    r"\bgame developer\b",
    r"\bgame dev\b",
    r"\bunity\b",
    r"\bunreal\b",
    r"\b3d\b",
    # استبعاد التقنيات واللغات الأخرى
    r"\breact native\b",
    r"\bflutter\b",
    r"\bjava\b",
    r"\bkotlin\b",
    r"\bswift\b",
    r"\bios\b",
    r"\bandroid\b",
    r"\bmobile\b",
    r"\bangular\b",
    r"\bvue\.?js\b",
    r"\bvue\b",
    r"\bsvelte\b",
    r"\bpython\b",
    r"\bphp\b",
    r"\blaravel\b",
    r"\bnet\b",
    r"\bc#\b",
    r"\bc\+\+\b",
    # استبعاد المجالات والإدارات غير البرمجية للواجهات
    r"\bsolution architect\b",
    r"\bsoftware architect\b",
    r"\bdata engineer\b",
    r"\bdata scientist\b",
    r"\bmachine learning\b",
    r"\bai engineer\b",
    r"\bdevops\b",
    r"\bbackend\b",
    r"\bback[- ]end\b",
    r"\bfull stack\b",
    r"\bfullstack\b",
    r"\bproduct manager\b",
    r"\bproject manager\b",
    r"\bqa\b",
    r"\bquality assurance\b",
]
def is_frontend_role(title: str) -> bool:
    title = (title or "").strip().lower()
    if not title:
        return False
    # استبعاد فوراً إذا تطابق مع القائمة المحظورة (Game, Java, Flutter, Backend...)
    for pattern in EXCLUDED_ROLE_PATTERNS:
        if re.search(pattern, title, re.I):
            return False
    # القبول في حال تطابق مع الأدوار المسموحة
    for pattern in ALLOWED_ROLE_PATTERNS:
        if re.search(pattern, title, re.I):
            return True
    return False
def is_remote_job(job: dict) -> bool:
    title = (job.get("job_title") or "").lower()
    location = (job.get("job_city") or "").lower()
    combined = f"{title} {location}"
    forbidden_remote_modes = ["on-site", "onsite", "on site", "office based", "office-based"]
    if any(mode in combined for mode in forbidden_remote_modes):
        return False
    return bool(job.get("job_is_remote", False))
LOCATION_SCORES = {
    "turkey": 22, "istanbul": 22, "ankara": 22, "izmir": 22, "tr": 22, "türkiye": 22,
    "ae": 20, "uae": 20, "dubai": 20, "abu dhabi": 20, "united arab emirates": 20,
    "sa": 18, "saudi": 18, "riyadh": 18, "jeddah": 18, "saudi arabia": 18,
    "qa": 16, "qatar": 16, "doha": 16,
    "kw": 15, "kuwait": 15,
    "bh": 15, "bahrain": 15,
    "om": 15, "oman": 15,
    "eg": 16, "egypt": 16, "cairo": 16,
    "worldwide": 15, "global": 15,
    "remote": 14,
}
def score_job(job: dict) -> int:
    title   = (job.get("job_title") or "").lower()
    desc    = (job.get("job_description") or "")[:500].lower()
    city    = (job.get("job_city") or "").lower()
    country = (job.get("job_country") or "").lower()
    is_remote = job.get("job_is_remote", False)
    score = 0
    for kw, pts in ROLE_SCORES.items():
        if kw in title:
            score += pts
            break
    skill_pts = sum(pts for kw, pts in SKILL_SCORES.items() if kw in title + " " + desc)
    score += min(skill_pts, 30)
    loc_hay = f"{city} {country}" + (" remote" if is_remote else "")
    for loc, pts in LOCATION_SCORES.items():
        if loc in loc_hay:
            score += pts
            break
    if is_remote:
        score += 8
    elif any(w in title for w in ("hybrid", "remote", "hibrit", "uzaktan")):
        score += 5
    return score
def score_label(score: int) -> str:
    if score >= 60: return "Excellent match"
    if score >= 45: return "Strong match"
    if score >= 30: return "Good match"
    return "Possible match"
APPLICANT_FETCH_LIMIT = 15
def fetch_applicant_count(url: str) -> int | None:
    if not url:
        return None
    try:
        resp = requests.get(url, headers=LINKEDIN_HEADERS, timeout=10)
        if resp.status_code != 200:
            return None
        m = re.search(r'([\d,]+)\+?\s*(?:applicants|people clicked apply|başvuru)', resp.text, re.I)
        if m:
            return int(m.group(1).replace(",", ""))
    except requests.RequestException:
        pass
    return None
def applicant_bonus(count: int | None) -> int:
    if count is None:
        return 0
    if count <= 10:
        return 20
    if count <= 25:
        return 14
    if count <= 50:
        return 8
    if count <= 100:
        return 2
    return -8
def enrich_with_competition(jobs: list) -> list:
    ranked = sorted(jobs, key=score_job, reverse=True)
    top, rest = ranked[:APPLICANT_FETCH_LIMIT], ranked[APPLICANT_FETCH_LIMIT:]
    for job in top:
        count = fetch_applicant_count(job.get("job_apply_link"))
        job["_applicants"] = count
        job["_score"] = score_job(job) + applicant_bonus(count)
        time.sleep(0.3)
    for job in rest:
        job["_applicants"] = None
        job["_score"] = score_job(job)
    return sorted(top + rest, key=lambda j: j["_score"], reverse=True)
# ── سحب البيانات من لينكدإن ───────────────────────────────────────────────────
def parse_card(card, search_location: str) -> dict | None:
    link_tag = card.find("a", class_="base-card__full-link")
    if not link_tag:
        return None
    raw_url = link_tag.get("href", "")
    apply_url = raw_url.split("?")[0].rstrip("/") if raw_url else ""
    match = re.search(r"-(\d{8,})$", apply_url)
    job_id = f"li_{match.group(1)}" if match else None
    if not job_id:
        return None
    title_tag   = card.find("h3", class_="base-search-card__title")
    company_tag = card.find("h4", class_="base-search-card__subtitle")
    loc_tag     = card.find("span", class_="job-search-card__location")
    title    = (title_tag.get_text(strip=True)   if title_tag   else "").strip()
    company  = (company_tag.get_text(strip=True) if company_tag else "").strip()
    location = (loc_tag.get_text(strip=True)     if loc_tag     else search_location).strip()
    card_text = card.get_text(" ", strip=True).lower()
    if "on-site" in card_text or "onsite" in card_text or "on site" in card_text or "ofiste" in card_text:
        return None
    job = {
        "job_id":        job_id,
        "job_title":     title,
        "employer_name": company,
        "job_city":      location,
        "job_country":   search_location,
        "job_is_remote": True,
        "job_apply_link": apply_url,
        "job_description": "",
    }
    if not is_remote_job(job):
        return None
    return job
def search_linkedin(keywords: str, location: str) -> list:
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {
        "keywords": keywords,
        "location": location,
        "f_TPR":    "r86400",  # آخر 24 ساعة
        "f_WT":     "2",
    }
    try:
        resp = requests.get(url, headers=LINKEDIN_HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for card in soup.find_all("li"):
            job = parse_card(card, location)
            if job:
                jobs.append(job)
        return jobs
    except requests.RequestException:
        return []
# ── تليجرام ───────────────────────────────────────────────────────────────────
def esc(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
def format_job(rank: int, job: dict) -> str:
    title      = esc(job.get("job_title") or "N/A")
    company    = esc(job.get("employer_name") or "N/A")
    location   = esc(job.get("job_city") or job.get("job_country") or "Unknown")
    is_remote  = job.get("job_is_remote", False)
    score      = job.get("_score", score_job(job))
    applicants = job.get("_applicants")
    title_lower = (job.get("job_title") or "").lower()
    if "hybrid" in title_lower or "hybrid" in location.lower() or "hibrit" in title_lower:
        work_mode = "Hybrid"
    elif is_remote or "remote" in title_lower or "uzaktan" in title_lower:
        work_mode = "Remote"
    else:
        work_mode = location
    apply_url  = job.get("job_apply_link") or ""
    safe_url   = apply_url.replace("&", "&amp;")
    apply_part = f' | <a href="{safe_url}">Apply on LinkedIn</a>' if safe_url else ""
    # تصنيف المستوى الوظيفي في الوسم (Badge)
    if "senior" in title_lower or "lead" in title_lower:
        badge = " [SENIOR / LEAD]"
    elif any(k in title_lower for k in ("junior", "entry level", "intern", "internship", "trainee", "staj", "stajyer")):
        badge = " [JUNIOR / INTERN]"
    else:
        badge = " [MID / GENERAL]"
    if applicants is None:
        competition = ""
    elif applicants <= 25:
        competition = f" | {applicants} applicants (low competition)"
    else:
        competition = f" | {applicants} applicants"
    return (
        f"<b>#{rank} {title}</b>{badge}\n"
        f"{company} | {work_mode}\n"
        f"<i>{score_label(score)} ({score} pts)</i>{competition}{apply_part}"
    )
def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        candidate = current + line + "\n"
        if len(candidate) > 4000:
            if current:
                chunks.append(current.rstrip())
            current = line + "\n"
        else:
            current = candidate
    if current.strip():
        chunks.append(current.rstrip())
    for chunk in chunks:
        try:
            resp = requests.post(url, json={
                "chat_id":   TELEGRAM_CHAT_ID,
                "text":      chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Error sending Telegram message: {e}")
            return False
    return True
# ── الذاكرة والإعدادات ────────────────────────────────────────────────────────
def check_config():
    missing = [k for k in ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")
               if not os.getenv(k) or "your_" in os.getenv(k)]
    if missing:
        print(f"ERROR: Missing values in .env: {', '.join(missing)}")
        sys.exit(1)
def load_seen_jobs() -> dict:
    if not os.path.exists(SEEN_JOBS_FILE):
        return {}
    try:
        with open(SEEN_JOBS_FILE, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    cutoff = (datetime.now() - timedelta(days=SEEN_JOBS_TTL_DAYS)).isoformat()
    return {jid: ts for jid, ts in data.items() if ts >= cutoff}
def save_seen_jobs(seen: dict):
    temp_file = SEEN_JOBS_FILE + ".tmp"
    with open(temp_file, "w") as f:
        json.dump(seen, f)
    os.replace(temp_file, SEEN_JOBS_FILE)
# ── الدالة الرئيسية ───────────────────────────────────────────────────────────
def main():
    check_config()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting React/Next.js job search...")
    seen = load_seen_jobs()
    this_run_ids: set = set()
    all_jobs: list = []
    for s in LINKEDIN_SEARCHES:
        jobs = search_linkedin(s["keywords"], s["location"])
        kept = 0
        for job in jobs:
            job_id = job.get("job_id")
            title = job.get("job_title") or ""
            if not job_id or job_id in seen or job_id in this_run_ids:
                continue
            if not is_frontend_role(title) or not is_remote_job(job):
                continue
            this_run_ids.add(job_id)
            all_jobs.append(job)
            kept += 1
        print(f"  '{s['keywords']}' / {s['location']} -> {kept} new relevant jobs")
    print(f"Total new relevant jobs: {len(all_jobs)}")
    if not all_jobs:
        sent = send_telegram(
            "<b>Daily Job Report - " + datetime.now().strftime("%b %d, %Y") + "</b>\n"
            "No new React/Next.js jobs found today. Check back tomorrow!"
        )
        if not sent:
            raise RuntimeError("Telegram message could not be sent")
    else:
        enriched_jobs = enrich_with_competition(all_jobs)
        top_jobs = sorted(enriched_jobs, key=lambda j: j.get("_score", 0), reverse=True)[:TOP_N]
        date_str = datetime.now().strftime("%b %d, %Y")
        lines = [
            f"<b>React / Next.js Job Report (All Levels) - {date_str}</b>\n"
            "Remote or Hybrid | All Experience Levels | LinkedIn\n",
            "<b>-- Best Matches --</b>\n"
        ]
        for i, job in enumerate(top_jobs, 1):
            lines.append(format_job(i, job))
            lines.append("")
        if not send_telegram("\n".join(lines)):
            raise RuntimeError("Telegram message could not be sent")
        print(f"Telegram sent successfully with {len(top_jobs)} matches.")
    now_iso = datetime.now().isoformat()
    ids_to_mark = this_run_ids if not all_jobs else {
        job.get("job_id") for job in top_jobs if job.get("job_id")
    }
    for job_id in ids_to_mark:
        seen[job_id] = now_iso
    save_seen_jobs(seen)
if __name__ == "__main__":
    main()