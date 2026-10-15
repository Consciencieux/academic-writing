# AGENTS.md

本仓库是多 Skill 体系。规则只存在于 `shared/rules/`（SSOT），各 Skill 只写工作流并用指针引用。

## 能力盘点归属（2026-10）

| 类别 | 主要来源 | 说明 |
| --- | --- | --- |
| 共享规范 | content-and-judgment.md、language.md、structure-and-formatting.md、ssot-and-concept-cleanup.md、红线表 | audit 与 guide 共同引用 |
| 审查行为 | self-check.md 主体、lint 的语言/内容检查 | 形成 academic-writing-audit 工作流 |
| 写作行为 | 原根 SKILL.md 中的起草/改写/扩写/压缩/润色 | 为 guide 提供边界；正面方法需新写 |
| 文档工具 | latex-mechanics.md、lint 的标签/引用/编译相关、assets/ | audit 按需调用，不强制拆分 |

## 结构

- 根 `SKILL.md`：薄入口，只负责路由，不含具体规则或审查流程。
- `skills/<name>/SKILL.md`：可独立发现的 Skill 入口。
  - `academic-writing-audit`：规则审查（扫描已有文稿）
  - `academic-writing-guide`：正面写作指导（待建）
- `shared/rules/`：规则权威源。禁止在 Skill 内复制条文。
- `scripts/`：机械检查与构建脚本。
- `assets/`：模板。

## 规则

1. 同一主题只在 `shared/rules/` 写一次；Skill 内只用指针（`见 shared/rules/xxx.md §n`）。
2. 现有规则尽量保留原文，不为架构机械重写。
3. 增删 Skill 后更新本文件与 README。
4. 保持通用，不写具体项目数据。

改完后检查指针有效、无复制条文、构建通过。
