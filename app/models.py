from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Enum, Date
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, PyEnum):
    ADMIN = "admin"
    ADJUSTER = "adjuster"
    REVIEWER = "reviewer"


class PuppetStatus(str, PyEnum):
    PENDING_ENTER = "待入台"
    ADJUSTING = "调校中"
    PENDING_REVIEW = "待试演"
    RETURNING = "返调中"
    PASSED = "通过"
    SEALED_OBSERVATION = "封存观察"


class JointName(str, PyEnum):
    SHOULDER = "肩"
    ELBOW = "肘"
    WRIST = "腕"
    HIP = "髋"
    KNEE = "膝"
    ANKLE = "踝"
    NECK = "颈"
    WAIST = "腰"
    FINGER = "指"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    phone = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)


class RoleType(Base):
    __tablename__ = "role_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class JointGroup(Base):
    __tablename__ = "joint_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class Workbench(Base):
    __tablename__ = "workbenches"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)


class Puppet(Base):
    __tablename__ = "puppets"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    role_type_id = Column(Integer, ForeignKey("role_types.id"), nullable=False)
    joint_group_id = Column(Integer, ForeignKey("joint_groups.id"), nullable=False)
    responsible_person_id = Column(Integer, ForeignKey("users.id"), index=True)
    current_status = Column(Enum(PuppetStatus), default=PuppetStatus.PENDING_ENTER, index=True)
    review_cycle_days = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_passed_date = Column(Date)
    current_adjustment_id = Column(Integer, ForeignKey("adjustments.id"))

    role_type = relationship("RoleType", lazy="joined")
    joint_group = relationship("JointGroup", lazy="joined")
    responsible_person = relationship("User", foreign_keys=[responsible_person_id], lazy="joined")
    current_adjustment = relationship(
        "Adjustment",
        foreign_keys=[current_adjustment_id],
        lazy="joined"
    )


class Adjustment(Base):
    __tablename__ = "adjustments"

    id = Column(Integer, primary_key=True, index=True)
    puppet_id = Column(Integer, ForeignKey("puppets.id"), nullable=False, index=True)
    workbench_id = Column(Integer, ForeignKey("workbenches.id"), nullable=False, index=True)
    adjuster_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum(PuppetStatus), default=PuppetStatus.ADJUSTING, index=True)

    enter_time = Column(DateTime, default=datetime.utcnow)
    submit_review_time = Column(DateTime)
    review_time = Column(DateTime)
    seal_time = Column(DateTime)

    tension_note = Column(Text)
    return_action_note = Column(Text)
    reviewer_id = Column(Integer, ForeignKey("users.id"))
    smoothness_score = Column(Integer)
    deviation_note = Column(Text)
    review_opinion = Column(Text)
    is_passed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    puppet = relationship("Puppet", foreign_keys=[puppet_id], lazy="joined")
    workbench = relationship("Workbench", lazy="joined")
    adjuster = relationship("User", foreign_keys=[adjuster_id], lazy="joined")
    reviewer = relationship("User", foreign_keys=[reviewer_id], lazy="joined")
    joint_adjustments = relationship(
        "JointAdjustment",
        back_populates="adjustment",
        cascade="all, delete-orphan"
    )


class JointAdjustment(Base):
    __tablename__ = "joint_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("adjustments.id"), nullable=False, index=True)
    joint_name = Column(Enum(JointName), nullable=False, index=True)
    before_value = Column(String(100))
    after_value = Column(String(100))
    tension_value = Column(String(100))
    is_stuck = Column(Integer, default=0)
    stuck_note = Column(Text)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    adjustment = relationship("Adjustment", back_populates="joint_adjustments")
