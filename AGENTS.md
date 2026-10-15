# AGENTS.md

本仓库是 **skill 包**（不是产品应用）。在这里改的是规则文本和检查脚本。

## 文件与归属

**一个主题只在一个文件里写条文**；别处要用就写指针（`见 xxx.md §n`），不复制原文。

| 文件 | 负责 |
| --- | --- |
| `SKILL.md` | 入口：frontmatter、适用范围、工作顺序、红线、路由表。保持精简，不放细节。 |
| `references/content-and-judgment.md` | 事实与推断、证据与结论强度、范围、不确定状态、零值与缺失、计算可复核、模型权限、边界该不该写 |
| `references/structure-and-formatting.md` | 主线与章节、标题、段落、列表、表格语义、图表分工、跨章重复、篇幅分配、视觉层级、版式约束 |
| `references/language.md` | 句式与逻辑密度、用词、语义重复、否定、数字叙述、术语、内容来源、强调、括号、元话语 |
| `references/ssot-and-concept-cleanup.md` | 单一事实来源、已移除概念清理 |
| `references/latex-mechanics.md` | 宏、生成内容、文献、三线表与列型、图件样式、标签语法、中文排版、编译核对 |
| `references/self-check.md` | 提交前清单 |
| `scripts/lint_tex.py` | 机械检查 |
| `assets/` | 可复制进项目的模板，不是规则 |
| `README.md`、`CHANGELOG.md`、`LICENSE` | 介绍、更新记录、MIT 许可 |

## 规则

1. 不复制条文。同一句话存在两处，迟早漂移。
2. 抽象词表以 `references/language.md` §11 为准；`scripts/lint_tex.py` 的 `ABSTRACT` 只是它的投影，改词表两处一起改。
3. 保持通用：不写任何具体项目的仓库名、编号、真实数值、专有词表。
4. frontmatter 只用规范允许的字段，`name` 与目录名一致；加字段前先核对 agentskills.io 规范。
5. 增删 `references/`、`scripts/`、`assets/` 文件后，同步 `SKILL.md` 的路由表。
6. 增删小节后重排编号，并修正所有指向它的指针。
7. Git 只做本地提交；push、建远端、发 Release 需明确指示。发版前先把 `CHANGELOG.md` 的 `Unreleased` 改为版本号，再打 `v<版本号>` 标签——release 工作流会校验标签与 changelog 条目是否对应。

## 改完检查

- [ ] 各文件小节编号连续，无跳号或重号
- [ ] 所有 `` `xxx.md` §n `` 与 `见 §n` 指针都指向存在的章节
- [ ] `references/`、`scripts/`、`assets/` 无未被 `SKILL.md` 引用的文件
- [ ] 脚本词表与 `references/language.md` §11 逐字一致
- [ ] 通用性：没有具体项目痕迹

```bash
python3 scripts/lint_tex.py <含 .tex 的目录> --severity error
```
