#!/usr/bin/env python3
"""Generate a project wiki draft from an analyzer profile."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

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


def md_list(items: list[str], empty: str = "从当前代码未确认") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def module_table(modules: list[dict]) -> str:
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


def read_json(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raw = path.read_text(encoding="utf-16")
    return json.loads(raw)


def read_text(path: Path, limit: int = 20000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def iter_module_files(root: Path, module: str, max_files: int = 120) -> list[Path]:
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


def is_source_file(path: Path) -> bool:
    rel = str(path).replace("\\", "/").lower()
    if path.name in {"pom.xml", "package.json"}:
        return False
    if "/src/" in rel:
        return True
    return path.suffix.lower() in {".java", ".kt", ".go", ".py", ".js", ".ts", ".tsx", ".vue"}


def compact_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


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


def module_code_facts(root: Path | None, modules: list[dict], limit: int = 6) -> dict[str, dict]:
    if not root or not root.exists():
        return {}

    facts: dict[str, dict] = {}
    for mod in modules[:limit]:
        name = mod.get("name")
        if not name:
            continue
        endpoints: list[str] = []
        types: list[str] = []
        async_jobs: list[str] = []
        configs: list[str] = []
        data_files: list[str] = []
        evidence: dict[str, list[str]] = defaultdict(list)

        for path in iter_module_files(root, name):
            rel = compact_path(root, path)
            text = read_text(path)
            lower_rel = rel.lower()

            if any(token in lower_rel for token in ["controller", "api", "router", "routes"]):
                for raw in ENDPOINT_RE.findall(text):
                    value = extract_endpoint_value(raw)
                    if value and len(endpoints) < 12:
                        endpoints.append(f"{value} ({rel})")

            if any(token in lower_rel for token in ["entity", "domain", "dto", "vo", "model"]):
                for type_name in JAVA_TYPE_RE.findall(text):
                    if len(types) < 16:
                        types.append(f"{type_name} ({rel})")

            for annotation in ANNOTATION_RE.findall(text):
                item = f"@{annotation} ({rel})"
                if annotation in {"RabbitListener", "KafkaListener", "Scheduled", "XxlJob"}:
                    if item not in async_jobs and len(async_jobs) < 12:
                        async_jobs.append(item)
                elif annotation in {"FeignClient", "Mapper", "Entity", "TableName"}:
                    if item not in data_files and len(data_files) < 12:
                        data_files.append(item)

            if any(token in lower_rel for token in ["config", "bootstrap", "application.", "docker", "pom.xml"]):
                if len(configs) < 12:
                    configs.append(rel)

            if not is_source_file(path):
                continue

            risk_patterns = {
                "并发控制": [r"tryLock", r"Redisson", r"RLock", r"synchronized", r"Semaphore"],
                "缓存一致性": [r"RedisTemplate", r"StringRedisTemplate", r"Cacheable", r"expire\(", r"delete\("],
                "异步消息": [r"RabbitTemplate", r"@RabbitListener", r"KafkaTemplate", r"@KafkaListener"],
                "幂等/防重": [r"idempot", r"重复", r"幂等", r"requestId", r"bizOrder"],
                "状态流转": [r"status", r"State", r"状态", r"ISSUING", r"USED", r"EXPIRED"],
                "条件更新": [r"\.eq\(", r"\.in\(", r"WHERE .*status", r"update .* set"],
            }
            for label, patterns in risk_patterns.items():
                if len(evidence[label]) >= 5:
                    continue
                if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
                    if rel:
                        evidence[label].append(rel)

        facts[name] = {
            "endpoints": endpoints,
            "types": types,
            "async_jobs": async_jobs,
            "configs": configs,
            "data_files": data_files,
            "risk_evidence": dict(evidence),
        }
    return facts


def risk_weight(mod: dict) -> int:
    """Prefer modules with interview-rich reliability and concurrency signals."""
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


def recommended_modules(modules: list[dict], limit: int = 6) -> list[dict]:
    """Blend large/core modules with high-risk modules so smaller but interview-heavy code is not missed."""
    selected: list[dict] = []
    seen: set[str] = set()

    def add(mod: dict) -> None:
        name = mod.get("name")
        if name and name not in seen and len(selected) < limit:
            selected.append(mod)
            seen.add(name)

    for mod in modules[:3]:
        add(mod)

    risk_ranked = sorted(
        modules,
        key=lambda mod: (risk_weight(mod), mod.get("interview_score", 0), mod.get("file_count", 0)),
        reverse=True,
    )
    for mod in risk_ranked:
        add(mod)

    for mod in modules:
        add(mod)

    return selected


def format_code_facts(facts: dict[str, dict]) -> str:
    if not facts:
        return "- 未启用源码增强扫描，或未发现可抽取的接口/实体/异步证据。"

    sections: list[str] = []
    for module, item in facts.items():
        parts = [f"### `{module}`"]
        parts.append("**接口线索：**")
        parts.append(md_list(item.get("endpoints", [])[:8]))
        parts.append("")
        parts.append("**核心对象线索：**")
        parts.append(md_list(item.get("types", [])[:8]))
        parts.append("")
        parts.append("**异步/任务/外部协作线索：**")
        parts.append(md_list(item.get("async_jobs", [])[:8] + item.get("data_files", [])[:4]))
        parts.append("")
        parts.append("**配置与启动证据：**")
        parts.append(md_list(item.get("configs", [])[:6]))
        sections.append("\n".join(parts))
    return "\n\n".join(sections)


def format_risk_matrix(facts: dict[str, dict]) -> str:
    rows = ["| 模块 | 风险主题 | 证据入口 |", "| --- | --- | --- |"]
    for module, item in facts.items():
        risk_evidence = item.get("risk_evidence", {})
        for risk, files in risk_evidence.items():
            files = [path for path in files if path]
            if files:
                rows.append(f"| `{module}` | {risk} | {', '.join(files[:3])} |")
    if len(rows) == 2:
        return "- 从增强扫描中未发现明确风险证据。"
    return "\n".join(rows)


def render(profile: dict, repo_root: Path | None = None) -> str:
    project_type = profile.get("project_type", {})
    ranked = project_type.get("ranked", [])
    primary_focus = ranked[0].get("focus", []) if ranked else []
    secondary_focus = ranked[1].get("focus", []) if len(ranked) > 1 else []
    modules = profile.get("modules", [])
    top_modules = modules[:8]
    hot_topics = profile.get("hot_topics", [])
    hints = profile.get("generation_hints", {})
    selected_modules = recommended_modules(modules)
    facts = module_code_facts(repo_root, selected_modules) if repo_root else {}

    hot_topic_lines = [
        f"{item.get('topic')}（证据数：{item.get('evidence_count')}）"
        for item in hot_topics[:10]
    ]

    main_module_lines = []
    for mod in selected_modules:
        risks = ", ".join(list(mod.get("risk_signals", {}).keys())[:5]) or "无明显风险信号"
        samples = ", ".join(mod.get("sample_files", [])[:3])
        reason = "综合分高"
        if risk_weight(mod) >= 12:
            reason = "高频风险信号集中"
        main_module_lines.append(
            f"`{mod.get('name')}`：推荐原因：{reason}；面试分数 {mod.get('interview_score')}；"
            f"重点信号：{risks}；证据文件：{samples}"
        )

    return f"""# Project Wiki

## 1. 项目总览
- 仓库路径：`{profile.get('root')}`
- 扫描文件数：{profile.get('file_count_scanned')}
- 主项目类型：{project_type.get('primary', 'unknown')}
- 次项目类型：{project_type.get('secondary') or '无'}
- 技术栈：{', '.join(profile.get('tech_stack', [])[:20]) or '从当前代码未确认'}

## 2. 项目类型判断
### 主类型面试方向
{md_list(primary_focus)}

### 次类型面试方向
{md_list(secondary_focus)}

## 3. 模块地图
{module_table(top_modules)}

## 4. 推荐主讲模块
{md_list(main_module_lines)}

## 5. 高频面试主题
{md_list(hot_topic_lines)}

## 6. 源码增强理解
{format_code_facts(facts)}

## 7. 风险证据矩阵
{format_risk_matrix(facts)}

## 8. 业务主线候选
基于项目类型、模块分数和风险信号，优先围绕这些方向组织面试题：

{md_list(hints.get('primary_archetype_focus', []) + hints.get('question_focus', []))}

## 9. 代码证据入口
生成题库前，应优先抽样阅读推荐主讲模块中的 `sample_files`，确认业务流程和风险点。若 wiki 结论与代码不一致，以代码为准，并在题库中标注“从当前代码未确认”。

## 10. 面试题生成建议
- 题目保持中层粒度，优先问业务场景、流程设计、可靠性、权衡和优化。
- 不要把题库变成源码逐行讲解。
- 标准详解版应覆盖背景、设计目标、项目实现、风险与取舍、可优化方向。
- 对推荐主讲模块分配 70-80% 的题量，其他模块作为支撑或追问。
- 对风险证据矩阵里的主题优先生成“场景题”：为什么这样设计、极端情况下如何保证一致性、失败后怎么补偿、怎么压测和观测。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Markdown project wiki from project_profile.json.")
    parser.add_argument("profile_json", help="Path to analyzer JSON output.")
    parser.add_argument("--repo-root", help="Repository root for optional source-enhanced wiki extraction.")
    parser.add_argument("--out", help="Output Markdown path. If omitted, print to stdout.")
    args = parser.parse_args()

    profile = read_json(Path(args.profile_json))
    repo_root = Path(args.repo_root) if args.repo_root else Path(profile.get("root", ""))
    if not repo_root.exists():
        repo_root = None
    markdown = render(profile, repo_root)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
