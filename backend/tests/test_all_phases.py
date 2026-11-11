"""Unit tests covering all phases: Dedupe, Scoring rules, Answer Bank, Fact Check, Document Builders."""

import os
import pytest
from pydantic import BaseModel

from models.job import Job
from models.profile import Profile
from models.settings import AnswerBank
from schemas.profile import (
    MasterProfileData,
    ContactInfo,
    ExperienceEntry,
    EducationEntry,
)
from services.dedupe import compute_description_hash, is_fuzzy_duplicate
from services.matcher import stage1_rule_filter
from services.answer_bank import is_sensitive_question, find_saved_answer
from services.fact_check import compute_ats_keyword_coverage, FactCheckReport
from docs.builder_docx import create_resume_docx
from docs.builder_pdf import create_resume_pdf


# ─── 1. Deduplication Tests ──────────────────────────────────


def test_description_hash_normalization():
    desc1 = "  Looking for a Python Engineer with 3+ years experience.\nMust know FastAPI.  "
    desc2 = "looking for a python engineer with 3+ years experience. must know fastapi."
    assert compute_description_hash(desc1) == compute_description_hash(desc2)


def test_cross_portal_fuzzy_duplicate():
    # Same company and title with slight variations
    is_dup = is_fuzzy_duplicate(
        job_a_title="Full Stack Software Engineer",
        job_a_comp="Adobe Systems Inc.",
        job_a_loc="San Jose, CA",
        job_b_title="Software Engineer - Full Stack",
        job_b_comp="Adobe",
        job_b_loc="San Jose, California",
    )
    assert is_dup is True


def test_distinct_jobs_not_duplicate():
    is_dup = is_fuzzy_duplicate(
        job_a_title="Data Scientist",
        job_a_comp="Google",
        job_a_loc="Mountain View, CA",
        job_b_title="Software Engineer",
        job_b_comp="Google",
        job_b_loc="Mountain View, CA",
    )
    assert is_dup is False


# ─── 2. Scoring Rules (Stage 1 Filter) Tests ─────────────────


def test_stage1_exclude_keywords():
    profile = Profile(
        name="Junior SDE",
        min_experience=0,
        max_experience=2,
        exclude_keywords='["Manager", "Director"]',
    )
    job = Job(title="Engineering Manager - Backend", company="Stripe")
    passed, reasons = stage1_rule_filter(job, profile)
    assert passed is False
    assert any("excluded keyword" in r.lower() or "seniority" in r.lower() for r in reasons)


def test_stage1_seniority_check_for_junior():
    profile = Profile(
        name="Junior SDE",
        min_experience=1,
        max_experience=2,
    )
    job = Job(title="Principal Architect", company="Amazon")
    passed, reasons = stage1_rule_filter(job, profile)
    assert passed is False


def test_stage1_matching_job():
    profile = Profile(
        name="Software Engineer",
        min_experience=1,
        max_experience=3,
        include_keywords='["Software"]',
        exclude_keywords='["Staff"]',
    )
    job = Job(title="Software Engineer I", company="Microsoft")
    passed, reasons = stage1_rule_filter(job, profile)
    assert passed is True
    assert len(reasons) == 0


# ─── 3. Answer Bank & Safety Guard Tests ─────────────────────


def test_sensitive_question_detection():
    assert is_sensitive_question("Are you legally authorized to work in the United States?") is True
    assert is_sensitive_question("What is your expected CTC or compensation?") is True
    assert is_sensitive_question("Do you require visa sponsorship now or in the future?") is True
    assert is_sensitive_question("How many years of experience do you have with React?") is False


# ─── 4. ATS Scoring & Fact Check Tests ───────────────────────


def test_ats_keyword_coverage():
    jd = "We are seeking a Python developer proficient in FastAPI, SQL, and Docker."
    skills = ["Python", "FastAPI", "React", "Docker", "AWS"]
    score, matched, missing = compute_ats_keyword_coverage(jd, skills)
    assert score > 50
    assert "Python" in matched
    assert "FastAPI" in matched
    assert "Docker" in matched


# ─── 5. Document Builders (DOCX & PDF) Tests ─────────────────


def test_docx_resume_builder(tmp_path):
    master = MasterProfileData(
        contact=ContactInfo(full_name="Alex Mercer", email="alex@example.com", phone="+1 555-0199"),
        summary="Experienced full-stack engineer specializing in Python and React.",
        skills=["Python", "FastAPI", "TypeScript", "React"],
        experience=[
            ExperienceEntry(
                title="Software Engineer",
                company="TechCorp",
                start_date="2022",
                end_date="2024",
                bullets=["Built distributed microservices handling 10k RPS", "Reduced latency by 35%"],
            )
        ],
        education=[EducationEntry(degree="B.S. Computer Science", institution="State University")],
    )

    docx_path = str(tmp_path / "test_resume.docx")
    out = create_resume_docx(master, docx_path)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000


def test_pdf_resume_builder(tmp_path):
    master = MasterProfileData(
        contact=ContactInfo(full_name="Alex Mercer", email="alex@example.com"),
        summary="Experienced full-stack engineer.",
        skills=["Python", "SQL"],
        experience=[
            ExperienceEntry(
                title="Backend Developer",
                company="CloudTech",
                start_date="2021",
                end_date="Present",
                is_current=True,
                bullets=["Engineered automated ingestion pipelines"],
            )
        ],
    )

    pdf_path = str(tmp_path / "test_resume.pdf")
    out = create_resume_pdf(master, pdf_path)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000


# ─── 6. Scan Filter Overrides Tests ─────────────────────────


@pytest.mark.anyio
async def test_scan_filters_workday_cxs():
    from sources.workday import WorkdaySource
    from models.profile import Profile

    adapter = WorkdaySource()
    profile = Profile(name="Test", target_titles='["Software Engineer"]', cities='["San Jose"]', countries='["United States"]')
    
    # Test with custom scan filter overrides
    filters = {
        "roles": ["Platform Engineer"],
        "cities": ["San Jose", "Remote"],
        "country": "United States",
        "limit": 5,
    }
    # Should run search without throwing
    jobs = await adapter.search(profile, filters=filters)
    assert isinstance(jobs, list)


def test_trigger_scan_api_with_filters():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db

    init_db()
    client = TestClient(app)
    res = client.post("/api/jobs/scan", json={
        "roles": "AI Engineer, Backend",
        "country": "India",
        "cities": "Bengaluru, Remote",
        "portals": ["workday"],
        "limit": 5,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "workday" in data["portals_scanned"]
    assert data["filters_applied"]["country"] == "India"


def test_matching_score_single_job_api():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db, get_session
    from models.job import Job

    init_db()
    client = TestClient(app)

    session = next(get_session())
    job = Job(
        title="Python AI Engineer",
        company="NVIDIA",
        location="Remote",
        source="workday",
        description="We are seeking a Python AI Engineer with experience in LLMs, PyTorch, and FastAPI.",
        status="new"
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    job_id = job.id

    res = client.post(f"/api/matching/score/{job_id}", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["job_id"] == job_id
    assert "score" in data
    assert isinstance(data["score"], int)
    assert "reasons" in data


def test_matching_review_queue_filters_api():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db

    init_db()
    client = TestClient(app)

    res = client.get("/api/matching/review-queue?min_score=20&source=workday")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    for it in items:
        assert it["score"] >= 20
        assert it["source"] == "workday"


def test_matching_review_queue_action():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db, get_session
    from models.job import Job

    init_db()
    client = TestClient(app)

    session = next(get_session())
    job = Job(
        title="ML Engineer",
        company="Scale AI",
        location="San Francisco, CA",
        source="linkedin",
        status="new"
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    res = client.post(f"/api/matching/review-queue/{job.id}/action", json={"action": "approve"})
    assert res.status_code == 200
    assert res.json()["new_status"] == "approved"


def test_kill_switch_api():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Activate kill switch
    res = client.post("/api/applications/kill-switch", json={"active": True})
    assert res.status_code == 200
    assert res.json()["kill_switch_active"] is True

    # Check status
    res = client.get("/api/applications/kill-switch")
    assert res.status_code == 200
    assert res.json()["kill_switch_active"] is True

    # Applying while kill switch is active should fail with 400
    res = client.post("/api/applications/apply", json={"job_id": 1})
    assert res.status_code == 400
    assert "Kill switch is active" in res.json()["detail"]

    # Deactivate kill switch
    res = client.post("/api/applications/kill-switch", json={"active": False})
    assert res.status_code == 200
    assert res.json()["kill_switch_active"] is False


def test_application_history_api():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/applications/history")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


def test_analytics_funnel_and_portals_api():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res_funnel = client.get("/api/analytics/funnel")
    assert res_funnel.status_code == 200
    funnel = res_funnel.json()
    assert "total_discovered" in funnel
    assert "applied" in funnel

    res_portals = client.get("/api/analytics/portals")
    assert res_portals.status_code == 200
    portals = res_portals.json()
    assert isinstance(portals, list)
    assert any(p["portal"] == "workday" for p in portals)


def test_analytics_export_csv_and_backup():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res_csv = client.get("/api/analytics/export/csv")
    assert res_csv.status_code == 200
    assert "text/csv" in res_csv.headers["content-type"]
    assert "attachment; filename=applications_tracker.csv" in res_csv.headers["content-disposition"]

    res_backup = client.get("/api/analytics/backup")
    assert res_backup.status_code == 200


def test_stage1_remote_conflict():
    profile = Profile(
        name="Remote Engineer",
        remote_preference="remote",
        min_experience=1,
        max_experience=4,
    )
    job = Job(
        title="Backend Engineer",
        company="ExampleCorp",
        description="This role is onsite only (5 days in office, no remote).",
    )
    passed, reasons = stage1_rule_filter(job, profile)
    assert passed is False
    assert any("onsite" in r.lower() for r in reasons)


def test_matching_score_all_api():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db

    init_db()
    client = TestClient(app)
    res = client.post("/api/matching/score-all", json={"limit": 3, "force_rescore": False})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "scored_count" in data
    assert "matched_count" in data
    assert "min_score_threshold" in data


def test_answer_bank_crud_api():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db

    init_db()
    client = TestClient(app)

    create_res = client.post("/api/answer-bank", json={
        "pattern": "What is your preferred work location?",
        "answer": "Remote or Bengaluru",
        "category": "general",
        "approved": False,
    })
    assert create_res.status_code == 200
    created = create_res.json()
    entry_id = created["id"]
    assert created["approved"] is False

    upd_res = client.put(f"/api/answer-bank/{entry_id}", json={"approved": True})
    assert upd_res.status_code == 200
    assert upd_res.json()["approved"] is True

    del_res = client.delete(f"/api/answer-bank/{entry_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] == entry_id


def test_tracker_manual_queue_and_audit_api():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import init_db, get_session
    from models.job import Job

    init_db()
    client = TestClient(app)

    session = next(get_session())
    job = Job(
        title="Platform Engineer",
        company="CloudTest",
        location="Remote",
        source="workday",
        status="manual",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    mq_res = client.get("/api/applications/manual-queue")
    assert mq_res.status_code == 200
    assert any(m["id"] == job.id for m in mq_res.json())

    move_res = client.put(f"/api/applications/tracker/{job.id}", json={"status": "interview"})
    assert move_res.status_code == 200
    assert move_res.json()["new_status"] == "interview"

    tracker_res = client.get("/api/applications/tracker")
    assert tracker_res.status_code == 200
    assert any(c["id"] == job.id for c in tracker_res.json()["interview"])

    audit_res = client.get("/api/analytics/audit?limit=10")
    assert audit_res.status_code == 200
    assert isinstance(audit_res.json(), list)
    assert len(audit_res.json()) > 0


def test_health_includes_scheduler_status():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    components = res.json()["components"]
    assert "scheduler" in components
    assert "running" in components["scheduler"]


# ─── 9. LaTeX Tailoring, Modular AI Skills & Fresher Filtering ─


def test_latex_parse_and_render_tailored(tmp_path):
    from docs.builder_latex import (
        SAMPLE_STARTER_LATEX,
        escape_latex,
        parse_latex_to_master_profile,
        render_tailored_latex,
    )

    assert escape_latex("AI & ML 100% #1_test") == r"AI \& ML 100\% \#1\_test"

    parsed = parse_latex_to_master_profile(SAMPLE_STARTER_LATEX)
    assert parsed.contact.full_name == "Manda Harshitha"
    assert "Spring Boot" in parsed.skills
    assert len(parsed.projects) == 2
    assert len(parsed.certifications) == 2
    assert len(parsed.education) == 3

    out_tex = tmp_path / "tailored.tex"
    path, tex = render_tailored_latex(
        data=parsed,
        output_path=str(out_tex),
        custom_summary="Tailored summary for SAP & Cloud teams (100% grounded).",
        tailored_project_bullets={
            "Spring Boot Employee Management System": ["Built RESTful Spring Boot APIs with MySQL & validation."]
        },
        emphasized_skills=["Java", "Spring Boot", "Python"],
    )
    assert out_tex.exists()
    assert r"\documentclass[a4paper,11pt]{article}" in tex
    assert r"SAP \& Cloud teams (100\% grounded)." in tex
    assert r"MySQL \& validation." in tex


def test_compact_context_slices_and_form_defaults():
    import asyncio
    from docs.builder_latex import SAMPLE_STARTER_LATEX, parse_latex_to_master_profile
    from llm.skills.context_builder import build_compact_context
    from llm.skills.form_answer_skill import skill_answer_form_question

    parsed = parse_latex_to_master_profile(SAMPLE_STARTER_LATEX)
    form_ctx = build_compact_context(parsed, slice_type="form")
    assert form_ctx["experience_level"] == "fresher"
    assert form_ctx["previous_company"] == "N/A"
    assert form_ctx["current_ctc"] == "N/A"
    assert "latex_template" not in form_ctx

    match_ctx = build_compact_context(parsed, slice_type="match")
    assert "experience" not in match_ctx
    assert "Java" in match_ctx["skills"]

    ans_prev = asyncio.run(skill_answer_form_question("What is your previous company?", parsed))
    assert ans_prev.answer == "N/A"
    assert ans_prev.source == "deterministic_default"
    assert ans_prev.requires_human is False

    ans_exp = asyncio.run(skill_answer_form_question("How many years of experience do you have?", parsed))
    assert ans_exp.answer == "0"
    assert ans_exp.source == "deterministic_default"


def test_fresher_stage1_filter_rejects_experienced_roles():
    fresher_profile = Profile(name="Fresher", min_experience=0, max_experience=0)

    mid_naukri = Job(
        title="Software Engineer",
        company="Acme",
        description="Experience required: 2 - 4 years of experience in Java and Spring Boot.",
    )
    passed, reasons = stage1_rule_filter(mid_naukri, fresher_profile, app_defaults={"experience_level": "fresher"})
    assert passed is False
    assert any("fresher/entry" in r.lower() for r in reasons)

    senior_title = Job(title="Senior Backend Engineer", company="Beta", description="Python APIs")
    passed_sr, _ = stage1_rule_filter(senior_title, fresher_profile)
    assert passed_sr is False

    entry_job = Job(
        title="Graduate Software Engineer",
        company="SAP",
        description="0 - 1 years experience. Ideal for fresher graduates with Java and Python.",
    )
    passed_entry, reasons_entry = stage1_rule_filter(entry_job, fresher_profile)
    assert passed_entry is True, reasons_entry


def test_latex_import_and_application_defaults_endpoints():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    tpl_res = client.get("/api/profiles/master/default-latex-template")
    assert tpl_res.status_code == 200
    assert r"\newcommand{\name}{Manda Harshitha}" in tpl_res.json()["latex"]

    put_res = client.put(
        "/api/settings/application-defaults",
        json={"experience_level": "fresher", "previous_company": "N/A", "years_of_experience": "0"},
    )
    assert put_res.status_code == 200
    assert put_res.json()["defaults"]["previous_company"] == "N/A"


def test_latex_project_ordering_and_styled_pdf_generation(tmp_path):
    from docs.builder_latex import (
        SAMPLE_STARTER_LATEX,
        parse_latex_to_master_profile,
        render_tailored_latex,
    )

    parsed = parse_latex_to_master_profile(SAMPLE_STARTER_LATEX)
    out_tex = tmp_path / "ordered.tex"
    _, tex = render_tailored_latex(
        data=parsed,
        output_path=str(out_tex),
        project_order=["Sarcasm Detection - NLP Machine Learning Project"],
        tailored_interests=["AI Engineering", "LLM Development"],
    )
    nlp_pos = tex.find("Sarcasm Detection")
    spring_pos = tex.find("Spring Boot Employee Management System")
    assert nlp_pos != -1 and spring_pos != -1 and nlp_pos < spring_pos
    assert "AI Engineering, LLM Development" in tex









