"""Resume parsing service: extracts text from PDF/DOCX and parses into MasterProfileData."""

import io
import json
import logging
import re
from typing import BinaryIO

from pypdf import PdfReader
from docx import Document

from schemas.profile import (
    MasterProfileData,
    ContactInfo,
    ExperienceEntry,
    ProjectEntry,
    EducationEntry,
    CertificationEntry,
)
from llm.provider import LLMMessage
from llm.router import get_router

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract plain text from PDF bytes."""
    reader = PdfReader(io.BytesIO(file_bytes))
    text_chunks = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            text_chunks.append(txt)
    return "\n\n".join(text_chunks)


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract plain text from DOCX bytes."""
    doc = Document(io.BytesIO(file_bytes))
    text_chunks = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_chunks.append(row_text)
    return "\n".join(text_chunks)


def extract_text_from_file(filename: str, file_bytes: bytes) -> str:
    """Extract plain text from uploaded file based on its extension."""
    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower_name.endswith(".docx") or lower_name.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        # Fallback to UTF-8 text decoding
        return file_bytes.decode("utf-8", errors="ignore")


def heuristic_parse_resume(raw_text: str) -> MasterProfileData:
    """Heuristic fallback parser when LLM is unavailable or offline."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    
    # 1. Contact info
    contact = ContactInfo()
    if lines:
        contact.full_name = lines[0]
    
    # Email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_text)
    if email_match:
        contact.email = email_match.group(0)
    
    # Phone
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", raw_text)
    if phone_match:
        contact.phone = phone_match.group(0)
    
    # Links
    for line in lines:
        if "linkedin.com" in line.lower() and not contact.linkedin:
            contact.linkedin = line
        elif "github.com" in line.lower() and not contact.github:
            contact.github = line

    # 2. Extract potential skills
    known_skills = [
        "Python", "JavaScript", "TypeScript", "React", "Next.js", "Node.js", "FastAPI",
        "SQL", "PostgreSQL", "SQLite", "Docker", "AWS", "Git", "HTML", "CSS", "Tailwind",
        "REST API", "GraphQL", "Playwright", "Selenium", "CI/CD", "Machine Learning", "NLP"
    ]
    found_skills = [s for s in known_skills if re.search(rf"\b{re.escape(s)}\b", raw_text, re.IGNORECASE)]

    # 3. Simple experience extraction
    summary = lines[1] if len(lines) > 1 else ""

    return MasterProfileData(
        contact=contact,
        summary=summary,
        experience=[],
        projects=[],
        skills=found_skills,
        education=[],
        certifications=[],
        achievements=[],
    )


async def parse_resume_to_master_profile(raw_text: str) -> MasterProfileData:
    """Parse resume text into structured MasterProfileData via LLM with heuristic fallback."""
    if not raw_text.strip():
        return MasterProfileData()

    system_prompt = (
        "You are an expert HR and ATS resume parser. Extract the candidate's exact resume details into structured JSON.\n"
        "HARD RULES:\n"
        "1. Never invent or hallucinate any details, dates, companies, degrees, or skills.\n"
        "2. Extract every factual bullet point under each role.\n"
        "3. Accurately separate skills into individual canonical names (e.g. 'Python', 'FastAPI', 'React').\n"
        "4. Capture education, certifications, and projects if present."
    )

    user_prompt = f"Resume text to parse:\n\n{raw_text[:12000]}"

    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    try:
        router = get_router()
        parsed_data, _ = await router.chat_json(
            messages=messages,
            response_model=MasterProfileData,
            task="strong",
            temperature=0.1,
            max_retries=2,
        )
        return parsed_data
    except Exception as exc:
        logger.warning("LLM parsing failed or unavailable (%s). Falling back to heuristic parser.", exc)
        return heuristic_parse_resume(raw_text)

