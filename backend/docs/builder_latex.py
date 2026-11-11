r"""ATS-Safe LaTeX Resume Builder & Parser.

Supports:
1. Preserving the user's exact LaTeX template preamble and custom macros
   (`\resumeSubheading`, `\resumeProject`, `\resumeItemListStart`, etc.).
2. Tailoring Summary, Project/Experience bullets, Technical Skills ordering,
   and Areas of Interest while escaping LaTeX special characters safely.
3. Importing an existing `.tex` resume directly into `MasterProfileData`.
4. Optional native `pdflatex` compilation when installed on the host.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Optional

from schemas.profile import (
    CertificationEntry,
    ContactInfo,
    EducationEntry,
    MasterProfileData,
    ProjectEntry,
)

# Exact user-provided LaTeX template as default baseline
DEFAULT_LATEX_TEMPLATE = r"""%-------------------------
% Resume in Latex
%------------------------

\documentclass[a4paper,11pt]{article}

\usepackage{latexsym}
\usepackage{xcolor}
\usepackage{float}
\usepackage{ragged2e}
\usepackage[empty]{fullpage}
\usepackage{wrapfig}
\usepackage{tabularx}
\usepackage{titlesec}
\usepackage{geometry}
\usepackage{marvosym}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome5}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{cfr-lm}
\usepackage[T1]{fontenc}

\setlength{\multicolsep}{0pt}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\geometry{
    left=1.4cm,
    top=0.8cm,
    right=1.2cm,
    bottom=1cm
}

\usepackage[most]{tcolorbox}

\tcbset{
    frame code={},
    center title,
    left=0pt,
    right=0pt,
    top=0pt,
    bottom=0pt,
    colback=gray!20,
    colframe=white,
    width=\dimexpr\textwidth\relax,
    enlarge left by=-2mm,
    boxsep=4pt,
    arc=0pt,
    outer arc=0pt,
}

\urlstyle{same}
\raggedright
\setlength{\tabcolsep}{0in}

%-------------------------
% Section formatting
%-------------------------

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-7pt}]

%-------------------------
% Custom commands
%-------------------------

\newcommand{\resumeItem}[2]{
  \item{
    \textbf{#1}{\hspace{0.5mm}#2 \vspace{-0.5mm}}
  }
}

\newcommand{\resumeSubheading}[4]{
\vspace{0.5mm}\item
    \begin{tabular*}{0.98\textwidth}[t]{l@{\extracolsep{\fill}}r}
        \textbf{#1} & \textit{\footnotesize{#4}} \\
        \textit{\footnotesize{#3}} & \footnotesize{#2}\\
    \end{tabular*}
    \vspace{-2.4mm}
}

\newcommand{\resumeProject}[3]{
\vspace{0.5mm}\item
    \begin{tabular*}{0.98\textwidth}[t]{l@{\extracolsep{\fill}}r}
        \textbf{#1} & \textit{\footnotesize{#3}} \\
        \multicolumn{2}{p{0.98\textwidth}}{\footnotesize{#2}}
    \end{tabular*}
    \vspace{-2.4mm}
}

\newcommand{\resumeItemListStart}{
\begin{justify}
\begin{itemize}[
    leftmargin=3ex,
    rightmargin=2ex,
    noitemsep,
    labelsep=1.2mm,
    itemsep=0mm
]
\small
}

\newcommand{\resumeItemListEnd}{
\end{itemize}
\end{justify}
\vspace{-2mm}
}

\newcommand{\resumeSubHeadingListStart}{
\begin{itemize}[leftmargin=*,labelsep=0mm]
}

\newcommand{\resumeSubHeadingListEnd}{
\end{itemize}
\vspace{2mm}
}
"""


_LATEX_SPECIAL_MAP = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def escape_latex(text: str) -> str:
    """Escape plain-text strings for safe inclusion inside LaTeX bodies."""
    if not text:
        return ""
    # Replace backslash first only if not already escaping a LaTeX special char
    out: list[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] in _LATEX_SPECIAL_MAP:
            # Already escaped (e.g. \&) -> preserve cleanly
            out.append(text[i : i + 2])
            i += 2
            continue
        if ch == "\\":
            out.append(r"\textbackslash{}")
        elif ch in _LATEX_SPECIAL_MAP:
            out.append(_LATEX_SPECIAL_MAP[ch])
        elif ch in ("—", "–"):
            out.append("--")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _extract_macro(tex: str, macro: str) -> str:
    m = re.search(rf"\\newcommand\{{\\{re.escape(macro)}\}}\{{((?:[^{{}}]|\\{{|\\}})*)\}}", tex)
    return m.group(1).strip() if m else ""


def _clean_latex_inline(text: str) -> str:
    text = text.replace(r"\&", "&").replace(r"\%", "%").replace(r"\#", "#").replace(r"\_", "_")
    text = text.replace("--", "-").strip()
    return re.sub(r"\s+", " ", text)


def _extract_brace_args(text: str, start_pos: int, count: int) -> tuple[list[str], int]:
    """Parse `count` consecutive `{...}` arguments handling nested braces."""
    args: list[str] = []
    pos = start_pos
    n = len(text)
    for _ in range(count):
        while pos < n and text[pos].isspace():
            pos += 1
        if pos >= n or text[pos] != "{":
            break
        depth = 0
        arg_start = pos + 1
        pos += 1
        while pos < n:
            if text[pos] == "\\" and pos + 1 < n:
                pos += 2
                continue
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                if depth == 0:
                    args.append(text[arg_start:pos].strip())
                    pos += 1
                    break
                depth -= 1
            pos += 1
    return args, pos


def parse_latex_to_master_profile(tex_source: str) -> MasterProfileData:
    """Extract structured MasterProfileData from a LaTeX resume template."""
    contact = ContactInfo(
        full_name=_clean_latex_inline(_extract_macro(tex_source, "name")),
        location=_clean_latex_inline(_extract_macro(tex_source, "address")),
        phone=_clean_latex_inline(_extract_macro(tex_source, "phone")),
        email=_clean_latex_inline(_extract_macro(tex_source, "emaila")),
        linkedin=_extract_macro(tex_source, "linkedin"),
        github=_macro if (_macro := _extract_macro(tex_source, "github")) else "",
        portfolio=_extract_macro(tex_source, "portfolio"),
        codechef=_extract_macro(tex_source, "codechef"),
    )

    # Split sections
    sec_pattern = re.compile(r"\\section\{([^}]+)\}")
    matches = list(sec_pattern.finditer(tex_source))
    sections: dict[str, str] = {}
    for idx, m in enumerate(matches):
        sec_name = m.group(1).strip().lower()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(tex_source)
        sections[sec_name] = tex_source[start:end]

    # Summary
    summary = ""
    for k, body in sections.items():
        if "summary" in k:
            clean = re.sub(r"\\small\{|\}|\\end\{document\}|%.*", "", body)
            summary = _clean_latex_inline(clean)
            break

    # Education
    education: list[EducationEntry] = []
    for k, body in sections.items():
        if "education" in k:
            for m in re.finditer(r"\\resumeSubheading\b", body):
                args, _ = _extract_brace_args(body, m.end(), 4)
                if len(args) >= 3:
                    deg_inst = _clean_latex_inline(args[0])
                    parts = [p.strip() for p in deg_inst.split("-", 1)]
                    degree = parts[0] if parts else deg_inst
                    institution = parts[1] if len(parts) > 1 else ""
                    dates = _clean_latex_inline(args[1])
                    course_raw = _clean_latex_inline(args[2])
                    course_clean = re.sub(r"^Relevant\s+(Coursework|Subjects):\s*", "", course_raw, flags=re.I)
                    courses = [c.strip() for c in course_clean.split(",") if c.strip()]
                    gpa = _clean_latex_inline(args[3]) if len(args) > 3 else ""
                    education.append(
                        EducationEntry(
                            degree=degree,
                            institution=institution,
                            graduation_date=dates,
                            gpa=gpa,
                            relevant_courses=courses,
                        )
                    )
            break

    # Projects
    projects: list[ProjectEntry] = []
    for k, body in sections.items():
        if "project" in k:
            proj_matches = list(re.finditer(r"\\resumeProject\b", body))
            for idx, pm in enumerate(proj_matches):
                args, after = _extract_brace_args(body, pm.end(), 3)
                block_end = proj_matches[idx + 1].start() if idx + 1 < len(proj_matches) else len(body)
                block = body[after:block_end]
                title = _clean_latex_inline(args[0]) if args else "Project"
                tech_raw = _clean_latex_inline(args[1]) if len(args) > 1 else ""
                tech_clean = re.sub(r"^Tools/Technologies:\s*", "", tech_raw, flags=re.I)
                techs = [t.strip() for t in tech_clean.split(",") if t.strip()]
                bullets = [
                    _clean_latex_inline(it.group(1))
                    for it in re.finditer(r"\\item\s+([^\n]+(?:\n(?!\s*\\item|\s*\\resumeItemListEnd)[^\n]+)*)", block)
                    if _clean_latex_inline(it.group(1))
                ]
                projects.append(
                    ProjectEntry(
                        name=title,
                        technologies=techs,
                        bullets=bullets,
                    )
                )
            break

    # Technical Skills
    skills: list[str] = []
    for k, body in sections.items():
        if "skill" in k:
            # Extract lines after \textbf{...} blocks
            cleaned = re.sub(r"\\begin\{[^}]+\}(?:\[[^\]]*\])?|\\end\{[^}]+\}|\\small\{|\\item\{|\}|\\\\", "\n", body)
            for ln in cleaned.splitlines():
                ln_clean = _clean_latex_inline(re.sub(r"\\textbf\{[^}]*\}", "", ln))
                if ln_clean:
                    for item in ln_clean.split(","):
                        tok = item.strip()
                        if tok and tok not in skills:
                            skills.append(tok)
            break

    # Certifications
    certifications: list[CertificationEntry] = []
    for k, body in sections.items():
        if "certification" in k:
            for m in re.finditer(r"\\resumeSubheading\b", body):
                args, _ = _extract_brace_args(body, m.end(), 4)
                if args:
                    certifications.append(
                        CertificationEntry(
                            name=_clean_latex_inline(args[0]),
                            date=_clean_latex_inline(args[1]) if len(args) > 1 else "",
                            issuer=_clean_latex_inline(args[2]) if len(args) > 2 else "",
                        )
                    )
            break

    # Achievements
    achievements: list[str] = []
    for k, body in sections.items():
        if "achievement" in k:
            for m in re.finditer(r"\\resumeSubheading\b", body):
                args, _ = _extract_brace_args(body, m.end(), 4)
                if args:
                    title = _clean_latex_inline(args[0])
                    dt = _clean_latex_inline(args[1]) if len(args) > 1 else ""
                    desc = _clean_latex_inline(args[2]) if len(args) > 2 else ""
                    entry = f"{title} ({dt}) — {desc}" if desc else title
                    achievements.append(entry)
            break

    # Areas of Interest / Additional Info
    interests: list[str] = []
    for k, body in sections.items():
        if "additional" in k or "interest" in k:
            cleaned = re.sub(r"\\textbf\{[^}]*\}|\\begin\{[^}]+\}(?:\[[^\]]*\])?|\\end\{[^}]+\}|\\small\{|\\item\{|\}|\\\\|%.*", "", body)
            for tok in _clean_latex_inline(cleaned).split(","):
                t = tok.strip()
                if t:
                    interests.append(t)
            break

    return MasterProfileData(
        contact=contact,
        summary=summary,
        experience=[],
        projects=projects,
        skills=skills,
        education=education,
        certifications=certifications,
        achievements=achievements,
        areas_of_interest=interests,
        latex_template=tex_source,
    )


def _extract_preamble(custom_template: str) -> str:
    """Keep custom LaTeX preamble up to Personal Information / begin{document}."""
    if not custom_template or "\\documentclass" not in custom_template:
        return DEFAULT_LATEX_TEMPLATE
    for marker in (r"%-----------", r"\newcommand{\name}", r"\begin{document}"):
        idx = custom_template.find(marker)
        if idx > 100 and marker != r"%-----------":
            return custom_template[:idx].rstrip() + "\n"
        if marker == r"%-----------":
            # Look specifically for Personal Information comment block
            pi = custom_template.find("% Personal Information")
            if pi > 100:
                dash = custom_template.rfind("%---", 0, pi)
                return custom_template[: dash if dash > 0 else pi].rstrip() + "\n"
    return DEFAULT_LATEX_TEMPLATE


def _group_skills_for_latex(skills: list[str]) -> list[tuple[str, list[str]]]:
    """Organize flat skill list into ATS-friendly technical categories without dropping any verified skill."""
    buckets: dict[str, list[str]] = {
        "Programming Languages": [],
        "Backend & Frameworks": [],
        "Frontend Development": [],
        "Databases": [],
        "AI & Machine Learning": [],
        "Core Computer Science": [],
        "Tools & Practices": [],
    }
    lang_kw = {"java", "python", "c", "c++", "javascript", "typescript", "sql", "go", "rust"}
    backend_kw = {"spring boot", "spring mvc", "django", "fastapi", "flask", "node.js", "express", "rest apis", "microservices"}
    fe_kw = {"html", "css", "bootstrap", "react", "next.js", "tailwind", "angular"}
    db_kw = {"mysql", "postgresql", "mongodb", "sqlite", "database design", "crud operations", "redis"}
    ai_kw = {"nlp", "machine learning", "text classification", "rag", "rag fundamentals", "pandas", "scikit-learn", "pytorch", "tensorflow", "llm"}
    cs_kw = {"data structures", "algorithms", "object-oriented programming", "oop", "dbms", "operating systems", "computer networks"}

    for raw in skills:
        s = raw.strip()
        if not s:
            continue
        sl = s.lower()
        if sl in lang_kw:
            buckets["Programming Languages"].append(s)
        elif sl in backend_kw or "spring" in sl or "api" in sl:
            buckets["Backend & Frameworks"].append(s)
        elif sl in fe_kw:
            buckets["Frontend Development"].append(s)
        elif sl in db_kw or "sql" in sl:
            buckets["Databases"].append(s)
        elif sl in ai_kw or "learning" in sl or "nlp" in sl or "rag" in sl:
            buckets["AI & Machine Learning"].append(s)
        elif sl in cs_kw or "structures" in sl:
            buckets["Core Computer Science"].append(s)
        else:
            buckets["Tools & Practices"].append(s)

    return [(cat, vals) for cat, vals in buckets.items() if vals]


def _order_projects(projects: list[ProjectEntry], project_order: Optional[list[str]] = None) -> list[ProjectEntry]:
    """Order candidate projects according to JD-inclined priority list."""
    if not project_order:
        return projects
    rank = {name.strip().lower(): i for i, name in enumerate(project_order) if name}
    return sorted(projects, key=lambda p: rank.get(p.name.strip().lower(), len(rank) + 1))


def render_tailored_latex(
    data: MasterProfileData,
    output_path: Optional[str] = None,
    custom_summary: Optional[str] = None,
    tailored_bullets: Optional[dict[str, list[str]]] = None,
    tailored_project_bullets: Optional[dict[str, list[str]]] = None,
    emphasized_skills: Optional[list[str]] = None,
    tailored_interests: Optional[list[str]] = None,
    project_order: Optional[list[str]] = None,
    custom_template: Optional[str] = None,
) -> tuple[str, str]:
    """Render a tailored, compilable LaTeX resume preserving the user's exact format."""
    preamble = _extract_preamble(custom_template or getattr(data, "latex_template", "") or "")
    c = data.contact

    lines: list[str] = [
        preamble,
        "%-------------------------------------------",
        "% Personal Information",
        "%-------------------------------------------",
        "",
        rf"\newcommand{{\name}}{{{escape_latex(c.full_name or 'Candidate Name')}}}",
        rf"\newcommand{{\address}}{{{escape_latex(c.location or 'India')}}}",
        rf"\newcommand{{\phone}}{{{escape_latex(c.phone or '')}}}",
        rf"\newcommand{{\emaila}}{{{escape_latex(c.email or '')}}}",
        rf"\newcommand{{\linkedin}}{{{c.linkedin or 'https://linkedin.com'}}}",
        rf"\newcommand{{\github}}{{{c.github or 'https://github.com'}}}",
        rf"\newcommand{{\portfolio}}{{{c.portfolio or ''}}}",
        rf"\newcommand{{\codechef}}{{{getattr(c, 'codechef', '') or ''}}}",
        "",
        r"%-------------------------------------------",
        r"%%%%%% CV STARTS HERE %%%%%%%%%%%%%%%%%%%%%%",
        r"%-------------------------------------------",
        "",
        r"\begin{document}",
        "",
        r"\fontfamily{cmr}\selectfont",
        "",
        r"%----------HEADING-----------------",
        r"\begin{center}",
        r"    {\Huge \textbf{\name}} \\",
        r"    \vspace{2pt}",
        r"    \small \address \\",
        r"    \vspace{2pt}",
    ]

    link_parts: list[str] = []
    if c.phone:
        link_parts.append(r"\faPhone\ \phone")
    if c.email:
        link_parts.append(r"\href{mailto:\emaila}{\faEnvelope\ \emaila}")
    if c.linkedin:
        link_parts.append(r"\href{\linkedin}{\faLinkedin\ LinkedIn}")
    if c.github:
        link_parts.append(r"\href{\github}{\faGithub\ GitHub}")
    if c.portfolio:
        link_parts.append(r"\href{\portfolio}{\faGlobe\ Portfolio}")
    if getattr(c, "codechef", ""):
        link_parts.append(r"\href{\codechef}{\faCode\ CodeChef}")
    if link_parts:
        lines.append("    " + r" \,|\, ".join(link_parts))
    lines.append(r"\end{center}")
    lines.append("")

    # Summary
    summary_text = (custom_summary or data.summary or "").strip()
    if summary_text:
        lines.extend([
            r"%-----------SUMMARY-----------",
            r"\section{Professional Summary}",
            r"\small{",
            escape_latex(summary_text),
            r"}",
            "",
        ])

    # Education
    if data.education:
        lines.extend([
            r"%-----------EDUCATION-----------",
            r"\section{Education}",
            r"\resumeSubHeadingListStart",
            "",
        ])
        for edu in data.education:
            heading = f"{edu.degree} -- {edu.institution}" if edu.institution else edu.degree
            courses = ", ".join(edu.relevant_courses) if edu.relevant_courses else ""
            subline = f"Relevant Coursework: {courses}" if courses else (edu.location or "")
            lines.extend([
                r"\resumeSubheading",
                f"    {{{escape_latex(heading)}}}",
                f"    {{{escape_latex(edu.graduation_date)}}}",
                f"    {{{escape_latex(subline)}}}",
                f"    {{{escape_latex(edu.gpa)}}}",
                "",
            ])
        lines.extend([r"\resumeSubHeadingListEnd", ""])

    # Work Experience (rendered when non-empty)
    if data.experience:
        lines.extend([
            r"%-----------EXPERIENCE-----------",
            r"\section{Experience}",
            r"\resumeSubHeadingListStart",
            "",
        ])
        for exp in data.experience:
            dates = f"{exp.start_date} -- {'Present' if exp.is_current else exp.end_date}".strip(" -")
            lines.extend([
                r"\resumeSubheading",
                f"    {{{escape_latex(exp.title)}}}",
                f"    {{{escape_latex(dates)}}}",
                f"    {{{escape_latex(exp.company)}}}",
                f"    {{{escape_latex(exp.location)}}}",
                r"\resumeItemListStart",
            ])
            bullets = (tailored_bullets or {}).get(f"{exp.company}_{exp.title}", exp.bullets)
            for b in bullets:
                lines.append(f"    \\item {escape_latex(b)}")
            lines.extend([r"\resumeItemListEnd", ""])
        lines.extend([r"\resumeSubHeadingListEnd", ""])

    # Projects
    if data.projects:
        lines.extend([
            r"%-----------PROJECTS-----------",
            r"\section{Projects}",
            r"\resumeSubHeadingListStart",
            "",
        ])
        for idx, proj in enumerate(_order_projects(data.projects, project_order), start=1):
            tech_str = f"Tools/Technologies: {', '.join(proj.technologies)}" if proj.technologies else escape_latex(proj.description)
            lines.extend([
                f"%-----------PROJECT {idx}-----------",
                r"\resumeProject",
                f"    {{{escape_latex(proj.name)}}}",
                f"    {{{escape_latex(tech_str)}}}",
                f"    {{{escape_latex(proj.url)}}}",
                r"\resumeItemListStart",
                "",
            ])
            proj_bullets = (tailored_project_bullets or {}).get(proj.name) or proj.bullets or ([proj.description] if proj.description else [])
            for b in proj_bullets:
                lines.append(f"    \\item {escape_latex(b)}")
                lines.append("")
            lines.extend([r"\resumeItemListEnd", ""])
        lines.extend([r"\resumeSubHeadingListEnd", ""])

    # Technical Skills
    skill_list = emphasized_skills or data.skills
    if skill_list:
        grouped = _group_skills_for_latex(skill_list)
        lines.extend([
            r"%-----------TECHNICAL SKILLS-----------",
            r"\section{Technical Skills}",
            r"\begin{itemize}[leftmargin=0.05in, label={}]",
            r"\small{\item{",
            "",
        ])
        for idx, (cat, vals) in enumerate(grouped):
            suffix = r" \\" if idx < len(grouped) - 1 else ""
            lines.append(rf"\textbf{{{escape_latex(cat)}:}}")
            lines.append(f"{escape_latex(', '.join(vals))}{suffix}")
            lines.append("")
        lines.extend([
            r"}}",
            r"\end{itemize}",
            "",
        ])

    # Certifications
    if data.certifications:
        lines.extend([
            r"%-----------CERTIFICATIONS-----------",
            r"\section{Certifications}",
            r"\resumeSubHeadingListStart",
            "",
        ])
        for cert in data.certifications:
            lines.extend([
                r"\resumeSubheading",
                f"    {{{escape_latex(cert.name)}}}",
                f"    {{{escape_latex(cert.date)}}}",
                f"    {{{escape_latex(cert.issuer)}}}",
                f"    {{{escape_latex(cert.credential_id)}}}",
                "",
            ])
        lines.extend([r"\resumeSubHeadingListEnd", ""])

    # Achievements
    if data.achievements:
        lines.extend([
            r"%-----------ACHIEVEMENTS-----------",
            r"\section{Achievements \& Activities}",
            r"\resumeSubHeadingListStart",
            "",
        ])
        for ach in data.achievements:
            if "—" in ach or " -- " in ach:
                sep = "—" if "—" in ach else " -- "
                head, tail = [p.strip() for p in ach.split(sep, 1)]
                lines.extend([
                    r"\resumeSubheading",
                    f"    {{{escape_latex(head)}}}",
                    "    {}",
                    f"    {{{escape_latex(tail)}}}",
                    "    {}",
                    "",
                ])
            else:
                lines.extend([
                    r"\resumeSubheading",
                    f"    {{{escape_latex(ach)}}}",
                    "    {}",
                    "    {}",
                    "    {}",
                    "",
                ])
        lines.extend([r"\resumeSubHeadingListEnd", ""])

    # Areas of Interest
    interests = tailored_interests or getattr(data, "areas_of_interest", [])
    if interests:
        lines.extend([
            r"%-----------ADDITIONAL INFORMATION-----------",
            r"\section{Additional Information}",
            r"\begin{itemize}[leftmargin=0.05in, label={}]",
            r"\small{\item{",
            "",
            r"\textbf{Areas of Interest:}",
            escape_latex(", ".join(interests)),
            "",
            r"}}",
            r"\end{itemize}",
            "",
        ])

    lines.extend([
        r"%-------------------------------------------",
        r"\end{document}",
    ])

    rendered = "\n".join(lines)
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        return output_path, rendered
    return "", rendered


def try_compile_latex_to_pdf(tex_path: str, pdf_output_path: str) -> bool:
    """Attempt compiling `.tex` to `.pdf` using pdflatex/xelatex/tectonic if installed."""
    compiler = shutil.which("pdflatex") or shutil.which("xelatex") or shutil.which("tectonic")
    if not compiler or not os.path.exists(tex_path):
        return False

    out_dir = os.path.dirname(os.path.abspath(pdf_output_path))
    os.makedirs(out_dir, exist_ok=True)
    try:
        if "tectonic" in os.path.basename(compiler).lower():
            cmd = [compiler, "-o", out_dir, tex_path]
        else:
            cmd = [compiler, "-interaction=nonstopmode", f"-output-directory={out_dir}", tex_path]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        compiled_pdf = os.path.splitext(tex_path)[0] + ".pdf"
        if proc.returncode == 0 and os.path.exists(compiled_pdf):
            if os.path.abspath(compiled_pdf) != os.path.abspath(pdf_output_path):
                shutil.move(compiled_pdf, pdf_output_path)
            return True
    except Exception:
        pass
    return False


async def render_latex_styled_pdf(
    data: MasterProfileData,
    pdf_output_path: str,
    custom_summary: Optional[str] = None,
    tailored_bullets: Optional[dict[str, list[str]]] = None,
    tailored_project_bullets: Optional[dict[str, list[str]]] = None,
    emphasized_skills: Optional[list[str]] = None,
    tailored_interests: Optional[list[str]] = None,
    project_order: Optional[list[str]] = None,
) -> bool:
    """Render an A4 selectable-text PDF matching the exact LaTeX layout via headless Chromium."""
    import html as _html

    try:
        from playwright.async_api import async_playwright
    except Exception:
        return False

    def esc(val: str) -> str:
        return _html.escape(val or "")

    c = data.contact
    links = []
    if c.phone:
        links.append(esc(c.phone))
    if c.email:
        links.append(f'<a href="mailto:{esc(c.email)}">{esc(c.email)}</a>')
    if c.linkedin:
        links.append(f'<a href="{esc(c.linkedin)}">LinkedIn</a>')
    if c.github:
        links.append(f'<a href="{esc(c.github)}">GitHub</a>')
    if c.portfolio:
        links.append(f'<a href="{esc(c.portfolio)}">Portfolio</a>')
    if getattr(c, "codechef", ""):
        links.append(f'<a href="{esc(c.codechef)}">CodeChef</a>')

    summary_text = (custom_summary or data.summary or "").strip()
    edu_html = ""
    if data.education:
        rows = []
        for edu in data.education:
            heading = f"{edu.degree} -- {edu.institution}" if edu.institution else edu.degree
            subline = f"Relevant Coursework: {', '.join(edu.relevant_courses)}" if edu.relevant_courses else edu.location
            rows.append(
                f'<div class="subrow"><div class="subtop"><b>{esc(heading)}</b><i>{esc(edu.gpa)}</i></div>'
                f'<div class="subbot"><i>{esc(subline)}</i><span>{esc(edu.graduation_date)}</span></div></div>'
            )
        edu_html = f'<section><h2>Education</h2>{"".join(rows)}</section>'

    exp_html = ""
    if data.experience:
        items = []
        for exp in data.experience:
            dates = f"{exp.start_date} -- {'Present' if exp.is_current else exp.end_date}".strip(" -")
            bullets = (tailored_bullets or {}).get(f"{exp.company}_{exp.title}", exp.bullets)
            lis = "".join(f"<li>{esc(b)}</li>" for b in bullets)
            items.append(
                f'<div class="subrow"><div class="subtop"><b>{esc(exp.title)}</b><i>{esc(exp.location)}</i></div>'
                f'<div class="subbot"><i>{esc(exp.company)}</i><span>{esc(dates)}</span></div>'
                f'<ul>{lis}</ul></div>'
            )
        exp_html = f'<section><h2>Experience</h2>{"".join(items)}</section>'

    proj_html = ""
    if data.projects:
        items = []
        for proj in _order_projects(data.projects, project_order):
            tech = f"Tools/Technologies: {', '.join(proj.technologies)}" if proj.technologies else proj.description
            bullets = (tailored_project_bullets or {}).get(proj.name) or proj.bullets or ([proj.description] if proj.description else [])
            lis = "".join(f"<li>{esc(b)}</li>" for b in bullets)
            items.append(
                f'<div class="subrow"><div class="subtop"><b>{esc(proj.name)}</b><i>{esc(proj.url)}</i></div>'
                f'<div class="tech">{esc(tech)}</div><ul>{lis}</ul></div>'
            )
        proj_html = f'<section><h2>Projects</h2>{"".join(items)}</section>'

    skills_html = ""
    skill_list = emphasized_skills or data.skills
    if skill_list:
        grouped = _group_skills_for_latex(skill_list)
        s_lines = "".join(
            f'<div class="skillline"><b>{esc(cat)}:</b> {esc(", ".join(vals))}</div>'
            for cat, vals in grouped
        )
        skills_html = f'<section><h2>Technical Skills</h2>{s_lines}</section>'

    cert_html = ""
    if data.certifications:
        rows = "".join(
            f'<div class="subrow"><div class="subtop"><b>{esc(cert.name)}</b><i>{esc(cert.credential_id)}</i></div>'
            f'<div class="subbot"><i>{esc(cert.issuer)}</i><span>{esc(cert.date)}</span></div></div>'
            for cert in data.certifications
        )
        cert_html = f'<section><h2>Certifications</h2>{rows}</section>'

    ach_html = ""
    if data.achievements:
        rows = []
        for ach in data.achievements:
            if "—" in ach or " -- " in ach:
                sep = "—" if "—" in ach else " -- "
                h, t = [p.strip() for p in ach.split(sep, 1)]
                rows.append(f'<div class="subrow"><div class="subtop"><b>{esc(h)}</b><span></span></div><div class="tech"><i>{esc(t)}</i></div></div>')
            else:
                rows.append(f'<div class="subrow"><div class="subtop"><b>{esc(ach)}</b></div></div>')
        ach_html = f'<section><h2>Achievements &amp; Activities</h2>{"".join(rows)}</section>'

    interests = tailored_interests or getattr(data, "areas_of_interest", [])
    add_html = ""
    if interests:
        add_html = f'<section><h2>Additional Information</h2><div class="skillline"><b>Areas of Interest:</b> {esc(", ".join(interests))}</div></section>'

    doc_html = f"""<!doctype html>
<html>
<head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 0.8cm 1.2cm 1cm 1.4cm; }}
body {{ font-family: "Computer Modern Serif", "Latin Modern Roman", "Times New Roman", Georgia, serif; font-size: 9.8pt; line-height: 1.32; color: #111; margin: 0; }}
.header {{ text-align: center; margin-bottom: 6px; }}
.header h1 {{ font-size: 20pt; margin: 0 0 2px 0; font-weight: 700; letter-spacing: 0.3px; }}
.header .addr {{ font-size: 9pt; margin-bottom: 2px; }}
.header .links {{ font-size: 8.8pt; }}
.header a {{ color: #111; text-decoration: none; }}
section {{ margin-top: 7px; }}
h2 {{ font-size: 11pt; font-variant: small-caps; text-transform: uppercase; letter-spacing: 0.5px; font-weight: 600; border-bottom: 0.9px solid #000; margin: 0 0 4px 0; padding-bottom: 1px; }}
.summary {{ text-align: justify; margin: 2px 0; }}
.subrow {{ margin-bottom: 4px; }}
.subtop, .subbot {{ display: flex; justify-content: space-between; align-items: baseline; }}
.subbot, .tech {{ font-size: 8.6pt; color: #222; }}
ul {{ margin: 2px 0 3px 16px; padding: 0; text-align: justify; }}
li {{ margin-bottom: 1.5px; }}
.skillline {{ margin-bottom: 2px; font-size: 9.2pt; }}
</style></head>
<body>
  <div class="header">
    <h1>{esc(c.full_name or "Candidate Name")}</h1>
    <div class="addr">{esc(c.location)}</div>
    <div class="links">{" &nbsp;|&nbsp; ".join(links)}</div>
  </div>
  {f'<section><h2>Professional Summary</h2><p class="summary">{esc(summary_text)}</p></section>' if summary_text else ''}
  {edu_html}
  {exp_html}
  {proj_html}
  {skills_html}
  {cert_html}
  {ach_html}
  {add_html}
</body>
</html>"""

    os.makedirs(os.path.dirname(os.path.abspath(pdf_output_path)), exist_ok=True)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(doc_html, wait_until="load")
            await page.pdf(path=pdf_output_path, format="A4", print_background=True)
            await browser.close()
        return os.path.exists(pdf_output_path)
    except Exception:
        return False


SAMPLE_STARTER_LATEX = r"""%-------------------------
% Resume in Latex
%------------------------

\documentclass[a4paper,11pt]{article}

\usepackage{latexsym}
\usepackage{xcolor}
\usepackage{float}
\usepackage{ragged2e}
\usepackage[empty]{fullpage}
\usepackage{wrapfig}
\usepackage{tabularx}
\usepackage{titlesec}
\usepackage{geometry}
\usepackage{marvosym}
\usepackage{verbatim}
\usepackage{enumitem}
\usepackage[hidelinks]{hyperref}
\usepackage{fancyhdr}
\usepackage{fontawesome5}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{cfr-lm}
\usepackage[T1]{fontenc}

\setlength{\multicolsep}{0pt}

\pagestyle{fancy}
\fancyhf{}
\fancyfoot{}
\renewcommand{\headrulewidth}{0pt}
\renewcommand{\footrulewidth}{0pt}

\geometry{
    left=1.4cm,
    top=0.8cm,
    right=1.2cm,
    bottom=1cm
}

\usepackage[most]{tcolorbox}

\tcbset{
    frame code={},
    center title,
    left=0pt,
    right=0pt,
    top=0pt,
    bottom=0pt,
    colback=gray!20,
    colframe=white,
    width=\dimexpr\textwidth\relax,
    enlarge left by=-2mm,
    boxsep=4pt,
    arc=0pt,
    outer arc=0pt,
}

\urlstyle{same}
\raggedright
\setlength{\tabcolsep}{0in}

\titleformat{\section}{
  \vspace{-4pt}\scshape\raggedright\large
}{}{0em}{}[\color{black}\titlerule \vspace{-7pt}]

\newcommand{\resumeItem}[2]{
  \item{
    \textbf{#1}{\hspace{0.5mm}#2 \vspace{-0.5mm}}
  }
}

\newcommand{\resumeSubheading}[4]{
\vspace{0.5mm}\item
    \begin{tabular*}{0.98\textwidth}[t]{l@{\extracolsep{\fill}}r}
        \textbf{#1} & \textit{\footnotesize{#4}} \\
        \textit{\footnotesize{#3}} & \footnotesize{#2}\\
    \end{tabular*}
    \vspace{-2.4mm}
}

\newcommand{\resumeProject}[3]{
\vspace{0.5mm}\item
    \begin{tabular*}{0.98\textwidth}[t]{l@{\extracolsep{\fill}}r}
        \textbf{#1} & \textit{\footnotesize{#3}} \\
        \multicolumn{2}{p{0.98\textwidth}}{\footnotesize{#2}}
    \end{tabular*}
    \vspace{-2.4mm}
}

\newcommand{\resumeItemListStart}{
\begin{justify}
\begin{itemize}[
    leftmargin=3ex,
    rightmargin=2ex,
    noitemsep,
    labelsep=1.2mm,
    itemsep=0mm
]
\small
}

\newcommand{\resumeItemListEnd}{
\end{itemize}
\end{justify}
\vspace{-2mm}
}

\newcommand{\resumeSubHeadingListStart}{
\begin{itemize}[leftmargin=*,labelsep=0mm]
}

\newcommand{\resumeSubHeadingListEnd}{
\end{itemize}
\vspace{2mm}
}

\newcommand{\name}{Manda Harshitha}
\newcommand{\address}{Hyderabad, Telangana, India}
\newcommand{\phone}{+91 7989508635}
\newcommand{\emaila}{harshithagoud32@gmail.com}
\newcommand{\linkedin}{https://www.linkedin.com/in/harshitha-manda-88a7362a1/}
\newcommand{\github}{https://github.com/Harshitha-m-2005}
\newcommand{\portfolio}{https://harshithamandaportfilo.netlify.app/}
\newcommand{\codechef}{https://www.codechef.com/users/mharshitha_210}

\begin{document}

\fontfamily{cmr}\selectfont

\begin{center}
    {\Huge \textbf{\name}} \\
    \vspace{2pt}
    \small \address \\
    \vspace{2pt}
    \faPhone\ \phone \,|\, 
    \href{mailto:\emaila}{\faEnvelope\ \emaila} \,|\, 
    \href{\linkedin}{\faLinkedin\ LinkedIn} \,|\, 
    \href{\github}{\faGithub\ GitHub} \,|\, 
    \href{\portfolio}{\faGlobe\ Portfolio} \,|\, 
    \href{\codechef}{\faCode\ CodeChef}
\end{center}

\section{Professional Summary}

\small{
Final-year BCA student with a strong foundation in Java, Python, data structures, databases, and software development. Hands-on experience building web applications and machine learning solutions using Spring Boot, Django, JavaScript, SQL, and NLP techniques. Familiar with REST APIs, object-oriented programming, database management, cloud computing fundamentals, and AI/ML concepts. Strong problem-solving and analytical skills with an interest in cloud-native development, enterprise software, AI engineering, and developer productivity. Eager to learn, collaborate in Agile teams, and contribute to scalable software solutions.
}

\section{Education}

\resumeSubHeadingListStart

\resumeSubheading
    {Bachelor of Computer Applications (BCA) -- KL University}
    {2023 -- Present}
    {Relevant Coursework: Data Structures \& Algorithms, Object-Oriented Programming, Database Management, AI \& Machine Learning, Web Development, Software Engineering}
    {}

\resumeSubheading
    {Intermediate Class 11 \& 12 -- Sri Chaithanya}
    {2020 -- 2022}
    {Relevant Subjects: Biology, Physics, Chemistry}
    {First Class}

\resumeSubheading
    {CBSE Class 10th -- Gorkey Public School}
    {2019 -- 2020}
    {Relevant Subjects: Mathematics, Science, Social Studies}
    {First Class}

\resumeSubHeadingListEnd

\section{Projects}

\resumeSubHeadingListStart

\resumeProject
    {Spring Boot Employee Management System}
    {Tools/Technologies: Java, Spring Boot, REST APIs, MySQL, Maven}
    {}

\resumeItemListStart

    \item Developed a modular employee management application using Java and Spring Boot following RESTful service architecture.

    \item Implemented employee, department, and role management with CRUD operations and MySQL persistence.

    \item Designed controller, service, and repository layers following standard backend development practices.

    \item Applied validation, exception handling, and API-based communication to improve application reliability.

\resumeItemListEnd

\resumeProject
    {Sarcasm Detection -- NLP Machine Learning Project}
    {Tools/Technologies: Python, NLP, Machine Learning, Pandas, Scikit-learn}
    {}

\resumeItemListStart

    \item Built a machine learning model to classify text as sarcastic or non-sarcastic using natural language processing techniques.

    \item Performed text preprocessing, feature extraction, model training, and evaluation using classification metrics.

    \item Experimented with different NLP techniques to improve model performance and understand linguistic patterns.

\resumeItemListEnd

\resumeSubHeadingListEnd

\section{Technical Skills}

\begin{itemize}[leftmargin=0.05in, label={}]
\small{\item{

\textbf{Programming Languages:}
Java, Python, C, JavaScript, SQL \\

\textbf{Backend Development:}
Spring Boot, Spring MVC, Django, REST APIs, Microservices \\

\textbf{Frontend Development:}
HTML, CSS, JavaScript, Bootstrap \\

\textbf{Databases:}
MySQL, SQL, Database Design, CRUD Operations \\

\textbf{AI \& Machine Learning:}
NLP, Machine Learning, Text Classification, RAG Fundamentals \\

\textbf{Core Computer Science:}
Data Structures \& Algorithms, Object-Oriented Programming, DBMS, Operating Systems, Computer Networks \\

\textbf{Tools \& Practices:}
Git, GitHub, Agile/Scrum, Cloud-Native Concepts, CI/CD Fundamentals

}}
\end{itemize}

\section{Certifications}

\resumeSubHeadingListStart

\resumeSubheading
    {Oracle Cloud Infrastructure Foundations Associate}
    {2025}
    {Foundational knowledge of cloud computing, OCI services, networking, and storage}
    {}

\resumeSubheading
    {Salesforce Associate Certification}
    {2024}
    {Foundational knowledge of Salesforce platform, CRM concepts, and AI-enabled business applications}
    {}

\resumeSubHeadingListEnd

\section{Achievements \& Activities}

\resumeSubHeadingListStart

\resumeSubheading
    {DEV-REL Hackathon -- Microsoft Hyderabad}
    {2024}
    {Participated in a machine learning hackathon focused on building a Retrieval-Augmented Generation (RAG) system for Large Language Models}
    {}

\resumeSubHeadingListEnd

\section{Additional Information}

\begin{itemize}[leftmargin=0.05in, label={}]
\small{\item{

\textbf{Areas of Interest:}
Cloud-Native Development, AI Engineering, Enterprise Software, Microservices, Developer Experience, Employee Experience

}}
\end{itemize}

\end{document}"""

