#!/usr/bin/env python3
"""Generate a Markdown and optional JSON project wiki from an analyzer profile."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


SKIP_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "target",
    "build",
    "dist",
    "out",
    "__pycache__",
}

TEXT_EXTENSIONS = {
    ".java",
    ".kt",
    ".go",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
    ".sql",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".properties",
    ".md",
}

JAVA_TYPE_RE = re.compile(r"\b(?:class|interface|enum|record)\s+([A-Z][A-Za-z0-9_]*)")
ENDPOINT_RE = re.compile(
    r"@(?:RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*(?:\(\s*([^)]*)\))?",
    re.MULTILINE,
)
ANNOTATION_RE = re.compile(r"@(RabbitListener|KafkaListener|Scheduled|XxlJob|FeignClient|Mapper|Entity|TableName)\b")
METHOD_RE = re.compile(r"\b(public|private|protected)\s+[\w<>, ?]+\s+([a-zA-Z][A-Za-z0-9_]*)\s*\(")
JS_ROUTE_RE = re.compile(r"\b(?:app|router|server)\s*\.\s*(get|post|put|delete|patch|all)\s*\(\s*['\"]([^'\"]+)['\"]")
NEST_DECORATOR_RE = re.compile(r"@(Controller|Get|Post|Put|Delete|Patch)\s*\(\s*['\"]?([^'\"\)]*)['\"]?\s*\)")
PY_ROUTE_RE = re.compile(r"@(?:app|router|blueprint)\.(get|post|put|delete|patch|route)\s*\(\s*['\"]([^'\"]+)['\"]")
DJANGO_PATH_RE = re.compile(r"\b(?:path|re_path)\s*\(\s*['\"]([^'\"]+)['\"]")
GO_ROUTE_RE = re.compile(r"\b\w+\.(GET|POST|PUT|DELETE|PATCH|Any)\s*\(\s*\"([^\"]+)\"")
PY_TYPE_RE = re.compile(r"\bclass\s+([A-Z][A-Za-z0-9_]*)\s*(?:\([^)]*\))?:")
TS_TYPE_RE = re.compile(r"\b(?:class|interface|type)\s+([A-Z][A-Za-z0-9_]*)")
GO_TYPE_RE = re.compile(r"\btype\s+([A-Z][A-Za-z0-9_]*)\s+(?:struct|interface)\b")

RISK_PATTERNS = {
    "并发控制": [r"tryLock", r"Redisson", r"RLock", r"synchronized", r"Semaphore", r"@Lock\b"],
    "Redis/缓存": [r"RedisTemplate", r"StringRedisTemplate", r"Cacheable", r"expire\(", r"delete\(", r"\.increment\("],
    "异步消息": [r"RabbitTemplate", r"@RabbitListener", r"KafkaTemplate", r"@KafkaListener", r"\.send\(", r"Celery", r"Bull", r"Queue", r"amqp", r"Kafka", r"BackgroundTasks"],
    "幂等/防重": [r"idempot", r"重复", r"幂等", r"requestId", r"bizOrder", r"duplicate"],
    "状态流转": [r"status", r"State", r"状态", r"ISSUING", r"USED", r"EXPIRED", r"TRADE_"],
    "条件更新": [r"\.eq\(", r"\.in\(", r"WHERE .*status", r"update .* set", r"lambdaUpdate"],
    "外部回调": [r"callback", r"notify", r"webhook", r"回调", r"third", r"第三方"],
    "搜索/索引": [r"Elasticsearch", r"SearchRequest", r"index", r"highlight", r"Repository"],
    "权限隔离": [r"permission", r"privilege", r"role", r"tenant", r"auth", r"RBAC"],
    "定时/补偿": [r"@Scheduled", r"@XxlJob", r"cron", r"DelayQueue", r"compensat", r"@Cron", r"setInterval", r"schedule"],
}

FLOW_KEYWORDS = [
    ("优惠券领取与核销", ["coupon", "promotion", "voucher", "discount", "优惠", "券", "UserCoupon", "ExchangeCode"]),
    ("订单交易与支付协作", ["order", "trade", "payment", "pay", "refund", "订单", "支付", "退款"]),
    ("课程发布与内容管理", ["course", "catalogue", "chapter", "lesson", "publish", "课程", "章节", "上架"]),
    ("学习进度与积分统计", ["learning", "progress", "lesson", "points", "liked", "积分", "进度"]),
    ("权限认证与访问控制", ["auth", "role", "permission", "privilege", "token", "权限", "认证"]),
    ("搜索索引与查询", ["search", "index", "elasticsearch", "highlight", "搜索", "索引"]),
    ("消息通知与异步处理", ["message", "mq", "rabbit", "kafka", "notify", "通知", "消息"]),
    ("媒体上传与资源管理", ["media", "upload", "file", "storage", "oss", "上传", "媒资"]),
]

ANGLE_BY_RISK = {
    "并发控制": ["如何防止并发超卖/重复写入", "多实例部署下锁或条件更新如何生效"],
    "Redis/缓存": ["缓存与数据库不一致窗口如何处理", "热点 key、穿透或失效风暴如何治理"],
    "异步消息": ["生产者/消费者失败后如何保证最终一致", "重复消费和消息堆积如何处理"],
    "幂等/防重": ["重复请求、重复回调或重复消息如何识别", "幂等键或唯一约束如何设计"],
    "状态流转": ["状态机如何限制非法流转", "失败回滚和人工补偿如何设计"],
    "条件更新": ["为什么需要条件更新", "高并发下如何验证不会覆盖正确状态"],
    "外部回调": ["第三方回调重复或乱序时如何处理", "回调验签和补偿查询怎么做"],
    "搜索/索引": ["索引与主库如何同步", "索引重建和补偿怎么设计"],
    "权限隔离": ["权限模型和数据边界如何保证", "权限缓存失效如何处理"],
    "定时/补偿": ["定时任务如何避免重复执行", "补偿任务如何做到可观测和可恢复"],
}


def md_list(items: list[str], empty: str = "从当前代码未确认") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def unique(items: list[str], limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            result.append(item)
            seen.add(item)
            if limit and len(result) >= limit:
                break
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-16")
    return json.loads(raw)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text(path: Path, limit: int = 30000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def iter_module_files(root: Path, module: str, max_files: int = 160) -> list[Path]:
    base = root / module if module != "." else root
    if not base.exists():
        return []
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.suffix.lower() in TEXT_EXTENSIONS or filename in {"Dockerfile", "pom.xml", "package.json"}:
                files.append(path)
                if len(files) >= max_files:
                    return files
    return files


def compact_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def is_source_file(path: Path) -> bool:
    rel = str(path).replace("\\", "/").lower()
    if path.name in {"pom.xml", "package.json"}:
        return False
    if "/src/" in rel:
        return True
    return path.suffix.lower() in {".java", ".kt", ".go", ".py", ".js", ".jsx", ".ts", ".tsx", ".vue"}


def extract_endpoint_value(raw: str | None) -> str:
    if not raw:
        return ""
    match = re.search(r'"([^"]+)"', raw)
    if match:
        return match.group(1)
    match = re.search(r"value\s*=\s*\"([^\"]+)\"", raw)
    if match:
        return match.group(1)
    return raw.strip().replace("\n", " ")[:80]


def detect_extractors(profile: dict[str, Any]) -> list[str]:
    tech_stack = set(profile.get("tech_stack", []))
    modules = profile.get("modules", [])
    extensions = {ext for mod in modules for ext in mod.get("top_extensions", {})}
    extractors = ["generic"]
    if {"spring-boot", "spring-cloud", "mybatis-plus"} & tech_stack or ".java" in extensions:
        extractors.append("java-spring")
    if {"node", "react", "nextjs"} & tech_stack or {".js", ".jsx", ".ts", ".tsx"} & extensions:
        extractors.append("node-ts-js")
    if "python" in tech_stack or ".py" in extensions:
        extractors.append("python-web")
    if ".go" in extensions:
        extractors.append("go-web")
    if {"react", "vue", "nextjs"} & tech_stack or {".vue", ".tsx", ".jsx"} & extensions:
        extractors.append("frontend-routes")
    return unique(extractors)


def extract_endpoints(text: str, rel: str) -> list[str]:
    endpoints: list[str] = []
    for raw in ENDPOINT_RE.findall(text):
        value = extract_endpoint_value(raw)
        if value:
            endpoints.append(f"{value} ({rel})")
    for method, value in JS_ROUTE_RE.findall(text):
        endpoints.append(f"{method.upper()} {value} ({rel})")
    for decorator, value in NEST_DECORATOR_RE.findall(text):
        if decorator == "Controller":
            endpoints.append(f"Controller {value or '/'} ({rel})")
        else:
            endpoints.append(f"{decorator.upper()} {value or '/'} ({rel})")
    for method, value in PY_ROUTE_RE.findall(text):
        endpoints.append(f"{method.upper()} {value} ({rel})")
    for value in DJANGO_PATH_RE.findall(text):
        endpoints.append(f"PATH {value} ({rel})")
    for method, value in GO_ROUTE_RE.findall(text):
        endpoints.append(f"{method.upper()} {value} ({rel})")
    return endpoints


def extract_domain_objects(text: str, path: Path, rel: str) -> list[str]:
    suffix = path.suffix.lower()
    names: list[str] = []
    if suffix in {".java", ".kt"}:
        names.extend(JAVA_TYPE_RE.findall(text))
    elif suffix in {".ts", ".tsx", ".js", ".jsx"}:
        names.extend(TS_TYPE_RE.findall(text))
    elif suffix == ".py":
        names.extend(PY_TYPE_RE.findall(text))
    elif suffix == ".go":
        names.extend(GO_TYPE_RE.findall(text))
    return [f"{name} ({rel})" for name in names]


def extract_methods(text: str, path: Path, rel: str) -> list[str]:
    suffix = path.suffix.lower()
    names: list[str] = []
    if suffix in {".java", ".kt"}:
        names.extend(name for _, name in METHOD_RE.findall(text))
    elif suffix in {".ts", ".tsx", ".js", ".jsx"}:
        names.extend(re.findall(r"\b(?:async\s+)?function\s+([a-zA-Z][A-Za-z0-9_]*)\s*\(", text))
        names.extend(re.findall(r"\b([a-zA-Z][A-Za-z0-9_]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", text))
    elif suffix == ".py":
        names.extend(re.findall(r"\bdef\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(", text))
        names.extend(re.findall(r"\basync\s+def\s+([a-zA-Z_][A-Za-z0-9_]*)\s*\(", text))
    elif suffix == ".go":
        names.extend(re.findall(r"\bfunc\s+(?:\([^)]*\)\s*)?([A-Z_a-z][A-Za-z0-9_]*)\s*\(", text))
    return [f"{name} ({rel})" for name in names]


def extract_collaborators(text: str, rel: str) -> list[str]:
    collaborators = [f"@{annotation} ({rel})" for annotation in ANNOTATION_RE.findall(text)]
    generic_patterns = [
        ("Queue", r"\b(?:Queue|Bull|Celery|Kafka|Rabbit|amqp|pubsub|BackgroundTasks)\b"),
        ("Cron/Schedule", r"\b(?:@Cron|cron|schedule|setInterval|APScheduler)\b"),
        ("ORM/Repository", r"\b(?:Repository|Prisma|TypeORM|Sequelize|SQLAlchemy|DjangoModel|GORM|db\.)\b"),
        ("Cache", r"\b(?:Redis|redis|cache|Cache|ioredis)\b"),
        ("HTTP Client", r"\b(?:FeignClient|axios|fetch\(|requests\.|http\.Client|RestTemplate)\b"),
    ]
    for label, pattern in generic_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            collaborators.append(f"{label} ({rel})")
    return collaborators


def risk_weight(mod: dict[str, Any]) -> int:
    weights = {
        "lock": 5,
        "distributed-lock": 5,
        "redis-counter": 5,
        "conditional-update": 5,
        "idempotency": 4,
        "cache-consistency": 4,
        "mq-async": 4,
        "external-callback": 4,
        "state-machine": 3,
        "workflow": 3,
        "scheduled-job": 2,
        "permission": 2,
        "search-index": 2,
    }
    risks = mod.get("risk_signals", {})
    return sum(weights.get(name, 1) for name in risks)


def recommended_modules(modules: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(mod: dict[str, Any]) -> None:
        name = mod.get("name")
        if name and name not in seen and len(selected) < limit:
            selected.append(mod)
            seen.add(name)

    for mod in modules[:3]:
        add(mod)
    for mod in sorted(
        modules,
        key=lambda item: (risk_weight(item), item.get("interview_score", 0), item.get("file_count", 0)),
        reverse=True,
    ):
        add(mod)
    for mod in modules:
        add(mod)
    return selected


def module_code_facts(root: Path | None, modules: list[dict[str, Any]], limit: int = 6) -> dict[str, dict[str, Any]]:
    if not root or not root.exists():
        return {}

    facts: dict[str, dict[str, Any]] = {}
    for mod in modules[:limit]:
        name = mod.get("name")
        if not name:
            continue
        endpoints: list[str] = []
        endpoint_files: list[str] = []
        domain_objects: list[str] = []
        domain_files: list[str] = []
        service_files: list[str] = []
        collaborator_files: list[str] = []
        collaborators: list[str] = []
        configs: list[str] = []
        methods: list[str] = []
        risk_evidence: dict[str, list[str]] = defaultdict(list)

        for path in iter_module_files(root, name):
            rel = compact_path(root, path)
            text = read_text(path)
            lower_rel = rel.lower()
            extracted_endpoints = extract_endpoints(text, rel)

            if extracted_endpoints or any(token in lower_rel for token in ["controller", "api", "router", "routes", "views.py", "urls.py"]):
                endpoint_files.append(rel)
                endpoints.extend(extracted_endpoints)

            extracted_types = extract_domain_objects(text, path, rel)
            if any(token in lower_rel for token in ["entity", "domain", "dto", "vo", "model", "schema", "types"]):
                domain_files.append(rel)
                domain_objects.extend(extracted_types)

            if any(token in lower_rel for token in ["service", "usecase", "handler", "processor", "manager"]):
                service_files.append(rel)
                methods.extend(extract_methods(text, path, rel))

            extracted_collaborators = extract_collaborators(text, rel) if is_source_file(path) else []
            if extracted_collaborators:
                collaborators.extend(extracted_collaborators)
                collaborator_files.append(rel)

            if any(token in lower_rel for token in ["config", "bootstrap", "application.", "docker", "pom.xml", "package.json"]):
                configs.append(rel)

            if not is_source_file(path):
                continue
            for label, patterns in RISK_PATTERNS.items():
                if len(risk_evidence[label]) >= 5:
                    continue
                if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
                    risk_evidence[label].append(rel)

        facts[name] = {
            "endpoints": unique(endpoints, 12),
            "endpoint_files": unique(endpoint_files, 12),
            "domain_objects": unique(domain_objects, 16),
            "domain_files": unique(domain_files, 12),
            "service_files": unique(service_files, 12),
            "methods": unique(methods, 12),
            "collaborators": unique(collaborators, 16),
            "collaborator_files": unique(collaborator_files, 12),
            "configs": unique(configs, 12),
            "risk_evidence": {key: unique(value, 5) for key, value in risk_evidence.items() if value},
        }
    return facts


def module_table(modules: list[dict[str, Any]]) -> str:
    lines = [
        "| 模块 | 面试分数 | 文件数 | 主要信号 | 风险信号 |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for mod in modules:
        signals = ", ".join(list(mod.get("signals", {}).keys())[:5]) or "-"
        risks = ", ".join(list(mod.get("risk_signals", {}).keys())[:5]) or "-"
        lines.append(
            f"| `{mod.get('name')}` | {mod.get('interview_score', 0)} | "
            f"{mod.get('file_count', 0)} | {signals} | {risks} |"
        )
    return "\n".join(lines)


def flow_name_for_module(module: str, facts: dict[str, Any]) -> tuple[str, str]:
    haystack = " ".join(
        [module]
        + facts.get("endpoints", [])
        + facts.get("domain_objects", [])
        + facts.get("service_files", [])
        + facts.get("methods", [])
        + facts.get("collaborators", [])
    ).lower()
    for name, keywords in FLOW_KEYWORDS:
        if any(keyword.lower() in haystack for keyword in keywords):
            return name, "high"
    return f"{module} 业务流候选", "low"


def question_angles(risk_topics: list[str], fallback_focus: list[str]) -> list[str]:
    angles: list[str] = []
    for topic in risk_topics:
        angles.extend(ANGLE_BY_RISK.get(topic, []))
    for focus in fallback_focus:
        angles.append(f"如何解释 {focus} 在本项目中的设计取舍")
    return unique(angles, 8)


def build_business_flows(
    selected_modules: list[dict[str, Any]],
    facts: dict[str, dict[str, Any]],
    primary_focus: list[str],
) -> list[dict[str, Any]]:
    flows: list[dict[str, Any]] = []
    for mod in selected_modules:
        module = mod.get("name", "")
        module_facts = facts.get(module, {})
        name, base_confidence = flow_name_for_module(module, module_facts)
        risk_evidence = module_facts.get("risk_evidence", {})
        risk_topics = list(risk_evidence.keys()) or list(mod.get("risk_signals", {}).keys())[:6]
        evidence_files = unique(
            module_facts.get("endpoint_files", [])
            + module_facts.get("service_files", [])
            + module_facts.get("domain_files", [])
            + module_facts.get("collaborator_files", [])
            + [file for files in risk_evidence.values() for file in files]
            + mod.get("sample_files", []),
            16,
        )

        confidence_score = 0
        confidence_score += 1 if module_facts.get("endpoints") or module_facts.get("endpoint_files") else 0
        confidence_score += 1 if module_facts.get("service_files") else 0
        confidence_score += 1 if module_facts.get("domain_objects") or module_facts.get("domain_files") else 0
        confidence_score += 1 if module_facts.get("collaborators") or risk_topics else 0
        confidence = "high" if confidence_score >= 3 else "medium" if confidence_score >= 2 else base_confidence

        interview_value = "high" if risk_weight(mod) >= 12 or len(risk_topics) >= 4 else "medium"
        flows.append(
            {
                "name": name,
                "modules": [module],
                "entrypoints": module_facts.get("endpoints", [])[:8],
                "domain_objects": module_facts.get("domain_objects", [])[:8],
                "collaborators": module_facts.get("collaborators", [])[:8],
                "risk_topics": risk_topics[:8],
                "evidence_files": evidence_files,
                "interview_value": interview_value,
                "confidence": confidence,
                "question_angles": question_angles(risk_topics[:6], primary_focus),
            }
        )
    return flows


def build_risk_matrix(facts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module, item in facts.items():
        for risk, files in item.get("risk_evidence", {}).items():
            rows.append({"module": module, "risk_topic": risk, "evidence_files": files[:5]})
    return rows


def build_question_plan(
    business_flows: list[dict[str, Any]],
    risk_matrix: list[dict[str, Any]],
    question_count: int,
) -> dict[str, Any]:
    total = max(1, question_count)
    primary_budget = max(1, round(total * 0.75))
    generic_budget = max(1, total // 10)
    support_budget = max(0, total - primary_budget - generic_budget)

    priority_risks = {"并发控制", "Redis/缓存", "异步消息", "幂等/防重", "条件更新", "外部回调"}

    def flow_priority(flow: dict[str, Any]) -> int:
        risks = set(flow.get("risk_topics", []))
        name = str(flow.get("name", ""))
        score = len(risks) + sum(2 for risk in risks if risk in priority_risks)
        if any(token in name for token in ["优惠券", "库存", "订单", "支付", "课程", "搜索", "进度"]):
            score += 3
        if "权限认证" in name:
            score -= 2
        if flow.get("confidence") == "high":
            score += 1
        return score

    high_flows = [flow for flow in business_flows if flow.get("interview_value") == "high"] or business_flows[:3]
    high_flows = sorted(high_flows, key=flow_priority, reverse=True)[:5]
    primary_flows: list[dict[str, Any]] = []
    if high_flows:
        weights = [max(1, len(flow.get("risk_topics", [])) + (2 if flow.get("confidence") == "high" else 0)) for flow in high_flows]
        allocated = 0
        for index, flow in enumerate(high_flows):
            if index == len(high_flows) - 1:
                count = max(1, primary_budget - allocated)
            else:
                count = max(1, round(primary_budget * weights[index] / sum(weights)))
                allocated += count
            primary_flows.append(
                {
                    "name": flow.get("name"),
                    "modules": flow.get("modules", []),
                    "question_count": count,
                    "focus": flow.get("risk_topics", [])[:5] or flow.get("question_angles", [])[:3],
                }
            )
    else:
        support_budget += primary_budget

    risk_topics = unique([row["risk_topic"] for row in risk_matrix], 6)
    supporting_topics = [
        {"name": topic, "question_count": max(1, support_budget // max(1, len(risk_topics))), "focus": [topic]}
        for topic in risk_topics[:support_budget]
    ]
    used = sum(item["question_count"] for item in primary_flows + supporting_topics)
    generic_count = max(0, total - used)

    return {
        "total": total,
        "primary_flows": primary_flows,
        "supporting_topics": supporting_topics,
        "generic_tech_questions": generic_count,
        "distribution_rule": "70-80% questions should follow primary flows; generic framework questions stay under 10%.",
    }


def build_wiki_model(profile: dict[str, Any], repo_root: Path | None = None, question_count: int = 30) -> dict[str, Any]:
    project_type = profile.get("project_type", {})
    ranked = project_type.get("ranked", [])
    primary_focus = ranked[0].get("focus", []) if ranked else []
    secondary_focus = ranked[1].get("focus", []) if len(ranked) > 1 else []
    modules = profile.get("modules", [])
    selected_modules = recommended_modules(modules)
    extractors = detect_extractors(profile)
    facts = module_code_facts(repo_root, selected_modules) if repo_root else {}
    business_flows = build_business_flows(selected_modules, facts, primary_focus)
    risk_matrix = build_risk_matrix(facts)
    question_plan = build_question_plan(business_flows, risk_matrix, question_count)

    recommended = []
    for mod in selected_modules:
        risks = list(mod.get("risk_signals", {}).keys())
        reason = "高频风险信号集中" if risk_weight(mod) >= 12 else "综合分高"
        recommended.append(
            {
                "name": mod.get("name"),
                "reason": reason,
                "interview_score": mod.get("interview_score", 0),
                "risk_signals": risks[:8],
                "sample_files": mod.get("sample_files", [])[:8],
            }
        )

    return {
        "root": profile.get("root"),
        "file_count_scanned": profile.get("file_count_scanned"),
        "project_type": {
            "primary": project_type.get("primary", "unknown"),
            "secondary": project_type.get("secondary"),
            "ranked": ranked[:5],
            "primary_focus": primary_focus,
            "secondary_focus": secondary_focus,
        },
        "tech_stack": profile.get("tech_stack", [])[:20],
        "extractors": extractors,
        "modules": modules[:8],
        "recommended_modules": recommended,
        "hot_topics": profile.get("hot_topics", [])[:10],
        "source_facts": facts,
        "risk_matrix": risk_matrix,
        "business_flows": business_flows,
        "business_mainline_candidates": profile.get("generation_hints", {}).get("primary_archetype_focus", [])
        + profile.get("generation_hints", {}).get("question_focus", []),
        "question_plan": question_plan,
        "confidence_note": "业务流图谱来自启发式源码扫描；若代码证据不足，应在题库中标注“从当前代码未完全确认”。",
    }


def format_code_facts(facts: dict[str, dict[str, Any]]) -> str:
    if not facts:
        return "- 未启用源码增强扫描，或未发现可抽取的接口/实体/异步证据。"

    sections: list[str] = []
    for module, item in facts.items():
        parts = [f"### `{module}`"]
        parts.append("**接口线索：**")
        parts.append(md_list(item.get("endpoints", [])[:8]))
        parts.append("")
        parts.append("**核心对象线索：**")
        parts.append(md_list(item.get("domain_objects", [])[:8]))
        parts.append("")
        parts.append("**服务/协作线索：**")
        parts.append(md_list(item.get("service_files", [])[:5] + item.get("collaborators", [])[:5]))
        parts.append("")
        parts.append("**配置与启动证据：**")
        parts.append(md_list(item.get("configs", [])[:6]))
        sections.append("\n".join(parts))
    return "\n\n".join(sections)


def format_risk_matrix(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "- 从增强扫描中未发现明确风险证据。"
    lines = ["| 模块 | 风险主题 | 证据入口 |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(f"| `{row['module']}` | {row['risk_topic']} | {', '.join(row['evidence_files'][:3])} |")
    return "\n".join(lines)


def format_business_flows(flows: list[dict[str, Any]]) -> str:
    if not flows:
        return "- 从当前代码未确认明确业务流。"
    sections: list[str] = []
    for flow in flows:
        suffix = "" if flow.get("confidence") != "low" else "（候选，当前代码未完全确认）"
        parts = [f"### {flow.get('name')}{suffix}"]
        parts.append(f"- 模块：{', '.join(f'`{m}`' for m in flow.get('modules', [])) or '从当前代码未确认'}")
        parts.append(f"- 面试价值：{flow.get('interview_value')}；置信度：{flow.get('confidence')}")
        parts.append(f"- 风险主题：{', '.join(flow.get('risk_topics', [])[:6]) or '从当前代码未确认'}")
        parts.append(f"- 入口证据：{'; '.join(flow.get('entrypoints', [])[:3]) or '从当前代码未确认'}")
        parts.append(f"- 核心对象：{'; '.join(flow.get('domain_objects', [])[:5]) or '从当前代码未确认'}")
        parts.append(f"- 追问角度：{'; '.join(flow.get('question_angles', [])[:4]) or '从当前代码未确认'}")
        sections.append("\n".join(parts))
    return "\n\n".join(sections)


def format_question_plan(plan: dict[str, Any]) -> str:
    lines = [f"- 总题量：{plan.get('total')}"]
    for item in plan.get("primary_flows", []):
        lines.append(
            f"- 主业务流 `{item.get('name')}`：{item.get('question_count')} 题；"
            f"模块：{', '.join(item.get('modules', []))}；重点：{', '.join(item.get('focus', []))}"
        )
    for item in plan.get("supporting_topics", []):
        lines.append(f"- 支撑主题 `{item.get('name')}`：{item.get('question_count')} 题")
    lines.append(f"- 泛技术栈基础题：{plan.get('generic_tech_questions', 0)} 题以内")
    return "\n".join(lines)


def render_markdown(wiki_model: dict[str, Any]) -> str:
    project_type = wiki_model.get("project_type", {})
    recommended_lines = [
        f"`{item.get('name')}`：推荐原因：{item.get('reason')}；面试分数 {item.get('interview_score')}；"
        f"重点信号：{', '.join(item.get('risk_signals', [])[:5]) or '无明显风险信号'}；"
        f"证据文件：{', '.join(item.get('sample_files', [])[:3])}"
        for item in wiki_model.get("recommended_modules", [])
    ]
    hot_topic_lines = [
        f"{item.get('topic')}（证据数：{item.get('evidence_count')}）"
        for item in wiki_model.get("hot_topics", [])
    ]

    return f"""# Project Wiki

## 1. 项目总览
- 仓库路径：`{wiki_model.get('root')}`
- 扫描文件数：{wiki_model.get('file_count_scanned')}
- 主项目类型：{project_type.get('primary', 'unknown')}
- 次项目类型：{project_type.get('secondary') or '无'}
- 技术栈：{', '.join(wiki_model.get('tech_stack', [])) or '从当前代码未确认'}
- 启用抽取器：{', '.join(wiki_model.get('extractors', [])) or 'generic'}

## 2. 项目类型判断
### 主类型面试方向
{md_list(project_type.get('primary_focus', []))}

### 次类型面试方向
{md_list(project_type.get('secondary_focus', []))}

## 3. 模块地图
{module_table(wiki_model.get('modules', []))}

## 4. 推荐主讲模块
{md_list(recommended_lines)}

## 5. 高频面试主题
{md_list(hot_topic_lines)}

## 6. 源码增强理解
{format_code_facts(wiki_model.get('source_facts', {}))}

## 7. 风险证据矩阵
{format_risk_matrix(wiki_model.get('risk_matrix', []))}

## 8. 业务流图谱
{format_business_flows(wiki_model.get('business_flows', []))}

## 9. 题库分布建议
{format_question_plan(wiki_model.get('question_plan', {}))}

## 10. 业务主线候选
基于项目类型、模块分数和风险信号，优先围绕这些方向组织面试题：

{md_list(wiki_model.get('business_mainline_candidates', []))}

## 11. 代码证据入口
生成题库前，应优先抽样阅读推荐主讲模块、业务流图谱和风险证据矩阵中的文件，确认业务流程和风险点。若 wiki 结论与代码不一致，以代码为准，并在题库中标注“从当前代码未确认”。

## 12. 面试题生成建议
- 题目保持中层粒度，优先问业务场景、流程设计、可靠性、权衡和优化。
- 优先遵循题库分布建议，不要平均覆盖所有模块。
- 不要把题库变成源码逐行讲解。
- 标准详解版应覆盖背景、设计目标、项目实现、风险与取舍、可优化方向。
- 对风险证据矩阵里的主题优先生成“场景题”：为什么这样设计、极端情况下如何保证一致性、失败后怎么补偿、怎么压测和观测。
- {wiki_model.get('confidence_note')}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Markdown project wiki from project_profile.json.")
    parser.add_argument("profile_json", help="Path to analyzer JSON output.")
    parser.add_argument("--repo-root", help="Repository root for optional source-enhanced wiki extraction.")
    parser.add_argument("--out", help="Output Markdown path. If omitted, print to stdout.")
    parser.add_argument("--json-out", help="Output structured wiki JSON path.")
    parser.add_argument("--plan-out", help="Output question distribution plan JSON path.")
    parser.add_argument("--question-count", type=int, default=30, help="Question count used for distribution planning.")
    args = parser.parse_args()

    profile = read_json(Path(args.profile_json))
    repo_root = Path(args.repo_root) if args.repo_root else Path(profile.get("root", ""))
    if not repo_root.exists():
        repo_root = None

    wiki_model = build_wiki_model(profile, repo_root, args.question_count)
    markdown = render_markdown(wiki_model)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)

    if args.json_out:
        write_json(Path(args.json_out), wiki_model)
    if args.plan_out:
        write_json(Path(args.plan_out), wiki_model.get("question_plan", {}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
