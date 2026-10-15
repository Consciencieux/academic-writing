# AGENTS.md

本仓库是 **多 Skill 体系**。规则只存在于 `shared/`，各 Skill 的 SKILL.md 只写流程并用指针引用。

## 结构

- `skills/<name>/SKILL.md`：可独立发现的 Skill 入口。
- `shared/`：规则权威源（SSOT）。禁止在 Skill 内复制条文。
- `scripts/`：机械检查与构建脚本。
- `assets/`：模板。

## 规则

1. 同一主题只在 `shared/` 写一次；Skill 内只用指针（`见 shared/xxx.md §n`）。
2. 增删 Skill 后更新本文件与 README。
3. 构建脚本负责把 shared 中所需规则打包进各 Skill 的安装包。
4. 保持通用，不写具体项目数据。

改完后检查指针有效、无复制条文、构建通过。
