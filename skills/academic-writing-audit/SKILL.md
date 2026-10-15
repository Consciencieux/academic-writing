---
name: academic-writing-audit
description: >-
  规则审查。扫描已有论文或章节中的证据不足、结论越界、语义重复、结构失衡、SSOT 违反、不合理语言模式等问题。
  输出问题位置、严重程度、判定依据与修改建议。用户要求时执行修正。
---

# 学术写作审查

扫描已有文稿，不做正向写作指导。

## 工作流

1. 跑机械检查（`scripts/lint_tex.py`，如为 LaTeX）。
2. 按需加载 `shared/rules/`：
   - 内容与判断 → content-and-judgment.md
   - 语言 → language.md
   - 结构 → structure-and-formatting.md
   - 治理 → ssot-and-concept-cleanup.md
3. 参考 self-check.md 清单逐条核对。
4. 输出问题清单（位置、严重程度、依据、建议）。区分「只报告」与「可直接修改」。
5. 用户要求修改时，按规则执行。

红线与具体条文见 shared/rules/。
