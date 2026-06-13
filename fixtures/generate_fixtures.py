#!/usr/bin/env python3
"""Deterministic fixture generator for THOL.

Everything is derived from a fixed seed so the whole battery is reproducible
byte-for-byte. Workspace inputs go to fixtures/out/<name>/ ; ground truth the
agent must never see goes to fixtures/truth/.
"""
import csv
import hashlib
import json
import random
import shutil
from pathlib import Path

SEED = 42
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
TRUTH = HERE / "truth"

WORDS = (
    "platform service request release pipeline window vendor policy review "
    "metric account region quarter audit access incident change control "
    "report schedule baseline margin forecast inventory channel partner "
    "delivery customer support upgrade rollout backlog roadmap capacity "
    "threshold latency budget renewal contract compliance training onboarding"
).split()


def para(rng, n_sentences=5):
    out = []
    for _ in range(n_sentences):
        n = rng.randint(8, 16)
        s = " ".join(rng.choice(WORDS) for _ in range(n))
        out.append(s[0].upper() + s[1:] + ".")
    return " ".join(out)


WORDS_FR = (
    "plateforme service requête déploiement pipeline fenêtre prestataire "
    "politique révision métrique compte région trimestre audit accès incident "
    "changement contrôle rapport calendrier référence marge prévision stock "
    "canal partenaire livraison client assistance mise rollout arriéré feuille "
    "capacité seuil latence budget renouvellement contrat conformité formation "
    "intégration sécurité hébergement astreinte sinistre disponibilité"
).split()


def para_fr(rng, n_sentences=5):
    out = []
    for _ in range(n_sentences):
        n = rng.randint(8, 16)
        s = " ".join(rng.choice(WORDS_FR) for _ in range(n))
        out.append(s[0].upper() + s[1:] + ".")
    return " ".join(out)


# Chinese (Han) word pool — no inter-word spaces, the script the multi-language
# chain (#8 estimate / #9 UTF-8 slicing / #10 BM25 bigrams) was hardened for.
WORDS_ZH = (
    "平台 服务 请求 发布 流水线 窗口 供应商 政策 审查 指标 账户 区域 季度 审计 "
    "访问 事件 变更 控制 报告 计划 基线 利润 预测 库存 渠道 合作 交付 客户 支持 "
    "升级 推出 积压 路线 容量 阈值 延迟 预算 续订 合同 合规 培训 入职 安全 托管 "
    "监控 性能 可用性 灾难 恢复 责任"
).split()


def para_zh(rng, n_sentences=5):
    # Han text runs together with no spaces — split_whitespace yields one giant
    # token, which is exactly what the tokeniser/BM25 fixes target.
    out = []
    for _ in range(n_sentences):
        n = rng.randint(8, 16)
        out.append("".join(rng.choice(WORDS_ZH) for _ in range(n)) + "。")
    return "".join(out)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hex(rng, n):
    return "".join(rng.choice("0123456789abcdef") for _ in range(n))


def _uuid(rng):
    return (f"{_hex(rng, 8)}-{_hex(rng, 4)}-4{_hex(rng, 3)}-"
            f"{rng.choice('89ab')}{_hex(rng, 3)}-{_hex(rng, 12)}")


# ---------------------------------------------------------------- seo-site
def gen_seo_site():
    rng = random.Random(SEED)
    root = OUT / "seo-site" / "site"

    def page(rel, title, desc, h1s, body_words, imgs_alt=True, extra_head="",
             links=()):
        head = [f"<title>{title}</title>"]
        if desc is not None:
            head.append(f'<meta name="description" content="{desc}">')
        head.append(extra_head)
        body = []
        for h in h1s:
            body.append(f"<h1>{h}</h1>")
        body.append(f"<p>{' '.join(rng.choice(WORDS) for _ in range(body_words))}</p>")
        for i in range(3 if rel == "index.html" else 1):
            alt = '' if not imgs_alt else f' alt="photo {i}"'
            body.append(f'<img src="/img/{rel.replace("/", "-")}-{i}.jpg"{alt}>')
        for href, label in links:
            body.append(f'<a href="{href}">{label}</a>')
        nav = " ".join(
            f'<a href="/{p}">{p.split("/")[-1].split(".")[0]}</a>'
            for p in ["index.html", "about.html", "contact.html", "legal.html"]
        )
        write(root / rel,
              "<!doctype html><html><head>\n" + "\n".join(filter(None, head)) +
              f"\n</head><body><nav>{nav}</nav>\n" + "\n".join(body) +
              "\n</body></html>\n")

    page("index.html", "Acme Outdoor Gear — Home", "Quality outdoor gear.",
         ["Welcome to Acme"], 180, imgs_alt=False)
    page("about.html", "About Acme", "Who we are.",
         ["Our story", "Our team", "Our values"], 220)
    page("contact.html", "Contact Acme", None, ["Contact us"], 120)
    page("legal.html",
         "Acme Outdoor Gear legal notices, terms of service, privacy policy, "
         "cookie policy, refund conditions and general information page",
         "Legal information.", ["Legal"], 150)
    page("products/p1.html", "Trail Backpack 40L", "Our best backpack.",
         ["Trail Backpack 40L"], 200,
         extra_head='<meta name="robots" content="noindex">')
    page("products/p2.html", "Storm Jacket", None, ["Storm Jacket"], 210)
    page("products/p3.html", "Trail Backpack 40L", "A lighter pack.",
         ["Summit Pack 28L"], 190)
    page("products/p4.html", "Camp Stove X2", "Compact stove.", [], 180)
    page("products/p5.html", "Titanium Mug", "Lightweight mug.",
         ["Titanium Mug"], 28)
    page("blog/b1.html", "How to pack light", None, ["How to pack light"], 320)
    page("blog/b2.html", "Choosing a tent", "Tent buying guide.",
         ["Choosing a tent"], 300,
         links=[("/blog/missing-page.html", "our winter guide")])
    page("blog/b3.html", "Layering basics", "Layering guide.",
         ["Layering basics"], 280,
         extra_head='<link rel="canonical" href="https://other-domain.example/layering">')

    issues = [
        {"id": "missing-meta-desc-p2", "file": "p2.html", "kws": ["meta description", "description"]},
        {"id": "missing-meta-desc-b1", "file": "b1.html", "kws": ["meta description", "description"]},
        {"id": "missing-meta-desc-contact", "file": "contact.html", "kws": ["meta description", "description"]},
        {"id": "dup-title-p1", "file": "p1.html", "kws": ["duplicat", "same title", "identical"]},
        {"id": "dup-title-p3", "file": "p3.html", "kws": ["duplicat", "same title", "identical"]},
        {"id": "multi-h1-about", "file": "about.html", "kws": ["h1"]},
        {"id": "no-h1-p4", "file": "p4.html", "kws": ["h1"]},
        {"id": "img-alt-index", "file": "index.html", "kws": ["alt"]},
        {"id": "broken-link-b2", "file": "b2.html", "kws": ["broken", "404", "missing-page", "dead"]},
        {"id": "noindex-p1", "file": "p1.html", "kws": ["noindex"]},
        {"id": "bad-canonical-b3", "file": "b3.html", "kws": ["canonical"]},
        {"id": "long-title-legal", "file": "legal.html", "kws": ["long", "length"]},
        {"id": "thin-content-p5", "file": "p5.html", "kws": ["thin", "short", "word count", "little content"]},
    ]
    write(TRUTH / "seo-audit.json", json.dumps({"issues": issues}, indent=1))


# -------------------------------------------------------------- access-log
def gen_access_log():
    rng = random.Random(SEED + 1)
    ips = [f"198.51.100.{i}" for i in range(1, 40)] + \
          [f"192.0.2.{i}" for i in range(1, 40)]
    top_ip = "203.0.113.7"
    paths = ["/", "/products", "/products/42", "/api/search", "/api/cart",
             "/api/checkout", "/blog", "/login", "/static/app.js",
             "/static/site.css"]
    agents = ["Mozilla/5.0", "curl/8.5", "Googlebot/2.1"]
    lines, n5xx = [], 0

    def line(hh, mm, ss, ip, path, code, size):
        return (f'{ip} - - [01/May/2026:{hh:02d}:{mm:02d}:{ss:02d} +0000] '
                f'"GET {path} HTTP/1.1" {code} {size} "-" "{rng.choice(agents)}"')

    for i in range(4500):
        hh = rng.randint(0, 23)
        ip = top_ip if rng.random() < 0.09 else rng.choice(ips)
        code = rng.choice([200] * 88 + [301, 404] * 5 + [500, 503])
        if code >= 500:
            n5xx += 1
        lines.append(line(hh, rng.randint(0, 59), rng.randint(0, 59),
                          ip, rng.choice(paths), code, rng.randint(180, 24000)))
    # the spike: /api/checkout 5xx burst inside hour 14
    for i in range(420):
        code = 500 if rng.random() < 0.8 else 502
        n5xx += 1
        ip = top_ip if rng.random() < 0.09 else rng.choice(ips)
        lines.append(line(14, rng.randint(0, 59), rng.randint(0, 59),
                          ip, "/api/checkout", code, rng.randint(180, 900)))
    # a few extra requests from top_ip to make it unambiguous
    for i in range(120):
        lines.append(line(rng.randint(0, 23), rng.randint(0, 59),
                          rng.randint(0, 59), top_ip, rng.choice(paths),
                          200, rng.randint(180, 24000)))
    rng.shuffle(lines)
    write(OUT / "access-log" / "access.log", "\n".join(lines) + "\n")
    top_count = sum(1 for l in lines if l.startswith(top_ip + " "))
    write(TRUTH / "log-forensics.json", json.dumps({
        "count_5xx": n5xx, "top_ip": top_ip, "top_ip_count": top_count,
        "spike_path": "/api/checkout", "spike_hour": 14}, indent=1))


# --------------------------------------------------------------- sales-csv
def gen_sales_csv():
    rng = random.Random(SEED + 2)
    regions = ["North America", "Europe", "APAC", "LATAM"]
    rweight = [0.38, 0.30, 0.22, 0.10]          # NA clearly first
    products = ["Falcon", "Heron", "Kestrel", "Osprey", "Swift"]
    prices = {"Falcon": 129.0, "Heron": 89.0, "Kestrel": 215.0,
              "Osprey": 49.0, "Swift": 159.0}
    months = [(m, 28) for m in range(1, 13)]
    rows = []
    for i in range(2000):
        m, dmax = months[rng.choices(range(12),
                                     weights=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.2, 1])[0]]
        d = rng.randint(1, dmax)
        region = rng.choices(regions, weights=rweight)[0]
        product = rng.choice(products)
        units = rng.randint(1, 60)
        rows.append({"order_id": f"O{i:05d}",
                     "date": f"2025-{m:02d}-{d:02d}", "region": region,
                     "product": product, "units": units,
                     "unit_price": f"{prices[product]:.2f}"})
    p = OUT / "sales-csv" / "sales.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    rev_region, units_product, rev_month = {}, {}, {}
    big_orders = 0
    for r in rows:
        rev = int(r["units"]) * float(r["unit_price"])
        rev_region[r["region"]] = rev_region.get(r["region"], 0) + rev
        units_product[r["product"]] = units_product.get(r["product"], 0) + int(r["units"])
        mon = r["date"][:7]
        rev_month[mon] = rev_month.get(mon, 0) + rev
        if rev > 5000:
            big_orders += 1
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November",
                   "December"]
    best_month = max(rev_month, key=rev_month.get)
    write(TRUTH / "data-analysis.json", json.dumps({
        "top_region": max(rev_region, key=rev_region.get),
        "top_product_units": max(units_product, key=units_product.get),
        "best_month_num": best_month,
        "best_month_name": month_names[int(best_month[5:]) - 1],
        "orders_over_5000": big_orders,
        "totals": {"revenue_by_region": rev_region,
                   "units_by_product": units_product,
                   "revenue_by_month": rev_month}}, indent=1))
    # report-pdf shares the same workspace input + truth
    write(TRUTH / "report-pdf.json", json.dumps({
        "top_region": max(rev_region, key=rev_region.get),
        "top_product_units": max(units_product, key=units_product.get),
        "best_month_name": month_names[int(best_month[5:]) - 1]}, indent=1))


# ----------------------------------------------------------------- longdoc
def gen_longdoc():
    rng = random.Random(SEED + 3)
    facts = {
        "retention": "Customer event data is retained for exactly 13 months, "
                     "after which it is irreversibly purged.",
        "codename": "The 2026 replatforming effort is referred to internally "
                    "by the codename Heliotrope.",
        "sla": "The public commitment is a monthly uptime SLA of 99.95% for "
               "the API tier.",
        "sev0": "A SEV-0 incident must be acknowledged by the on-call lead "
                "within 15 minutes of the first page.",
        "dr": "The designated disaster-recovery region is Lisbon, with a "
              "recovery time objective of four hours.",
    }
    sections = ["Purpose and scope", "Service tiers", "Data lifecycle",
                "Incident management", "Vendor management",
                "Business continuity", "Change management", "Access control",
                "Capacity planning", "Reporting calendar", "Appendix A",
                "Appendix B"]
    plant = {2: facts["retention"], 1: facts["sla"], 3: facts["sev0"],
             5: facts["dr"], 6: facts["codename"]}
    doc = ["# Meridian Operations Handbook (rev. 14)\n"]
    for i, s in enumerate(sections):
        doc.append(f"\n## {i + 1}. {s}\n")
        for j in range(rng.randint(6, 9)):
            doc.append(para(rng) + "\n")
            if i in plant and j == 3:
                doc.append(plant[i] + "\n")
    write(OUT / "longdoc" / "handbook.md", "\n".join(doc))
    write(TRUTH / "doc-digest.json", json.dumps({"answers": {
        "q1_retention": ["13 month", "13-month", "13 months"],
        "q2_codename": ["heliotrope"],
        "q3_sla": ["99.95"],
        "q4_sev0_minutes": ["15 minute", "15-minute", "15 min", "within 15"],
        "q5_dr_region": ["lisbon"]}}, indent=1))


# -------------------------------------------------------------- longdoc-fr
# French/accented variant of gen_longdoc — exercises the markdown compactor,
# disclose footer and stash recall on non-ASCII (UTF-8 multi-byte) prose.
# Same structure/seed family so it is a clean A/B against the EN doc-digest;
# needles deliberately include accents (Héliotrope) and a FR decimal comma
# (99,95 %) to stress lowercasing and exact-value recall on non-EN content.
def gen_longdoc_fr():
    rng = random.Random(SEED + 30)
    facts = {
        "retention": "Les données d'événements client sont conservées pendant "
                     "exactement treize mois, après quoi elles sont purgées "
                     "de manière irréversible.",
        "codename": "L'effort de replateformisation de 2026 est désigné en "
                    "interne par le nom de code Héliotrope.",
        "sla": "L'engagement public est un SLA de disponibilité mensuelle de "
               "99,95 % pour le palier API.",
        "sev0": "Un incident SEV-0 doit être acquitté par le responsable "
                "d'astreinte dans les quinze minutes suivant la première alerte.",
        "dr": "La région de reprise après sinistre désignée est Lisbonne, avec "
              "un objectif de temps de reprise de quatre heures.",
    }
    sections = ["Objet et portée", "Paliers de service", "Cycle de vie des données",
                "Gestion des incidents", "Gestion des prestataires",
                "Continuité d'activité", "Gestion du changement",
                "Contrôle des accès", "Planification de capacité",
                "Calendrier de reporting", "Annexe A", "Annexe B"]
    plant = {2: facts["retention"], 1: facts["sla"], 3: facts["sev0"],
             5: facts["dr"], 6: facts["codename"]}
    doc = ["# Manuel d'exploitation Meridian (rév. 14)\n"]
    for i, s in enumerate(sections):
        doc.append(f"\n## {i + 1}. {s}\n")
        for j in range(rng.randint(6, 9)):
            doc.append(para_fr(rng) + "\n")
            if i in plant and j == 3:
                doc.append(plant[i] + "\n")
    write(OUT / "longdoc-fr" / "manuel.md", "\n".join(doc))
    write(TRUTH / "doc-digest-fr.json", json.dumps({"answers": {
        "q1_retention": ["treize mois", "13 mois"],
        "q2_codename": ["héliotrope", "heliotrope"],
        "q3_sla": ["99,95", "99.95"],
        "q4_sev0_minutes": ["quinze minute", "15 minute", "15 min"],
        "q5_dr_region": ["lisbonne"]}}, indent=1, ensure_ascii=False))


# -------------------------------------------------------------- longdoc-zh
# Chinese (Han) variant of gen_longdoc — the end-to-end multi-language guard.
# Han is the worst case for every stage Tokenade was hardened for in the
# #8→#10 series: no inter-word spaces (estimate() & BM25 split_whitespace
# both break), 3-byte codepoints (UTF-8 slicing panics), and a script with no
# case (lowercasing no-ops). The doc is long enough (~thousands of ideographs
# at ~1 token/char) to clear the REAL 5 000-token disclose threshold — the
# exact regime #8 fixed, where a 5k-token blob estimated ~1.1k and was never
# stashed. Needles keep a Latin codename (Héliotrope) and an ASCII decimal
# (99.95) to stress mixed-script recall; truth keys accept Han, ASCII and
# romanised answers since the agent may reply in any of them.
def gen_longdoc_zh():
    rng = random.Random(SEED + 31)
    facts = {
        "retention": "客户事件数据的保留期限为十三个月，之后将被不可逆地清除。",
        "codename": "二零二六年的重新平台化项目内部代号为 Héliotrope。",
        "sla": "公开承诺的 API 层级月度可用性 SLA 为 99.95%。",
        "sev0": "SEV-0 级别事件必须由值班负责人在首次告警后十五分钟内确认。",
        "dr": "指定的灾难恢复区域为里斯本，恢复时间目标为四小时。",
    }
    sections = ["目的与范围", "服务层级", "数据生命周期", "事件管理",
                "供应商管理", "业务连续性", "变更管理", "访问控制",
                "容量规划", "报告日程", "附录甲", "附录乙"]
    plant = {2: facts["retention"], 1: facts["sla"], 3: facts["sev0"],
             5: facts["dr"], 6: facts["codename"]}
    doc = ["# Meridian 运维手册（修订版 14）\n"]
    for i, s in enumerate(sections):
        doc.append(f"\n## {i + 1}. {s}\n")
        for j in range(rng.randint(6, 9)):
            doc.append(para_zh(rng) + "\n")
            if i in plant and j == 3:
                doc.append(plant[i] + "\n")
    write(OUT / "longdoc-zh" / "manuel.md", "\n".join(doc))
    write(TRUTH / "doc-digest-zh.json", json.dumps({"answers": {
        "q1_retention": ["十三个月", "13个月", "13 个月", "thirteen month"],
        "q2_codename": ["héliotrope", "heliotrope"],
        "q3_sla": ["99.95", "99,95"],
        "q4_sev0_minutes": ["十五分钟", "15分钟", "15 分钟", "15 min",
                            "fifteen minute"],
        "q5_dr_region": ["里斯本", "lisbon", "lisbonne"]}},
        indent=1, ensure_ascii=False))


# ------------------------------------------------------------------ ci-log
def gen_ci_log():
    rng = random.Random(SEED + 4)
    L = ["$ ci-runner --job test --python 3.12",
         "Collecting dependencies from requirements.txt"]
    for pkg in ("requests urllib3 certifi idna charset-normalizer flask "
                "werkzeug jinja2 itsdangerous click sqlalchemy alembic "
                "greenlet stripe pydantic pydantic-core annotated-types "
                "pytest pluggy iniconfig coverage").split():
        L.append(f"  Downloading {pkg}-{rng.randint(1,9)}.{rng.randint(0,20)}."
                 f"{rng.randint(0,9)}-py3-none-any.whl ({rng.randint(20,900)} kB)")
        L.append(f"  Installing collected package: {pkg} ... done")
    L.append("WARNING: pip is being invoked by an old script wrapper.")
    # red herring 1: flaky network error that succeeds on retry
    L += ["ERROR: connection to mirror.internal timed out (attempt 1/3)",
          "Retrying in 2s...",
          "ERROR: connection to mirror.internal timed out (attempt 2/3)",
          "Retrying in 4s...",
          "Resolved mirror.internal — dependency cache warmed (attempt 3/3 OK)"]
    L.append("$ python -m pytest -q tests/")
    files = ["tests/test_auth.py", "tests/test_cart.py", "tests/test_catalog.py",
             "tests/test_payments.py", "tests/test_refunds.py",
             "tests/test_search.py", "tests/test_shipping.py"]
    for f in files:
        for k in range(rng.randint(12, 30)):
            # red herring 2: deprecation warnings that name error-ish files
            if rng.random() < 0.08:
                L.append(f"{f}::test_{k:03d} PASSED  "
                         "(DeprecationWarning: error_handling.legacy_hook is "
                         "deprecated, see docs/error-handling.md)")
            else:
                L.append(f"{f}::test_{k:03d} PASSED")
    L += ["tests/test_refunds.py::test_refund_idempotent FAILED",
          "",
          "=================================== FAILURES ===================================",
          "____________________________ test_refund_idempotent ____________________________",
          "    def test_refund_idempotent():",
          "        first = apply_refund(order, key='abc')",
          ">       second = apply_refund(order, key='abc')",
          '  File "src/payments/refund.py", line 142, in apply_refund',
          "    prior = _ledger[req['idempotency_key']]",
          "KeyError: 'idempotency_key'",
          "=========================== short test summary info ============================",
          "FAILED tests/test_refunds.py::test_refund_idempotent - KeyError: 'idempotency_key'",
          "1 failed, 161 passed, 14 warnings in 41.32s",
          "$ exit 1"]
    write(OUT / "ci-log" / "build.log", "\n".join(L) + "\n")
    write(TRUTH / "code-debug-cilog.json", json.dumps({
        "markers_required": ["refund.py", "idempotency_key"],
        "herrings": ["mirror.internal", "error-handling.md"]}, indent=1))


# --------------------------------------------------------------- release-log
def gen_release_log():
    """A long, noisy CI/CD release log. The scored facts are rare, UNIQUE,
    verbatim needles (the pushed image digest for one service, a resolved dep
    version, the trace id of the single 503, the port a health check finally
    passed on, the commit) buried among thousands of near-duplicate noise
    lines (varying heartbeats, layer exports, 200-OK smoke requests, dep
    fetches). This probes *verbatim fidelity under compression* — orthogonal
    to log-forensics (statistical aggregation) and code-debug-cilog (root-
    cause reasoning), both of which survive losing individual lines. The four
    near-identical `pushed <svc>@sha256:<digest>` lines are a deliberate trap
    for fuzzy de-duplication: merging them destroys the checkout answer."""
    rng = random.Random(SEED + 6)
    t = [0]
    L = []

    def stamp():
        sec = t[0]
        return (f"2026-06-09T{14 + sec // 3600:02d}:{(sec // 60) % 60:02d}:"
                f"{sec % 60:02d}.{(sec * 37) % 1000:03d}Z")

    def log(level, comp, msg):
        L.append(f"{stamp()} {level:<5} [{comp}] {msg}")
        t[0] += 1

    def heartbeats(n):
        for _ in range(n):
            log("DEBUG", "orchestrator",
                f"heartbeat ok queue={rng.randint(0, 3)} "
                f"inflight={rng.randint(0, 5)} leader=node-{rng.randint(1, 5)}")

    build_no = rng.randint(4000, 9999)
    commit = _hex(rng, 7)
    log("INFO", "pipeline",
        f"=== release pipeline #{build_no} commit {commit} "
        "ref refs/tags/v2.7.0 runner gha-linux-x64 ===")
    heartbeats(700)

    # --- dependency resolution: ~45 near-identical 'resolved' lines ---
    log("INFO", "resolver", "resolving dependency graph from lockfile")
    deps = ("requests urllib3 certifi idna flask werkzeug jinja2 click "
            "sqlalchemy alembic greenlet pydantic pytest coverage zlib "
            "libffi ncurses readline bzip2 xz sqlite gdbm openldap cyrus-sasl "
            "krb5 libxml2 libxslt curl nghttp2 c-ares libpsl brotli "
            "ca-certificates busybox musl pcre2 oniguruma jansson lz4 "
            "zstd libedit gmp mpfr").split()
    for d in deps:
        log("DEBUG", "resolver",
            f"fetching {d} index from registry.internal/simple/{d}/")
        ver = (f"{rng.randint(1, 9)}.{rng.randint(0, 30)}."
               f"{rng.randint(0, 9)}-r{rng.randint(0, 9)}")
        log("INFO", "resolver", f"resolved {d}=={ver}")
    # the needle dep version, flanked by close decoys
    openssl_ver = "3.2.1-r4"
    log("INFO", "resolver", "resolved openssl-dev==3.2.1-r3")    # decoy
    log("INFO", "resolver", f"resolved openssl=={openssl_ver}")  # NEEDLE
    log("INFO", "resolver", "resolved libressl==3.7.2")          # decoy
    heartbeats(900)

    # --- image builds: 4 services, many near-dup 'exporting layer' lines ---
    services = ["gateway", "checkout", "payments", "catalog"]
    pushed = {}
    for svc in services:
        nlayers = rng.randint(22, 38)
        log("INFO", "buildkit", f"building image {svc}:v2.7.0 ({nlayers} steps)")
        for _ in range(nlayers):
            log("DEBUG", "buildkit",
                f"exporting layer sha256:{_hex(rng, 64)} ({rng.randint(1, 240)} MB)")
        final = _hex(rng, 64)
        pushed[svc] = final
        # all four 'pushed' lines are near-identical except svc + digest.
        log("INFO", "registry",
            f"pushed {svc}:v2.7.0 -> registry.internal/{svc}@sha256:{final}")
        heartbeats(500)

    # --- smoke tests: hundreds of 200s, exactly one 503 ---
    log("INFO", "smoke", "running post-deploy smoke suite (480 checks)")
    paths = ["/health", "/api/cart", "/api/catalog", "/api/login",
             "/api/search", "/api/orders", "/api/profile", "/static/app.js"]
    bad_trace = _uuid(rng)
    inject_at = rng.randint(120, 360)
    for i in range(480):
        if i == inject_at:
            log("WARN", "smoke",
                f"GET /api/checkout 503 4021ms trace={bad_trace} "
                "upstream=payments")
        else:
            # latencies sometimes read '503ms' etc. -> noise for `grep 503`
            ms = rng.choice([7, 9, 11, 14, 22, 503, 200, 118])
            log("DEBUG", "smoke",
                f"GET {rng.choice(paths)} 200 {ms}ms trace={_uuid(rng)}")
    heartbeats(700)

    # --- payments health check: fails on several ports, then passes ---
    payments_port = 8084
    for p in (8080, 8081, 8082, 8083):
        log("WARN", "health",
            f"payments not ready on :{p} (connection refused), retrying")
    log("INFO", "health",
        f"payments healthy on :{payments_port} (200 in 7ms)")  # NEEDLE
    for svc, p in (("gateway", 8080), ("catalog", 8088), ("checkout", 8090)):
        log("INFO", "health",
            f"{svc} healthy on :{p} (200 in {rng.randint(3, 9)}ms)")  # decoys
    heartbeats(300)

    log("INFO", "pipeline",
        f"release #{build_no} complete: 4 images pushed, 480/480 smoke ok "
        "(1 transient 503 retried green), exit 0")

    write(OUT / "release-log" / "release.log", "\n".join(L) + "\n")
    write(TRUTH / "log-needle.json", json.dumps({
        "build_no": build_no,
        "commit": commit,
        "checkout_digest": pushed["checkout"],
        "openssl_version": openssl_ver,
        "bad_trace": bad_trace,
        "payments_port": payments_port,
    }, indent=1))


# ----------------------------------------------------------- log-needle-zh
def gen_log_needle_zh():
    """Chinese (Han) twin of gen_release_log — the ONLY bench that exercises
    the stash + BM25 search path on non-latin text, which is exactly what the
    multi-language recall fix (#10 CJK bigrams) repaired and which the passive
    doc-digest-zh read never touches. The descriptive log messages are Han run
    together with NO inter-word spaces (the worst case for whitespace
    tokenisation); the scored needles stay ASCII (sha256 digests, an openssl
    version, a trace uuid, a port, a commit) — realistic, since a real
    Chinese-locale server log interleaves Han prose with ASCII IDs/hashes. To
    answer, an agent must (a) BM25-recall the right Han noise region once the
    long log is folded/stashed, then (b) grep the verbatim ASCII needle out of
    near-duplicate decoys. Structure / seed-discipline mirror gen_release_log
    so the two stay comparable; only the message language differs."""
    rng = random.Random(SEED + 16)
    t = [0]
    L = []

    def stamp():
        sec = t[0]
        return (f"2026-06-09T{14 + sec // 3600:02d}:{(sec // 60) % 60:02d}:"
                f"{sec % 60:02d}.{(sec * 37) % 1000:03d}Z")

    def log(level, comp, msg):
        L.append(f"{stamp()} {level:<5} [{comp}] {msg}")
        t[0] += 1

    def heartbeats(n):
        for _ in range(n):
            log("DEBUG", "orchestrator",
                f"心跳正常 队列={rng.randint(0, 3)} "
                f"处理中={rng.randint(0, 5)} 主节点=node-{rng.randint(1, 5)}")

    build_no = rng.randint(4000, 9999)
    commit = _hex(rng, 7)
    log("INFO", "pipeline",
        f"=== 发布流水线 #{build_no} 提交 {commit} "
        "引用 refs/tags/v2.7.0 运行器 gha-linux-x64 ===")
    heartbeats(700)

    # --- 依赖解析：约 45 行近乎相同的“已解析”记录 ---
    log("INFO", "resolver", "正在从锁文件解析依赖图")
    deps = ("requests urllib3 certifi idna flask werkzeug jinja2 click "
            "sqlalchemy alembic greenlet pydantic pytest coverage zlib "
            "libffi ncurses readline bzip2 xz sqlite gdbm openldap cyrus-sasl "
            "krb5 libxml2 libxslt curl nghttp2 c-ares libpsl brotli "
            "ca-certificates busybox musl pcre2 oniguruma jansson lz4 "
            "zstd libedit gmp mpfr").split()
    for d in deps:
        log("DEBUG", "resolver",
            f"正在从 registry.internal/simple/{d}/ 获取 {d} 索引")
        ver = (f"{rng.randint(1, 9)}.{rng.randint(0, 30)}."
               f"{rng.randint(0, 9)}-r{rng.randint(0, 9)}")
        log("INFO", "resolver", f"已解析 {d}=={ver}")
    # the needle dep version, flanked by close decoys
    openssl_ver = "3.2.1-r4"
    log("INFO", "resolver", "已解析 openssl-dev==3.2.1-r3")        # decoy
    log("INFO", "resolver", f"已解析 openssl=={openssl_ver}")      # NEEDLE
    log("INFO", "resolver", "已解析 libressl==3.7.2")              # decoy
    heartbeats(900)

    # --- 镜像构建：4 个服务，大量近乎相同的“导出层”记录 ---
    services = ["gateway", "checkout", "payments", "catalog"]
    pushed = {}
    for svc in services:
        nlayers = rng.randint(22, 38)
        log("INFO", "buildkit", f"正在构建镜像 {svc}:v2.7.0（{nlayers} 个步骤）")
        for _ in range(nlayers):
            log("DEBUG", "buildkit",
                f"导出层 sha256:{_hex(rng, 64)}（{rng.randint(1, 240)} MB）")
        final = _hex(rng, 64)
        pushed[svc] = final
        # all four 'pushed' lines are near-identical except svc + digest.
        log("INFO", "registry",
            f"已推送 {svc}:v2.7.0 -> registry.internal/{svc}@sha256:{final}")
        heartbeats(500)

    # --- 冒烟测试：数百次 200，恰好一次 503 ---
    log("INFO", "smoke", "正在运行部署后冒烟测试套件（480 项检查）")
    paths = ["/health", "/api/cart", "/api/catalog", "/api/login",
             "/api/search", "/api/orders", "/api/profile", "/static/app.js"]
    bad_trace = _uuid(rng)
    inject_at = rng.randint(120, 360)
    for i in range(480):
        if i == inject_at:
            log("WARN", "smoke",
                f"GET /api/checkout 503 4021ms trace={bad_trace} "
                "上游=payments")
        else:
            # latencies sometimes read '503ms' etc. -> noise for `grep 503`
            ms = rng.choice([7, 9, 11, 14, 22, 503, 200, 118])
            log("DEBUG", "smoke",
                f"GET {rng.choice(paths)} 200 {ms}ms trace={_uuid(rng)}")
    heartbeats(700)

    # --- payments 健康检查：先在多个端口失败，最终通过 ---
    payments_port = 8084
    for p in (8080, 8081, 8082, 8083):
        log("WARN", "health",
            f"payments 在 :{p} 未就绪（连接被拒绝），正在重试")
    log("INFO", "health",
        f"payments 在 :{payments_port} 健康（7ms 内返回 200）")  # NEEDLE
    for svc, p in (("gateway", 8080), ("catalog", 8088), ("checkout", 8090)):
        log("INFO", "health",
            f"{svc} 在 :{p} 健康（{rng.randint(3, 9)}ms 内返回 200）")  # decoys
    heartbeats(300)

    log("INFO", "pipeline",
        f"发布 #{build_no} 完成：已推送 4 个镜像，冒烟 480/480 通过"
        "（1 次瞬时 503 重试成功），退出码 0")

    write(OUT / "log-needle-zh" / "release.log", "\n".join(L) + "\n")
    write(TRUTH / "log-needle-zh.json", json.dumps({
        "build_no": build_no,
        "commit": commit,
        "checkout_digest": pushed["checkout"],
        "openssl_version": openssl_ver,
        "bad_trace": bad_trace,
        "payments_port": payments_port,
    }, indent=1))


# -------------------------------------------------------------- tinyledger
def gen_tinyledger():
    root = OUT / "tinyledger"
    if root.exists():
        shutil.rmtree(root)
    write(root / "README.md",
          "# tinyledger\n\nA small double-entry ledger library.\n\n"
          "Run the tests with:\n\n    python3 -m unittest discover -s tests -t .\n")
    write(root / "ledger" / "__init__.py",
          "from .money import Money\nfrom .account import Account\n"
          "from .transactions import Transaction, post\n")
    # The planted bug: from_float truncates instead of rounding.
    write(root / "ledger" / "money.py", '''\
"""Money as integer cents. Floats only ever appear at the boundary."""


class Money:
    __slots__ = ("cents",)

    def __init__(self, cents: int):
        if not isinstance(cents, int):
            raise TypeError("cents must be int")
        self.cents = cents

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(int(value * 100))

    def __add__(self, other):
        return Money(self.cents + other.cents)

    def __sub__(self, other):
        return Money(self.cents - other.cents)

    def __neg__(self):
        return Money(-self.cents)

    def __eq__(self, other):
        return isinstance(other, Money) and self.cents == other.cents

    def __repr__(self):
        return f"Money({self.cents})"

    def __str__(self):
        sign = "-" if self.cents < 0 else ""
        return f"{sign}{abs(self.cents) // 100}.{abs(self.cents) % 100:02d}"
''')
    write(root / "ledger" / "account.py", '''\
from .money import Money


class Account:
    def __init__(self, name: str):
        self.name = name
        self.balance = Money(0)

    def credit(self, amount: Money):
        self.balance = self.balance + amount

    def debit(self, amount: Money):
        self.balance = self.balance - amount
''')
    write(root / "ledger" / "transactions.py", '''\
from .money import Money
from .account import Account


class Transaction:
    def __init__(self, debit_account: Account, credit_account: Account,
                 amount: Money, memo: str = ""):
        if amount.cents <= 0:
            raise ValueError("transaction amount must be positive")
        self.debit_account = debit_account
        self.credit_account = credit_account
        self.amount = amount
        self.memo = memo


def post(tx: Transaction):
    tx.debit_account.debit(tx.amount)
    tx.credit_account.credit(tx.amount)
''')
    write(root / "ledger" / "report.py", '''\
from .account import Account


def trial_balance(accounts):
    total = sum(a.balance.cents for a in accounts)
    return {"accounts": {a.name: str(a.balance) for a in accounts},
            "balanced": total == 0}
''')
    write(root / "tests" / "__init__.py", "")
    write(root / "tests" / "test_money.py", '''\
import unittest

from ledger.money import Money


class TestMoney(unittest.TestCase):
    def test_construct(self):
        self.assertEqual(Money(150).cents, 150)

    def test_add_sub(self):
        self.assertEqual(Money(150) + Money(50), Money(200))
        self.assertEqual(Money(150) - Money(50), Money(100))

    def test_str(self):
        self.assertEqual(str(Money(1999)), "19.99")
        self.assertEqual(str(Money(-5)), "-0.05")

    def test_from_float_exact(self):
        self.assertEqual(Money.from_float(12.0), Money(1200))

    def test_from_float_cents(self):
        # 19.99 is not exactly representable in binary floating point;
        # conversion must round to the nearest cent.
        self.assertEqual(Money.from_float(19.99), Money(1999))
        self.assertEqual(Money.from_float(0.29), Money(29))

    def test_from_float_negative(self):
        self.assertEqual(Money.from_float(-19.99), Money(-1999))
''')
    write(root / "tests" / "test_ledger.py", '''\
import unittest

from ledger import Account, Money, Transaction, post
from ledger.report import trial_balance


class TestLedger(unittest.TestCase):
    def test_post_moves_money(self):
        cash, sales = Account("cash"), Account("sales")
        post(Transaction(cash, sales, Money(2500)))
        self.assertEqual(cash.balance, Money(-2500))
        self.assertEqual(sales.balance, Money(2500))

    def test_rejects_non_positive(self):
        a, b = Account("a"), Account("b")
        with self.assertRaises(ValueError):
            Transaction(a, b, Money(0))

    def test_trial_balance(self):
        cash, sales = Account("cash"), Account("sales")
        post(Transaction(cash, sales, Money.from_float(19.99)))
        tb = trial_balance([cash, sales])
        self.assertTrue(tb["balanced"])
        self.assertEqual(tb["accounts"]["sales"], "19.99")
''')
    hashes = {str(p.relative_to(root)): sha(p)
              for p in sorted((root / "tests").rglob("*.py"))}
    write(TRUTH / "code-bugfix-py.json", json.dumps({"test_hashes": hashes},
                                                    indent=1))


# --------------------------------------------------------------- iterledger
def gen_iterledger():
    """A ledger lib with THREE independent bugs in three files, plus a
    verbose unittest suite. Solving it requires several test re-runs — the
    only iterative (non one-shot) task in the corpus. Each re-run reprints
    the suite output; the still-failing tracebacks repeat verbatim until
    fixed. Measures repeated test-output handling over a debug loop."""
    root = OUT / "iterledger"
    if root.exists():
        shutil.rmtree(root)
    write(root / "README.md",
          "# iterledger\n\nA small double-entry ledger library.\n\n"
          "Run the tests with:\n\n"
          "    python3 -m unittest discover -s tests -t .\n")
    write(root / "ledger" / "__init__.py",
          "from .money import Money\nfrom .account import Account\n"
          "from .transactions import Transaction, post\n")
    # BUG 1 (money.py): from_float truncates instead of rounding.
    write(root / "ledger" / "money.py", '''\
"""Money as integer cents. Floats only ever appear at the boundary."""


class Money:
    __slots__ = ("cents",)

    def __init__(self, cents: int):
        if not isinstance(cents, int):
            raise TypeError("cents must be int")
        self.cents = cents

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(int(value * 100))

    def __add__(self, other):
        return Money(self.cents + other.cents)

    def __sub__(self, other):
        return Money(self.cents - other.cents)

    def __neg__(self):
        return Money(-self.cents)

    def __eq__(self, other):
        return isinstance(other, Money) and self.cents == other.cents

    def __repr__(self):
        return f"Money({self.cents})"

    def __str__(self):
        sign = "-" if self.cents < 0 else ""
        return f"{sign}{abs(self.cents) // 100}.{abs(self.cents) % 100:02d}"
''')
    # BUG 2 (account.py): debit credits instead of subtracting.
    write(root / "ledger" / "account.py", '''\
from .money import Money


class Account:
    def __init__(self, name: str):
        self.name = name
        self.balance = Money(0)

    def credit(self, amount: Money):
        self.balance = self.balance + amount

    def debit(self, amount: Money):
        self.balance = self.balance + amount
''')
    write(root / "ledger" / "transactions.py", '''\
from .money import Money
from .account import Account


class Transaction:
    def __init__(self, debit_account: Account, credit_account: Account,
                 amount: Money, memo: str = ""):
        if amount.cents <= 0:
            raise ValueError("transaction amount must be positive")
        self.debit_account = debit_account
        self.credit_account = credit_account
        self.amount = amount
        self.memo = memo


def post(tx: Transaction):
    tx.debit_account.debit(tx.amount)
    tx.credit_account.credit(tx.amount)
''')
    # BUG 3 (report.py): balanced flag inverted.
    write(root / "ledger" / "report.py", '''\
from .account import Account


def trial_balance(accounts):
    total = sum(a.balance.cents for a in accounts)
    return {"accounts": {a.name: str(a.balance) for a in accounts},
            "balanced": total != 0}
''')
    write(root / "tests" / "__init__.py", "")
    write(root / "tests" / "test_money.py", '''\
import unittest

from ledger.money import Money


class TestMoney(unittest.TestCase):
    def test_construct(self):
        self.assertEqual(Money(150).cents, 150)

    def test_add_sub(self):
        self.assertEqual(Money(150) + Money(50), Money(200))
        self.assertEqual(Money(150) - Money(50), Money(100))

    def test_str(self):
        self.assertEqual(str(Money(1999)), "19.99")
        self.assertEqual(str(Money(-5)), "-0.05")

    def test_from_float_exact(self):
        self.assertEqual(Money.from_float(12.0), Money(1200))

    def test_from_float_cents(self):
        # 19.99 is not exactly representable in binary floating point;
        # conversion must round to the nearest cent.
        self.assertEqual(Money.from_float(19.99), Money(1999))
        self.assertEqual(Money.from_float(0.29), Money(29))

    def test_from_float_negative(self):
        self.assertEqual(Money.from_float(-19.99), Money(-1999))
''')
    write(root / "tests" / "test_account.py", '''\
import unittest

from ledger import Account, Money


class TestAccount(unittest.TestCase):
    def test_credit(self):
        a = Account("a")
        a.credit(Money(2500))
        self.assertEqual(a.balance, Money(2500))

    def test_debit(self):
        a = Account("a")
        a.debit(Money(2500))
        self.assertEqual(a.balance, Money(-2500))

    def test_credit_then_debit(self):
        a = Account("a")
        a.credit(Money(5000))
        a.debit(Money(2000))
        self.assertEqual(a.balance, Money(3000))
''')
    write(root / "tests" / "test_ledger.py", '''\
import unittest

from ledger import Account, Money, Transaction, post
from ledger.report import trial_balance


class TestLedger(unittest.TestCase):
    def test_post_moves_money(self):
        cash, sales = Account("cash"), Account("sales")
        post(Transaction(cash, sales, Money(2500)))
        self.assertEqual(cash.balance, Money(-2500))
        self.assertEqual(sales.balance, Money(2500))

    def test_rejects_non_positive(self):
        a, b = Account("a"), Account("b")
        with self.assertRaises(ValueError):
            Transaction(a, b, Money(0))

    def test_trial_balance_balanced(self):
        cash, sales = Account("cash"), Account("sales")
        post(Transaction(cash, sales, Money.from_float(19.99)))
        tb = trial_balance([cash, sales])
        self.assertTrue(tb["balanced"])
        self.assertEqual(tb["accounts"]["sales"], "19.99")

    def test_trial_balance_unbalanced(self):
        cash = Account("cash")
        cash.credit(Money(100))
        tb = trial_balance([cash])
        self.assertFalse(tb["balanced"])
''')
    hashes = {str(p.relative_to(root)): sha(p)
              for p in sorted((root / "tests").rglob("*.py"))}
    write(TRUTH / "code-iterate-tests.json",
          json.dumps({"test_hashes": hashes}, indent=1))


# --------------------------------------------------------------- jsfeature
def gen_jsfeature():
    root = OUT / "jsfeature"
    if root.exists():
        shutil.rmtree(root)
    write(root / "package.json", json.dumps({
        "name": "strutil", "version": "1.2.0", "type": "module",
        "scripts": {"test": "node --test"}}, indent=1))
    write(root / "strutil.js", '''\
export function capitalize(s) {
  return s.length ? s[0].toUpperCase() + s.slice(1) : s;
}

export function truncate(s, n) {
  return s.length <= n ? s : s.slice(0, Math.max(0, n - 1)) + "\\u2026";
}
''')
    write(root / "test" / "strutil.test.js", '''\
import test from "node:test";
import assert from "node:assert/strict";
import { capitalize, truncate } from "../strutil.js";

test("capitalize", () => {
  assert.equal(capitalize("hello"), "Hello");
  assert.equal(capitalize(""), "");
});

test("truncate", () => {
  assert.equal(truncate("hello", 10), "hello");
  assert.equal(truncate("hello world", 6), "hello\\u2026");
});
''')
    write(root / "SPEC.md", '''\
# Feature request: `slugify`

Add to `strutil.js` an exported function:

```js
export function slugify(input, options = {})
```

Behavior (all REQUIRED):

1. Lowercase the input.
2. Remove diacritics: Unicode-normalize (NFD) and strip combining marks, so
   `"Crème Brûlée"` → `"creme-brulee"`.
3. Every maximal run of characters that are not `[a-z0-9]` becomes a single
   hyphen `-`.
4. No leading or trailing hyphens in the result.
5. `options.maxLen` (default `64`): if the slug is longer, cut it at
   `maxLen`, then also remove any trailing hyphen the cut may expose.
6. If the result is empty (e.g. input is only punctuation), return `"n-a"`.
7. Non-string input must throw a `TypeError`.

Existing tests must keep passing (`npm test`).
''')
    write(TRUTH / "jsfeature_hidden.test.js", '''\
import test from "node:test";
import assert from "node:assert/strict";
import { slugify, capitalize, truncate } from "./strutil.js";

test("existing API intact", () => {
  assert.equal(capitalize("abc"), "Abc");
  assert.equal(truncate("hello", 10), "hello");
});

test("basic", () => {
  assert.equal(slugify("Hello, World!"), "hello-world");
});

test("diacritics", () => {
  assert.equal(slugify("Crème Brûlée"), "creme-brulee");
});

test("collapses runs and trims", () => {
  assert.equal(slugify("  --A  &  B--  "), "a-b");
});

test("maxLen with trailing hyphen cleanup", () => {
  assert.equal(slugify("ab ".repeat(40), { maxLen: 5 }), "ab-ab");
  assert.equal(slugify("aaa bbb", { maxLen: 4 }), "aaa");
});

test("default maxLen is 64", () => {
  assert.equal(slugify("a".repeat(80)).length, 64);
});

test("empty becomes n-a", () => {
  assert.equal(slugify("!!!"), "n-a");
});

test("non-string throws TypeError", () => {
  assert.throws(() => slugify(42), TypeError);
});
''')


# ------------------------------------------------------------ migration-py
def gen_migration():
    rng = random.Random(SEED + 5)
    root = OUT / "migration-py"
    if root.exists():
        shutil.rmtree(root)
    write(root / "MIGRATION.md", '''\
# Migration: `legacy_http.fetch` → `net.http_get`

`webtools/legacy_http.py` is deprecated and will be deleted. Every module
under `webtools/app/` must stop importing it.

Replace:

```python
from webtools.legacy_http import fetch
data = fetch(url, 30, 2)            # positional: url, timeout, retries
```

with:

```python
from webtools.net import http_get
data = http_get(url, timeout=30, retries=2)   # keyword-only
```

Semantics are identical. Do not change `webtools/legacy_http.py` or
`webtools/net.py` themselves, and do not change any behavior. The test
suite must keep passing:

    python3 -m unittest discover -s tests -t .
''')
    write(root / "webtools" / "__init__.py", "")
    sim = '''\
def _simulate(url: str) -> dict:
    """Deterministic offline stand-in for a network round-trip."""
    return {"url": url, "status": 200, "body": f"payload:{len(url)}"}
'''
    write(root / "webtools" / "legacy_http.py", sim + '''\


def fetch(url, timeout, retries):
    """DEPRECATED — use webtools.net.http_get instead."""
    assert timeout > 0 and retries >= 0
    return _simulate(url)
''')
    write(root / "webtools" / "net.py", sim + '''\


def http_get(url, *, timeout, retries):
    assert timeout > 0 and retries >= 0
    return _simulate(url)
''')
    write(root / "webtools" / "app" / "__init__.py", "")
    names = ["catalog", "pricing", "stock", "users", "orders", "billing",
             "shipping", "reviews", "search", "alerts", "feeds", "geo"]
    for n in names:
        t, r = rng.choice([10, 20, 30]), rng.choice([0, 1, 2, 3])
        write(root / "webtools" / "app" / f"{n}.py", f'''\
from webtools.legacy_http import fetch

BASE = "https://api.example.com/{n}"


def load_{n}(item_id):
    return fetch(f"{{BASE}}/{{item_id}}", {t}, {r})


def {n}_status():
    return load_{n}("status")["status"]
''')
    write(root / "tests" / "__init__.py", "")
    tests = ["import unittest", ""]
    for n in names:
        tests.append(f"from webtools.app.{n} import load_{n}, {n}_status")
    tests += ["", "", "class TestApp(unittest.TestCase):"]
    for n in names:
        tests += [f"    def test_{n}(self):",
                  f"        d = load_{n}(7)",
                  f"        self.assertEqual(d['status'], 200)",
                  f"        self.assertTrue(d['url'].endswith('/7'))",
                  f"        self.assertEqual({n}_status(), 200)",
                  ""]
    write(root / "tests" / "test_app.py", "\n".join(tests))
    frozen = ["webtools/legacy_http.py", "webtools/net.py",
              "tests/test_app.py"]
    write(TRUTH / "code-migration-py.json", json.dumps({
        "modules": names,
        "frozen_hashes": {f: sha(root / f) for f in frozen}}, indent=1))


# ------------------------------------------------------------- events-csv
# Axis: LOTS of data. ~150k-row CSV — far too large to read into context, so
# every competitor must derive the answers programmatically. Impartial: pure
# aggregation, the verifier only checks numeric correctness, not method.
def gen_events_csv():
    rng = random.Random(SEED + 10)
    countries = ["US", "DE", "JP", "BR", "IN", "FR", "GB", "CA"]
    cweight = [0.34, 0.18, 0.14, 0.10, 0.08, 0.07, 0.05, 0.04]  # US clearly first
    etypes = ["view", "click", "add_to_cart", "purchase", "refund"]
    eweight = [0.50, 0.28, 0.12, 0.08, 0.02]                    # view clearly first
    N = 150_000
    rows = []
    for i in range(N):
        m = rng.choices(range(1, 13),
                        weights=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2.4])[0]  # Dec peak
        d = rng.randint(1, 28)
        country = rng.choices(countries, weights=cweight)[0]
        etype = rng.choices(etypes, weights=eweight)[0]
        # amount in integer cents; only purchases carry meaningful revenue
        amt = rng.randint(500, 80_000) if etype == "purchase" else 0
        rows.append((f"E{i:07d}", f"2025-{m:02d}-{d:02d}",
                     f"U{rng.randint(1, 20000):05d}", country, etype, amt))
    p = OUT / "events-csv" / "events.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "date", "user_id", "country", "event_type",
                    "amount_cents"])
        w.writerows(rows)

    rev_country, ev_count, rev_month = {}, {}, {}
    big = 0
    for _id, date, _u, country, etype, amt in rows:
        ev_count[etype] = ev_count.get(etype, 0) + 1
        if amt:
            rev_country[country] = rev_country.get(country, 0) + amt
            mon = date[:7]
            rev_month[mon] = rev_month.get(mon, 0) + amt
            if amt > 50_000:
                big += 1
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November",
                   "December"]
    best_month = max(rev_month, key=rev_month.get)
    write(TRUTH / "data-bigvolume.json", json.dumps({
        "rows": N,
        "top_country_revenue": max(rev_country, key=rev_country.get),
        "most_frequent_event": max(ev_count, key=ev_count.get),
        "best_revenue_month_name": month_names[int(best_month[5:]) - 1],
        "best_revenue_month_num": best_month,
        "purchases_over_500usd": big}, indent=1))


# -------------------------------------------------------------- html-docs
# Axis: web-style content WITHOUT a live network (reproducible). Three noisy
# real-shaped HTML pages — nav/footer boilerplate, inline <style>, <script>,
# tracking blobs — with a handful of facts buried in the markup. Impartial:
# the facts are plainly in the HTML; any tool (cat, a reader, an HTML→md
# converter) can recover them. The verifier checks only the facts.
def gen_html_docs():
    rng = random.Random(SEED + 11)
    root = OUT / "html-docs" / "site"
    nav = ('<nav><ul>' + ''.join(f'<li><a href="/{x}.html">{x.title()}</a></li>'
           for x in ("index", "about", "product", "pricing")) + '</ul></nav>')
    foot = ('<footer><p>&copy; 2025 Northwind Instruments. '
            'All rights reserved.</p></footer>')
    style = ('<style>body{font-family:sans-serif;margin:0}'
             '.hero{padding:40px}nav ul{list-style:none;display:flex}</style>')
    track = ('<script>window.dataLayer=window.dataLayer||[];'
             'function gtag(){dataLayer.push(arguments)}'
             'gtag("js");gtag("config","UA-00000-1");</script>')

    def page(rel, title, head_extra, body):
        html = (f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width">'
                f'<title>{title}</title>{style}{head_extra}{track}</head>'
                f'<body>{nav}<main class="hero">{body}</main>{foot}</body></html>')
        write(root / rel, html)

    filler = lambda n: f'<p>{para(rng, n)}</p>'
    page("index.html", "Northwind Instruments — Precision Sensors",
         "", f'<h1>Precision Sensors for Industry</h1>{filler(3)}{filler(2)}')
    page("about.html", "About — Northwind Instruments", "",
         f'<h1>About Us</h1>{filler(2)}'
         '<p>Northwind Instruments was founded in <strong>1998</strong> in '
         'Rotterdam. Today the company is led by CEO '
         '<span class="exec">Marisa Feld</span>, who joined in 2016.</p>'
         f'{filler(2)}<p>We employ <b>4,200</b> people across 11 countries.</p>')
    page("product.html", "FluxCore 7 — Northwind Instruments", "",
         '<h1>FluxCore 7 Sensor</h1>'
         f'{filler(2)}<table><tr><th>Spec</th><th>Value</th></tr>'
         '<tr><td>Operating range</td><td>-40C to 125C</td></tr>'
         '<tr><td>Sampling rate</td><td>2000 Hz</td></tr>'
         '<tr><td>Net weight</td><td>340 grams</td></tr></table>'
         f'{filler(2)}')
    page("pricing.html", "Pricing — Northwind Instruments", "",
         '<h1>Plans</h1>'
         '<div class="plan"><h2>Starter</h2><p class="price">$49/mo</p></div>'
         '<div class="plan"><h2>Pro</h2><p class="price">$199/mo</p></div>'
         '<div class="plan"><h2>Enterprise</h2><p class="price">'
         'Contact sales</p></div>'
         f'{filler(2)}')
    write(TRUTH / "html-extract.json", json.dumps({
        "founded_year": "1998",
        "ceo_name": "Marisa Feld",
        "pro_plan_price": "199",
        "sampling_rate_hz": "2000",
        "net_weight_grams": "340"}, indent=1))


# ------------------------------------------------------------- tiny-config
# Axis: VERY little data, trivial question. Measures the FIXED overhead any
# token tool adds: the right answer is one or two values in a ~12-line file,
# so a vanilla read is already near-optimal. If a competitor spends extra
# turns here, that is pure overhead. Impartial: a one-line read suffices.
def gen_tiny_config():
    root = OUT / "tiny-config"
    write(root / "config.toml", '''\
# service configuration — do not commit secrets here
[server]
host = "0.0.0.0"
port = 8443
workers = 4

[database]
name = "ledger_prod"
pool_size = 16
ssl = true

[features]
telemetry = false
beta_ui = true
''')
    write(TRUTH / "config-peek.json", json.dumps({
        "port": "8443",
        "database_name": "ledger_prod"}, indent=1))


def main():
    OUT.mkdir(exist_ok=True)
    TRUTH.mkdir(exist_ok=True)
    gen_seo_site()
    gen_access_log()
    gen_sales_csv()
    gen_longdoc()
    gen_longdoc_fr()
    gen_longdoc_zh()
    gen_ci_log()
    gen_release_log()
    gen_log_needle_zh()
    gen_tinyledger()
    gen_iterledger()
    gen_jsfeature()
    gen_migration()
    gen_events_csv()
    gen_html_docs()
    gen_tiny_config()
    print(f"fixtures written to {OUT}")
    print(f"ground truth written to {TRUTH}  (never copied into workspaces)")


if __name__ == "__main__":
    main()
