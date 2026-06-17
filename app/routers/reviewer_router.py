from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from app.database import get_db
from app.models import (
    User, Puppet, PuppetStatus, Adjustment, Workbench
)
from app.schemas import (
    ReviewRequest, AdjustmentResponse, SealObservationRequest
)
from app.auth import require_reviewer, require_admin_or_reviewer, get_current_user

router = APIRouter(prefix="/api/reviewer", tags=["复核员管理"])


@router.get("/adjustments/pending", response_model=List[AdjustmentResponse])
def list_pending_adjustments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    return db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.PENDING_REVIEW
    ).order_by(Adjustment.submit_review_time.asc()).all()


@router.get("/adjustments/my-reviewed", response_model=List[AdjustmentResponse])
def list_my_reviewed(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    return db.query(Adjustment).filter(
        Adjustment.reviewer_id == current_user.id
    ).order_by(Adjustment.review_time.desc()).all()


@router.get("/adjustments/{adj_id}", response_model=AdjustmentResponse)
def get_adjustment(
    adj_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    return adj


@router.post("/adjustments/{adj_id}/review", response_model=AdjustmentResponse)
def review_adjustment(
    adj_id: int,
    data: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.status != PuppetStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，不是待试演状态"
        )

    adj.smoothness_score = data.smoothness_score
    adj.deviation_note = data.deviation_note
    adj.review_opinion = data.review_opinion
    adj.reviewer_id = current_user.id
    adj.review_time = datetime.utcnow()
    adj.is_passed = data.is_passed
    adj.updated_at = datetime.utcnow()

    puppet = adj.puppet
    if data.is_passed == 1:
        adj.status = PuppetStatus.PASSED
        puppet.current_status = PuppetStatus.PASSED
        puppet.last_passed_date = date.today()
        puppet.current_adjustment_id = None
    else:
        adj.status = PuppetStatus.RETURNING
        puppet.current_status = PuppetStatus.RETURNING
        if data.review_opinion:
            adj.return_action_note = (adj.return_action_note or "") + \
                f"\n【返调意见】{data.review_opinion}"

    db.commit()
    db.refresh(adj)
    return adj


@router.post("/adjustments/{adj_id}/seal-observation", response_model=AdjustmentResponse)
def seal_observation(
    adj_id: int,
    data: Optional[SealObservationRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_reviewer)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.status != PuppetStatus.PASSED:
        raise HTTPException(
            status_code=400,
            detail=f"只有已通过的调校单才能转为封存观察状态"
        )

    adj.status = PuppetStatus.SEALED_OBSERVATION
    adj.seal_time = datetime.utcnow()
    if data and data.review_opinion:
        adj.review_opinion = (adj.review_opinion or "") + \
            f"\n【封存观察备注】{data.review_opinion}"

    puppet = adj.puppet
    puppet.current_status = PuppetStatus.SEALED_OBSERVATION
    puppet.current_adjustment_id = None

    db.commit()
    db.refresh(adj)
    return adj


@router.get("/workbench-backlog")
def get_workbench_backlog(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    workbenches = db.query(Workbench).all()
    result = []
    for wb in workbenches:
        active_count = db.query(Adjustment).filter(
            Adjustment.workbench_id == wb.id,
            Adjustment.status.in_([
                PuppetStatus.ADJUSTING,
                PuppetStatus.RETURNING
            ])
        ).count()
        pending_count = db.query(Adjustment).filter(
            Adjustment.workbench_id == wb.id,
            Adjustment.status == PuppetStatus.PENDING_REVIEW
        ).count()
        result.append({
            "workbench_id": wb.id,
            "workbench_code": wb.code,
            "workbench_name": wb.name,
            "active_adjustment_count": active_count,
            "pending_review_count": pending_count,
            "total_backlog": active_count + pending_count
        })
    return sorted(result, key=lambda x: x["total_backlog"], reverse=True)


@router.get("/overdue-review")
def get_overdue_review(
    hours: int = Query(default=24, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer)
):
    threshold = datetime.utcnow() - timedelta(hours=hours)
    overdue = db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.PENDING_REVIEW,
        Adjustment.submit_review_time <= threshold
    ).order_by(Adjustment.submit_review_time.asc()).all()

    result = []
    for adj in overdue:
        wait_hours = (datetime.utcnow() - adj.submit_review_time).total_seconds() / 3600
        result.append({
            "adjustment_id": adj.id,
            "puppet_code": adj.puppet.code if adj.puppet else "",
            "puppet_name": adj.puppet.name if adj.puppet else "",
            "submit_time": adj.submit_review_time,
            "wait_hours": round(wait_hours, 1),
            "workbench_code": adj.workbench.code if adj.workbench else "",
            "adjuster_name": adj.adjuster.full_name if adj.adjuster else ""
        })
    return result
