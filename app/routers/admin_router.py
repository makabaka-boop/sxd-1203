from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import (
    User, UserRole, RoleType, JointGroup, Workbench, Puppet, PuppetStatus, Adjustment
)
from app.schemas import (
    UserCreate, UserUpdate, UserResponse,
    RoleTypeCreate, RoleTypeUpdate, RoleTypeResponse,
    JointGroupCreate, JointGroupUpdate, JointGroupResponse,
    WorkbenchCreate, WorkbenchUpdate, WorkbenchResponse,
    PuppetCreate, PuppetUpdate, PuppetResponse, AdjustmentResponse
)
from app.auth import require_admin, get_password_hash

router = APIRouter(prefix="/api/admin", tags=["管理员管理"])


@router.post("/users", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    existing = db.query(User).filter(User.username == user_data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在"
        )
    user = User(
        username=user_data.username,
        full_name=user_data.full_name,
        role=user_data.role,
        phone=user_data.phone,
        password_hash=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=List[UserResponse])
def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    return query.order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = user_data.model_dump(exclude_unset=True)
    if "password" in update_data and update_data["password"]:
        user.password_hash = get_password_hash(update_data["password"])
        del update_data["password"]

    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.post("/role-types", response_model=RoleTypeResponse)
def create_role_type(
    data: RoleTypeCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    existing = db.query(RoleType).filter(RoleType.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色类型名称已存在")
    obj = RoleType(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/role-types", response_model=List[RoleTypeResponse])
def list_role_types(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    return db.query(RoleType).order_by(RoleType.created_at.desc()).all()


@router.put("/role-types/{item_id}", response_model=RoleTypeResponse)
def update_role_type(
    item_id: int,
    data: RoleTypeUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(RoleType).filter(RoleType.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="角色类型不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/role-types/{item_id}")
def delete_role_type(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(RoleType).filter(RoleType.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="角色类型不存在")

    puppet_count = db.query(Puppet).filter(Puppet.role_type_id == item_id).count()
    if puppet_count > 0:
        raise HTTPException(status_code=400, detail=f"存在{puppet_count}个木偶使用此角色类型，无法删除")

    db.delete(obj)
    db.commit()
    return {"message": "删除成功"}


@router.post("/joint-groups", response_model=JointGroupResponse)
def create_joint_group(
    data: JointGroupCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    existing = db.query(JointGroup).filter(JointGroup.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="关节组名称已存在")
    obj = JointGroup(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/joint-groups", response_model=List[JointGroupResponse])
def list_joint_groups(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    return db.query(JointGroup).order_by(JointGroup.created_at.desc()).all()


@router.put("/joint-groups/{item_id}", response_model=JointGroupResponse)
def update_joint_group(
    item_id: int,
    data: JointGroupUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(JointGroup).filter(JointGroup.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="关节组不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/joint-groups/{item_id}")
def delete_joint_group(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(JointGroup).filter(JointGroup.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="关节组不存在")

    puppet_count = db.query(Puppet).filter(Puppet.joint_group_id == item_id).count()
    if puppet_count > 0:
        raise HTTPException(status_code=400, detail=f"存在{puppet_count}个木偶使用此关节组，无法删除")

    db.delete(obj)
    db.commit()
    return {"message": "删除成功"}


@router.post("/workbenches", response_model=WorkbenchResponse)
def create_workbench(
    data: WorkbenchCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    existing = db.query(Workbench).filter(Workbench.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="台位编号已存在")
    obj = Workbench(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/workbenches", response_model=List[WorkbenchResponse])
def list_workbenches(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    return db.query(Workbench).order_by(Workbench.created_at.desc()).all()


@router.put("/workbenches/{item_id}", response_model=WorkbenchResponse)
def update_workbench(
    item_id: int,
    data: WorkbenchUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(Workbench).filter(Workbench.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="台位不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "code" in update_data and update_data["code"]:
        existing = db.query(Workbench).filter(
            Workbench.code == update_data["code"],
            Workbench.id != item_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="台位编号已被其他台位使用")

    for field, value in update_data.items():
        if value is not None:
            setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/workbenches/{item_id}")
def delete_workbench(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(Workbench).filter(Workbench.id == item_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="台位不存在")

    adj_count = db.query(Adjustment).filter(Adjustment.workbench_id == item_id).count()
    if adj_count > 0:
        raise HTTPException(status_code=400, detail=f"存在{adj_count}条调校记录关联此台位，无法删除")

    db.delete(obj)
    db.commit()
    return {"message": "删除成功"}


@router.post("/puppets", response_model=PuppetResponse)
def create_puppet(
    data: PuppetCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    existing = db.query(Puppet).filter(Puppet.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="木偶编号已存在")

    role_type = db.query(RoleType).filter(RoleType.id == data.role_type_id).first()
    if not role_type:
        raise HTTPException(status_code=404, detail="角色类型不存在")

    joint_group = db.query(JointGroup).filter(JointGroup.id == data.joint_group_id).first()
    if not joint_group:
        raise HTTPException(status_code=404, detail="关节组不存在")

    if data.responsible_person_id:
        person = db.query(User).filter(User.id == data.responsible_person_id).first()
        if not person:
            raise HTTPException(status_code=404, detail="责任人不存在")

    obj = Puppet(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/puppets", response_model=List[PuppetResponse])
def list_puppets(
    role_type_id: Optional[int] = None,
    joint_group_id: Optional[int] = None,
    responsible_person_id: Optional[int] = None,
    current_status: Optional[PuppetStatus] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    query = db.query(Puppet)
    if role_type_id:
        query = query.filter(Puppet.role_type_id == role_type_id)
    if joint_group_id:
        query = query.filter(Puppet.joint_group_id == joint_group_id)
    if responsible_person_id:
        query = query.filter(Puppet.responsible_person_id == responsible_person_id)
    if current_status:
        query = query.filter(Puppet.current_status == current_status)
    if keyword:
        keyword_like = f"%{keyword}%"
        query = query.filter(
            (Puppet.code.like(keyword_like)) | (Puppet.name.like(keyword_like))
        )
    return query.order_by(Puppet.created_at.desc()).all()


@router.get("/puppets/{puppet_id}", response_model=PuppetResponse)
def get_puppet(
    puppet_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(Puppet).filter(Puppet.id == puppet_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="木偶不存在")
    return obj


@router.put("/puppets/{puppet_id}", response_model=PuppetResponse)
def update_puppet(
    puppet_id: int,
    data: PuppetUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    obj = db.query(Puppet).filter(Puppet.id == puppet_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="木偶不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


@router.get("/puppets/{puppet_id}/adjustments", response_model=List[AdjustmentResponse])
def get_puppet_adjustments(
    puppet_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    puppet = db.query(Puppet).filter(Puppet.id == puppet_id).first()
    if not puppet:
        raise HTTPException(status_code=404, detail="木偶不存在")
    adjs = db.query(Adjustment).filter(Adjustment.puppet_id == puppet_id).order_by(Adjustment.created_at.desc()).all()
    return adjs
