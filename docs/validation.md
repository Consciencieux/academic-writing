# 验证记录

## 已执行

- 28 项仓库回归测试通过：核心投影、标准 ID、行为用例结构、源码与安装包相对链接、Guide/Audit 资源、多根 TeX 隔离、代码环境屏蔽、引用候选与退出码。
- 三种安装 ZIP 已生成、解包并校验链接。相同本地工具链连续构建的字节相同。
- GitHub Actions `Validate Skills` 在 Ubuntu、Windows、macOS 上通过（[run 38915095937](https://github.com/Consciencieux/academic-writing/actions/runs/38915095937)），内容为语法检查、unittest、源码校验与三种安装包构建。
- 中文 LaTeX 模板片段曾用 XeLaTeX/latexmk 编译为一页 PDF，引用已解析；最终日志没有 Warning、undefined 或 Overfull 提示。

## 未执行

- 模型行为用例尚未在真实客户端上运行，不能据自动测试声称初稿质量或长期遵循率已提高。
- 没有测试所有客户端的安装/自动激活，也没有把模板 smoke test 表述为任意论文都能编译。

下一步是按 evals 的同一材料和任务记录真实模型输出、误报/漏报、人工修订量与加载成本，再用结果调整方法和示例。
