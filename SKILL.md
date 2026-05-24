---
name: project-interview-qa
description: Generate and continue project-specific technical interview practice from the current codebase. Use when the user asks for interview questions, reference answers, technical 八股 plus project questions, resume project follow-up questions, project review questions, candidate prep materials, Markdown interview Q&A, deep dives, mock interviews, answer polishing, or more questions based on the current repository.
---

# Project Interview Q&A

Generate or continue Markdown interview practice grounded in the current repository. Build a factual project profile first, turn it into a structured wiki model plus Markdown wiki as the intermediate understanding layer, then generate interview questions from the wiki, question distribution plan, and verified code evidence.

## Default Behavior

- Candidate level: use the user's requested level; otherwise default to 中级开发.
- Question count: use the user's requested count; otherwise generate 30 questions.
- Output language: Chinese unless the user requests another language.
- Output destination: reply in chat unless the user asks to save a file.
- Evidence rule: mention only modules, flows, files, libraries, and behavior observed in the repository. If not confirmed, say "从当前代码未确认".
- Wiki rule: for first-pass question banks, create or use a structured project wiki before generating questions. The wiki model guides business-flow ranking and question distribution; code evidence remains authoritative.
- Continuation rule: if the user asks to continue from a generated question bank, use follow-up modes instead of regenerating the whole bank.
- Granularity rule: default to medium-granularity scenario/design questions. Avoid narrow code-detail questions unless the user explicitly asks for code-level drilling.
- Answer depth rule: `标准详解版` must be meaningfully detailed, covering background, design goal, implementation path, risks/tradeoffs, and possible improvements.

## Workflow

1. Decide whether this is a first-pass question bank or a continuation request.

- First pass: user asks to generate interview questions, a question bank, project 八股, or reference answers.
- Continuation: user asks to 展开/追问/模拟/优化答案/补题/继续问/复习路线, or references a prior question number, module, topic, or answer.

For continuation requests, read `references/followup-modes.md` and use the mode matching the user intent. Reuse the existing profile/wiki/question context when available; rerun the analyzer and regenerate the wiki only if context is missing, stale, or the user changed repositories.

2. For first-pass generation, run the analyzer from the repository root:

```bash
python <skill-dir>/scripts/analyze_project.py <repo-root> --pretty
```

Use its JSON as the primary project profile. Pay special attention to:

- `project_type.primary` and `project_type.secondary`
- `tech_stack`
- `modules[].interview_score`
- `modules[].risk_signals`
- `hot_topics`
- `generation_hints`
- wiki sections `源码增强理解`, `风险证据矩阵`, `业务流图谱`, and `题库分布建议`
- `extractors`, which shows which stack-specific extraction profiles were enabled

3. Generate a project wiki model and Markdown draft from the analyzer JSON:

```bash
python <skill-dir>/scripts/generate_project_wiki.py <profile-json> \
  --repo-root <repo-root> \
  --out <wiki-md> \
  --json-out <wiki-json> \
  --plan-out <question-plan-json> \
  --question-count <count>
```

The `--repo-root` argument enables source-enhanced wiki extraction: API/controller clues, domain objects, async jobs, config entries, a risk evidence matrix, business-flow graph, and a question distribution plan for recommended modules. The Markdown wiki is for user-facing understanding; `wiki.json` and `question-plan.json` are for Codex's internal decisions. If the user asks to save artifacts, write them to the requested location. Otherwise, use temporary paths and summarize only the relevant wiki conclusions in the final answer.

4. Read references only as needed:

- `references/archetypes.yaml`: project-type definitions and interview focus areas.
- `references/signal-rules.yaml`: how concrete code signals map to interview angles.
- `references/wiki-guidelines.md`: how to use wiki as the project-understanding layer.
- `references/extractor-profiles.md`: what stack-specific extractors can infer and how to interpret confidence.
- `references/question-rubrics.md`: quality rules for good and bad questions.
- `references/output-contract.md`: required Markdown structure.
- `references/followup-modes.md`: continuation modes after a question bank is generated.

5. Inspect source files named by the analyzer/wiki for the top modules, business flows, and hot topics. Do not rely only on keyword scores or wiki text; verify the important flow in code before writing questions.

6. Rank 3-5 main modules or business flows using the wiki conclusions, analyzer scores, question plan, and verified code evidence. Use project-type-sensitive ranking:

- Transactional commerce or education sales: orders, payments, refunds, carts, coupons, inventory, course purchase, quota, pricing, settlement.
- Learning/content/media platforms: course publishing, progress tracking, delayed writes, counters, search sync, media upload, content states.
- SaaS/admin/workflow systems: roles, permissions, tenants, approvals, audit logs, reporting, import/export.
- Social/messaging/collaboration: message delivery, unread counters, notifications, ordering, deduplication, fanout, rate limiting.
- Data/analytics/AI: pipelines, metrics, model inference, embeddings, vector search, batch jobs, observability.
- Infrastructure/developer tools: plugin boundaries, config precedence, recovery, filesystem/network safety, integration tests.
- Frontend/mobile/product apps: state flow, routing, forms, API caching, error states, performance, accessibility.
- Games/interactive tools: game loop, rendering, input, deterministic state, performance.

If the wiki reports only `generic` extractor support for a repository, lower confidence in concrete route/object claims and inspect source files more carefully before writing project-specific answers.

7. Generate the question bank from the wiki plus code evidence. Follow `question_plan.primary_flows` first, then supporting topics, then limited generic technical basics. Concentrate 70-80% of questions on the selected high-value flows and their supporting infrastructure. Avoid even module-by-module coverage. Prefer questions about business scenarios, design choices, reliability, and tradeoffs over exact method/field/SQL details. End full question banks with the continuation prompts from `references/followup-modes.md`.

Use the wiki risk evidence matrix to turn implementation signals into medium-granularity scenario questions. For example, a module with lock, Redis counter, MQ, conditional update, or state-machine evidence should produce questions about concurrency, consistency, idempotency, failure recovery, observability, and evolution, not trivia about a single method name.

8. If the user asks for a saved artifact, run:

```bash
python <skill-dir>/scripts/validate_question_bank.py <markdown-file> --profile <profile-json> --wiki-json <wiki-json> --expected-count <count>
```

For chat-only output, self-check the same criteria: exact question count, required answer labels, project-type section, module ranking, business-flow focus, wiki-informed distribution, and visible use of analyzer hot topics.

## Continuation Modes

Use `references/followup-modes.md` for exact output shapes.

- Deep Dive: expand one question, module, or topic into a multi-level follow-up chain.
- Mock Interview: ask one question at a time, wait for the user's answer, then critique and continue.
- Answer Polishing: rewrite a provided or generated answer into natural candidate-style speech.
- More Questions: add focused questions for a module/topic without repeating the prior bank.
- Review Plan: turn the question bank into a practical preparation path.

When continuing from prior questions, preserve numbering if the prior count is clear. If not clear, label the output by topic rather than inventing previous numbers.

## Output Requirements

Follow `references/output-contract.md`.

Each question must include:

- `考察点`
- `标准详解版`
- `面试表达版`
- `结合本项目`
- `可选追问`

Answers should combine a common interview concept with the project's actual implementation. Prefer practical follow-ups about tradeoffs, failure modes, optimization, testing, and troubleshooting.

For `标准详解版`, use 4-6 concise sentences or compact bullets. Cover:

- 背景: why this issue matters in this project type.
- 设计目标: what the implementation is trying to guarantee.
- 项目实现: how the relevant modules cooperate at a flow level.
- 风险与取舍: what can still fail or what tradeoff exists.
- 可优化方向: how to harden or improve the design.

## Quality Rules

- Prefer project-specific risk-bearing flows over generic framework questions.
- Do not over-prioritize Gateway, JWT, Feign, CRUD, or framework setup unless they directly support the selected high-value flow.
- If the analyzer highlights locks, Redis counters, conditional updates, MQ, delayed jobs, callbacks, permissions, indexing, workflows, or pipelines, reflect those signals in the question bank.
- Do not turn analyzer signals into overly narrow trivia. Use them to identify broader interview scenarios and reliability questions.
- At least 80% of questions should be answerable as project/design explanations, not by memorizing a specific method implementation.
- Use wiki to preserve business context and prevent scattered question coverage.
- If wiki conclusions and code evidence disagree, trust code evidence and state uncertainty.
- Treat existing interview notes as hints only; still ground new questions in code.
- Keep `SKILL.md` lean. Put reusable ranking rules in references and deterministic scanning or validation in scripts.
