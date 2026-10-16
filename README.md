# 学术写作 Skill 体系

面向 AI 的学术写作工作流：总入口负责路由，Guide 以正向方法生成正文，Audit 独立检查已有文稿；具体判定规范只在 `shared/rules/` 维护一次。

## 结构

```text
academic-writing/
├── SKILL.md                               # 源码仓库总入口（薄路由）
├── skills/
│   ├── academic-writing/SKILL.md          # 可独立发现的总入口
│   ├── academic-writing-guide/
│   │   ├── SKILL.md                       # 核心写作契约与规则加载
│   │   └── references/                   # 章节方法、修订方法、示例
│   └── academic-writing-audit/
│       ├── SKILL.md                       # 局部/全文审查入口
│       └── references/                   # 全文审查方法
├── shared/rules/                          # 规则权威来源（SSOT）
├── scripts/lint_tex.py                    # LaTeX 机械检查
├── scripts/package_skills.py              # 独立 Skill 安装包生成
├── assets/                                # 中文 LaTeX 模板
└── tests/manual-evals.md                  # 人工验收场景
```

## 如何使用

- **论文起草、改写、扩写、压缩或润色**：调用 `academic-writing-guide`。它在开始时读取适用的事实、语言与结构规则，先组织论证再生成正文。
- **整篇论文通读、检查章节职责/重复/篇幅/工程材料泄露**：调用 `academic-writing-audit` 的全文模式。长篇文稿可以分批读，但未实际读完不能宣称完成全文审查。
- **从研究问题开始规划全流程**：调用 `academic-writing` 总入口，由它路由到 Guide 或 Audit。

独立审查不是每一段写作的默认步骤。规范用于写作过程中形成成熟文本，Audit 留给用户指定的审查、完整章节、重大结构变化和交付前检查。

## 本地生成可安装包

需 Python 3.8+，不需要第三方依赖：

```bash
python3 scripts/package_skills.py --check-only
python3 scripts/package_skills.py --output-dir dist
```

生成三个 ZIP：

- `academic-writing-guide.zip`：可单独安装的 Guide，包含它需要的共享规则。
- `academic-writing-audit.zip`：可单独安装的 Audit，包含共享规则、lint 脚本和模板。
- `academic-writing-skills.zip`：包含并列的 `academic-writing`、`academic-writing-guide`、`academic-writing-audit` 三个 Skill 目录。

单 Skill ZIP 包含唯一的同名顶层目录，适合按 Agent Skills 格式安装。合集 ZIP 解压后是三个并列的 Skill 目录；对支持本地文件系统技能目录发现的客户端，可将它们放入该客户端扫描的 Skills 目录。具体发现位置和激活方式以客户端文档为准。

**共享规则仍然只有一个源码维护点**：`shared/rules/`。打包时生成的 `references/rules/` 是发布产物中的只读副本，不回填到源码仓库；它让 Skill 离开本仓库后仍能访问规则。

对于直接使用源代码目录的 Agent，Guide 与 Audit 将从 `../../shared/rules/` 寻找规则；独立包中的它们从 `references/rules/` 寻找。仅复制单个 `SKILL.md` 文件不能构成完整安装。

## 校验与发版

GitHub PR 和推送到 `main` 会执行 `Validate Skills`，校验 Skills 和打包结构。正式 Release 由 `v*` 标签触发；发版前先在 `CHANGELOG.md` 添加与标签匹配的版本条目。

可用 [人工验收用例](tests/manual-evals.md) 检查模型是否真的读取文件、正确路由并处理跨章节语义问题。规则加载和执行规范可以提高一致性，但仍应通过实际论文结果检验效果。

更多维护约定见 [AGENTS.md](AGENTS.md)。
