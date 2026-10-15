---
name: academic-writing
description: >-
  学术写作全流程协调入口。判断用户当前处于论文写作的哪个阶段，调度对应的专业 Skill。
  用于从头写作、不确定先做什么、或需要跨模块协同的场景。
  不做具体规则审查，也不做正面写作指导。
compatibility: >-
  scripts/lint_tex.py 需要 Python 3.8+，无第三方依赖。
  中文文稿用 xelatex 或 lualatex，不要用 pdflatex。
---

# 学术写作（总入口）

负责流程协调与路由，不复制具体规则，不执行审查或写作。

## 何时使用

- 从头写一篇论文，不确定先做什么
- 需要跨多个专业模块协同
- 只改一段或一个具体任务时，直接进入对应专业 Skill，不经过本入口

## 流程

1. 研究问题与写作目标
2. 论证与证据规划
3. 结构与篇幅规划 → 调用 guide
4. 章节写作与图表设计 → 调用 guide
5. 规则审查与修订 → 调用 academic-writing-audit
6. 格式与提交前检查

## 调用

| 任务 | Skill |
| --- | --- |
| 审查已有文稿（证据、语言、结构、SSOT） | `skills/academic-writing-audit` |
| 正面写作指导（从提纲到正文） | `skills/academic-writing-guide` |

规则权威源见 `shared/rules/`。各 Skill 只用指针引用，不复制条文。
