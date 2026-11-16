"""가상 운영 데이터 생성기. 실제 데이터와 무관하며 seed 로 재현한다."""
import json, csv, random, os
from datetime import datetime, timedelta

random.seed(20261116)
OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)
END = datetime(2026, 11, 16, 9, 0)
START = END - timedelta(days=30)

COMPANY = {"name": "가나다커머스", "note": "예시 데이터용 가상 회사", "domain": "example.com"}
DEPTS = ["플랫폼개발팀", "주문서비스팀", "데이터팀", "고객지원팀", "인프라운영팀"]
PROJECTS = [
    ("PRJ-01", "쇼핑몰 웹", "주문서비스팀"), ("PRJ-02", "주문 API", "주문서비스팀"),
    ("PRJ-03", "결제 연동", "플랫폼개발팀"), ("PRJ-04", "회원 인증", "플랫폼개발팀"),
    ("PRJ-05", "추천 분석", "데이터팀"), ("PRJ-06", "데이터 웨어하우스", "데이터팀"),
    ("PRJ-07", "상담 챗봇", "고객지원팀"), ("PRJ-08", "공통 인프라", "인프라운영팀"),
]
LAST = ["김", "이", "박", "최", "정", "강", "조", "윤", "장", "임", "한", "오"]
FIRST = ["하늘", "도윤", "서연", "지호", "민준", "예린", "시우", "다은", "주원", "채원", "건우", "수아"]
ROLES = ["관리자", "운영자", "운영자", "조회자"]

users = []
for i in range(12):
    dept = DEPTS[i % len(DEPTS)] if i >= 2 else "인프라운영팀"
    users.append({"id": f"U{i+1:02d}", "name": LAST[i] + FIRST[(i * 5) % 12],
                  "email": f"user{i+1:02d}@example.com", "dept": dept,
                  "role": "관리자" if i < 2 else ROLES[i % 4]})
ops = [u for u in users if u["role"] in ("관리자", "운영자")]

CLOUDS = [("AWS", "ap-northeast-2"), ("Azure", "koreacentral"), ("사내 서버", "본사 IDC")]
NETS = {"AWS": "192.0.2.", "Azure": "198.51.100.", "사내 서버": "203.0.113."}  # 문서용 IP 대역
SPECS = [(2, 4), (2, 8), (4, 8), (4, 16), (8, 16), (8, 32), (16, 64)]
KINDS = {"PRJ-01": "web", "PRJ-02": "api", "PRJ-03": "pay", "PRJ-04": "auth",
         "PRJ-05": "ml", "PRJ-06": "dw", "PRJ-07": "bot", "PRJ-08": "infra"}

servers, ipn = [], {k: 10 for k in NETS}
for p, pname, _ in PROJECTS:
    for j in range(random.randint(5, 10)):
        cloud, region = random.choices(CLOUDS, [5, 3, 2])[0]
        cpu, mem = random.choice(SPECS)
        st = random.choices(["실행 중", "중지", "오류"], [88, 9, 3])[0]
        servers.append({"id": f"SV-{len(servers)+1:03d}", "name": f"{KINDS[p]}-{j+1:02d}",
                        "project": p, "cloud": cloud, "region": region,
                        "ip": NETS[cloud] + str(ipn[cloud]), "vcpu": cpu, "memory_gb": mem,
                        "os": random.choice(["Ubuntu 22.04", "Ubuntu 24.04", "Rocky Linux 9", "Windows Server 2022"]),
                        "status": st, "created": (START - timedelta(days=random.randint(30, 700))).strftime("%Y-%m-%d")})
        ipn[cloud] += 1

# 일별 사용률: 서버마다 기본값 + 주말 낮음 + 잡음, 몇 대는 과부하 · 저사용
metrics = []
for s in servers:
    base = random.choice([8, 15, 25, 35, 45, 60, 75])
    s["_base"] = base
    for d in range(30):
        day = START + timedelta(days=d + 1)
        if s["status"] == "중지" and d > 20:
            continue
        wk = 0.7 if day.weekday() >= 5 else 1.0
        cpu = max(1, min(99, base * wk + random.gauss(0, 6)))
        metrics.append({"server": s["id"], "date": day.strftime("%Y-%m-%d"),
                        "cpu_avg": round(cpu, 1), "cpu_max": round(min(100, cpu * random.uniform(1.2, 1.6)), 1),
                        "mem_avg": round(max(5, min(98, base * 0.9 + 15 + random.gauss(0, 5))), 1),
                        "disk_used": round(min(97, 30 + base * 0.5 + d * 0.3 + random.gauss(0, 2)), 1)})

RULES = [("CPU 사용률 90% 이상", "심각"), ("CPU 사용률 80% 이상", "경고"), ("메모리 사용률 90% 이상", "심각"),
         ("디스크 사용률 85% 이상", "경고"), ("응답 시간 3초 이상", "경고"), ("헬스 체크 실패", "심각"),
         ("프로세스 재시작 감지", "정보"), ("인증서 만료 14일 전", "정보")]
alerts = []
hot = sorted(servers, key=lambda s: -s["_base"])[:20]
for i in range(320):
    s = random.choice(hot) if random.random() < 0.7 else random.choice(servers)
    rule, sev = random.choices(RULES, [6, 10, 4, 6, 7, 3, 5, 2])[0]
    t = START + timedelta(minutes=random.randint(0, 30 * 24 * 60))
    alerts.append({"id": "", "time": t, "server": s["id"], "project": s["project"], "rule": rule, "severity": sev})
alerts.sort(key=lambda a: a["time"])
for i, a in enumerate(alerts):
    a["id"] = f"AL-{i+1:04d}"
    a["acknowledged"] = random.random() < (0.95 if a["time"] < END - timedelta(days=2) else 0.5)

# 인시던트: 심각 알림 일부를 묶어 만든다. 상태는 업계 일반 4단계.
PRI_TARGET = {"P1": 4, "P2": 8, "P3": 24, "P4": 72}  # 해결 목표 시간
CAUSES = ["배포 후 설정 누락", "트래픽 급증", "디스크 가득 참", "외부 결제사 지연", "인증서 갱신 누락",
          "메모리 누수", "DB 연결 수 초과", "네트워크 장비 점검 영향", "배치 작업 겹침", "원인 조사 중"]
incidents, used = [], set()
cands = [a for a in alerts if a["severity"] in ("심각", "경고")]
random.shuffle(cands)
for a in cands:
    if len(incidents) >= 42:
        break
    if a["id"] in used:
        continue
    group = [b for b in alerts if b["server"] == a["server"] and abs((b["time"] - a["time"]).total_seconds()) < 3 * 3600
             and b["id"] not in used][:5]
    for b in group:
        used.add(b["id"])
    opened = min(b["time"] for b in group) + timedelta(minutes=random.randint(1, 20))
    pri = random.choices(["P1", "P2", "P3", "P4"], [3, 4, 4, 2] if a["severity"] == "심각" else [0, 2, 5, 5])[0]
    age_h = (END - opened).total_seconds() / 3600
    target = PRI_TARGET[pri]
    took = target * random.choices([0.2, 0.4, 0.6, 0.9, 1.3, 2.0], [3, 4, 4, 3, 2, 1])[0]
    owner = random.choice(ops)
    tl = [{"time": opened, "event": "생성", "by": "시스템"}]
    ack = opened + timedelta(minutes=random.randint(3, 60))
    if ack < END:
        tl.append({"time": ack, "event": "처리 시작", "by": owner["name"]})
    resolved = opened + timedelta(hours=took)
    if resolved < END and age_h > 1:
        state = "해결"
        tl.append({"time": resolved, "event": "해결", "by": owner["name"]})
        closed = resolved + timedelta(hours=random.randint(4, 96))
        if closed < END:
            state = "종료"
            tl.append({"time": closed, "event": "종료", "by": random.choice(ops)["name"]})
    else:
        state = "처리 중" if ack < END else "신규"
        resolved = None
    srv = next(s for s in servers if s["id"] == a["server"])
    incidents.append({"id": "", "title": f"{srv['name']} {a['rule']}", "priority": pri, "state": state,
                      "server": srv["id"], "project": srv["project"], "assignee": owner["id"] if state != "신규" else None,
                      "opened": opened, "resolved": resolved, "target_hours": target,
                      "within_target": (resolved - opened).total_seconds() / 3600 <= target if resolved else None,
                      "cause": random.choice(CAUSES) if resolved else None,
                      "alerts": [b["id"] for b in group], "timeline": tl})
incidents.sort(key=lambda x: x["opened"])
# 직전 네 건은 처리 중으로 둔다(처리 큐 시연용)
for x in incidents[-6:-2]:
    if x["state"] in ("해결", "종료"):
        x.update(state="처리 중", resolved=None, within_target=None, cause=None,
                 timeline=[t for t in x["timeline"] if t["event"] in ("생성", "처리 시작")])
# 그 앞 세 건은 해결(종료 전)로 둔다
for x in incidents[-9:-6]:
    if x["state"] == "종료":
        x["state"] = "해결"
        x["timeline"] = [t for t in x["timeline"] if t["event"] != "종료"]
# 최근 두 건은 아직 아무도 잡지 않은 신규로 둔다
for x, mins in zip(incidents[-2:], (25, 8)):
    x["opened"] = END - timedelta(minutes=mins)
    x.update(state="신규", assignee=None, resolved=None, within_target=None, cause=None,
             timeline=[{"time": x["opened"], "event": "생성", "by": "시스템"}])
for i, x in enumerate(incidents):
    x["id"] = f"INC-{i+1:03d}"

# 월별 비용(원): 서버 사양 기반 + 스토리지 · 네트워크
UNIT = {"AWS": 52000, "Azure": 48000, "사내 서버": 21000}  # vCPU 당 월 비용
costs = []
for m in range(6):
    month = (datetime(2026, 6, 1) + timedelta(days=31 * m)).strftime("%Y-%m")
    for p, _, _ in PROJECTS:
        for cloud, _ in CLOUDS:
            ss = [s for s in servers if s["project"] == p and s["cloud"] == cloud]
            if not ss:
                continue
            comp = sum(s["vcpu"] * UNIT[cloud] for s in ss) * random.uniform(0.92, 1.08) * (1 + 0.02 * m)
            costs.append({"month": month, "project": p, "cloud": cloud,
                          "compute": round(comp, -3), "storage": round(comp * random.uniform(0.08, 0.18), -3),
                          "network": round(comp * random.uniform(0.03, 0.09), -3)})

def ser(o):
    if isinstance(o, datetime):
        return o.strftime("%Y-%m-%d %H:%M")
    raise TypeError
for s in servers:
    s.pop("_base")
for a in alerts:
    a["time"] = ser(a["time"])
data = {"company": COMPANY, "departments": DEPTS,
        "projects": [{"id": p, "name": n, "dept": d} for p, n, d in PROJECTS],
        "users": users, "servers": servers, "metrics_daily": metrics,
        "alerts": alerts, "incidents": incidents, "costs_monthly": costs}
with open(os.path.join(OUT, "all.json"), "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=1, default=ser)
for k in ("users", "servers", "metrics_daily", "alerts", "costs_monthly"):
    rows = data[k]
    with open(os.path.join(OUT, f"{k}.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
inc_rows = [{**{k: v for k, v in x.items() if k not in ("timeline", "alerts")},
             "alerts": " ".join(x["alerts"])} for x in incidents]
with open(os.path.join(OUT, "incidents.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(inc_rows[0].keys()))
    w.writeheader()
    for r in inc_rows:
        w.writerow({k: ser(v) if isinstance(v, datetime) else v for k, v in r.items()})
print({k: len(v) for k, v in data.items() if isinstance(v, list)})
