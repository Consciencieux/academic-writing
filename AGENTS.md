# AGENTS.md

本仓库是多 Skill 体系。**规则正文的单一权威来源为 `shared/rules/`**。Skill 入口规定任务流程和何时读取规则，不能在 Skill 内复制维护整套规则条文。

## Skill 分工

| 组件 | 负责 | 不负责 |
| --- | --- | --- |
| 根 `SKILL.md` 与 `skills/academic-writing/` | 识别任务、协调全流程、路由专业 Skill | 实施详细审查或替代 Guide 起草正文 |
| `skills/academic-writing-guide/` | 正向写作、起草/改写/扩写/压缩/润色，长文的章节论证连续性 | 对已有整篇论文做独立全面审查 |
| `skills/academic-writing-audit/` | 局部审查、全文通读及跨章节问题定位 | 用审查禁令替代正向写作方法 |
| `shared/rules/` | 事实、语言、结构、SSOT、LaTeX 和 self-check 的规范 | 具体 Agent 任务编排 |
| `scripts/`、`assets/` | 机械检查、安装包生成及 LaTeX 模板 | 无法机械确认的学术语义判断 |

## 写作与审查原则

1. Guide 的 `SKILL.md` 中保留始终适用的精简正向契约，详细规则按任务实际读取。源代码规则查找路径是 `../../shared/rules/`，独立安装包是 `references/rules/`。
2. 所有正常学术写作都应读取内容与语言规则；完整章节、跨章节任务要读取结构规则；多文件数据一致性与概念变更要读取 SSOT 规则。不要靠仅列出文件名替代读取。
3. Audit 必须区分局部审查和全文审查。用户要求完整通读时建立覆盖清单，实际读取所有可访问的必要部分，检查跨章节职责、重复、篇幅和材料泄露；缺文件时不能假称已读完。
4. 论文正文只呈现研究所需的内容。Agent 的状态卡、规划过程、审查报告和工程交流材料不能直接混入正文。
5. 写作以问题与证据组织成熟初稿，避免默认每段进行多轮独立审查；用户明确要求中途审查时照做。

## 维护与发布

- 新增规范只改 `shared/rules/`，Skill 只调整执行方法与指针。原有规则内容尽量保留；改变判断口径时更新 CHANGELOG。
- `skills/*/references/` 保存该 Skill 自己的方法与示例，不放第二份共享规则原文。
- `scripts/package_skills.py` 生成独立 ZIP；其中 `references/rules/` 是临时打包副本，不在源码仓库重复维护。
- 修改 Skill、路径或资源后运行 `python3 scripts/package_skills.py --check-only` 和正常打包，并检查产物结构。
- 规则、工作流改变后按 `tests/manual-evals.md` 的相关场景进行实际测试，不以复述规则的流畅程度代表遵守率。
- 增删或重命名 Skill、修改分发行为后同步根入口、README 和相关工作流。仓库不写具体论文项目的数据和经历。
