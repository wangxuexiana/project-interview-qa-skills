# Wiki Guidelines

Use the project wiki as the intermediate understanding layer between raw code scanning and interview-question generation.

## Purpose

The wiki should explain the project at a module and flow level:

- What type of project it is.
- Which modules matter most.
- Which business flows are likely interview highlights.
- Which risk-bearing topics deserve questions.
- Which code files should be inspected before generating answers.
- Which API/domain/async/config evidence supports the interpretation.
- Which risk topics have direct source evidence and should become scenario questions.
- Which business flows should drive the question distribution plan.

## Source Priority

Use this evidence priority:

1. Code evidence from source files, configs, schemas, tests, and scripts.
2. Analyzer profile JSON.
3. Existing README/docs/wiki/project notes.
4. File names and dependency names.
5. Model inference.

If wiki or docs mention a feature but code does not confirm it, mark it as "从当前代码未确认".

## Wiki Sections

The generated wiki should include:

- 项目总览
- 项目类型判断
- 模块地图
- 推荐主讲模块
- 高频面试主题
- 源码增强理解
- 风险证据矩阵
- 业务流图谱
- 题库分布建议
- 业务主线候选
- 代码证据入口
- 面试题生成建议

## Strong Wiki Criteria

A strong project wiki is not just a summary of file counts. It should:

- Name the likely business capabilities exposed by controller/router/API files.
- Surface domain objects from entity/model/DTO/VO/schema files.
- Surface async, scheduled, callback, and external integration clues.
- Connect each recommended module to concrete risk evidence.
- Convert module evidence into one or more business-flow candidates.
- Separate confirmed code facts from inference.
- Give the question generator enough context to ask about flows, failure modes, and tradeoffs.

Avoid turning the wiki into a full source-code explanation. Keep evidence compact: list representative files and signals, then let Codex inspect the files before making detailed claims.

## Structured Wiki Model

When available, use `wiki.json` as the decision surface and Markdown wiki as the reading surface. The structured model should include:

- `recommended_modules`: modules worth discussing and why.
- `risk_matrix`: risk topics with representative evidence files.
- `business_flows`: candidate or confirmed flows with modules, entrypoints, domain objects, collaborators, risk topics, evidence files, confidence, interview value, and question angles.
- `question_plan`: recommended distribution for the requested question count.
- `extractors`: enabled source extraction profiles, such as `java-spring`, `node-ts-js`, `python-web`, `go-web`, or `frontend-routes`.

Confidence meanings:

- `high`: entrypoint/service/domain/collaboration evidence is present.
- `medium`: some code evidence exists but flow boundaries are incomplete.
- `low`: the flow is inferred from names/signals and must be described as "从当前代码未完全确认".

## How To Use Wiki For Questions

- Prefer modules and flows that appear both in the wiki and in code evidence.
- Use wiki to avoid scattered module coverage.
- Use wiki to keep questions at medium granularity.
- Use analyzer `sample_files` to verify implementation before writing concrete claims.
- Use wiki conclusions as ranking guidance, not as unquestionable facts.
- Convert risk evidence into scenario questions: concurrency, consistency, idempotency, compensation, observability, testing, deployment, and evolution.
- If a smaller module has dense risk evidence, allow it to outrank a larger CRUD-heavy module.
- Follow `question_plan` before inventing a new module distribution.
- If a flow has `confidence: low`, avoid concrete implementation claims until inspecting evidence files.
- If only the `generic` extractor is enabled, treat route/object/collaboration evidence as weaker and verify more source files.

## When To Regenerate

Regenerate the wiki when:

- The user changes repository or module scope.
- The user asks for a new project type or interview target.
- The code changed significantly.
- The previous wiki does not mention the topic the user wants to practice.
