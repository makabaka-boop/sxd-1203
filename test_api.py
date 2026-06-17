import urllib.request
import urllib.parse
import json

BASE = "http://localhost:8114"

def req(method, path, data=None, token=None, query=None):
    url = BASE + path
    if query:
        qs = urllib.parse.urlencode({k: v for k, v in query.items() if v is not None})
        if qs:
            url = url + "?" + qs
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

results = []

def test(name, expected_status, status, res):
    ok = status == expected_status
    results.append((name, "✅ PASS" if ok else "❌ FAIL", status, res))
    return ok

print("="*60)
print("木偶管理系统 API 测试（含 Bug 修复验证）")
print("="*60)

# 1. 健康检查
print("\n[1] 健康检查")
s, r = req("GET", "/health")
test("健康检查", 200, s, r)
print(f"  状态={s}, 端口={r.get('port')}")

# 2. 管理员登录
print("\n[2] 管理员登录")
s, r = req("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
test("管理员登录", 200, s, r)
admin_token = r.get("access_token") if s == 200 else None
print(f"  状态={s}, 角色={r.get('user',{}).get('role')}")

# 3. 调校员登录
print("\n[3] 调校员登录")
s, r = req("POST", "/api/auth/login", {"username": "adjuster1", "password": "adj123"})
test("调校员登录", 200, s, r)
adjuster_token = r.get("access_token") if s == 200 else None
print(f"  状态={s}, 姓名={r.get('user',{}).get('full_name')}")

# 4. 复核员登录
print("\n[4] 复核员登录")
s, r = req("POST", "/api/auth/login", {"username": "reviewer1", "password": "rev123"})
test("复核员登录", 200, s, r)
reviewer_token = r.get("access_token") if s == 200 else None
print(f"  状态={s}, 姓名={r.get('user',{}).get('full_name')}")

# ============================================================
# BUG FIX 1: 禁止通过注册接口创建管理员账号
# ============================================================
print("\n" + "="*60)
print("BUG FIX 1: 注册接口禁止创建管理员")
print("="*60)

print("\n[5] 注册管理员账号（应被拒绝 403）")
s, r = req("POST", "/api/auth/register", {
    "username": "hacker_admin",
    "full_name": "黑客管理员",
    "role": "admin",
    "password": "hack123",
    "phone": "13900000000"
})
test("注册管理员被拒", 403, s, r)
print(f"  状态={s}, 原因={r.get('detail','')[:50]}")

print("\n[6] 注册调校员账号（应成功 200）")
s, r = req("POST", "/api/auth/register", {
    "username": "new_adjuster",
    "full_name": "新调校员",
    "role": "adjuster",
    "password": "new123456"
})
test("注册调校员成功", 200, s, r)
print(f"  状态={s}, 角色={r.get('role')}")

print("\n[7] 管理员创建管理员账号（应成功 200）")
s, r = req("POST", "/api/admin/users", {
    "username": "admin2",
    "full_name": "第二管理员",
    "role": "admin",
    "password": "admin456"
}, token=admin_token)
test("管理员创建管理员成功", 200, s, r)
print(f"  状态={s}, 角色={r.get('role')}")

# ============================================================
# BUG FIX 2: 防止同一木偶并行入台
# ============================================================
print("\n" + "="*60)
print("BUG FIX 2: 防止同一木偶并行活跃调校单")
print("="*60)

print("\n[8] 调校员入台 (P-001 到 WB-A01)")
s, r = req("POST", "/api/adjuster/adjustments/enter", {
    "puppet_id": 1, "workbench_id": 1
}, token=adjuster_token)
test("入台操作", 200, s, r)
adj_id = r.get("id") if s == 200 else None
print(f"  状态={s}, 调校单ID={adj_id}, 当前状态={r.get('status')}")

print("\n[9] 同一木偶再次入台（应被拒绝 400）")
s, r = req("POST", "/api/adjuster/adjustments/enter", {
    "puppet_id": 1, "workbench_id": 2
}, token=adjuster_token)
test("并行入台被拒", 400, s, r)
print(f"  状态={s}, 原因={str(r.get('detail',''))[:50]}")

print("\n[10] 另一调校员对同一木偶入台（也应被拒）")
s2, r2 = req("POST", "/api/auth/login", {"username": "adjuster2", "password": "adj123"})
adj2_token = r2.get("access_token") if s2 == 200 else None
s, r = req("POST", "/api/adjuster/adjustments/enter", {
    "puppet_id": 1, "workbench_id": 3
}, token=adj2_token)
test("另一调校员并入台被拒", 400, s, r)
print(f"  状态={s}, 原因={str(r.get('detail',''))[:50]}")

# ============================================================
# BUG FIX 3: 木偶责任人字段
# ============================================================
print("\n" + "="*60)
print("BUG FIX 3: 木偶责任人字段")
print("="*60)

print("\n[11] 查看木偶详情（应含责任人信息）")
s, r = req("GET", "/api/admin/puppets/1", token=admin_token)
test("木偶含责任人", 200, s, r)
has_person = r.get("responsible_person") is not None or r.get("responsible_person_id") is not None
print(f"  状态={s}, 责任人ID={r.get('responsible_person_id')}, 责任人={r.get('responsible_person')}")

print("\n[12] 创建木偶时指定责任人")
s, r = req("POST", "/api/admin/puppets", {
    "code": "P-011",
    "name": "测试木偶",
    "role_type_id": 1,
    "joint_group_id": 1,
    "responsible_person_id": 2,
    "review_cycle_days": 30
}, token=admin_token)
test("创建木偶指定责任人", 200, s, r)
print(f"  状态={s}, 责任人ID={r.get('responsible_person_id')}")

print("\n[13] 修改木偶责任人")
s, r = req("PUT", "/api/admin/puppets/11", {
    "responsible_person_id": 3
}, token=admin_token)
test("修改木偶责任人", 200, s, r)
print(f"  状态={s}, 新责任人ID={r.get('responsible_person_id')}")

# ============================================================
# BUG FIX 4: 按责任人筛选查询
# ============================================================
print("\n" + "="*60)
print("BUG FIX 4: 按责任人筛选查询")
print("="*60)

print("\n[14] 管理员按责任人筛选木偶")
s, r = req("GET", "/api/admin/puppets", token=admin_token, query={"responsible_person_id": 2})
test("管理员按责任人筛选", 200, s, r)
count = len(r) if isinstance(r, list) else 0
print(f"  状态={s}, 责任人ID=2 的木偶数量={count}")

print("\n[15] 统计接口按责任人筛选木偶")
s, r = req("GET", "/api/stats/puppets", token=admin_token, query={"responsible_person_id": 3})
test("统计按责任人筛选木偶", 200, s, r)
count = len(r) if isinstance(r, list) else 0
all_match = all(p.get("responsible_person_id") == 3 for p in r) if isinstance(r, list) and r else False
print(f"  状态={s}, 结果数={count}, 全部匹配责任人ID=3: {all_match}")

print("\n[16] 统计接口按责任人筛选调校单")
s, r = req("GET", "/api/stats/adjustments", token=admin_token, query={"responsible_person_id": 2})
test("统计按责任人筛选调校单", 200, s, r)
count = len(r) if isinstance(r, list) else 0
print(f"  状态={s}, 结果数={count}")

# ============================================================
# 继续原有业务流程测试
# ============================================================
print("\n" + "="*60)
print("业务流程继续测试")
print("="*60)

print("\n[17] 添加关节调校记录")
joints_data = [
    {"joint_name": "肩", "before_value": "90°", "after_value": "120°", "tension_value": "3.2N"},
    {"joint_name": "肘", "before_value": "阻尼2.1", "after_value": "阻尼1.8", "is_stuck": 1, "stuck_note": "轻微卡滞"},
    {"joint_name": "膝", "before_value": "回弹15%", "after_value": "回弹5%", "tension_value": "4.0N"},
]
ok_count = 0
for j in joints_data:
    s, rj = req("POST", f"/api/adjuster/adjustments/{adj_id}/joints", j, token=adjuster_token)
    if s == 200:
        ok_count += 1
test(f"添加{len(joints_data)}个关节", len(joints_data), ok_count, {"success": ok_count})
print(f"  成功={ok_count}/{len(joints_data)}")

print("\n[18] 提交复核")
s, r = req("POST", f"/api/adjuster/adjustments/{adj_id}/submit-review", {
    "tension_note": "牵线张力均匀，左右差<0.3N",
    "return_action_note": "首次调校完成待试演"
}, token=adjuster_token)
test("提交复核", 200, s, r)
print(f"  状态={s}, 当前状态={r.get('status')}")

print("\n[19] 试演复核-返调")
s, r = req("POST", f"/api/reviewer/adjustments/{adj_id}/review", {
    "smoothness_score": 45,
    "deviation_note": "左肩动作偏差过大",
    "review_opinion": "肩部动作不协调，需返调",
    "is_passed": 0
}, token=reviewer_token)
test("试演返调", 200, s, r)
print(f"  状态={s}, 结果状态={r.get('status')}, 通过标记={r.get('is_passed')}")

print("\n[20] 返调后重新提交复核")
s, r = req("POST", f"/api/adjuster/adjustments/{adj_id}/joints", {
    "joint_name": "腕", "before_value": "灵活度60%", "after_value": "灵活度85%"
}, token=adjuster_token)
s, r = req("POST", f"/api/adjuster/adjustments/{adj_id}/submit-review", {
    "tension_note": "返调后肩部动作改善",
    "return_action_note": "已调整肩部牵线张力"
}, token=adjuster_token)
test("返调后重新提交", 200, s, r)
print(f"  状态={s}, 当前状态={r.get('status')}")

print("\n[21] 二次试演通过")
s, r = req("POST", f"/api/reviewer/adjustments/{adj_id}/review", {
    "smoothness_score": 88,
    "deviation_note": "肩部改善明显",
    "review_opinion": "返调效果良好，通过",
    "is_passed": 1
}, token=reviewer_token)
test("二次试演通过", 200, s, r)
print(f"  状态={s}, 结果状态={r.get('status')}, 分数={r.get('smoothness_score')}")

print("\n[22] 关节异常排行")
s, r = req("GET", "/api/stats/joint-abnormal-rank", token=admin_token)
test("关节异常排行", 200, s, r)
if isinstance(r, list) and r:
    top = r[0]
    print(f"  第一名: {top.get('joint_name')} 卡滞{top.get('stuck_count')}次")

print("\n[23] 调校通过率统计")
s, r = req("GET", "/api/stats/adjustment-pass-rate", token=admin_token)
test("通过率统计", 200, s, r)
print(f"  总数={r.get('total_adjustments')}, 通过={r.get('passed_count')}, 通过率={r.get('pass_rate')}%")

print("\n[24] 系统总览")
s, r = req("GET", "/api/stats/overview", token=admin_token)
test("系统总览", 200, s, r)
print(f"  木偶总数={r.get('total_puppets')}, 调校单总数={r.get('total_adjustments')}")

print("\n[25] 权限拦截测试")
s, r = req("GET", "/api/admin/users", token=adjuster_token)
test("权限拦截", 403, s, r)
print(f"  状态={s}, 拦截成功={s==403}")

# 汇总
print("\n" + "="*60)
print("测试结果汇总")
print("="*60)
pass_count = sum(1 for x in results if x[1] == "✅ PASS")
total = len(results)
for name, status, code, _ in results:
    print(f"  {status} {name}")
print("="*60)
print(f"总计: {pass_count}/{total} 通过 - {'🎉 全部通过' if pass_count == total else '⚠️ 存在失败项'}")
