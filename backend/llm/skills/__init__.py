"""Context-efficient modular AI skills package.

Each skill constructs a compact, task-specific slice of the candidate's
MasterProfile, SearchProfile, and Application Defaults instead of sending the
entire profile/template on every LLM invocation.
"""

from llm.skills.context_builder import build_compact_context, extract_salient_jd
from llm.skills.resume_tailor_skill import (
    TailoredResumeOutput,
    skill_tailor_resume,
)
from llm.skills.interview_prep_skill import (
    InterviewQuestion,
    InterviewPrepResult,
    CompanyResearchResult,
    skill_prepare_interview,
    skill_company_research,
)
from llm.skills.job_match_skill import (
    LLMMatchResult,
    skill_score_job_match,
)
from llm.skills.form_answer_skill import (
    FormAnswerResult,
    skill_answer_form_question,
)

__all__ = [
    "build_compact_context",
    "extract_salient_jd",
    "TailoredResumeOutput",
    "skill_tailor_resume",
    "InterviewQuestion",
    "InterviewPrepResult",
    "CompanyResearchResult",
    "skill_prepare_interview",
    "skill_company_research",
    "LLMMatchResult",
    "skill_score_job_match",
    "FormAnswerResult",
    "skill_answer_form_question",
]

