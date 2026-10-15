---
name: academic-writing
description: >-
  学术写作全流程协调入口。判断用户当前处于论文写作的哪个阶段，调度对应的专业 Skill（audit / guide / length / figures 等）。
  用于从头写作、不确定先做什么、或需要跨模块协同的场景。
---

# 学术写作（总入口）

负责流程协调，不复制具体规则。

## 流程

1. 研究问题与写作目标
2. 论证与证据规划
3. 结构与篇幅规划 → 调用 guide / length
4. 章节写作与图表设计 → 调用 guide / figures
5. 规则审查与修订 → 调用 audit
6. 格式与提交前检查

用户只修改一段时，直接进入对应专业 Skill。

## 调用

- 审查已有文稿 → academic-writing-audit
- 正面写作指导 → academic-writing-guide
- 篇幅规划 → academic-writing-length（待建）
- 图表设计 → academic-writing-figures（待建）

规则详见 `shared/`。
