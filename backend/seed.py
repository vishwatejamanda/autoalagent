"""Seed database with realistic sample profile, jobs, and answer bank data for immediate testing."""

import json
from datetime import datetime, timezone
from sqlmodel import Session, select

from app.database import engine, init_db
from models.profile import MasterProfile, Profile
from models.job import Job, JobScore
from models.settings import AnswerBank
from schemas.profile import (
    MasterProfileData,
    ContactInfo,
    ExperienceEntry,
    EducationEntry,
    ProjectEntry,
    CertificationEntry,
)
from services.dedupe import compute_description_hash


def seed_data():
    print("Initializing database...")
    init_db()

    with Session(engine) as session:
        # 1. Master Profile
        existing_master = session.exec(select(MasterProfile)).first()
        if not existing_master:
            sample_master = MasterProfileData(
                contact=ContactInfo(
                    full_name="Alex Mercer",
                    email="alex.mercer@example.com",
                    phone="+1 (555) 234-5678",
                    location="San Francisco, CA",
                    linkedin="https://linkedin.com/in/alex-mercer-dev",
                    github="https://github.com/alexmercer-dev",
                ),
                summary="Full Stack Software Engineer with 3+ years of experience designing scalable distributed web services, RESTful APIs, and responsive frontends using Python (FastAPI/Django), TypeScript, and React/Next.js.",
                skills=[
                    "Python", "FastAPI", "TypeScript", "React", "Next.js", "SQL",
                    "PostgreSQL", "SQLite", "Docker", "Git", "REST APIs", "Tailwind CSS",
                    "Playwright", "AWS"
                ],
                experience=[
                    ExperienceEntry(
                        title="Software Engineer",
                        company="Nexus Cloud Systems",
                        location="San Francisco, CA",
                        start_date="Jan 2022",
                        end_date="Present",
                        is_current=True,
                        bullets=[
                            "Architected high-throughput REST APIs using FastAPI and PostgreSQL handling 15k+ daily requests with 99.9% uptime",
                            "Led migration of monolith frontend to Next.js App Router, decreasing page load times by 40%",
                            "Implemented background task queues and automated data pipeline syncs using Python and Redis",
                        ],
                    ),
                    ExperienceEntry(
                        title="Junior Software Developer",
                        company="Catalyst Tech Labs",
                        location="San Jose, CA",
                        start_date="Jun 2020",
                        end_date="Dec 2021",
                        is_current=False,
                        bullets=[
                            "Engineered responsive UI components in React and TypeScript integrated with backend REST endpoints",
                            "Wrote automated unit and integration tests achieving 88% test coverage across key repositories",
                        ],
                    ),
                ],
                education=[
                    EducationEntry(
                        degree="B.S. in Computer Science",
                        institution="University of California, Davis",
                        graduation_date="2020",
                    )
                ],
            )
            master = MasterProfile(
                data=sample_master.model_dump_json(),
                version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(master)
            print("✓ Seeded Master Profile ('Alex Mercer')")

        # 2. Personas (Profiles)
        existing_profile = session.exec(select(Profile)).first()
        if not existing_profile:
            p1 = Profile(
                name="Software Engineer (Full Stack)",
                target_titles=json.dumps(["Software Engineer", "Full Stack Engineer", "Python Developer"]),
                include_keywords=json.dumps(["Software", "Full Stack", "Developer"]),
                exclude_keywords=json.dumps(["Senior", "Staff", "Director", "Lead"]),
                countries=json.dumps(["United States", "Remote"]),
                cities=json.dumps(["San Francisco", "San Jose", "Remote"]),
                remote_preference="hybrid",
                min_experience=1,
                max_experience=4,
                salary_expectation="$120,000 - $145,000",
                notice_period="2 weeks",
                base_resume_emphasis="Emphasize Python, FastAPI, React/Next.js, and high-performance API design.",
                allowed_portals=json.dumps(["workday", "linkedin", "naukri"]),
                daily_cap=25,
                auto_apply_mode="review",
                min_match_score=65,
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(p1)
            print("✓ Seeded Job Hunting Persona ('Software Engineer')")

        # 3. Sample Jobs
        existing_jobs = session.exec(select(Job)).all()
        if not existing_jobs:
            sample_jobs = [
                Job(
                    source="workday",
                    external_id="adobe_R149201",
                    title="Software Engineer - Web Technologies",
                    company="Adobe",
                    location="San Jose, CA (Hybrid)",
                    url="https://adobe.wd5.myworkdayjobs.com/external_experienced/job/San-Jose/Software-Engineer_R149201",
                    description="Adobe is seeking a passionate Software Engineer to join our Creative Cloud core services team. You will build high-reliability web APIs using Python, TypeScript, and modern cloud technologies. Qualifications: 2-4 years of experience with Python or JavaScript, understanding of REST APIs and relational databases.",
                    description_hash=compute_description_hash("Adobe is seeking a passionate Software Engineer to join our Creative Cloud core services team."),
                    easy_apply=False,
                    status="matched",
                ),
                Job(
                    source="linkedin",
                    external_id="li_38920194",
                    title="Full Stack Engineer (React / Python)",
                    company="Stripe",
                    location="San Francisco, CA / Remote",
                    url="https://www.linkedin.com/jobs/view/38920194",
                    description="We are looking for a Full Stack Engineer to build tools that help businesses manage their payments globally. Experience with Python, Next.js, and API design required. Candidates should have 2+ years of professional development experience.",
                    description_hash=compute_description_hash("We are looking for a Full Stack Engineer to build tools that help businesses manage their payments globally."),
                    easy_apply=True,
                    status="matched",
                ),
                Job(
                    source="workday",
                    external_id="netflix_JR29012",
                    title="Software Engineer, Platform Tools",
                    company="Netflix",
                    location="Los Gatos, CA",
                    url="https://netflix.wd1.myworkdayjobs.com/Netflix_Jobs/job/Los-Gatos/Software-Engineer_JR29012",
                    description="Netflix is looking for an engineer to help scale internal developer tooling. Requirements: Strong proficiency in Python or Java, familiarity with Docker and microservice architectures.",
                    description_hash=compute_description_hash("Netflix is looking for an engineer to help scale internal developer tooling."),
                    easy_apply=False,
                    status="new",
                ),
            ]
            for j in sample_jobs:
                session.add(j)
            session.commit()

            # Add sample scores
            j1 = session.exec(select(Job).where(Job.company == "Adobe")).first()
            if j1:
                score1 = JobScore(
                    job_id=j1.id,
                    profile_id=1,
                    score=88,
                    reasons=json.dumps([
                        "Strong alignment with candidate's Python and TypeScript expertise",
                        "Experience level (2-4 yrs) matches candidate's 3 years background",
                        "Hybrid San Jose location fits candidate preferences"
                    ]),
                    gaps=json.dumps([]),
                    red_flags=json.dumps([]),
                )
                session.add(score1)

            j2 = session.exec(select(Job).where(Job.company == "Stripe")).first()
            if j2:
                score2 = JobScore(
                    job_id=j2.id,
                    profile_id=1,
                    score=92,
                    reasons=json.dumps([
                        "Direct match for React, Next.js, and Python API development",
                        "Remote-friendly opportunity",
                        "Clear seniority alignment"
                    ]),
                    gaps=json.dumps([]),
                    red_flags=json.dumps([]),
                )
                session.add(score2)

            print("✓ Seeded Sample Jobs & Match Scores (Adobe, Stripe, Netflix)")

        # 4. Answer Bank
        existing_answers = session.exec(select(AnswerBank)).all()
        if not existing_answers:
            sample_answers = [
                AnswerBank(
                    pattern="Are you legally authorized to work in the United States?",
                    category="authorization",
                    answer="Yes, I am a US citizen and authorized to work for any employer without sponsorship.",
                    approved=True,
                    times_used=4,
                ),
                AnswerBank(
                    pattern="Will you now or in the future require visa sponsorship?",
                    category="authorization",
                    answer="No, I will not require visa sponsorship.",
                    approved=True,
                    times_used=4,
                ),
                AnswerBank(
                    pattern="What is your notice period?",
                    category="general",
                    answer="2 weeks from receiving and signing a written offer.",
                    approved=True,
                    times_used=3,
                ),
                AnswerBank(
                    pattern="What is your expected compensation or CTC?",
                    category="salary",
                    answer="$130,000 - $145,000 base salary, open to total compensation discussions.",
                    approved=True,
                    times_used=2,
                ),
                AnswerBank(
                    pattern="How many years of experience do you have with Python?",
                    category="skills",
                    answer="3+ years of professional production experience.",
                    approved=True,
                    times_used=5,
                ),
            ]
            for a in sample_answers:
                session.add(a)
            print("✓ Seeded Answer Bank entries with standard approvals")

        session.commit()
        print("\n🎉 Database seeded successfully! You can now start the frontend and explore with live data immediately.")


if __name__ == "__main__":
    seed_data()

