# Academic Writing

中文学术论文写作与审查。重点处理黑话、电报体、装饰性加粗、长句与括号堆叠、表格滥用、章节重复和内容删除不彻底。

## 使用

- `academic-writing-guide`：规划、写作、续写、修订、图表、引证和完整删除。
- `academic-writing-audit`：只读通读与诊断，输出位置、依据和明确处理建议。
- `academic-writing`：多步骤任务协调；检查并修改时按已有授权交接。

同一个 Agent 可顺序执行这些角色。普通段落写作不逐段启动独立全文审查。

## 规则怎样进入写作

执行入口内嵌[短核心](shared/core.md)。凡生成中文正文、相关工作、摘要、图注或表内说明，完整读取[语言规则](shared/standards/prose.md)和成文方法；再按当前动作读取内容判断、组织、图表、引证或删除要求。

详细规范保留具体词表、错误句式、例外和判定测试。默认不把所有文件一次读进上下文，也不靠一句“保持自然”代替规范。章节切换刷新当前问题与短核心，上下文重置后重读必需资源。具体结构见[架构说明](docs/architecture.md)。

## 构建与安装

使用 Python 3.11 或更新版本，运行：

```bash
python -m unittest discover -s tests -v
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
```

生成 `academic-writing-guide.zip`、`academic-writing-audit.zip` 和 `academic-writing-skills.zip`。合集解压为三个并列 Skill 目录；按客户端支持的方式安装完整目录，不能只复制 SKILL.md。

各执行包包含完整标准、方法、工具和模板；资源路径在构建时改写并检查。论文项目可采用[项目指令片段](assets/project-AGENTS.snippet.md)，不要把本仓库维护指令覆盖到论文项目。

## 候选检查

```bash
python /path/to/skill/scripts/lint_tex.py /path/to/paper
python /path/to/skill/scripts/lint_text.py /path/to/paper.md
```

默认显示语言候选。`--severity warn` 可筛选显示级别，`--fail-on warn` 可提高失败门槛；候选仍须结合语义核对。Markdown/纯文本和 TeX 共用中文模式检查，支持代码屏蔽、普通正文加粗、抽象词、短语堆叠、括号、重复提示与长表单元格等。

这些工具不进行语义自动改写，不承诺识别所有坏句。完整删除按[CONS-04](shared/standards/consistency.md#cons-04)搜索实际授权范围及别名，并复查文本、文件名和相关生成物。

## 维护与实际评估

修改核心后执行 `python scripts/package_skills.py --sync`。规范内容改动时更新对应候选和[行为用例](evals/README.md)，不得只验证“还有这个关键词”。

自动测试与模型行为测试分开：前者验证文件和工具，后者记录初稿、误报/漏报、中文自然度、规则读取以及长任务退化。本仓库不以静态测试通过宣称模型已充分遵守全部规则。
