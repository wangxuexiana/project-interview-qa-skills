# Follow-up Modes

Use follow-up modes when the user already has a generated question bank or asks to continue practicing from previous questions, modules, or answers.

## Mode Selection

- **Deep Dive**: use when the user asks "展开 Q7", "继续追问", "讲深一点", "围绕某题继续问", or names a specific topic/module.
- **Mock Interview**: use when the user says "模拟面试", "你当面试官", "我来回答", or provides an answer for critique.
- **Answer Polishing**: use when the user asks "优化答案", "说得自然点", "改成面试表达", "像我自己说的话".
- **More Questions**: use when the user asks "再来 10 题", "补题", "某模块不够", or requests more questions for a module/topic.
- **Review Plan**: use when the user asks "怎么复习", "哪些必背", "帮我安排准备顺序".

## Deep Dive Output

For one question or topic, produce:

```markdown
## 深挖：<题目或主题>

### 原题核心

### 追问链
1. ...
2. ...
3. ...
4. ...
5. ...

### 回答要点

### 容易踩坑

### 更好的面试表达
```

## Mock Interview Output

Ask one question at a time unless the user requests a full script. After the user answers:

- score the answer briefly,
- identify missing points,
- ask one deeper follow-up,
- provide a better candidate-style answer.

Use this shape:

```markdown
## 模拟面试

**面试官问题：**

**你的回答点评：**

**缺失要点：**

**继续追问：**

**参考表达：**
```

## Answer Polishing Output

Rewrite the answer in a natural first-person style. Keep it truthful to the repository evidence.

```markdown
## 答案优化

**原答案问题：**

**优化版表达：**

**可加分补充：**

**不要这样说：**
```

## More Questions Output

When adding questions after an existing bank:

- Continue numbering when the previous question count is clear.
- Keep the same required answer labels as the main question bank.
- Keep the new questions focused on the requested module/topic.
- Do not repeat questions that already appeared.

## Review Plan Output

Create a concise practice path:

```markdown
## 复习路线

### 必讲模块

### 必背问题

### 深挖顺序

### 模拟面试安排
```

## Continuation Prompts

When finishing a full question bank, append:

```markdown
## 后续可继续练习
- 输入“展开 Q7”，我会生成该题的多层追问链。
- 输入“模拟 <模块名> 面试”，我会按面试官节奏一次问一题。
- 输入“优化 Q12 答案”，我会改成更自然的候选人表达。
- 输入“补 10 道 <模块/主题> 题”，我会继续生成专项题。
- 输入“给我复习路线”，我会按重要性安排准备顺序。
```
