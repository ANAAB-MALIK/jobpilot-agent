"""
Job Agent
---------
1. CV padhta hai (.txt ya .pdf)         -> PERCEPT
2. CV se skills nikalta hai
3. Internet (job API) se live jobs laata hai. Na chale to jobs_sample.json use karta hai
4. Har job ko match score deta hai      -> DECISION
5. Best jobs ke liye cover letter banata hai aur apply se pehle ijazat maangta hai -> ACTION
"""

import json
import os
import re
import sys
import urllib.parse
import urllib.request

# ---------------------------------------------------------------
# STEP 1: Skills ki list (isme apni marzi se naye skills add kar sakti ho)
# ---------------------------------------------------------------
SKILLS = [
    "python", "java", "c++", "javascript", "html", "css", "sql", "mysql",
    "react", "node", "django", "flask", "git", "excel", "photoshop",
    "shopify", "wordpress", "seo", "marketing", "design", "canva",
    "data analysis", "machine learning", "communication", "writing",
]


# ---------------------------------------------------------------
# STEP 2: CV padhna
# ---------------------------------------------------------------
def read_cv(path):
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader  # pip install pypdf
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    with open(path, encoding="utf-8") as f:
        return f.read()


def find_skills(text):
    """Text mein jo skills maujood hain, unki list wapis deta hai."""
    text = text.lower()
    return [s for s in SKILLS if re.search(r"(?<![a-z+])" + re.escape(s) + r"(?![a-z+])", text)]


# ---------------------------------------------------------------
# STEP 3: Jobs laana (pehle internet, warna sample file)
# ---------------------------------------------------------------
def clean_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")


HEADERS = {"User-Agent": "Mozilla/5.0 (JobAgent student project)", "Accept": "application/json"}


def _get_json(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_live_jobs(keyword):
    """Source 1: Remotive (remote jobs, keyword se search)."""
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
# STEP 4: Match score
# ---------------------------------------------------------------
SOFT_SKILLS = {"communication", "writing"}   # ye har job mein hoti hain, score mein count nahi hongi


def score_job(job, cv_skills):
    """Match % = (CV ki kitni technical skills job se milti hain) / (job ki skills, kam az kam 3)."""
    job_text = job.get("title", "") + " " + clean_html(job.get("description", ""))
    job_skills = [s for s in find_skills(job_text) if s not in SOFT_SKILLS]
    matched = [s for s in cv_skills if s in job_skills]
    if not matched:
        return 0, []
    return min(100, round(100 * len(matched) / max(len(job_skills), 3))), matched


# ---------------------------------------------------------------
# STEP 5: Cover letter (template)
# ---------------------------------------------------------------
def write_cover_letter(name, job, matched):
    skills = ", ".join(matched) if matched else "learning quickly"
    return f"""Dear {job.get('company_name', 'Hiring Team')},

I am writing to apply for the position of {job.get('title', 'this role')}.
I have hands-on experience with {skills}, and I believe these skills
match what you are looking for.

I am a motivated learner who enjoys solving real problems, and I would
be happy to discuss how I can contribute to your team.

Thank you for your time and consideration.

Sincerely,
{name}
"""


# ---------------------------------------------------------------
# STEP 6: AGENT
# ---------------------------------------------------------------
def run(cv_path):
    cv_text = read_cv(cv_path)
    name = cv_text.strip().splitlines()[0].strip() if cv_text.strip() else "Applicant"
    cv_skills = find_skills(cv_text)
    print(f"CV: {name}")
    print(f"Skills found: {', '.join(cv_skills) if cv_skills else 'none'}\n")

    jobs = get_jobs(cv_skills)
    ranked = []
    for job in jobs:
        score, matched = score_job(job, cv_skills)
        ranked.append((score, job, matched))
    ranked.sort(key=lambda item: item[0], reverse=True)

    for rank, (score, job, matched) in enumerate(ranked[:3], start=1):
        print("=" * 50)
        print(f"#{rank}  {job['title']} @ {job.get('company_name', '?')}")
        print(f"Match: {score}%   Matching skills: {', '.join(matched) or '-'}")
        print(f"Link: {job.get('url', '-')}")

        letter = write_cover_letter(name, job, matched)
        print("\n--- Cover letter draft ---")
        print(letter)

        answer = input("Apply to this job? (yes/no): ").strip().lower()
        if answer in ("y", "yes"):
            filename = f"cover_letter_{rank}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(letter)
            print(f"Cover letter saved as '{filename}'. Open this link to apply:")
            print(job.get("url", "-"), "\n")
        else:
            print("Skipped.\n")


if __name__ == "__main__":
    cv_file = sys.argv[1] if len(sys.argv) > 1 else "sample_cv.txt"
    run(cv_file)
