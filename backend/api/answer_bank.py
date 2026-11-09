"""Answer Bank API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from models.settings import AnswerBank
from models.audit import AuditLog

router = APIRouter(prefix="/answer-bank", tags=["answer-bank"])


@router.get("")
async def list_answers(
    category: Optional[str] = None,
    approved_only: bool = False,
    session: Session = Depends(get_session),
):
    """List questions in Answer Bank."""
    query = select(AnswerBank)
    if category:
        query = query.where(AnswerBank.category == category)
    if approved_only:
        query = query.where(AnswerBank.approved == True)

    answers = session.exec(query.order_by(AnswerBank.id.desc())).all()
    return answers


@router.post("")
async def create_answer(body: dict, session: Session = Depends(get_session)):
    """Add a new question pattern and approved answer."""
    pattern = body.get("pattern")
    answer = body.get("answer")
    category = body.get("category", "general")
    approved = body.get("approved", True)

    if not pattern or not answer:
        raise HTTPException(status_code=400, detail="pattern and answer are required")

    entry = AnswerBank(
        pattern=pattern,
        answer=answer,
        category=category,
        approved=approved,
        times_used=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.add(AuditLog(
        action="answer_bank_created",
        entity_type="answer_bank",
        details=f"Added answer for pattern '{pattern}' (category: {category})",
        created_at=datetime.now(timezone.utc),
    ))
    session.commit()
    session.refresh(entry)
    return entry


@router.put("/{entry_id}")
async def update_answer(entry_id: int, body: dict, session: Session = Depends(get_session)):
    """Update or approve an answer."""
    entry = session.get(AnswerBank, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    if "answer" in body:
        entry.answer = body["answer"]
    if "pattern" in body:
        entry.pattern = body["pattern"]
    if "category" in body:
        entry.category = body["category"]
    if "approved" in body:
        entry.approved = bool(body["approved"])

    entry.updated_at = datetime.now(timezone.utc)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.delete("/{entry_id}")
async def delete_answer(entry_id: int, session: Session = Depends(get_session)):
    """Delete an answer entry."""
    entry = session.get(AnswerBank, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")

    session.delete(entry)
    session.commit()
    return {"deleted": entry_id}

