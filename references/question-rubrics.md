# Question Rubrics

Use these rubrics when turning a project profile into interview questions.

## Good Questions

- Ask about behavior that exists in the repository, not only about the framework.
- Tie a common interview concept to a concrete module, class, command, route, schema, queue, cache key, or data flow.
- Prefer risk-bearing flows over simple CRUD.
- Prefer business-flow questions from `wiki.json.business_flows` over isolated module questions.
- Ask questions that support follow-up discussion: tradeoffs, failure modes, optimizations, and tests.
- Include candidate-facing wording that can be spoken in an interview.
- Prefer medium-granularity scenario questions: module-level or flow-level questions that a candidate can explain in 1-3 minutes.
- Ask about "why this design", "how the flow works", "what risks exist", and "how to improve it" before asking about exact lines, method names, or fields.
- Make the detailed answer genuinely detailed: business background, design goal, implementation path, risk/failure mode, and possible improvement.

## Bad Questions

- Generic framework questions that do not mention the project.
- Even coverage of every module when only a few modules contain real interview value.
- Ignoring the question distribution plan and drifting into unrelated framework topics.
- Questions based only on dependency names when no code path proves the behavior.
- Long textbook answers that do not explain how the project implements or fails to implement the concept.
- Overconfident claims about production readiness when the code does not show reliability features.
- Overly narrow code-detail questions such as "what does this exact method do", "why this one field is set", or "what is this exact SQL condition" unless the user explicitly asks for code-level drilling.
- Questions that require memorizing implementation minutiae rather than explaining architecture, business flow, tradeoffs, and reliability.

## Required Answer Shape

Each question must include:

- `考察点`: one or two concrete skills the interviewer is testing.
- `标准详解版`: a rich explanation with background, design goal, implementation path, risks, and optimization ideas.
- `面试表达版`: concise first-person wording suitable for a candidate.
- `结合本项目`: concrete module, file, flow, or code evidence.
- `可选追问`: one practical follow-up question.

## Detailed Answer Depth

For `标准详解版`, do not write a one-sentence answer. Use 4-6 concise sentences or compact bullets covering:

1. Why this problem exists in this type of project.
2. What design goal the project is trying to achieve.
3. How the project implements the flow at a module level.
4. What consistency, concurrency, security, or reliability risk remains.
5. What improvement or production-hardening direction can be discussed.

Avoid reciting every method call. Mention code evidence in `结合本项目`, not as the whole answer.

## Question Granularity

Use this priority:

1. Business-flow question from the wiki: "优惠券领取如何避免超发？"
2. Flow/design question: "课程上架为什么要拆草稿表和正式表？"
3. Reliability/tradeoff question: "MQ 异步后如何保证最终一致？"
4. Code-level question: only use when it represents a broader interview point.

For a 30-question bank, at least 24 questions should be scenario/design/reliability questions. At most 6 should be narrow code-level questions.

## Weighting Guidance

- For 30 questions, choose 3-5 main modules or flows.
- Put 70-80% of questions on `question_plan.primary_flows` and the cross-cutting infrastructure that supports them.
- Use only a few questions for secondary modules.
- If the analyzer finds hot topics, include at least 5 of the top 8 unless the evidence is weak.
- If a module has only config or CRUD code, keep it low priority unless it supports a high-value flow.
- Keep generic framework basics under 10% unless the user explicitly requests technical-stack basics.
