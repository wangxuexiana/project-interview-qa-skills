#!/usr/bin/env python3
"""Validate a generated Markdown interview question bank."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


QUESTION_RE = re.compile(r"^###\s+Q\d+[\.\s]", re.MULTILINE)
REQUIRED_LABELS = [
    "**考察点：**",
    "**标准详解版：**",
    "- 背景：",
    "- 设计目标：",
    "- 项目实现：",
    "- 风险与取舍：",
    "- 可优化方向：",
    "**面试表达版：**",
    "**结合本项目：**",
    "**可选追问：**",
]


def load_profile(path: str | None) -> dict:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def validate(markdown: str, expected_count: int, profile: dict) -> dict:
    questions = QUESTION_RE.findall(markdown)
    missing_labels = [label for label in REQUIRED_LABELS if label not in markdown]
    warnings = []
    errors = []

    if len(questions) != expected_count:
        errors.append(f"Expected {expected_count} questions, found {len(questions)}.")

    if missing_labels:
        errors.append("Missing required labels: " + ", ".join(missing_labels))

    if "## 项目类型判断" not in markdown:
        warnings.append("Missing project archetype section.")
    if "## Wiki 理解摘要" not in markdown:
        warnings.append("Missing wiki understanding summary section.")
    if "## 模块面试价值评估" not in markdown:
        warnings.append("Missing module interview-value section.")
    if "## 高频面试点" not in markdown:
        warnings.append("Missing high-frequency interview topics section.")
    if "## 后续可继续练习" not in markdown:
        warnings.append("Missing continuation-practice section.")

    modules = [m.get("name", "") for m in profile.get("modules", [])[:5]]
    if modules:
        mentioned = [m for m in modules if m and m in markdown]
        if not mentioned:
            warnings.append("None of the top profile modules are mentioned in the question bank.")

    hot_topics = [t.get("topic", "") for t in profile.get("hot_topics", [])[:8]]
    if hot_topics:
        mentioned_topics = [t for t in hot_topics if t and t in markdown]
        if len(mentioned_topics) < min(3, len(hot_topics)):
            warnings.append("Few analyzer hot topics are visibly represented in the output.")

    generic_terms = ["Gateway", "JWT", "Feign", "CRUD"]
    generic_count = sum(markdown.lower().count(term.lower()) for term in generic_terms)
    if generic_count > max(10, expected_count // 2) and hot_topics:
        warnings.append("Generic architecture terms may be overrepresented compared with project-specific hot topics.")

    detail_sections = re.findall(
        r"\*\*标准详解版：\*\*(.*?)(?:\*\*面试表达版：\*\*|### Q\d+|$)",
        markdown,
        flags=re.S,
    )
    too_short = [
        section for section in detail_sections
        if len(re.sub(r"\s+", "", section)) < 80
    ]
    if detail_sections and len(too_short) > max(2, expected_count // 5):
        warnings.append("Many 标准详解版 sections look too short for detailed interview preparation.")

    return {
        "ok": not errors,
        "question_count": len(questions),
        "expected_count": expected_count,
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Markdown interview question bank.")
    parser.add_argument("markdown_file")
    parser.add_argument("--profile")
    parser.add_argument("--expected-count", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    markdown = Path(args.markdown_file).read_text(encoding="utf-8", errors="ignore")
    result = validate(markdown, args.expected_count, load_profile(args.profile))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        status = "OK" if result["ok"] else "FAILED"
        print(f"Validation {status}: {result['question_count']}/{result['expected_count']} questions")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
