# 从 PR4 迁移

基线为 Consciencieux/academic-writing PR4 的 `5f79dc1df2e704d0f7cb93dc97641065382a3429`。这是架构重整，不是只添加几份参考材料。请保留 Git 历史和自己的未提交改动。

交付压缩包外层提供 `apply_update.py` 与 `update-manifest.json`。在真实仓库上先运行检查，再明确 --apply；它按已核对的 Git blob 哈希检查旧文件，新增路径有冲突时拒绝覆盖，并只处理清单中的文件，不操作分支或提交。无需联网。

```bash
python /解压目录/apply_update.py /你的/academic-writing
python /解压目录/apply_update.py /你的/academic-writing --apply
```

工具在仓库外建立备份后更新。出现本地修改、版本不符、符号链接、目标路径冲突或摘要不符时停止；先保留/协调改动，不强制绕过。也可逐文件使用 `repository/` 中的新源码，但必须按清单删除退役文件，否则旧规范会继续被加载。

## 内容迁移

原 shared/rules 六份文件与目录 README 退役。内容进入 shared/core、shared/standards、shared/protocols、shared/tooling 以及 Guide/Audit 方法。原始五份材料的全部二级章节在 [coverage.md](coverage.md) 中有明确归属；有口径变化的地方标出理由，不用“原文完整保留”掩盖变更。

`skills/academic-writing/SKILL.md` 退役，根 SKILL.md 成为协调入口唯一源码，构建生成发布位置。Guide 原 chapter-methods、revision-workflows、examples 与 Audit 原 full-document-audit 由任务方法替换；内容不是继续附在旧文件后面。

lint 不再把正则命中作为硬性语义判决；分别检查静态根文件，代码环境不作为正文词句检查。默认退出码不被风格候选阻断。静态扫描能力不等同真实 TeX 解析或编译。

## 更新后

```bash
python -m unittest discover -s tests -v
python scripts/package_skills.py --check-only
python scripts/package_skills.py --output-dir dist
git diff --check
git status --short
```

该包不提交、不推送、不改原论文。自动测试与真实模型评估分开：运行来源见测试记录；模型初稿质量要用 evals 中的固定材料对比，不能从文件迁移成功推断。
