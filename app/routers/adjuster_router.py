from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import (
    User, Puppet, PuppetStatus, Adjustment, JointAdjustment, Workbench, RoleType
)
from app.schemas import (
    AdjustmentEnterRequest, AdjustmentUpdateRequest, SubmitReviewRequest,
    JointAdjustmentCreate, JointAdjustmentUpdate, JointAdjustmentResponse,
    AdjustmentResponse, PuppetResponse
)
from app.auth import require_adjuster, get_current_user

router = APIRouter(prefix="/api/adjuster", tags=["调校员管理"])

ACTIVE_STATUSES = [
    PuppetStatus.ADJUSTING,
    PuppetStatus.PENDING_REVIEW,
    PuppetStatus.RETURNING
]


@router.post("/adjustments/enter", response_model=AdjustmentResponse)
def enter_workbench(
    data: AdjustmentEnterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    puppet = db.query(Puppet).filter(Puppet.id == data.puppet_id).first()
    if not puppet:
        raise HTTPException(status_code=404, detail="木偶不存在")

    active_adj = db.query(Adjustment).filter(
        Adjustment.puppet_id == data.puppet_id,
        Adjustment.status.in_(ACTIVE_STATUSES)
    ).first()
    if active_adj:
        raise HTTPException(
            status_code=400,
            detail=f"该木偶已有活跃调校单（#{active_adj.id}，状态「{active_adj.status.value}」），不可重复入台"
        )

    workbench = db.query(Workbench).filter(Workbench.id == data.workbench_id).first()
    if not workbench:
        raise HTTPException(status_code=404, detail="台位不存在")

    adjustment = Adjustment(
        puppet_id=data.puppet_id,
        workbench_id=data.workbench_id,
        adjuster_id=current_user.id,
        status=PuppetStatus.ADJUSTING,
        enter_time=datetime.utcnow()
    )
    db.add(adjustment)
    db.flush()

    puppet.current_status = PuppetStatus.ADJUSTING
    puppet.current_adjustment_id = adjustment.id

    db.commit()
    db.refresh(adjustment)
    return adjustment


@router.get("/adjustments/my", response_model=List[AdjustmentResponse])
def list_my_adjustments(
    status: Optional[PuppetStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    query = db.query(Adjustment).filter(Adjustment.adjuster_id == current_user.id)
    if status:
        query = query.filter(Adjustment.status == status)
    return query.order_by(Adjustment.created_at.desc()).all()


@router.get("/puppets/available", response_model=List[PuppetResponse])
def list_available_puppets(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    return db.query(Puppet).filter(
        Puppet.current_status.in_([
            PuppetStatus.PENDING_ENTER,
            PuppetStatus.PASSED,
            PuppetStatus.SEALED_OBSERVATION
        ])
    ).order_by(Puppet.created_at.desc()).all()


@router.get("/adjustments/{adj_id}", response_model=AdjustmentResponse)
def get_adjustment(
    adj_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权查看此调校单")
    return adj


@router.put("/adjustments/{adj_id}", response_model=AdjustmentResponse)
def update_adjustment_info(
    adj_id: int,
    data: AdjustmentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权修改此调校单")
    if adj.status != PuppetStatus.ADJUSTING and adj.status != PuppetStatus.RETURNING:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，无法修改调校信息"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(adj, field, value)

    adj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(adj)
    return adj


@router.post("/adjustments/{adj_id}/joints", response_model=JointAdjustmentResponse)
def add_joint_adjustment(
    adj_id: int,
    data: JointAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此调校单")
    if adj.status != PuppetStatus.ADJUSTING and adj.status != PuppetStatus.RETURNING:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，无法添加关节调校"
        )

    existing = db.query(JointAdjustment).filter(
        JointAdjustment.adjustment_id == adj_id,
        JointAdjustment.joint_name == data.joint_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"「{data.joint_name.value}」关节已存在调校记录，如需修改请更新该记录"
        )

    obj = JointAdjustment(adjustment_id=adj_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/adjustments/{adj_id}/joints/{joint_id}", response_model=JointAdjustmentResponse)
def update_joint_adjustment(
    adj_id: int,
    joint_id: int,
    data: JointAdjustmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此调校单")
    if adj.status != PuppetStatus.ADJUSTING and adj.status != PuppetStatus.RETURNING:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，无法修改关节调校"
        )

    joint = db.query(JointAdjustment).filter(
        JointAdjustment.id == joint_id,
        JointAdjustment.adjustment_id == adj_id
    ).first()
    if not joint:
        raise HTTPException(status_code=404, detail="关节调校记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(joint, field, value)

    adj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(joint)
    return joint


@router.delete("/adjustments/{adj_id}/joints/{joint_id}")
def delete_joint_adjustment(
    adj_id: int,
    joint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此调校单")
    if adj.status != PuppetStatus.ADJUSTING and adj.status != PuppetStatus.RETURNING:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，无法删除关节调校"
        )

    joint = db.query(JointAdjustment).filter(
        JointAdjustment.id == joint_id,
        JointAdjustment.adjustment_id == adj_id
    ).first()
    if not joint:
        raise HTTPException(status_code=404, detail="关节调校记录不存在")

    db.delete(joint)
    db.commit()
    return {"message": "删除成功"}


@router.post("/adjustments/{adj_id}/submit-review", response_model=AdjustmentResponse)
def submit_for_review(
    adj_id: int,
    data: Optional[SubmitReviewRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    adj = db.query(Adjustment).filter(Adjustment.id == adj_id).first()
    if not adj:
        raise HTTPException(status_code=404, detail="调校单不存在")
    if adj.adjuster_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此调校单")
    if adj.status != PuppetStatus.ADJUSTING and adj.status != PuppetStatus.RETURNING:
        raise HTTPException(
            status_code=400,
            detail=f"当前状态为「{adj.status.value}」，无法提交复核"
        )

    joint_count = db.query(JointAdjustment).filter(
        JointAdjustment.adjustment_id == adj_id
    ).count()
    if joint_count == 0:
        raise HTTPException(
            status_code=400,
            detail="请至少添加一条关节调校记录后再提交复核"
        )

    if data:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                setattr(adj, field, value)

    adj.status = PuppetStatus.PENDING_REVIEW
    adj.submit_review_time = datetime.utcnow()
    adj.updated_at = datetime.utcnow()

    puppet = adj.puppet
    puppet.current_status = PuppetStatus.PENDING_REVIEW

    db.commit()
    db.refresh(adj)
    return adj


@router.get("/joint-stuck")
def get_joint_stuck_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_adjuster)
):
    stucks = db.query(JointAdjustment).filter(
        JointAdjustment.is_stuck == 1
    ).order_by(JointAdjustment.created_at.desc()).limit(50).all()
    return [
        {
            "id": s.id,
            "joint_name": s.joint_name.value,
            "stuck_note": s.stuck_note,
            "adjustment_id": s.adjustment_id,
            "created_at": s.created_at
        }
        for s in stucks
    ]
