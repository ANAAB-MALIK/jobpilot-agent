"""
Job Agent - core logic (CV reading, skill detection, job search, scoring, cover letter)
Used by app.py (web page). You can also run it directly:  python job_agent.py meri_cv.pdf
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

# ---------------------------------------------------------------
# SKILLS: "skill name": [other ways it can be written]
# Add your own skills here. Left side = name shown, right side = spellings to look for.
# ---------------------------------------------------------------
SKILL_ALIASES = {
    "python": [],
    "java": [],
    "c++": [],
    "javascript": [],
    "html": [],
    "css": [],
    "sql": [],
    "mysql": [],
    "database": ["databases"],
    "react": [],
    "node": ["node.js", "nodejs"],
    "django": [],
    "flask": [],
    "git": [],
    "excel": [],
    "photoshop": ["adobe photoshop"],
    "illustrator": ["adobe illustrator"],
    "canva": [],
    "figma": [],
    "graphic design": ["graphic designer", "graphic designing", "graphics design"],
    "branding": ["brand design", "brand identity"],
    "print design": ["print designer"],
    "ui design": ["ui/ux", "ux design", "ui designer"],
    "shopify": [],
    "e-commerce": ["ecommerce", "e commerce", "online store", "online shop"],
    "wordpress": [],
    "seo": [],
    "social media": [],
    "marketing": [],
    "content writing": ["copywriting", "content creation", "content writer"],
    "data analysis": ["data analyst", "data analytics"],
    "machine learning": [],
    "customer service": ["customer support"],
    "communication": [],
    "creativity": ["creative"],
    "writing": [],
}
SKILLS = list(SKILL_ALIASES)
SOFT_SKILLS = {"communication", "writing", "creativity"}   # every job mentions these, so they don't count in the score

DISPLAY = {"sql": "SQL", "mysql": "MySQL", "html": "HTML", "css": "CSS", "seo": "SEO",
           "javascript": "JavaScript", "e-commerce": "E-commerce", "c++": "C++", "ui design": "UI Design"}


def display_name(skill):
    return DISPLAY.get(skill, skill.title())


def find_skills(text):
    """Returns the skills (from SKILL_ALIASES) that appear in the text."""
    text = text.lower()
    found = []
    for skill, aliases in SKILL_ALIASES.items():
        for word in [skill] + aliases:
            if re.search(r"(?<![a-z+])" + re.escape(word) + r"(?![a-z+])", text):
                found.append(skill)
                break
    return found


# ---------------------------------------------------------------
# CV reading
# ---------------------------------------------------------------
def read_cv(path):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if path.lower().endswith(".docx"):
        from docx import Document
        return "\n".join(p.text for p in Document(path).paragraphs)
    with open(path, encoding="utf-8") as f:
        return f.read()


def guess_name(cv_text):
    """First real line of the CV (skips single-letter lines like a big drop-cap 'A')."""
    for line in cv_text.splitlines():
        line = line.strip()
        if len(re.sub(r"[^A-Za-z]", "", line)) >= 3:
            return line.title() if line.isupper() else line
    return "Applicant"


# ---------------------------------------------------------------
# Getting jobs (internet first, sample file as backup)
# ---------------------------------------------------------------
def clean_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")


HEADERS = {"User-Agent": "Mozilla/5.0 (JobAgent student project)", "Accept": "application/json"}


def _get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_live_jobs(keyword):
    """Source 1: Remotive (remote jobs, searched by keyword)."""
    url = "https://remotive.com/api/remote-jobs?limit=30&search=" + urllib.parse.quote(keyword)
    return _get_json(url).get("jobs", [])


def fetch_arbeitnow_jobs():
    """Source 2: Arbeitnow (free job board API, backup)."""
    return _get_json("https://www.arbeitnow.com/api/job-board-api").get("data", [])


def load_sample_jobs():
    folder = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(folder, "jobs_sample.json"), encoding="utf-8") as f:
        return json.load(f)


def get_jobs(cv_skills):
    keyword = cv_skills[0] if cv_skills else "developer"
    try:
        jobs = fetch_live_jobs(keyword)
        if jobs:
            print(f"[Fetched {len(jobs)} live jobs from the internet: '{keyword}']")
            return jobs
    except Exception as error:
        print(f"[Could not reach the job API ({error}). Using sample jobs]")
    return load_sample_jobs()


# ---------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------
def score_job(job, cv_skills):
    """Match % = (your technical skills found in the job) / (skills the job lists, at least 3)."""
    job_text = job.get("title", "") + " " + clean_html(job.get("description", ""))
    job_skills = [s for s in find_skills(job_text) if s not in SOFT_SKILLS]
    matched = [s for s in cv_skills if s in job_skills]
    if not matched:
        return 0, []
    return min(100, round(100 * len(matched) / max(len(job_skills), 3))), matched


# ---------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------
def write_cover_letter(name, job, matched, about=""):
    skills = [display_name(s) for s in matched if s not in SOFT_SKILLS]
    if len(skills) > 1:
        skills_text = ", ".join(skills[:-1]) + " and " + skills[-1]
    else:
        skills_text = skills[0] if skills else "quick learning"
    company = job.get("company_name") or "Hiring Team"
    about_line = f"\n{about.strip()}\n" if about and about.strip() else ""
    return f"""Dear {company} Hiring Team,

I am writing to apply for the {job.get('title', 'open')} position at {company}.
I have hands-on experience with {skills_text}, which matches the skills
mentioned in your job description.
{about_line}
I am a motivated learner who enjoys solving real problems and delivering
quality work, and I would welcome the chance to discuss how I can contribute
to your team.

Thank you for your time and consideration.

Sincerely,
{name}
"""


# ---------------------------------------------------------------
# Command-line version
# ---------------------------------------------------------------
def run(cv_path):
    cv_text = read_cv(cv_path)
    name = guess_name(cv_text)
    cv_skills = find_skills(cv_text)
    print(f"CV: {name}")
    print(f"Skills found: {', '.join(display_name(s) for s in cv_skills) or 'none'}\n")

    ranked = sorted(((*score_job(j, cv_skills), j) for j in get_jobs(cv_skills)),
                    key=lambda item: item[0], reverse=True)

    for rank, (score, matched, job) in enumerate(ranked[:3], start=1):
        print("=" * 50)
        print(f"#{rank}  {job['title']} @ {job.get('company_name', '?')}")
        print(f"Match: {score}%   Matching skills: {', '.join(matched) or '-'}")
        print(f"Link: {job.get('url', '-')}")
        letter = write_cover_letter(name, job, matched)
        print("\n--- Cover letter draft ---")
        print(letter)
        if input("Apply to this job? (yes/no): ").strip().lower() in ("y", "yes"):
            filename = f"cover_letter_{rank}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(letter)
            print(f"Cover letter saved as '{filename}'. Open this link to apply:\n{job.get('url', '-')}\n")
        else:
            print("Skipped.\n")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sample_cv.txt")
