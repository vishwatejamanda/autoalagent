"""ATS-Safe PDF Resume Builder using ReportLab (Single-column, selectable text, standard typography)."""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib import colors

from schemas.profile import MasterProfileData


def create_resume_pdf(
    data: MasterProfileData,
    output_path: str,
    custom_summary: str | None = None,
    tailored_bullets: dict[str, list[str]] | None = None,
) -> str:
    """Build a clean ATS-friendly PDF resume."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ResumeTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        alignment=1,  # Center
        textColor=colors.HexColor("#111827"),
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=1,  # Center
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )

    heading_style = ParagraphStyle(
        "ResumeHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "ResumeBullet",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#374151"),
        leftIndent=15,
        spaceAfter=2,
    )

    elements = []

    # 1. Header (Name & Contact)
    elements.append(Paragraph(data.contact.full_name or "Candidate Name", title_style))

    contact_parts = []
    if data.contact.email:
        contact_parts.append(data.contact.email)
    if data.contact.phone:
        contact_parts.append(data.contact.phone)
    if data.contact.location:
        contact_parts.append(data.contact.location)
    if data.contact.linkedin:
        contact_parts.append(data.contact.linkedin)
    if data.contact.github:
        contact_parts.append(data.contact.github)

    if contact_parts:
        elements.append(Paragraph(" &bull; ".join(contact_parts), contact_style))

    def add_section(title: str):
        elements.append(Paragraph(title.upper(), heading_style))
        elements.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#D1D5DB"), spaceAfter=5))

    # 2. Professional Summary
    summary_text = custom_summary or data.summary
    if summary_text:
        add_section("Professional Summary")
        elements.append(Paragraph(summary_text, body_style))
        elements.append(Spacer(1, 4))

    # 3. Technical Skills
    if data.skills:
        add_section("Technical Skills")
        elements.append(Paragraph(", ".join(data.skills), body_style))
        elements.append(Spacer(1, 4))

    # 4. Work Experience
    if data.experience:
        add_section("Professional Experience")
        for exp in data.experience:
            dates = f"{exp.start_date} – {'Present' if exp.is_current else exp.end_date}"
            role_header = f"<b>{exp.title}</b> — {exp.company} <i>({dates})</i>"
            elements.append(Paragraph(role_header, body_style))

            bullets = (tailored_bullets or {}).get(f"{exp.company}_{exp.title}", exp.bullets)
            for b in bullets:
                elements.append(Paragraph(f"&bull; {b}", bullet_style))
            elements.append(Spacer(1, 4))

    # 5. Projects
    if data.projects:
        add_section("Projects")
        for proj in data.projects:
            tech = f" <i>[{', '.join(proj.technologies)}]</i>" if proj.technologies else ""
            elements.append(Paragraph(f"<b>{proj.name}</b>{tech}", body_style))
            if proj.description:
                elements.append(Paragraph(proj.description, bullet_style))
            for b in proj.bullets:
                elements.append(Paragraph(f"&bull; {b}", bullet_style))
            elements.append(Spacer(1, 3))

    # 6. Education
    if data.education:
        add_section("Education")
        for edu in data.education:
            grad = f" <i>({edu.graduation_date})</i>" if edu.graduation_date else ""
            elements.append(Paragraph(f"<b>{edu.degree}</b> — {edu.institution}{grad}", body_style))
            elements.append(Spacer(1, 2))

    # 7. Certifications
    if data.certifications:
        add_section("Certifications")
        for cert in data.certifications:
            issuer = f" — {cert.issuer}" if cert.issuer else ""
            dt = f" <i>({cert.date})</i>" if cert.date else ""
            elements.append(Paragraph(f"&bull; <b>{cert.name}</b>{issuer}{dt}", bullet_style))

    doc.build(elements)
    return output_path

