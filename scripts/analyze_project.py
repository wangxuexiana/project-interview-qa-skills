#!/usr/bin/env python3
"""Build a lightweight interview-oriented profile for a source repository."""

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
    ".next",
    ".nuxt",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
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
    ".rs",
    ".cs",
    ".php",
    ".rb",
    ".swift",
    ".sql",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".gradle",
    ".properties",
    ".md",
}

TECH_PATTERNS = {
    "spring-boot": ["spring-boot", "@SpringBootApplication"],
    "spring-cloud": ["spring-cloud", "@FeignClient", "GatewayFilter", "nacos"],
    "mybatis-plus": ["mybatis-plus", "BaseMapper", "ServiceImpl"],
    "redis": ["RedisTemplate", "StringRedisTemplate", "redis", "Redisson"],
    "rabbitmq": ["RabbitListener", "RabbitTemplate", "RabbitMQ", "MqConstants"],
    "kafka": ["KafkaListener", "KafkaTemplate", "kafka"],
    "elasticsearch": ["Elasticsearch", "RestHighLevelClient", "SearchRequest"],
    "mysql": ["mysql", "MySQL"],
    "postgres": ["postgres", "PostgreSQL"],
    "react": ["react", "useState", "useEffect"],
    "vue": ["vue", "Vue"],
    "nextjs": ["next", "NextResponse"],
    "node": ["package.json", "express", "fastify", "nestjs"],
    "python": ["requirements.txt", "pyproject.toml", "fastapi", "django"],
    "docker": ["Dockerfile", "docker-compose"],
}

ARCHETYPES = {
    "transactional-commerce-or-education-sales": {
        "signals": [
            "order", "payment", "refund", "cart", "coupon", "promotion", "voucher",
            "inventory", "stock", "quota", "purchase", "pay", "trade", "settlement",
        ],
        "focus": [
            "high concurrency", "idempotency", "stock or quota deduction",
            "payment callback", "order state machine", "cache/MQ consistency",
            "compensation",
        ],
    },
    "learning-content-or-media-platform": {
        "signals": [
            "course", "lesson", "learning", "progress", "media", "upload", "publish",
            "review", "comment", "like", "feed", "search", "catalogue", "chapter",
        ],
        "focus": [
            "publishing workflow", "progress tracking", "delayed writes", "counters",
            "search index sync", "media storage", "content state transitions",
        ],
    },
    "saas-admin-or-business-workflow": {
        "signals": [
            "tenant", "role", "permission", "privilege", "approval", "workflow",
            "audit", "organization", "department", "dashboard", "report", "form",
        ],
        "focus": [
            "RBAC/ABAC", "tenant isolation", "workflow state machine",
            "auditability", "data permissions", "reporting queries",
        ],
    },
    "social-messaging-or-collaboration": {
        "signals": [
            "message", "chat", "inbox", "notification", "push", "unread", "reply",
            "comment", "like", "follow", "fanout", "websocket",
        ],
        "focus": [
            "message delivery", "unread counters", "ordering", "deduplication",
            "fanout strategy", "rate limiting",
        ],
    },
    "data-analytics-or-ai": {
        "signals": [
            "etl", "pipeline", "metric", "dashboard", "model", "embedding", "vector",
            "inference", "training", "dataset", "feature", "batch", "stream",
        ],
        "focus": [
            "data flow", "schema evolution", "batch/stream tradeoffs",
            "model serving", "latency", "observability", "reproducibility",
        ],
    },
    "infrastructure-or-developer-tool": {
        "signals": [
            "plugin", "cli", "deploy", "monitor", "config", "automation", "build",
            "ci", "cd", "runner", "workspace", "tool", "sdk",
        ],
        "focus": [
            "extension boundaries", "config precedence", "failure recovery",
            "filesystem/network safety", "integration tests",
        ],
    },
    "frontend-mobile-or-product-app": {
        "signals": [
            "component", "route", "store", "state", "form", "offline", "cache",
            "accessibility", "responsive", "mobile", "screen", "page",
        ],
        "focus": [
            "component design", "state flow", "API caching", "error states",
            "performance", "UX edge cases", "testability",
        ],
    },
    "game-or-interactive-tool": {
        "signals": [
            "game", "physics", "render", "canvas", "three", "unity", "input",
            "sprite", "animation", "multiplayer", "score",
        ],
        "focus": [
            "game loop", "state consistency", "performance", "deterministic rules",
            "rendering architecture", "interaction design",
        ],
    },
}

RISK_PATTERNS = {
    "lock": [r"@Lock\b", r"RLock\b", r"Redisson", r"tryLock", r"distributed\s*lock"],
    "redis-counter": [r"\.increment\(", r"INCR\b", r"ZSet", r"BitMap", r"opsForHash", r"opsForZSet"],
    "conditional-update": [r"WHERE .*<", r"WHERE .*status", r"\.eq\(.*Status", r"\.in\(.*Status"],
    "mq-async": [r"@RabbitListener", r"RabbitTemplate", r"\.send\(", r"KafkaListener", r"QueueBinding"],
    "idempotency": [r"idempot", r"duplicate", r"重复", r"幂等", r"bizOrder", r"requestId"],
    "state-machine": [r"status", r"State", r"状态", r"TRADE_", r"ISSUING", r"USED", r"EXPIRED"],
    "external-callback": [r"callback", r"notify", r"webhook", r"回调", r"third", r"第三方"],
    "search-index": [r"SearchRequest", r"Elasticsearch", r"index", r"highlight", r"Repository"],
    "permission": [r"permission", r"privilege", r"role", r"tenant", r"auth", r"RBAC"],
    "workflow": [r"approval", r"workflow", r"process", r"审核", r"审批"],
    "scheduled-job": [r"@Scheduled", r"@XxlJob", r"cron", r"DelayQueue"],
    "cache-consistency": [r"Cacheable", r"cache", r"缓存", r"delete\(.*CACHE", r"expire\("],
}


def iter_files(root: Path, max_files: int) -> list[Path]:
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.suffix.lower() in TEXT_EXTENSIONS or filename in {"Dockerfile", "pom.xml", "package.json"}:
                files.append(path)
                if len(files) >= max_files:
                    return files
    return files


def read_text(path: Path, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    return text[:limit]


def module_name(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) <= 1:
        return "."
    if parts[0] in {"src", "app", "lib", "server", "client"}:
        return parts[0]
    return parts[0]


def count_matches(text: str, patterns: list[str]) -> int:
    score = 0
    lower = text.lower()
    for pattern in patterns:
        if pattern.startswith("@") or "\\" in pattern or "(" in pattern:
            score += len(re.findall(pattern, text, flags=re.IGNORECASE))
        else:
            score += lower.count(pattern.lower())
    return score


def profile(root: Path, max_files: int, read_limit: int) -> dict:
    files = iter_files(root, max_files)
    module_stats: dict[str, dict] = defaultdict(lambda: {
        "file_count": 0,
        "extensions": Counter(),
        "signals": Counter(),
        "risk_signals": Counter(),
        "sample_files": [],
    })
    tech_scores = Counter()
    archetype_scores = Counter()
    hot_evidence: dict[str, list[str]] = defaultdict(list)

    for path in files:
        mod = module_name(root, path)
        rel = str(path.relative_to(root)).replace("\\", "/")
        text = read_text(path, read_limit)
        combined = rel + "\n" + text

        stats = module_stats[mod]
        stats["file_count"] += 1
        stats["extensions"][path.suffix.lower() or path.name] += 1
        if len(stats["sample_files"]) < 8:
            stats["sample_files"].append(rel)

        for tech, patterns in TECH_PATTERNS.items():
            n = count_matches(combined, patterns)
            if n:
                tech_scores[tech] += n
                stats["signals"][tech] += n

        for archetype, cfg in ARCHETYPES.items():
            n = count_matches(combined, cfg["signals"])
            if n:
                archetype_scores[archetype] += n
                stats["signals"][archetype] += n

        for risk, patterns in RISK_PATTERNS.items():
            n = count_matches(combined, patterns)
            if n:
                stats["risk_signals"][risk] += n
                hot_evidence[risk].append(rel)

    ranked_archetypes = [
        {
            "name": name,
            "score": score,
            "focus": ARCHETYPES[name]["focus"],
        }
        for name, score in archetype_scores.most_common(3)
    ]

    modules = []
    primary_focus = set(ranked_archetypes[0]["focus"] if ranked_archetypes else [])
    selected_archetypes = {item["name"] for item in ranked_archetypes[:2]}
    for name, stats in module_stats.items():
        risk_score = sum(stats["risk_signals"].values())
        archetype_score = sum(v for k, v in stats["signals"].items() if k in ARCHETYPES)
        selected_archetype_score = sum(v for k, v in stats["signals"].items() if k in selected_archetypes)
        tech_score = sum(
            v for k, v in stats["signals"].items() if k in TECH_PATTERNS
        )
        score = int(
            risk_score * 8
            + selected_archetype_score * 3
            + archetype_score
            + tech_score * 0.5
            + stats["file_count"] * 0.2
        )
        modules.append({
            "name": name,
            "interview_score": score,
            "file_count": stats["file_count"],
            "top_extensions": dict(stats["extensions"].most_common(5)),
            "signals": dict(stats["signals"].most_common(10)),
            "risk_signals": dict(stats["risk_signals"].most_common(10)),
            "sample_files": stats["sample_files"],
        })
    modules.sort(key=lambda item: (item["interview_score"], item["file_count"]), reverse=True)

    hot_topics = []
    for risk, count in Counter({k: len(v) for k, v in hot_evidence.items()}).most_common(12):
        files_for_risk = sorted(set(hot_evidence[risk]))[:6]
        hot_topics.append({
            "topic": risk,
            "evidence_count": count,
            "sample_files": files_for_risk,
        })

    return {
        "root": str(root),
        "file_count_scanned": len(files),
        "project_type": {
            "primary": ranked_archetypes[0]["name"] if ranked_archetypes else "unknown",
            "secondary": ranked_archetypes[1]["name"] if len(ranked_archetypes) > 1 else None,
            "ranked": ranked_archetypes,
        },
        "tech_stack": [name for name, _ in tech_scores.most_common(20)],
        "modules": modules[:20],
        "hot_topics": hot_topics,
        "generation_hints": {
            "recommended_main_modules": [m["name"] for m in modules[:5]],
            "question_focus": [
                t["topic"] for t in hot_topics[:8]
            ],
            "primary_archetype_focus": list(primary_focus),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a repository for interview-question generation.")
    parser.add_argument("path", nargs="?", default=".", help="Repository path to analyze.")
    parser.add_argument("--max-files", type=int, default=1200)
    parser.add_argument("--read-limit", type=int, default=12000)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    result = profile(root, args.max_files, args.read_limit)
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
