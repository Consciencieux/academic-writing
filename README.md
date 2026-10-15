# 学术写作 Skill 体系

面向 AI 的学术写作治理体系：总入口负责流程协调，专业 Skill 各司其职，共享规则保持单一来源。

## 架构

```text
academic-writing/
├── SKILL.md                 # 薄入口：只路由，不含具体规则
├── skills/                 # 可独立发现的 Skill
│   ├── academic-writing-audit/    # 规则审查（扫描已有文稿）
│   ├── academic-writing-guide/    # 正面写作指导（待建）
│   └── academic-writing/          # 流程协调（与根入口一致）
├── shared/                 # 规则权威源（SSOT）
├── scripts/
├── assets/
└── ...
```

详见 [AGENTS.md](AGENTS.md)。

## 使用

- 审查已有文稿 → `academic-writing-audit`
- 从头写作或不确定先做什么 → 根入口或 `skills/academic-writing`
- 正面写作方法 → `academic-writing-guide`（建设中）

规则只在 `shared/rules/` 维护一次。
