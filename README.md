# 学术写作 Skill 体系

面向 AI 的学术写作治理体系：总入口负责流程协调，专业 Skill 各司其职，共享规则保持单一来源。

## 架构

```text
academic-writing/
├── SKILL.md                 # 薄入口：只路由，不含具体规则
├── skills/                 # 可独立发现的 Skill
│   ├── academic-writing-audit/    # 规则审查（后置、独立）
│   ├── academic-writing-guide/    # 正向写作（契约已立；章节方法/范例待补）
│   └── academic-writing/          # 流程协调（与根入口一致）
├── shared/                 # 规则权威源（SSOT）
├── scripts/
├── assets/
└── ...
```

详见 [AGENTS.md](AGENTS.md)。

## 使用

- 从头写作或不确定先做什么 → 根入口或 `skills/academic-writing`
- 正向写作（起草 / 改写等）→ `academic-writing-guide`（正向契约已立；章节方法与范例待补）
- 审查已有文稿 → `academic-writing-audit`（完整章节 / 重大结构调整 / 交付前）

写作优先用 guide；审查后置，不要用反复 Audit→修补替代正向写作。规则只在 `shared/rules/` 维护一次。
