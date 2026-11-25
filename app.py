"""
JobPilot - AI Job Agent (Streamlit web page)
Run:  streamlit run app.py
Needs: job_agent.py and jobs_sample.json in the same folder.
"""

import html
import io

import streamlit as st

from job_agent import (
    SKILLS,
    SOFT_SKILLS,
    clean_html,
    fetch_arbeitnow_jobs,
    fetch_live_jobs,
    find_skills,
    load_sample_jobs,
    score_job,
    write_cover_letter,
)

st.set_page_config(page_title="JobPilot - AI Job Agent", page_icon="🤖", layout="centered")

# ---------------------------------------------------------------
# Look & feel
# ---------------------------------------------------------------
st.markdown(
    """
<style>
.hero{background:linear-gradient(135deg,#1e1b4b 0%,#4338ca 55%,#7c3aed 100%);
      color:#fff;padding:28px 26px;border-radius:18px;margin-bottom:16px}
.hero h1{margin:0 0 6px 0;font-size:2rem;color:#fff;padding:0}
.hero p{margin:0;opacity:.92;font-size:1rem}
.steps{display:flex;gap:10px;margin:0 0 20px 0;flex-wrap:wrap}
.step{flex:1;min-width:150px;background:#f5f3ff;border:1px solid #ddd6fe;
      border-radius:14px;padding:12px 14px;color:#312e81;font-size:.9rem}
.step b{display:block;margin-bottom:2px}
.chip{display:inline-block;background:#eef2ff;color:#3730a3;border:1px solid #c7d2fe;
      border-radius:999px;padding:2px 10px;margin:2px 4px 2px 0;font-size:.8rem}
.chip.missing{background:#fff7ed;color:#9a3412;border-color:#fed7aa}
.badge{float:right;color:#fff;border-radius:999px;padding:3px 14px;font-weight:700}
.jobtitle{font-size:1.1rem;font-weight:700;margin:0}
.company{color:#6b7280;margin:0 0 8px 0}
.label{font-size:.8rem;color:#6b7280;margin:6px 0 2px 0}
</style>

<div class="hero">
  <h1>🤖 JobPilot</h1>
  <p>An AI agent that reads your CV, searches live job boards, ranks the best matches
     and drafts your cover letters. It never applies without your approval.</p>
</div>

<div class="steps">
  <div class="step"><b>1 · Perceive</b>Reads your CV and detects your skills</div>
  <div class="step"><b>2 · Search</b>Fetches live openings from the internet</div>
  <div class="step"><b>3 · Decide</b>Scores every job against your skills</div>
  <div class="step"><b>4 · Act</b>Drafts a cover letter, then asks for your approval</div>
</div>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def read_uploaded_cv(file):
    """Extract text from an uploaded CV (pdf, docx or txt)."""
    filename = file.name.lower()
    if filename.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file.read()))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if filename.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(file.read()))
        parts = [para.text for para in doc.paragraphs]
        for table in doc.tables:
            for row in table.rows:
                parts.extend(cell.text for cell in row.cells)
        return "\n".join(parts)
    return file.read().decode("utf-8", errors="ignore")


def get_jobs_with_source(keywords):
    """Live jobs from 2 sources; falls back to sample jobs.
    Returns (jobs, is_live, errors)."""
    jobs, seen, errors = [], set(), []

    def add(job_list):
        for job in job_list:
            if job.get("url") not in seen:
                seen.add(job.get("url"))
                jobs.append(job)

    try:
        for keyword in keywords[:5]:
            add(fetch_live_jobs(keyword))
    except Exception as error:
        errors.append(f"Remotive: {error}")

    try:
        add(fetch_arbeitnow_jobs())
    except Exception as error:
        errors.append(f"Arbeitnow: {error}")

    if jobs:
        return jobs, True, errors
    return load_sample_jobs(), False, errors


def rank_jobs(jobs, skills, top=5):
    """Score every job; keep only jobs that match at least one technical skill."""
    ranked = []
    for job in jobs:
        score, matched = score_job(job, skills)
        if score == 0:
            continue
        job_text = job.get("title", "") + " " + clean_html(job.get("description", ""))
        missing = [s for s in find_skills(job_text) if s not in matched and s not in SOFT_SKILLS]
        ranked.append((score, matched, missing, job))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[:top]


def chips(items, css_class=""):
    return "".join(f'<span class="chip {css_class}">{html.escape(i)}</span>' for i in items) or "-"


# ---------------------------------------------------------------
# Step 1: upload
# ---------------------------------------------------------------
cv_file = st.file_uploader("Upload your CV (PDF, Word or TXT)", type=["pdf", "docx", "txt"])

if cv_file:
    cv_text = read_uploaded_cv(cv_file)
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    name = st.text_input("Your name (used in the cover letter)", value=lines[0] if lines else "")

    detected = find_skills(cv_text)
    skills = st.multiselect("Skills found in your CV (you can edit them)", options=SKILLS, default=detected)

    # -----------------------------------------------------------
    # Step 2: run the agent
    # -----------------------------------------------------------
    if st.button("🚀 Run agent", type="primary"):
        if not skills:
            st.error("No skills selected. Add at least one skill.")
        else:
            with st.status("Agent is working...", expanded=True) as status:
                st.write(f"👁️ **Perceive:** read your CV and found {len(skills)} skills.")
                st.write("🌐 **Search:** asking live job boards for openings...")
                search_skills = [x for x in skills if x not in SOFT_SKILLS] or skills
                jobs, is_live, errors = get_jobs_with_source(search_skills)
                st.write(f"🧠 **Decide:** scoring {len(jobs)} jobs against your skills...")
                ranked = rank_jobs(jobs, skills)
                st.write("✍️ **Act:** drafting cover letters for the best matches.")
                status.update(label="Agent finished", state="complete", expanded=False)

            st.session_state["results"] = {
                "is_live": is_live,
                "errors": errors,
                "ranked": ranked,
                "name": name,
            }

# ---------------------------------------------------------------
# Step 3: results
# ---------------------------------------------------------------
if "results" in st.session_state:
    res = st.session_state["results"]

    st.subheader("Top matches for you")
    if res["is_live"]:
        st.success("Live openings fetched from the internet just now.")
    else:
        st.warning("Could not reach the job boards, so sample jobs are shown.")
        for message in res.get("errors", []):
            st.caption("Reason: " + message)

    if res["is_live"] and res.get("errors"):
        st.caption("Note: one job source was unavailable (" + "; ".join(res["errors"])[:150] + ")")
    if not res["ranked"]:
        st.info("No jobs matched your technical skills right now. Try adding more skills above.")

    for i, (score, matched, missing, job) in enumerate(res["ranked"], start=1):
        color = "#16a34a" if score >= 70 else "#d97706" if score >= 50 else "#6b7280"
        with st.container(border=True):
            st.markdown(
                f'<span class="badge" style="background:{color}">{score}% match</span>'
                f'<p class="jobtitle">#{i} · {html.escape(job.get("title", ""))}</p>'
                f'<p class="company">{html.escape(job.get("company_name", "Unknown company"))}</p>'
                f'<p class="label">Your matching skills</p>{chips(matched)}'
                f'<p class="label">Other skills this job mentions</p>{chips(missing, "missing")}',
                unsafe_allow_html=True,
            )
            st.progress(min(score, 100) / 100)

            with st.expander("Cover letter draft (editable)"):
                letter = st.text_area(
                    "Draft", write_cover_letter(res["name"], job, matched), height=260, key=f"letter{i}"
                )
                st.download_button("⬇️ Download cover letter", letter, f"cover_letter_{i}.txt", key=f"dl{i}")

            st.link_button("✅ Approve & open application page", job.get("url", "#"))

    st.caption("Agent type: goal-based · Percepts: CV + live job listings · Actions: rank, draft, ask approval")
