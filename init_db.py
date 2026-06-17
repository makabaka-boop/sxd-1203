from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models import (
    User, UserRole, RoleType, JointGroup, Workbench,
    Puppet, PuppetStatus
)
from app.auth import get_password_hash


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            users = [
                User(
                    username="admin",
                    password_hash=get_password_hash("admin123"),
                    full_name="系统管理员",
                    role=UserRole.ADMIN,
                    phone="13800000001"
                ),
                User(
                    username="adjuster1",
                    password_hash=get_password_hash("adj123"),
                    full_name="张调校",
                    role=UserRole.ADJUSTER,
                    phone="13800000002"
                ),
                User(
                    username="adjuster2",
                    password_hash=get_password_hash("adj123"),
                    full_name="李调校",
                    role=UserRole.ADJUSTER,
                    phone="13800000003"
                ),
                User(
                    username="reviewer1",
                    password_hash=get_password_hash("rev123"),
                    full_name="王复核",
                    role=UserRole.REVIEWER,
                    phone="13800000004"
                ),
                User(
                    username="reviewer2",
                    password_hash=get_password_hash("rev123"),
                    full_name="赵复核",
                    role=UserRole.REVIEWER,
                    phone="13800000005"
                ),
            ]
            db.add_all(users)
            db.commit()

        if db.query(RoleType).count() == 0:
            role_types = [
                RoleType(name="主角", description="主要演出角色，动作要求最高"),
                RoleType(name="配角", description="次要演出角色"),
                RoleType(name="群演", description="群体表演木偶"),
                RoleType(name="动物", description="动物形象木偶"),
                RoleType(name="道具偶", description="功能性道具木偶"),
            ]
            db.add_all(role_types)
            db.commit()

        if db.query(JointGroup).count() == 0:
            joint_groups = [
                JointGroup(name="全身标准组", description="肩肘腕髋膝踝颈腰指共9关节"),
                JointGroup(name="上半身组", description="肩肘腕颈腰指关节"),
                JointGroup(name="下半身组", description="髋膝踝关节"),
                JointGroup(name="简化组", description="肩肘髋膝基础关节"),
            ]
            db.add_all(joint_groups)
            db.commit()

        if db.query(Workbench).count() == 0:
            workbenches = [
                Workbench(code="WB-A01", name="A区一号台", description="精密调校台位"),
                Workbench(code="WB-A02", name="A区二号台", description="精密调校台位"),
                Workbench(code="WB-B01", name="B区一号台", description="标准调校台位"),
                Workbench(code="WB-B02", name="B区二号台", description="标准调校台位"),
                Workbench(code="WB-C01", name="C区一号台", description="粗调/返修台位"),
            ]
            db.add_all(workbenches)
            db.commit()

        if db.query(Puppet).count() == 0:
            puppets = [
                Puppet(code="P-001", name="孙悟空一号", role_type_id=1, joint_group_id=1, review_cycle_days=30),
                Puppet(code="P-002", name="唐僧一号", role_type_id=1, joint_group_id=2, review_cycle_days=30),
                Puppet(code="P-003", name="猪八戒一号", role_type_id=1, joint_group_id=1, review_cycle_days=30),
                Puppet(code="P-004", name="沙和尚一号", role_type_id=2, joint_group_id=1, review_cycle_days=45),
                Puppet(code="P-005", name="白龙马一号", role_type_id=4, joint_group_id=4, review_cycle_days=60),
                Puppet(code="P-006", name="观音菩萨", role_type_id=2, joint_group_id=2, review_cycle_days=45),
                Puppet(code="P-007", name="小妖甲", role_type_id=3, joint_group_id=4, review_cycle_days=90),
                Puppet(code="P-008", name="小妖乙", role_type_id=3, joint_group_id=4, review_cycle_days=90),
                Puppet(code="P-009", name="树精", role_type_id=3, joint_group_id=2, review_cycle_days=60),
                Puppet(code="P-010", name="山神道具", role_type_id=5, joint_group_id=2, review_cycle_days=120),
            ]
            db.add_all(puppets)
            db.commit()

        print("数据库初始化完成")
        print("默认账号:")
        print("  管理员: admin / admin123")
        print("  调校员: adjuster1 / adj123, adjuster2 / adj123")
        print("  复核员: reviewer1 / rev123, reviewer2 / rev123")

    finally:
        db.close()


if __name__ == "__main__":
    init_db()
