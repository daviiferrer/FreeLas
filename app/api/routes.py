import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import event_bus
from app.database import get_db
from app.models.project import Project, ProjectStatus

logger = logging.getLogger("freelaas.api")

router = APIRouter(prefix="/api")


@router.get("/projects")
async def list_projects(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).order_by(Project.scraped_at.desc()).limit(limit).offset(offset)

    if status:
        try:
            status_enum = ProjectStatus(status)
            query = query.where(Project.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    result = await db.execute(query)
    projects = [p.to_dict() for p in result.scalars().all()]

    return {"projects": projects, "count": len(projects)}


@router.get("/projects/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project.to_dict()


@router.get("/proposals")
async def list_proposals(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project)
        .where(Project.status == ProjectStatus.phase3_pass)
        .order_by(Project.scraped_at.desc())
        .limit(limit)
    )
    projects = [p.to_dict() for p in result.scalars().all()]
    return {"proposals": projects, "count": len(projects)}


@router.put("/proposals/{project_id}")
async def update_proposal(
    project_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).where(Project.project_id == project_id))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if "proposal_text" in body:
        project.proposal_text = body["proposal_text"]
    if "recommended_price" in body:
        project.recommended_price = body["recommended_price"]
    if "recommended_delivery_time" in body:
        project.recommended_delivery_time = body["recommended_delivery_time"]

    await db.commit()
    return project.to_dict()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    stats = {}
    for status in ProjectStatus:
        result = await db.execute(
            select(func.count(Project.project_id)).where(Project.status == status)
        )
        stats[status.value] = result.scalar() or 0

    total = await db.execute(select(func.count(Project.project_id)))
    stats["total"] = total.scalar() or 0

    return stats


@router.post("/pipeline/run")
async def trigger_pipeline():
    """Manually trigger a pipeline cycle."""
    from app.pipeline.orchestrator import PipelineOrchestrator
    orchestrator = PipelineOrchestrator()
    asyncio.create_task(orchestrator.run_full_cycle())
    return {"status": "started", "message": "Pipeline cycle triggered"}


@router.get("/events")
async def sse_events():
    """Server-Sent Events endpoint for real-time pipeline monitoring."""
    queue = event_bus.subscribe()

    async def event_stream():
        try:
            while True:
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"data: {data}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
