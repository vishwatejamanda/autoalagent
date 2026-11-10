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




