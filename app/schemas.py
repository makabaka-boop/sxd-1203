from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models import UserRole, PuppetStatus, JointName


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: UserRole
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[int] = None


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    phone: Optional[str]
    created_at: datetime
    is_active: int

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RoleTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class RoleTypeCreate(RoleTypeBase):
    pass


class RoleTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class JointGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class JointGroupCreate(JointGroupBase):
    pass


class JointGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class JointGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkbenchBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class WorkbenchCreate(WorkbenchBase):
    pass


class WorkbenchUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None


class WorkbenchResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PuppetBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    role_type_id: int
    joint_group_id: int
    responsible_person_id: Optional[int] = None
    review_cycle_days: int = Field(default=30, ge=1)


class PuppetCreate(PuppetBase):
    pass


class PuppetUpdate(BaseModel):
    name: Optional[str] = None
    role_type_id: Optional[int] = None
    joint_group_id: Optional[int] = None
    responsible_person_id: Optional[int] = None
    review_cycle_days: Optional[int] = None


class PuppetResponse(BaseModel):
    id: int
    code: str
    name: str
    role_type_id: int
    joint_group_id: int
    responsible_person_id: Optional[int] = None
    current_status: PuppetStatus
    review_cycle_days: int
    created_at: datetime
    last_passed_date: Optional[date]
    role_type: Optional[RoleTypeResponse]
    joint_group: Optional[JointGroupResponse]
    responsible_person: Optional[UserResponse] = None

    class Config:
        from_attributes = True


class JointAdjustmentBase(BaseModel):
    joint_name: JointName
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    tension_value: Optional[str] = None
    is_stuck: int = 0
    stuck_note: Optional[str] = None
    remark: Optional[str] = None


class JointAdjustmentCreate(JointAdjustmentBase):
    pass


class JointAdjustmentUpdate(BaseModel):
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    tension_value: Optional[str] = None
    is_stuck: Optional[int] = None
    stuck_note: Optional[str] = None
    remark: Optional[str] = None


class JointAdjustmentResponse(BaseModel):
    id: int
    joint_name: JointName
    before_value: Optional[str]
    after_value: Optional[str]
    tension_value: Optional[str]
    is_stuck: int
    stuck_note: Optional[str]
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AdjustmentEnterRequest(BaseModel):
    puppet_id: int
    workbench_id: int


class AdjustmentUpdateRequest(BaseModel):
    tension_note: Optional[str] = None
    return_action_note: Optional[str] = None


class SubmitReviewRequest(BaseModel):
    tension_note: Optional[str] = None
    return_action_note: Optional[str] = None


class ReviewRequest(BaseModel):
    smoothness_score: int = Field(..., ge=0, le=100)
    deviation_note: Optional[str] = None
    review_opinion: Optional[str] = None
    is_passed: int


class AdjustmentResponse(BaseModel):
    id: int
    puppet_id: int
    workbench_id: int
    adjuster_id: int
    status: PuppetStatus
    enter_time: Optional[datetime]
    submit_review_time: Optional[datetime]
    review_time: Optional[datetime]
    seal_time: Optional[datetime]
    tension_note: Optional[str]
    return_action_note: Optional[str]
    reviewer_id: Optional[int]
    smoothness_score: Optional[int]
    deviation_note: Optional[str]
    review_opinion: Optional[str]
    is_passed: int
    created_at: datetime
    updated_at: datetime
    puppet: Optional[PuppetResponse]
    workbench: Optional[WorkbenchResponse]
    adjuster: Optional[UserResponse]
    reviewer: Optional[UserResponse]
    joint_adjustments: List[JointAdjustmentResponse]

    class Config:
        from_attributes = True


class StatItem(BaseModel):
    name: str
    count: int


class JointAbnormalRank(BaseModel):
    joint_name: JointName
    stuck_count: int
    rank: int


class AdjustmentPassRate(BaseModel):
    total_adjustments: int
    passed_count: int
    returned_count: int
    pass_rate: float


class PendingReviewItem(BaseModel):
    adjustment_id: int
    puppet_code: str
    puppet_name: str
    role_type_name: str
    workbench_code: str
    adjuster_name: str
    submit_time: datetime
    wait_hours: float


class WarningItem(BaseModel):
    warning_type: str
    description: str
    related_id: Optional[int]
    related_info: Optional[str]


class SealObservationRequest(BaseModel):
    review_opinion: Optional[str] = None
