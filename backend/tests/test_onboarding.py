"""Tests for the CareerOps-aligned Onboarding and Doctor system."""

import pytest
from fastapi.testclient import TestClient

from app.database import init_db
from app.main import app
from schemas.onboarding import (
    CandidateAnswers,
    CompensationAnswers,
    CvAnswers,
    LocationAnswers,
    NarrativeAnswers,
    OnboardingAnswers,
    PortalsAnswers,
)
from services.onboarding import (
    init_personalization_templates,
    run_doctor,
    save_onboarding_answers,
    sync_markdown_tracker,
    validate_cv_markdown,
)

SAMPLE_VALID_CV_MARKDOWN = """# Manda Harshitha

Hyderabad, India | harshithagoud32@gmail.com | +91-7989508635

## Professional Summary
Final-year BCA student specializing in Java, Python, and AI/ML solutions.

## Work Experience
### Tech Innovations — Hyderabad
**Software Engineering Intern**
2024 - Present
- Built RESTful backend APIs with Spring Boot and MySQL.
- Designed database schemas and optimized CRUD query latency.

## Projects
### Sarcasm Detection NLP
- Built machine learning model using Python, NLP, and Scikit-learn.

## Technical Skills
- Programming Languages: Python, Java, SQL, JavaScript
- Frameworks: Spring Boot, Django, FastAPI
- AI & ML: NLP, Scikit-learn, PyTorch, RAG Fundamentals

## Education
- Bachelor of Computer Applications (BCA) — KL University (2023 - Present)
"""


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_validate_cv_markdown_success():
    passed, errors, parsed = validate_cv_markdown(SAMPLE_VALID_CV_MARKDOWN)
    assert passed is True
    assert len(errors) == 0
    assert parsed.contact.full_name == "Manda Harshitha"
    assert len(parsed.experience) >= 1
    assert parsed.experience[0].company.startswith("Tech Innovations")
    assert parsed.experience[0].title == "Software Engineering Intern"
    assert "Python" in parsed.skills
    assert "Java" in parsed.skills


def test_validate_cv_markdown_missing_experience():
    bad_cv = "# Jane Doe\n\n## Education\n- BS in CS\n\n## Skills\n- Python"
    passed, errors, _ = validate_cv_markdown(bad_cv)
    assert passed is False
    assert any("experience" in e.lower() for e in errors)


def test_init_personalization_templates():
    copied = init_personalization_templates()
    # Should create or preserve personalization files
    assert isinstance(copied, list)


def test_save_onboarding_answers_and_doctor_report():
    answers = OnboardingAnswers(
        spend_tier="standard",
        candidate=CandidateAnswers(
            full_name="Manda Harshitha",
            email="harshithagoud32@gmail.com",
            location="Hyderabad, Telangana, India",
            years_of_experience=0,
        ),
        target_roles=["Software Engineer", "AI Engineer", "Backend Developer"],
        compensation=CompensationAnswers(
            target_range="6-10 LPA",
            currency="INR",
            minimum="5 LPA",
        ),
        location=LocationAnswers(
            country="India",
            city="Hyderabad",
            timezone="Asia/Kolkata",
        ),
        portals=PortalsAnswers(
            positive=["Software Engineer", "AI Engineer", "Python Developer"],
            negative=["Senior", "Staff", "Principal", "Director"],
            countries=["India"],
            cities=["Hyderabad", "Bengaluru"],
        ),
        cv=CvAnswers(
            raw_markdown=SAMPLE_VALID_CV_MARKDOWN,
            max_pages=1,
            strict_pages=True,
        ),
    )

    doc = save_onboarding_answers(answers)
    assert doc.data_root != ""
    assert doc.onboarding_needed is False
    # CV check should pass
    cv_check = next((c for c in doc.checks if "CV Structure" in c.name), None)
    assert cv_check is not None
    assert cv_check.status == "ok"


def test_onboarding_api_endpoints():
    client = TestClient(app)

    # 1. Validate CV endpoint
    v_res = client.post("/api/onboarding/validate-cv", json={"markdown": SAMPLE_VALID_CV_MARKDOWN})
    assert v_res.status_code == 200
    assert v_res.json()["valid"] is True

    # 2. Setup endpoint
    setup_payload = {
        "spend_tier": "standard",
        "candidate": {
            "full_name": "Manda Harshitha",
            "email": "harshithagoud32@gmail.com",
            "location": "Hyderabad, India",
            "years_of_experience": 0,
        },
        "target_roles": ["Software Engineer", "AI Engineer"],
        "compensation": {
            "target_range": "6-10 LPA",
            "currency": "INR",
        },
        "location": {
            "country": "India",
            "city": "Hyderabad",
            "timezone": "Asia/Kolkata",
        },
        "portals": {
            "positive": ["Software Engineer", "AI Engineer"],
            "negative": ["Senior", "Lead"],
            "countries": ["India"],
            "cities": ["Hyderabad"],
        },
        "cv": {
            "raw_markdown": SAMPLE_VALID_CV_MARKDOWN,
            "max_pages": 1,
            "strict_pages": False,
        },
    }
    s_res = client.post("/api/onboarding/setup", json=setup_payload)
    assert s_res.status_code == 200
    doc_data = s_res.json()
    assert doc_data["onboarding_needed"] is False

    # 3. Status endpoint
    stat_res = client.get("/api/onboarding/status")
    assert stat_res.status_code == 200
    stat_data = stat_res.json()
    assert "profile" in stat_data["completed_steps"]
    assert "cv" in stat_data["completed_steps"]
    assert "portals" in stat_data["completed_steps"]

    # 4. Doctor check endpoint
    doc_res = client.get("/api/onboarding/doctor")
    assert doc_res.status_code == 200
    assert "checks" in doc_res.json()

    # 5. Sync tracker endpoint
    tr_res = client.post("/api/onboarding/sync-tracker")
    assert tr_res.status_code == 200
    assert tr_res.json()["success"] is True
