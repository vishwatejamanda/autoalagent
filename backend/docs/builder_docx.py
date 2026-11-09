"""ATS-Safe DOCX Resume Builder (Single-column, standard headings, no tables/images)."""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

from schemas.profile import MasterProfileData


def create_resume_docx(
    data: MasterProfileData,
    output_path: str,
    custom_summary: str | None = None,
    tailored_bullets: dict[str, list[str]] | None = None,
) -> str:
    """Build a clean, single-column, ATS-friendly DOCX resume."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc = Document()

    # Set 0.75-inch standard margins
    for section in doc.sections:
        section.top_margin = Inches(0.75)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # 1. Header (Name & Contact)
    name_p = doc.add_paragraph()
    name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = name_p.add_run(data.contact.full_name or "Candidate Name")
    run.font.name = "Calibri"
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = RGBColor(17, 24, 39)

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
        contact_p = doc.add_paragraph()
        contact_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c_run = contact_p.add_run(" | ".join(contact_parts))
        c_run.font.name = "Calibri"
        c_run.font.size = Pt(9.5)
        c_run.font.color.rgb = RGBColor(75, 85, 99)

    def add_section_heading(title: str):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(2)
        p_run = p.add_run(title.upper())
        p_run.font.name = "Calibri"
        p_run.font.size = Pt(11)
        p_run.font.bold = True
        p_run.font.color.rgb = RGBColor(31, 41, 55)

    # 2. Professional Summary
    summary_text = custom_summary or data.summary
    if summary_text:
        add_section_heading("Professional Summary")
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        s_run = p.add_run(summary_text)
        s_run.font.name = "Calibri"
        s_run.font.size = Pt(10)

    # 3. Skills
    if data.skills:
        add_section_heading("Technical Skills")
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        s_run = p.add_run(", ".join(data.skills))
        s_run.font.name = "Calibri"
        s_run.font.size = Pt(10)

    # 4. Work Experience
    if data.experience:
        add_section_heading("Professional Experience")
        for idx, exp in enumerate(data.experience):
            role_p = doc.add_paragraph()
            role_p.paragraph_format.space_before = Pt(4)
            role_p.paragraph_format.space_after = Pt(1)
            
            # Title & Company
            title_run = role_p.add_run(f"{exp.title} — {exp.company}")
            title_run.font.name = "Calibri"
            title_run.font.size = Pt(10.5)
            title_run.font.bold = True

            dates = f"{exp.start_date} – {'Present' if exp.is_current else exp.end_date}"
            loc = f" | {exp.location}" if exp.location else ""
            date_run = role_p.add_run(f" ({dates}{loc})")
            date_run.font.name = "Calibri"
            date_run.font.size = Pt(9.5)
            date_run.font.italic = True
            date_run.font.color.rgb = RGBColor(107, 114, 128)

            # Bullets
            bullets = (tailored_bullets or {}).get(f"{exp.company}_{exp.title}", exp.bullets)
            for b in bullets:
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_after = Pt(2)
                b_run = bp.add_run(b)
                b_run.font.name = "Calibri"
                b_run.font.size = Pt(10)

    # 5. Projects
    if data.projects:
        add_section_heading("Projects")
        for proj in data.projects:
            pp = doc.add_paragraph()
            pp.paragraph_format.space_before = Pt(3)
            pp.paragraph_format.space_after = Pt(1)
            
            p_run = pp.add_run(proj.name)
            p_run.font.name = "Calibri"
            p_run.font.size = Pt(10.5)
            p_run.font.bold = True

            if proj.technologies:
                t_run = pp.add_run(f" [{', '.join(proj.technologies)}]")
                t_run.font.name = "Calibri"
                t_run.font.size = Pt(9.5)
                t_run.font.italic = True

            if proj.description:
                dp = doc.add_paragraph()
                dp.paragraph_format.space_after = Pt(2)
                d_run = dp.add_run(proj.description)
                d_run.font.name = "Calibri"
                d_run.font.size = Pt(10)

            for b in proj.bullets:
                bp = doc.add_paragraph(style="List Bullet")
                bp.paragraph_format.space_after = Pt(2)
                b_run = bp.add_run(b)
                b_run.font.name = "Calibri"
                b_run.font.size = Pt(10)

    # 6. Education
    if data.education:
        add_section_heading("Education")
        for edu in data.education:
            ep = doc.add_paragraph()
            ep.paragraph_format.space_after = Pt(2)
            deg_run = ep.add_run(f"{edu.degree} — {edu.institution}")
            deg_run.font.name = "Calibri"
            deg_run.font.size = Pt(10)
            deg_run.font.bold = True

            if edu.graduation_date:
                grad_run = ep.add_run(f" ({edu.graduation_date})")
                grad_run.font.name = "Calibri"
                grad_run.font.size = Pt(9.5)
                grad_run.font.italic = True

    # 7. Certifications
    if data.certifications:
        add_section_heading("Certifications")
        for cert in data.certifications:
            cp = doc.add_paragraph(style="List Bullet")
            cp.paragraph_format.space_after = Pt(2)
            cert_text = f"{cert.name} — {cert.issuer}" if cert.issuer else cert.name
            if cert.date:
                cert_text += f" ({cert.date})"
            c_run = cp.add_run(cert_text)
            c_run.font.name = "Calibri"
            c_run.font.size = Pt(10)

    doc.save(output_path)
    return output_path

