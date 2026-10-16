# 维护本仓库

改 Skill 的标准、方法、入口或打包逻辑时看这里。写论文请用安装后的 Skill，不要用本文件当写作提示词。Agent 改本仓库时同时遵循 [AGENTS.md](AGENTS.md)。内容归属见[架构](docs/architecture.md)。

## 命令

需要 Python 3.11 或更新版本：

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
```

`requirements.txt` 只服务构建（PyYAML）。安装包里的正文检查器使用标准库。`dist/` 不入库。

## 改动范围

- 成文目标只改 `shared/core.md`；Guide 和 Audit 入口链接它。
- 判定口径改对应 `shared/standards/` 文件，并更新相关 evals 用例。
- 加载表改执行入口；刷新事件改 `shared/protocols/context.md`；工具结果处理改 `shared/tooling/documents.md`。
- 使用者可见的行为变化写入 `CHANGELOG.md` 的 Unreleased。发版时把它收进带日期的版本节，再打 `vMAJOR.MINOR.PATCH` 标签。
