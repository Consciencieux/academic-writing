# Academic Writing

学术论文写作与审查的三 Skill 体系。以论证、证据和读者理解组织文章，避免依赖反复“生成—全篇检查—局部补丁”。

## 使用哪一个入口

| 任务 | Skill | 产物 |
| --- | --- | --- |
| 起草、续写、修改、篇幅规划、文献综合、图表、投稿整理 | academic-writing-guide | 实际正文/源文件及必要修改说明 |
| 全文通读、跨章结构与重复、证据/文献/图表检查 | academic-writing-audit | 只读诊断与明确处理判断 |
| 多步骤写作或检查后修订 | academic-writing | 协调上述角色，不另写一套方法 |

Guide 是正文的唯一编辑角色。Audit 可以给改法示例，但不修改文稿；联合请求由协调入口接续 Guide，不再让用户重复授权同一修改范围。角色不等于独立进程，不要求多 Agent。

## 内容怎么拆

- [共享核心](shared/core.md)：短的共同底线，自动同步到 Guide/Audit 入口。
- `shared/standards/`：按证据、组织、语言、图表、引证和事实一致性维护唯一判定标准；同时包含硬约束、条件要求和可调整默认值。
- `skills/academic-writing-guide/references/`：按当前要做的写作决定提供方法，文章各章节作为第二导航轴。
- `shared/protocols/`、`shared/tooling/`：上下文与角色交接、文稿工具的操作方式。
- `evals/`、`tests/`：模型行为用例与确定性测试；二者的通过含义不同。

篇幅归论证与章节规划，图表及引证有专项方法；它们不是独立 Skill。规则不按“正面/负面”分库，审查清单不另抄一套判定条文。详见[架构](docs/architecture.md)。

## 安装

```bash
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
```

默认使用 `dist/academic-writing-skills.zip`：解压后为三个并列的完整 Skill 目录，放入客户端实际支持的 Skills 目录。具体激活方式以客户端为准。`guide.zip` 和 `audit.zip` 的完整文件名分别为 `academic-writing-guide.zip`、`academic-writing-audit.zip`，用于只需要该角色的场景；专项包不假装另一角色已经安装。

仓库根 [SKILL.md](SKILL.md) 是协调入口源码，构建时放入 `academic-writing/`。所有安装包包含所需规则、方法、脚本和模板；构建器改写并验证真实相对链接。

仅复制 SKILL.md 不构成安装。直接从源码使用时应保留整个仓库布局。把[论文项目指令片段](assets/project-AGENTS.snippet.md)合并进论文自己的 AGENTS.md，可帮助持续选中正确角色；不要用本仓库的维护 AGENTS.md 覆盖论文项目。

## 维护与验证

修改共享核心后运行 `python scripts/package_skills.py --sync`，提交生成后的入口。标准使用稳定 ID 和显式锚点；修改口径同时更新相关 evals 用例和 CHANGELOG。

```bash
python -m unittest discover -s tests -v
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
```

[评估方案](evals/README.md)提供固定材料、任务和预期，包括正常表达的误报反例。自动测试可以检查包的结构与工具行为，不能证明模型初稿质量提高。请分别保留工具测试与真实模型运行记录，不把其中一种冒充另一种。

当前尚未正式发布。源码校验与模型行为评估分开记录，不以自动测试代替初稿质量判断。
