# AGENTS.md

本仓库是多 Skill 体系。规则只存在于 `shared/rules/`（SSOT），各 Skill 只写工作流并用指针引用。

## 能力盘点归属（2026-10）

| 类别 | 主要来源 | 说明 |
| --- | --- | --- |
| 共享规范 | content-and-judgment.md、language.md、structure-and-formatting.md、ssot-and-concept-cleanup.md、红线表 | audit 与 guide 共同引用；guide 按任务加载，audit 按审查范围加载 |
| 审查行为 | self-check.md 主体、lint 的语言/内容检查 | 形成 academic-writing-audit 工作流；审查后置 |
| 写作行为 | academic-writing-guide 正向契约（写作方法 / 规则加载 / 写作质量） | 起草、改写、扩写、压缩、润色执行入口；章节方法与范例待补 |
| 文档工具 | latex-mechanics.md、lint 的标签/引用/编译相关、assets/ | audit 按需调用，不强制拆分 |

## 结构

- 根 `SKILL.md`：薄入口，只负责路由，不含具体规则或审查流程。
- `skills/<name>/SKILL.md`：可独立发现的 Skill 入口。
  - `academic-writing-audit`：规则审查（扫描已有文稿；后置）
  - `academic-writing-guide`：正向写作契约已立；各章方法与高质量范例待补
- `shared/rules/`：规则权威源。禁止在 Skill 内复制条文。
- `scripts/`：机械检查与构建脚本。
- `assets/`：模板。

## 规则

1. 同一主题只在 `shared/rules/` 写一次；Skill 内只用指针（`见 shared/rules/xxx.md §n`）。
2. 现有规则尽量保留原文，不为架构机械重写；不要把负面规则全文改写成正面提示。
3. guide 提供正向方法与精简核心约束；audit 负责独立审查。写作阶段不要用反复 Audit→修补替代正向写作。
4. 增删 Skill 后更新本文件与 README。
5. 保持通用，不写具体项目数据。

改完后检查指针有效、无复制条文、构建通过。
