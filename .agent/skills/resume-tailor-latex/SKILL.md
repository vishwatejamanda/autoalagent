---
name: resume-tailor-latex
description: Tailor the candidate's LaTeX resume strictly from verified Master Profile facts without fabrications, using the compact tailor context slice.
---

# Resume Tailor (LaTeX + Anti-Fabrication) Skill

## Purpose
Produce job-tailored `.tex`, `.pdf`, and `.docx` resumes grounded 100% in verified facts from `MasterProfileData`.

## Context Budget
- Use `build_compact_context(..., slice_type="tailor")` instead of serializing full raw profile objects or redundant template code.
- Extract salient JD requirements (`<= 2600` chars) via `extract_salient_jd`.

## Strict Rules
1. Never invent employers, internships, dates, degrees, certifications, or skills.
2. For freshers (`experience == []`), tailor `tailored_project_bullets` keyed by exact project name rather than inventing work experience.
3. Preserve all LaTeX preamble commands (`\documentclass[a4paper,11pt]{article}`, `\resumeSubheading`, `\resumeProject`, `\resumeItemListStart`) and escape special characters (`& % $ # _ { } ~ ^`).
4. Report missing JD requirements exclusively in `missing_skills_gaps`.

