# 架构

## 执行角色

根 SKILL.md 协调任务。Guide 规划、成文和修订，Audit 通读并诊断。一个 Agent 可依任务顺序执行这些角色。

## 内容归属

六份标准分别负责证据、组织、语言、图表、引证和一致性。每份标准集中保存有关的判定、典型错误与例外。证据管主张成立，组织管内容位置，语言管句段表达，图表管视觉与行列，引证管来源支持，一致性管维护关系。

Guide 的六份方法按论证安排、成文修订、资料引证、图表、交付和章节任务组织。篇幅属于论证安排，章节任务提供第二导航轴。

成文目标集中在 shared/core.md。两个执行入口通过相对链接读取；同一会话中复用已读取的资源。加载规则由各执行入口定义，刷新事件由 shared/protocols/context.md 定义。

## 工具与分发

scripts/lint_tex.py 与 scripts/lint_text.py 共用 language_checks.py。抽象词表从语言标准读取。操作及结果处理见[文稿工具](../shared/tooling/documents.md)。

构建器将共享标准、方法和工具复制进独立 Skill，改写并检查相对链接。安装包按文件职责保留目录；维护文档与评估材料留在源码仓库。

## 维护

标准内容与具体判定相互对应，重组时一并检查例子和例外。对文章质量的评估使用[固定任务](../evals/README.md)。

Skill 格式依据 [Agent Skills 规范](https://agentskills.io/specification)。YAML 解析使用 [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation)。
