# Academic Writing

中文学术论文写作与审查。提供成文方法、详细语言与证据标准，以及 TeX、Markdown 候选检查工具。

## 入口

- [Guide](skills/academic-writing-guide/SKILL.md)：规划、写作、续写、润色、图表、引证和内容修订。
- [Audit](skills/academic-writing-audit/SKILL.md)：通读、核对、诊断与处理建议。
- [协调入口](SKILL.md)：安排多步骤任务及写作、审查的交接。

## 安装

使用 Python 3.11 或更新版本，在仓库根目录执行：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
```

`dist/academic-writing-skills.zip` 包含三个并列的完整 Skill 目录。将它们放入客户端支持的 Skills 位置即可使用。`academic-writing-guide.zip`、`academic-writing-audit.zip` 提供单角色安装。

论文项目可以合并[项目指令片段](assets/project-AGENTS.snippet.md)。直接使用仓库源码时保留其目录布局。安装包内的正文候选检查器使用 Python 标准库；构建依赖列在 requirements.txt。

## 工具与维护

工具命令、覆盖范围和结果处理见[文稿工具](shared/tooling/documents.md)，TeX 构建见[LaTeX 操作](shared/tooling/latex.md)。

[架构](docs/architecture.md)说明各类内容的归属。[评估方案](evals/README.md)提供真实写作任务和评审方法。
