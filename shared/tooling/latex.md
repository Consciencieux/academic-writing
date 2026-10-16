# LaTeX 操作

## 构建

读取文稿项目的 AGENTS、主 .tex、latexmkrc、文献和图件配置。使用项目现有构建命令；新中文文稿可使用 XeLaTeX 或 LuaLaTeX。

```bash
latexmk -xelatex main.tex
python /path/to/skill/scripts/lint_tex.py . --json
```

根据项目设置选择引擎和主文件。检查编译日志里的未定义引用、书目缺失、重复标签和溢出，确认文献处理程序实际执行。动态包含、外部标签和宏展开结合主文件与编译结果定位。

## 数据与引用

同一可变事实用宏、\input 或生成表承接唯一来源。图表由数据和脚本生成，.bib 维护文献元数据。正文使用目标体例需要的作者式引用或编号引用。

标签放在 caption 或相应编号对象之后，通过引用命令回指。路径、URL、单位与数学符号使用已加载宏包的命令；编辑后核对转义及断行。

## 模板与成品

[中文导言](../../assets/preamble-zh.tex)、[元数据](../../assets/metadata-macros.tex)、[表图片段](../../assets/table-and-figure.tex)供新文稿起步，投稿稿件使用目标模板。

构建后按[文稿工具](documents.md)处理结果并查看页面，特别检查表宽、跨页表头、正文强调、图注和引用定位。
