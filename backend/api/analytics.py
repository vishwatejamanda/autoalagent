"""Analytics, Reporting, and Backup/Export API endpoints."""

import csv
import io
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response, FileResponse
from sqlmodel import Session, select, func

from app.database import get_session
from app.config import get_settings
from models.job import Job, JobScore
from models.application import Application, Resume

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/funnel")
async def get_funnel_stats(session: Session = Depends(get_session)):
    """Application funnel metrics and overall conversion statistics."""
    total_jobs = session.exec(select(func.count(Job.id))).one()
    matched_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "matched")).one()
    review_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "review")).one()
    applied_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "applied")).one()
    interview_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "interview")).one()
    offer_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "offer")).one()
    rejected_jobs = session.exec(select(func.count(Job.id)).where(Job.status == "rejected")).one()

    return {
        "total_discovered": total_jobs or 0,
        "matched": matched_jobs or 0,
        "in_review": review_jobs or 0,
        "applied": applied_jobs or 0,
        "interviewing": interview_jobs or 0,
        "offers": offer_jobs or 0,
        "rejected": rejected_jobs or 0,
        "response_rate_percent": round((((interview_jobs or 0) + (offer_jobs or 0)) / max(applied_jobs or 1, 1)) * 100, 1),
    }


@router.get("/portals")
async def get_portal_distribution(session: Session = Depends(get_session)):
    """Application and discovery distribution across portals."""
    portals = ["linkedin", "naukri", "workday"]
    distribution = []

    for p in portals:
        discovered = session.exec(select(func.count(Job.id)).where(Job.source == p)).one() or 0
        applied = session.exec(select(func.count(Application.id)).where(Application.portal == p)).one() or 0
        distribution.append({
            "portal": p,
            "discovered": discovered,
            "applied": applied,
        })

    return distribution


@router.get("/export/csv")
async def export_tracker_csv(session: Session = Depends(get_session)):
    """Export all jobs and applications tracker to CSV."""
    jobs = session.exec(select(Job).order_by(Job.id.desc())).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Title", "Company", "Location", "Source",
        "Status", "URL", "Created At"
    ])

    for j in jobs:
        writer.writerow([
            j.id,
            j.title,
            j.company,
            j.location,
            j.source,
            j.status,
            j.url,
            j.created_at.isoformat() if j.created_at else "",
        ])

    csv_content = output.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications_tracker.csv"},
    )


@router.get("/backup")
async def backup_database():
    """Download current SQLite database file for offline backup."""
    settings = get_settings()
    db_path = settings.DATABASE_URL.replace("sqlite:///./", "./").replace("sqlite:///", "")
    db_abs = os.path.abspath(db_path)

    if not os.path.exists(db_abs):
        raise HTTPException(status_code=404, detail="Database file not found")

    return FileResponse(
        db_abs,
        media_type="application/x-sqlite3",
        filename="job_agent_backup.db",
    )


@router.post("/restore")
async def restore_database(file: UploadFile = File(...)):
    """Restore SQLite database from an uploaded backup file."""
    settings = get_settings()
    db_path = settings.DATABASE_URL.replace("sqlite:///./", "./").replace("sqlite:///", "")
    db_abs = os.path.abspath(db_path)

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded backup file is empty")

    # Safety: backup existing db before overwrite if it exists
    if os.path.exists(db_abs):
        shutil.copyfile(db_abs, f"{db_abs}.bak")

    with open(db_abs, "wb") as f:
        f.write(contents)

    return {"success": True, "message": "Database restored successfully from backup."}

