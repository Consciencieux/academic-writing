# 学术写作

> 面向 AI 的学术写作 skill：内容与判断、结构与呈现、语言、单一事实来源、已移除概念清理，附机械检查脚本与可复用模板。

## 这是什么

写学术论文、研究报告、开题与结题材料、方案、总结、说明、调研、分析时的规则集与配套工具。当前以 LaTeX 为主要实现层，规则本身不依赖具体排版工具。它约束三件事：

- **写什么**：事实与推断分离、证据决定结论强度、结论与范围匹配、缺失不等于 0、来源冲突不静默解决、计算可复核。
- **怎么组织**：章节与主线、标题、段落、列表、表格语义、图与正文分工、跨章重复、篇幅分配、空栏目。
- **怎么表达**：模板腔、语义回环、否定尾巴、括号堆叠、抽象词、电报体、术语泄漏、内容来源混入。

外加一层文档治理：同一个事实只维护一处（宏／`\input`／`.bib`／生成文件），删除概念就是彻底删除。

## 目录结构

```text
academic-writing/
├── SKILL.md                     入口：适用范围、工作顺序、红线、按需加载路由
├── references/                  规则正文，按主题分开，用哪块读哪块
│   ├── content-and-judgment.md      事实、证据、判断强度、计算、模型权限
│   ├── structure-and-formatting.md  章节、标题、段落、表格、图、篇幅、版式
│   ├── language.md                  句式、用词、重复、否定、括号、内容来源
│   ├── ssot-and-concept-cleanup.md  单一事实来源与已移除概念清理
│   ├── latex-mechanics.md           宏、文献、三线表、中文排版、编译核对
│   └── self-check.md                提交前检查清单
├── scripts/
│   └── lint_tex.py              机械检查（无第三方依赖，Python 3.8+）
└── assets/                      可复制进项目的起始文件，不是规则
    ├── preamble-zh.tex              中文文稿 preamble（含 L／Y／V 列型）
    ├── metadata-macros.tex          元数据宏模板
    └── table-and-figure.tex         三线表与图件骨架
```

## 安装

放到 agent 会扫描的 skill 根目录下。目录名需与 `SKILL.md` 的 `name` 一致。

| 作用范围 | 路径 |
| --- | --- |
| 全局（所有工作区） | `~/.dsh/skills/academic-writing/` |
| 全局（agents 约定） | `~/.agents/skills/academic-writing/` |
| 单个项目 | `<项目根>/.dsh/skills/academic-writing/` |
| 单个项目（agents 约定） | `<项目根>/.agents/skills/academic-writing/` |

项目根指最近一个含 `.git` 的上级目录。也可以只建软链，源文件留在本仓库：

```bash
ln -s /path/to/academic-writing ~/.dsh/skills/academic-writing
```

扫描只认 skill 根目录下的直接子项（`<名>/SKILL.md`），嵌套的 `**/SKILL.md` 不会被发现。

## 使用

写或改 `.tex` 正文时加载本 skill。`SKILL.md` 里是工作顺序与红线；需要哪一块时，按其中的路由表打开 `references/` 对应文件。

机械检查：

```bash
# 交付前自查（报告 info 及以上）
python3 scripts/lint_tex.py <文稿目录或 main.tex>

# CI 或提交门禁：只在 error 时失败
python3 scripts/lint_tex.py <文稿目录> --severity error
```

检查项包括：结论强度词、因果表述、缺失被写成 0、元话语与过程播报、填空腔标签、否定尾巴、括号与破折号堆叠、内部术语、装饰性加粗、重复标签、未定义引用与文献键、**宏已定义的值又在正文写死（SSOT）**，以及**不在编译闭包内的残留 `.tex`**。

项目级检查从 `\documentclass` 根文件沿 `\input`／`\include` 展开，因此未被引用的历史拆分文件不会被误报为重复标签，而是单独提示为「第二维护点」。退出码 0 表示无命中，1 表示有命中。

脚本只覆盖可机械判定的部分；语义、证据与判断仍须按 `references/` 人工核对。

## 设计约束

- **通用**：不含任何具体项目的数据、仓库名或专有词表。
- **单一维护点**：每个主题只有一个归属文件，其他位置只给指针；`references/language.md` §11 的抽象词表是权威，`scripts/lint_tex.py` 里的词表只是它的投影。
- **按需加载**：`SKILL.md` 保持精简，细节放在 `references/`。

改这个仓库之前先读 [AGENTS.md](AGENTS.md)：里面是各文件的负责范围、硬规则和改完之后的检查项。

## 许可

MIT，见 [LICENSE](LICENSE)。
