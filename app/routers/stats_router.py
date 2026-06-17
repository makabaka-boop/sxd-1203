from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, date, timedelta
from app.database import get_db
from app.models import (
    User, Puppet, PuppetStatus, Adjustment, JointAdjustment,
    JointName, Workbench, RoleType, UserRole, ReturnRecord
)
from app.schemas import (
    AdjustmentResponse, JointAbnormalRank, AdjustmentPassRate,
    PendingReviewItem, WarningItem, ReturnRateResponse,
    AdjusterReturnRankItem, OverdueReturnItem
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/stats", tags=["统计分析与查询"])


@router.get("/adjustments", response_model=List[AdjustmentResponse])
def query_adjustments(
    role_type_id: Optional[int] = None,
    joint_group_id: Optional[int] = None,
    responsible_person_id: Optional[int] = None,
    workbench_id: Optional[int] = None,
    adjuster_id: Optional[int] = None,
    status: Optional[PuppetStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    query = db.query(Adjustment)

    need_puppet_join = role_type_id or joint_group_id or responsible_person_id
    if need_puppet_join:
        query = query.join(Puppet, Adjustment.puppet_id == Puppet.id)
        if role_type_id:
            query = query.filter(Puppet.role_type_id == role_type_id)
        if joint_group_id:
            query = query.filter(Puppet.joint_group_id == joint_group_id)
        if responsible_person_id:
            query = query.filter(Puppet.responsible_person_id == responsible_person_id)

    if workbench_id:
        query = query.filter(Adjustment.workbench_id == workbench_id)
    if adjuster_id:
        query = query.filter(Adjustment.adjuster_id == adjuster_id)
    if status:
        query = query.filter(Adjustment.status == status)
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.filter(Adjustment.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Adjustment.created_at <= end_dt)

    return query.order_by(Adjustment.created_at.desc()).all()


@router.get("/puppets", response_model=List)
def query_puppets(
    role_type_id: Optional[int] = None,
    joint_group_id: Optional[int] = None,
    responsible_person_id: Optional[int] = None,
    workbench_id: Optional[int] = None,
    current_status: Optional[PuppetStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    query = db.query(Puppet)

    if workbench_id:
        query = query.join(
            Adjustment, Puppet.current_adjustment_id == Adjustment.id
        )
        query = query.filter(Adjustment.workbench_id == workbench_id)

    if role_type_id:
        query = query.filter(Puppet.role_type_id == role_type_id)
    if joint_group_id:
        query = query.filter(Puppet.joint_group_id == joint_group_id)
    if responsible_person_id:
        query = query.filter(Puppet.responsible_person_id == responsible_person_id)
    if current_status:
        query = query.filter(Puppet.current_status == current_status)
    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.filter(Puppet.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Puppet.created_at <= end_dt)
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.filter(
            (Puppet.code.like(keyword_like)) | (Puppet.name.like(keyword_like))
        )

    puppets = query.order_by(Puppet.created_at.desc()).all()
    result = []
    for p in puppets:
        info = {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "current_status": p.current_status.value,
            "review_cycle_days": p.review_cycle_days,
            "created_at": p.created_at,
            "last_passed_date": p.last_passed_date,
            "role_type_name": p.role_type.name if p.role_type else "",
            "joint_group_name": p.joint_group.name if p.joint_group else "",
            "responsible_person_id": p.responsible_person_id,
            "responsible_person_name": p.responsible_person.full_name if p.responsible_person else "",
        }
        if p.current_adjustment:
            info["workbench_code"] = p.current_adjustment.workbench.code if p.current_adjustment.workbench else ""
            info["workbench_name"] = p.current_adjustment.workbench.name if p.current_adjustment.workbench else ""
            info["adjuster_name"] = p.current_adjustment.adjuster.full_name if p.current_adjustment.adjuster else ""
        result.append(info)
    return result


@router.get("/joint-abnormal-rank", response_model=List[JointAbnormalRank])
def get_joint_abnormal_rank(
    limit: int = Query(default=10, ge=1, le=50),
    days: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    query = db.query(
        JointAdjustment.joint_name,
        func.count(JointAdjustment.id).label("stuck_count")
    ).filter(JointAdjustment.is_stuck == 1)

    if days:
        threshold = datetime.utcnow() - timedelta(days=days)
        query = query.filter(JointAdjustment.created_at >= threshold)

    result = query.group_by(JointAdjustment.joint_name).order_by(
        func.count(JointAdjustment.id).desc()
    ).limit(limit).all()

    rank_list = []
    for idx, (joint_name, stuck_count) in enumerate(result, start=1):
        rank_list.append(JointAbnormalRank(
            joint_name=joint_name,
            stuck_count=stuck_count,
            rank=idx
        ))
    return rank_list


@router.get("/pending-review-list", response_model=List[PendingReviewItem])
def get_pending_review_list(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    pending = db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.PENDING_REVIEW
    ).order_by(Adjustment.submit_review_time.asc()).all()

    items = []
    for adj in pending:
        puppet = adj.puppet
        workbench = adj.workbench
        adjuster = adj.adjuster

        wait_hours = 0.0
        if adj.submit_review_time:
            wait_hours = (datetime.utcnow() - adj.submit_review_time).total_seconds() / 3600

        items.append(PendingReviewItem(
            adjustment_id=adj.id,
            puppet_code=puppet.code if puppet else "",
            puppet_name=puppet.name if puppet else "",
            role_type_name=puppet.role_type.name if puppet and puppet.role_type else "",
            workbench_code=workbench.code if workbench else "",
            adjuster_name=adjuster.full_name if adjuster else "",
            submit_time=adj.submit_review_time or adj.created_at,
            wait_hours=round(wait_hours, 1)
        ))
    return items


@router.get("/adjustment-pass-rate", response_model=AdjustmentPassRate)
def get_adjustment_pass_rate(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    adjuster_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    base_filter = [Adjustment.review_time.isnot(None)]

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        base_filter.append(Adjustment.review_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        base_filter.append(Adjustment.review_time <= end_dt)
    if adjuster_id:
        base_filter.append(Adjustment.adjuster_id == adjuster_id)

    filter_condition = and_(*base_filter)

    total = db.query(func.count(Adjustment.id)).filter(filter_condition).scalar() or 0
    passed = db.query(func.count(Adjustment.id)).filter(
        filter_condition, Adjustment.is_passed == 1
    ).scalar() or 0
    returned = total - passed
    rate = round((passed / total * 100), 2) if total > 0 else 0.0

    return AdjustmentPassRate(
        total_adjustments=total,
        passed_count=passed,
        returned_count=returned,
        pass_rate=rate
    )


@router.get("/warnings", response_model=List[WarningItem])
def get_warnings(
    review_overdue_hours: int = Query(default=24, ge=1),
    workbench_threshold: int = Query(default=3, ge=1),
    return_unreviewed_hours: int = Query(default=48, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    warnings: List[WarningItem] = []

    review_threshold = datetime.utcnow() - timedelta(hours=review_overdue_hours)
    overdue_reviews = db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.PENDING_REVIEW,
        Adjustment.submit_review_time <= review_threshold
    ).all()
    for adj in overdue_reviews:
        wait_h = (datetime.utcnow() - adj.submit_review_time).total_seconds() / 3600
        puppet = adj.puppet
        warnings.append(WarningItem(
            warning_type="试演超期",
            description=f"木偶「{puppet.code if puppet else adj.puppet_id}」待试演已超{round(wait_h,1)}小时未复核",
            related_id=adj.id,
            related_info=f"调校单#{adj.id}"
        ))

    return_threshold = datetime.utcnow() - timedelta(hours=return_unreviewed_hours)
    return_no_review = db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.RETURNING,
        Adjustment.updated_at <= return_threshold
    ).all()
    for adj in return_no_review:
        wait_h = (datetime.utcnow() - adj.updated_at).total_seconds() / 3600
        puppet = adj.puppet
        warnings.append(WarningItem(
            warning_type="返调后未复核",
            description=f"木偶「{puppet.code if puppet else adj.puppet_id}」返调中已超{round(wait_h,1)}小时未再次提交复核",
            related_id=adj.id,
            related_info=f"调校单#{adj.id}"
        ))

    workbenches = db.query(Workbench).all()
    for wb in workbenches:
        active_count = db.query(Adjustment).filter(
            Adjustment.workbench_id == wb.id,
            Adjustment.status.in_([
                PuppetStatus.ADJUSTING,
                PuppetStatus.RETURNING,
                PuppetStatus.PENDING_REVIEW
            ])
        ).count()
        if active_count >= workbench_threshold:
            warnings.append(WarningItem(
                warning_type="同台位积压",
                description=f"台位「{wb.code} {wb.name}」当前活跃调校单数达{active_count}个（阈值{workbench_threshold}）",
                related_id=wb.id,
                related_info=f"台位#{wb.id}"
            ))

    top_stuck_joints = db.query(
        JointAdjustment.joint_name,
        func.count(JointAdjustment.id).label("cnt")
    ).filter(JointAdjustment.is_stuck == 1).group_by(
        JointAdjustment.joint_name
    ).order_by(func.count(JointAdjustment.id).desc()).limit(3).all()
    for joint_name, cnt in top_stuck_joints:
        if cnt >= 2:
            warnings.append(WarningItem(
                warning_type="卡滞高发关节",
                description=f"「{joint_name.value}」关节累计出现{cnt}次卡滞记录，请关注设计或材质问题",
                related_id=None,
                related_info=f"卡滞次数:{cnt}"
            ))

    today = date.today()
    puppets_to_review = db.query(Puppet).filter(
        Puppet.current_status == PuppetStatus.PASSED,
        Puppet.last_passed_date.isnot(None)
    ).all()
    for p in puppets_to_review:
        if p.last_passed_date:
            days_since = (today - p.last_passed_date).days
            if days_since >= p.review_cycle_days:
                warnings.append(WarningItem(
                    warning_type="复核周期到期",
                    description=f"木偶「{p.code} {p.name}」距上次通过已{days_since}天，超过{p.review_cycle_days}天复核周期",
                    related_id=p.id,
                    related_info=f"木偶#{p.id}"
                ))

    return warnings


@router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    total_puppets = db.query(func.count(Puppet.id)).scalar() or 0
    status_counts = db.query(
        Puppet.current_status, func.count(Puppet.id)
    ).group_by(Puppet.current_status).all()
    status_map = {s.value: c for s, c in status_counts}

    total_adjustments = db.query(func.count(Adjustment.id)).scalar() or 0
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time())
    today_adjustments = db.query(func.count(Adjustment.id)).filter(
        Adjustment.created_at >= today_start
    ).scalar() or 0

    adjuster_count = db.query(func.count(User.id)).filter(
        User.role == UserRole.ADJUSTER, User.is_active == 1
    ).scalar() or 0
    reviewer_count = db.query(func.count(User.id)).filter(
        User.role == UserRole.REVIEWER, User.is_active == 1
    ).scalar() or 0

    return {
        "total_puppets": total_puppets,
        "total_adjustments": total_adjustments,
        "today_adjustments": today_adjustments,
        "active_adjusters": adjuster_count,
        "active_reviewers": reviewer_count,
        "status_distribution": {
            s.value: status_map.get(s.value, 0) for s in PuppetStatus
        }
    }


@router.get("/return-rate", response_model=ReturnRateResponse)
def get_return_rate(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    adjuster_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    base_filter = [Adjustment.review_time.isnot(None)]

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        base_filter.append(Adjustment.review_time >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        base_filter.append(Adjustment.review_time <= end_dt)
    if adjuster_id:
        base_filter.append(Adjustment.adjuster_id == adjuster_id)

    filter_condition = and_(*base_filter)

    total_reviewed = db.query(func.count(Adjustment.id)).filter(filter_condition).scalar() or 0
    total_returned = db.query(func.count(Adjustment.id)).filter(
        filter_condition, Adjustment.is_passed == 0
    ).scalar() or 0

    rate = round((total_returned / total_reviewed * 100), 2) if total_reviewed > 0 else 0.0

    return ReturnRateResponse(
        total_reviewed=total_reviewed,
        total_returned=total_returned,
        return_rate=rate
    )


@router.get("/adjuster-return-rank", response_model=List[AdjusterReturnRankItem])
def get_adjuster_return_rank(
    limit: int = Query(default=10, ge=1, le=50),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    query = db.query(
        Adjustment.adjuster_id,
        func.sum(Adjustment.return_count).label("total_return_count")
    ).filter(Adjustment.return_count > 0)

    if start_date:
        start_dt = datetime.combine(start_date, datetime.min.time())
        query = query.filter(Adjustment.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Adjustment.created_at <= end_dt)

    result = query.group_by(Adjustment.adjuster_id).order_by(
        func.sum(Adjustment.return_count).desc()
    ).limit(limit).all()

    rank_list = []
    for idx, (adjuster_id, total_return_count) in enumerate(result, start=1):
        user = db.query(User).filter(User.id == adjuster_id).first()
        rank_list.append(AdjusterReturnRankItem(
            adjuster_id=adjuster_id,
            adjuster_name=user.full_name if user else "",
            total_return_count=int(total_return_count or 0),
            rank=idx
        ))
    return rank_list


@router.get("/overdue-returns", response_model=List[OverdueReturnItem])
def get_overdue_returns(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user)
):
    now = datetime.utcnow()

    returning_adjs = db.query(Adjustment).filter(
        Adjustment.status == PuppetStatus.RETURNING
    ).all()

    overdue_items = []
    for adj in returning_adjs:
        latest_record = db.query(ReturnRecord).filter(
            ReturnRecord.adjustment_id == adj.id
        ).order_by(ReturnRecord.return_count.desc()).first()

        if not latest_record or not latest_record.expected_complete_time:
            continue

        if now <= latest_record.expected_complete_time:
            continue

        overdue_hours = (now - latest_record.expected_complete_time).total_seconds() / 3600

        overdue_items.append(OverdueReturnItem(
            adjustment_id=adj.id,
            puppet_code=adj.puppet.code if adj.puppet else "",
            puppet_name=adj.puppet.name if adj.puppet else "",
            adjuster_name=adj.adjuster.full_name if adj.adjuster else "",
            return_count=adj.return_count,
            expected_complete_time=latest_record.expected_complete_time,
            overdue_hours=round(overdue_hours, 1),
            latest_return_reason=latest_record.return_reason
        ))

    return sorted(overdue_items, key=lambda x: x.overdue_hours, reverse=True)
