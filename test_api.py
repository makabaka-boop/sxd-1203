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
print("木偶管理系统 API 测试")
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

# 5. 查询角色类型
print("\n[5] 管理员查角色类型")
s, r = req("GET", "/api/admin/role-types", token=admin_token)
test("查角色类型", 200, s, r)
print(f"  状态={s}, 数量={len(r) if isinstance(r, list) else 0}")

# 6. 查询关节组
print("\n[6] 管理员查关节组")
s, r = req("GET", "/api/admin/joint-groups", token=admin_token)
test("查关节组", 200, s, r)
print(f"  状态={s}, 数量={len(r) if isinstance(r, list) else 0}")

# 7. 查询台位
print("\n[7] 管理员查台位")
s, r = req("GET", "/api/admin/workbenches", token=admin_token)
test("查台位", 200, s, r)
print(f"  状态={s}, 数量={len(r) if isinstance(r, list) else 0}")

# 8. 入台操作
print("\n[8] 调校员入台")
s, r = req("POST", "/api/adjuster/adjustments/enter", {
    "puppet_id": 1, "workbench_id": 1
}, token=adjuster_token)
test("入台操作", 200, s, r)
adj_id = r.get("id") if s == 200 else None
print(f"  状态={s}, 调校单ID={adj_id}, 当前状态={r.get('status')}")

# 9. 重复入台检查
print("\n[9] 测试并放入台（应拒绝）")
s, r = req("POST", "/api/adjuster/adjustments/enter", {
    "puppet_id": 1, "workbench_id": 2
}, token=adjuster_token)
test("并放入台被拒", 400, s, r)
print(f"  状态={s}, 原因={str(r.get('detail',''))[:40]}")

# 10. 添加关节调校
print("\n[10] 添加关节调校记录")
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

# 11. 提交复核
print("\n[11] 提交复核")
s, r = req("POST", f"/api/adjuster/adjustments/{adj_id}/submit-review", {
    "tension_note": "牵线张力均匀，左右差<0.3N",
    "return_action_note": "首次调校完成待试演"
}, token=adjuster_token)
test("提交复核", 200, s, r)
print(f"  状态={s}, 当前状态={r.get('status')}, 提交时间={r.get('submit_review_time') is not None}")

# 12. 待试演清单
print("\n[12] 复核员查待试演")
s, r = req("GET", "/api/reviewer/adjustments/pending", token=reviewer_token)
test("待试演查询", 200, s, r)
print(f"  状态={s}, 待试演数={len(r) if isinstance(r, list) else 0}")

# 13. 关节异常排行
print("\n[13] 关节异常排行")
s, r = req("GET", "/api/stats/joint-abnormal-rank", token=admin_token)
test("关节异常排行", 200, s, r)
if isinstance(r, list) and r:
    top = r[0]
    print(f"  状态={s}, 第一名: {top.get('joint_name')} 卡滞{top.get('stuck_count')}次")
else:
    print(f"  状态={s}, 无数据")

# 14. 待试演清单接口
print("\n[14] 待试演清单接口")
s, r = req("GET", "/api/stats/pending-review-list", token=admin_token)
test("待试演清单", 200, s, r)
print(f"  状态={s}, 数量={len(r) if isinstance(r, list) else 0}")

# 15. 试演通过
print("\n[15] 试演复核-通过")
s, r = req("POST", f"/api/reviewer/adjustments/{adj_id}/review", {
    "smoothness_score": 92,
    "deviation_note": "左手微延迟0.1s可接受",
    "review_opinion": "整体流畅通过",
    "is_passed": 1
}, token=reviewer_token)
test("试演通过", 200, s, r)
print(f"  状态={s}, 结果状态={r.get('status')}, 通过标记={r.get('is_passed')}, 分数={r.get('smoothness_score')}")

# 16. 调校通过率
print("\n[16] 调校通过率统计")
s, r = req("GET", "/api/stats/adjustment-pass-rate", token=admin_token)
test("通过率统计", 200, s, r)
print(f"  状态={s}, 总数={r.get('total_adjustments')}, 通过={r.get('passed_count')}, 通过率={r.get('pass_rate')}%")

# 17. 系统总览
print("\n[17] 系统总览")
s, r = req("GET", "/api/stats/overview", token=admin_token)
test("系统总览", 200, s, r)
if isinstance(r, dict):
    print(f"  木偶总数={r.get('total_puppets')}, 调校单总数={r.get('total_adjustments')}")
    print(f"  状态分布={r.get('status_distribution')}")

# 18. 系统预警
print("\n[18] 系统预警")
s, r = req("GET", "/api/stats/warnings", token=admin_token, query={"workbench_threshold": 1})
test("系统预警", 200, s, r)
warn_types = set()
if isinstance(r, list):
    for w in r:
        warn_types.add(w.get("warning_type"))
print(f"  状态={s}, 预警数={len(r) if isinstance(r, list) else 0}, 类型={list(warn_types)[:3]}")

# 19. 综合查询
print("\n[19] 综合条件查询调校单")
s, r = req("GET", "/api/stats/adjustments", token=admin_token, query={"status": "通过"})
test("综合查询", 200, s, r)
print(f"  状态={s}, 查询结果={len(r) if isinstance(r, list) else 0}条通过记录")

# 20. 权限测试 - 非管理员访问管理员API
print("\n[20] 权限测试 - 调校员访问管理员API")
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
