---
name: interview-prep-fresher
description: Prepare tailored technical and behavioral interview questions and company research briefs grounded in projects, coursework, and verified skills.
---

# Interview Prep Skill

## Purpose
Generate high-probability technical questions, behavioral prompts, talking points, and interviewer questions without fabricating past experience.

## Context Budget
- Load `build_compact_context(..., slice_type="interview")` (experience level, top skills, projects, achievements, certifications) + condensed JD (`extract_salient_jd`).

## Fresher Guidance
- When `experience_level == "fresher"`, anchor system & coding deep-dives around the candidate's listed academic/personal Projects, DBMS/OOP/DSA coursework, and Hackathons.
- Provide honest bridging strategies for missing stack items using adjacent verified tools.

