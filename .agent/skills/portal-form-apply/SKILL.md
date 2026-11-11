---
name: portal-form-apply
description: Answer portal application form custom questions using deterministic Fresher / N/A defaults first, falling back to compact form AI context, and pause cleanly on login walls or CAPTCHAs.
---

# Portal Form & Application Skill

## Purpose
Keep automated and review-assisted applications reliable across LinkedIn, Naukri, and Workday while strictly respecting auth boundaries and anti-fabrication rules.

## Workflow
1. Resolve deterministic defaults first (`years_of_experience="0"`, `previous_company="N/A"`, `current_ctc="N/A"`, `notice_period="Immediate"` for freshers) and `AnswerBank` cached answers.
2. Only call `skill_answer_form_question` (`slice_type="form"`) for custom narrative questions.
3. Never bypass CAPTCHAs or OAuth walls (e.g., Naukri "Continue with Google" or Workday "Sign In"); capture screenshot, report `login_required` / `captcha_paused`, and direct the user to Settings -> Browser Login Helper.

