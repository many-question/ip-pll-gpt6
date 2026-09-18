# 本轮工具与语言依据

访问日期：2026-09-18。

- [Accellera Verilog-AMS 标准下载页](https://www.accellera.org/downloads/standards/v-ams)：语言官方发布源。
- [Accellera Verilog-AMS LRM 2023](https://www.accellera.org/images/downloads/standards/v-ams/VAMS-LRM-2023.pdf)：参考模拟事件、`cross`、`timer`、`transition` 和 `idtmod` 的语义。本项目使用保守的 Verilog-A 子集；实际兼容性由服务器 Spectre 21.1.0.509.isr12 的编译和测试验证。
- 项目 `skills/eda-servers/SKILL.md`、`skills/virtuoso/SKILL.md` 与已安装 `spectre/SKILL.md` 及其 netlist/parallel 参考：核验 SSH、网表运行及结果回收流程。实际 Python API 通过已安装 `virtuoso_bridge.spectre.runner` 源码核实。

FLL 算法、测试网表和模块行为代码为本项目实现；其数值参数沿用候选 B 或在本轮明确标注为工作假设，不是文献给出的工艺性能，也不声称来自晶体管提取。
