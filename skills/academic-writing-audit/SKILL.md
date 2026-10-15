---
name: academic-writing-audit
description: >-
  规则审查（规则警察）。扫描已有论文或章节中的 AI 坏习惯、空话、逻辑问题、表格滥用、SSOT 违反等。
  输出问题位置、严重程度、判定依据与修改建议。用户要求时执行修正。
---

# 学术写作审查

扫描已有文稿，不做正向写作指导。

## 工作流

1. 跑机械检查（`scripts/lint_tex.py`，如为 LaTeX）。
2. 按需加载 `shared/` 中的规则：
   - 内容与判断 → shared/content-and-judgment.md
   - 语言 → shared/language.md
   - 结构 → shared/structure-and-formatting.md
   - 治理 → shared/ssot-and-concept-cleanup.md
3. 输出问题清单（机械命中 + 需判断项）。
4. 用户要求修改时，按规则执行。

红线见总入口或 shared 对应章节。
