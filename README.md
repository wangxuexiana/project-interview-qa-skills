# Project Interview Q&A

基于当前代码仓库自动生成项目专属技术面试题库的 Codex Skill。它会先扫描项目生成项目画像，再生成结构化 `wiki.json`、Markdown Wiki 和题库分布计划，最后由 Codex 基于业务流、风险证据和代码入口产出场景化面试问答。

## 它适合做什么

如果你准备面试，但不知道自己的项目会被怎样追问，这个 skill 可以让 Codex 先读懂当前项目，再帮你整理出更像真实面试的问题和参考答案。它不会只生成通用八股题，而是会优先围绕项目里的核心业务流、高并发点、缓存一致性、MQ、幂等、状态流转、权限、安全、测试和部署等主题组织题库。

你可以直接这样问 Codex：

```text
基于当前项目生成 30 道中级开发面试题
```

也可以继续追问：

```text
展开 Q7
模拟优惠券模块面试
优化 Q12 的面试表达
补 10 道高并发相关题
给我一份复习路线
```

## 核心能力

- 项目画像分析：识别项目类型、技术栈、核心模块和风险信号。
- 结构化项目 Wiki：输出 Markdown Wiki 和可供 Codex 决策的 `wiki.json`。
- 业务流图谱：从接口、领域对象、服务、MQ/定时任务和风险证据中归纳高价值业务流。
- 题库分布计划：为 30 题或用户指定题量分配主业务流、支撑主题和泛技术栈题量。
- 面试题库生成：每题包含考察点、标准详解版、面试表达版、结合本项目和可选追问。
- 追问训练：支持展开、模拟面试、答案润色、补题和复习路线。

## 安装目录

Skill frontmatter 名称是 `project-interview-qa`。开源安装时推荐目录也使用：

```text
project-interview-qa/
```

当前本地仓库目录可能是 `project-interview-qa-skills/`，这是仓库路径名称，不影响 skill 名称；发布或安装到 Codex skills 目录时建议统一为 `project-interview-qa`。

## 目录结构

```text
project-interview-qa/
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── archetypes.yaml
│   ├── extractor-profiles.md
│   ├── followup-modes.md
│   ├── output-contract.md
│   ├── question-rubrics.md
│   ├── signal-rules.yaml
│   └── wiki-guidelines.md
└── scripts/
    ├── analyze_project.py
    ├── generate_project_wiki.py
    └── validate_question_bank.py
```

## CLI 示例

生成项目画像：

```bash
python scripts/analyze_project.py <repo-root> --pretty > project-profile.json
```

生成 Markdown Wiki、结构化 Wiki 和题库分布计划：

```bash
python scripts/generate_project_wiki.py project-profile.json \
  --repo-root <repo-root> \
  --out project-wiki.md \
  --json-out project-wiki.json \
  --plan-out question-plan.json \
  --question-count 30
```

校验已保存的题库：

```bash
python scripts/validate_question_bank.py interview-qa.md \
  --profile project-profile.json \
  --wiki-json project-wiki.json \
  --expected-count 30
```

## 能力边界

- 业务流图谱使用启发式源码扫描，不要求完整 AST 调用链。
- Java/Spring 项目识别最强；Node、Python、Go、前端项目使用通用 route/service/model/job 文件名和风险信号规则。
- 第二梯队抽取器已覆盖 Java/Spring、Node/TypeScript、Python Web、Go Web 和前端路由/组件线索；`wiki.json.extractors` 会显示本次实际启用的抽取器。
- 如果 Wiki 中业务流置信度为 `low`，生成题库时应标注“从当前代码未完全确认”，并优先检查证据文件。
- 本 skill 不直接脚本化生成最终 30 题；题库仍由 Codex 根据 Wiki、结构化计划和输出规范生成。

## 项目类型覆盖

| 类型 | 面试焦点 |
| --- | --- |
| 交易型电商/教育销售 | 高并发、幂等、库存/额度扣减、支付回调、补偿 |
| 学习/内容/媒体平台 | 发布流程、进度追踪、延迟写入、搜索同步 |
| SaaS/后台/工作流 | RBAC/ABAC、租户隔离、审批状态机、审计 |
| 社交/消息/协作 | 消息投递、未读计数、排序、去重、扩散 |
| 数据/分析/AI | 数据流、Schema 演化、模型推理、可观测性 |
| 基础设施/开发者工具 | 扩展边界、配置优先级、故障恢复、安全 |
| 前端/移动端产品 | 组件设计、状态流、API 缓存、错误处理 |
| 游戏/交互工具 | 游戏循环、状态一致性、渲染架构、性能 |

## 许可证

MIT
