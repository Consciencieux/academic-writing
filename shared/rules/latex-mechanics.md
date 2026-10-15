# LaTeX 落地做法

把前面几份规则落到 `.tex` 上：哪些内容该抽成宏，表格和图怎么写，引用怎么保持唯一来源，改完怎么核对。

若项目已有 `latexmkrc`、`preamble.tex`、模板或 AGENTS.md 约定，以项目约定为准，本文件只给通用做法和常见陷阱。下面提到的目录划分、宏写法和编译配置是一套常见形态，可作为参考，不必照搬。

配套资源：`assets/preamble-zh.tex`、`assets/metadata-macros.tex`、`assets/table-and-figure.tex` 可直接改成项目起点；`scripts/lint_tex.py` 处理第 9 至 10 节里可机械判定的部分。

## 1 文件职责

常见划分：

| 文件／目录 | 职责 |
| --- | --- |
| `main.tex` | 入口：文档类、加载 preamble、元数据、正文装配 |
| `preamble.tex` | 版式设置：宏包、字体、间距、图件样式、列型定义 |
| 元数据区／`metadata.tex` | 项目字段与 PDF 元数据的宏定义 |
| `chapters/`、`frontmatter/`、`appendices/` | 正文、前置部分、附录 |
| `bibliography/*.bib` | 参考文献的权威来源 |
| `latexmkrc` | 构建配置（引擎、biber、输出目录） |
| `build/` | 编译产物，不入库 |

正文文件首行写 `% !TEX root = main.tex`（子目录中写成相对入口的路径，如 `../main.tex`），编辑器据此定位根文件。

拆分与合并本身不是目标：文件过大的理由应该是内容体量，而不是「结构看起来更正式」。

## 2 会变的值走宏，不在正文写死

正文里反复出现、且可能变化的数值、日期、版本、阈值、名称，应定义一次再引用。这是 SSOT 规则在 LaTeX 里的主要落点。

```latex
% 元数据区：定义一次
\newcommand{\ReportAsOf}{2026-01-01}
\newcommand{\ProjectNumber}{X000000000000}
\newcommand{\TargetConcurrentUsers}{100}
\newcommand{\TargetAccuracy}{90\%}

% 正文：只引用
截至 \ReportAsOf{}，并发指标仍为 \TargetConcurrentUsers{} 人。
```

要点：

- 宏是唯一维护点：改日期只改一处，正文所有出现位置同步。
- 正文不要出现与宏并存的同一个字面值；两处写法不一致时，读者无法判断哪个是当前口径。
- 百分号、下划线、`&`、`#`、`$` 在宏里要转义（`\%`、`\_`、`\&`、`\#`、`\$`）。
- 一个值只支持它实际覆盖的表述。宏解决了「值不一致」，不解决「把设计目标写成已实现能力」——后者仍受内容规则约束。

## 3 生成内容优先于手工誉抄

实验结果、统计数据、扫描得到的表格、逐条状态清单，优先由数据或脚本生成 `.tex`，正文用 `\input` 引入。

手工誉抄的表格有三个问题：转录错误、与数据源脱节、更新时需要人工比对。用生成文件时，脚本和数据是权威来源，`.tex` 是产物。

若暂时只能手工维护，至少让每个数字能指向它的来源，并在正文注明口径与范围。

## 4 参考文献

- `.bib` 是文献元数据的唯一权威来源。正文只写 `\cite{key}`，不复制作者、年份、标题、期刊到正文或表格里。
- 入口处一次性声明：`\addbibresource{bibliography/references.bib}`。
- 引用键名应稳定、可读；键名变更会导致全文引用失效。
- 引用必须真实对应所支持的内容。不要为了参考文献数量好看而添加无关来源。
- 一条来源只支持它实际覆盖的主张；来源整体权威，不等于它可以承担其中没有出现的细节。
- 长 URL 在两端对齐下容易出界，常见做法是让文献列表左对齐（`\AtBeginBibliography{\raggedright}`）而不是硬缩字号。

## 5 表格

表格的语义（该不该用、列行如何分工）归 `structure-and-formatting.md` §7，本节只讲 LaTeX 写法。

- 用 `booktabs` 的三线表（`\toprule`／`\midrule`／`\bottomrule`），不画竖线、不用双横线制造「正式感」。
- 定宽用 `tabularx`，配合自定义列型控制换行。可在 preamble 定义：

  ```latex
  \newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}  % 定宽左对齐
  \newcolumntype{Y}{>{\raggedright\arraybackslash}X}          % 自适应左对齐
  \newcolumntype{V}[1]{>{\hsize=#1\hsize}Y}                  % 按内容量加权的 Y 列
  ```

  `V` 列的权重之和应等于该表 `V` 列的列数，否则列宽计算会失衡。

- 长表格用 `\small` 之类缩小字号是版式手段，前提是信息关系已经确定；不要为了塞进一页而删掉必要的限定或合并不同逻辑。

## 6 图

- 图件样式集中在 preamble 定义（如 `\tikzset{...}`），各图只覆写尺寸和间距。样式散落在各图里会导致同一文档出现几种视觉不一致的箭头和盒子。
- `\caption` 回答「这是什么」；它说明什么、意味着什么写在正文。
- 图、表、正文不重复播报同一过程。流程已由图承载时，正文直接写原因、条件、结果或判断。
- 只提供装饰、没有新增信息的图不要加。
- 图内的文字是正文的一部分，同样受语言规则约束：不加装饰性引号，不把关键条件塞进图注括号。

## 7 标签与交叉引用

交叉引用的用法（编号何时使用、能否承担主要信息）归 `structure-and-formatting.md` §13，本节只讲 LaTeX 写法。

- `\label` 紧跟被引对象；`\ref`／`\eqref` 用于回查。
- 标签命名保持体系一致（如 `chap:`、`sec:`、`fig:`、`tab:` 前缀），避免重复标签。
- 编译后检查是否有未定义引用或重复标签（见 §9）。

## 8 中文排版要点

- `ctexbook`／`ctexart` 文档类配 `xelatex` 或 `lualatex` 编译，不要用 `pdflatex` 直接编译中文文档。
- 字体集通过文档类选项指定（示例用 `fontset=fandol`）；缺字体时优先改字体集选项，不要靠改字号或强行换行绕过。
- 中文与命令之间用 `{}` 隔开，避免宏吞掉后续空格或粘到汉字：`\ReportAsOf{} 核对`、`\ReportBatch{} 年`。
- 中文标点用全角（，。；：、），英文缩写与数字用半角；中英文之间按项目约定决定是否加空格，全文保持一致。
- 引号用中文引号或 LaTeX 的 ``` `` ```／`''`，同一篇内不混用。
- 长英文标识符、URL、路径是中文文档最常见的溢出源。示例项目在 preamble 设置 `\setlength{\emergencystretch}{5em}` 给断行留余量；若仍溢出，优先调整该设定或改用 `\path`、`\url` 等命令，而不是缩小正文字号。
- 代码、路径、提交号用等宽命令（`\texttt{}`、`\path{}`），不要用加粗或引号代替。

## 9 编译与核对

先看项目有没有 `latexmkrc`；有就以它为准，直接跑：

```bash
cd <文稿目录>
latexmk main.tex
```

示例项目的 `latexmkrc` 使用 `xelatex` 引擎、`biber` 处理文献、输出到 `build/`（中间文件在 `build/aux/`），成品为 `build/main.pdf`；清理用 `latexmk -C`。

核对清单：

- 编译是否零错误通过；`-halt-on-error` 下任何错误都会中断，先修错误再看版式。
- `LaTeX Warning: There were undefined references`／`Citation ... undefined`：引用或文献键写错，或需要再编译一轮。
- `Label(s) may have changed. Rerun to get cross-references right`：再跑一次，直到该警告消失。
- `Overfull \hbox`：溢出警告。优先检查长英文标识符、URL、过宽的表格列。
- 文献是否真的生成（`biber` 未运行成功时文献会整体缺失，但编译可能不报错）。
- PDF 元数据（`\hypersetup` 的 `pdftitle`／`pdfauthor` 等）是否与正文一致。

不要在核对阶段为了「编译通过」而改动事实、数字或判断（版式调整的约束见 `structure-and-formatting.md` §15）。

## 10 改动后的一致性扫描

本节只是 SSOT 规则在 LaTeX 文档上的**扫描清单**；规则本身（哪些内容要有权威来源、四种承接方式、判断标准）归 `ssot-and-concept-cleanup.md`。

改一个口径、术语、数值或结构时，做全文扫描，范围至少包括：`chapters/`、`frontmatter/`、`appendices/`、元数据区、`.bib`，以及与该文稿并行的填报文本或摘要。

扫描目标：

- 旧口径是否还有残留（同一个事实的两套说法）。
- 术语是否仍然统一（同一概念是否换了称谓）。
- 被移除的概念是否还在（见 `ssot-and-concept-cleanup.md`）。
- 交叉引用是否仍然指向正确的对象。
- 数值是否全部来自宏或生成文件，没有新写死的副本。

若同一处反复对不上，先判断是正文偏了还是权威来源偏了；权威来源（规范、证据目录、官方材料、代码）与实现或事实不符时，先改权威来源，再改正文。
