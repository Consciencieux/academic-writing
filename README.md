# 学术写作 Skill 体系

面向 AI 的学术写作治理体系：总入口负责流程协调，专业 Skill 各司其职，共享规则保持单一来源。

## 架构

```text
academic-writing/
├── skills/                 # 可独立发现的 Skill
│   ├── academic-writing/          # 总入口：流程协调与路由
│   ├── academic-writing-audit/    # 规则审查
│   ├── academic-writing-guide/    # 正面写作指导
│   └── ...
├── shared/                 # 规则权威源（SSOT）
├── scripts/
├── assets/
└── ...
```

详见 [AGENTS.md](AGENTS.md)。

## 安装

各 Skill 通过构建后独立安装到 agent 的 skill 目录。源码中的 `shared/` 不会被直接扫描。
