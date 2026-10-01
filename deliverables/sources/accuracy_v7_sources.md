# accuracy_v7 使用的资料和工程依据

本轮以项目已有电路、原始仿真及本机可用的 Spectre 帮助为依据，另核对 Cadence 官方站点的采样噪声测量说明；未改变电感 Q 假设。

- 需求：受保护的 `kickstart/02_project_design_brief.md`，以及 `share/reports/decisions/` 中已有团队决定。抖动积分为 10 kHz–输出频率一半，暂不包括离散杂散。
- 前轮失败和通过项：[closure_v6](../integration/closure_v6/README.md)。保留 4 µs 精度失败，不用后续窗口改写它。
- 仿真器说明：项目保存的 `research/spectre_help/pss.txt`，当前服务器安装版 Spectre 的 `-h pss` 输出。有关周期射击起点的说明位于 585–600 行，支持比较不同 tstab 起点；有关积分与误差容限位于 642–677 行。它提供工具语义，不保证本电路会收敛。
- 观察器代码：[lc_loop_observer.va](../blocks/interface_v5/lc_loop_observer.va)。输入没有电流贡献，但 `cross(...,1f,1u)` 会请求事件定位；因此使用密集波形独立插值，并比较保留/移除观察器两组。
- 工艺模型：服务器指定的 TSMC180 BCD Gen2，根模型 SHA-256 为 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。不向交付目录复制工艺文件。

运行后的有效参数以每次 `spectre.out` 为准。当前流程显式覆盖 maxstep/reltol/method/errpreset；实际绝对容差仍需从日志读取，不能把网表请求值当作实际生效值。

另读取安装版命令帮助，保存为 `research/spectre_help/command_accuracy_v7.txt`。其422–427行说明裸 `-preset_override` 会保留全部网表选项；对应试案日志确认100 nV/100 fA绝对容差。原选择性覆盖试案保持1 µV/1 pA。两者的errpreset标签仍为moderate，不把网表中的conservative文字当成实际生效。

## 采样率与周期噪声的核查

访问日期：2026-10-01。

- Cadence 官方博客，[Spectre Tech Tips: Measuring Noise in Digital Circuits](https://community.cadence.com/cadence_blogs_8/b/cic/posts/spectre-tech-tips-measuring-noise-in-digital-circuits)。支持数字边沿使用 sampled Edge Crossing、按边沿斜率转成时间噪声的测量选择；不提供本项目性能证据。
- Cadence 官方论坛，[Phase noise and jitter simulation](https://community.cadence.com/cadence_technology_forums/f/rf-design/47558/phase-noise-and-jitter-simulation/1372822)。讨论 PSS 基频与被测时钟频率不同时的 sample ratio 和相位/时间量纲。用于提出比值核查，不把论坛例子的数值移植为设计指标。
- 本机安装版 `research/spectre_help/pnoise.txt` 明确定义 sampleratio 为采样频率除以 PSS fund。对本项目最高档，984/24=41；这一换算须结合真实周期波形和所选边沿验证。

新增的 RC 仿真只校验测量归一化：相同984 MHz正弦经过1 kΩ/20 fF，比较 PSS984 MHz+ratio1 与 PSS24 MHz+ratio41，并以 ratio1+24 MHz 的错误积分带宽作为反例。热噪声用一阶 RC 的解析采样谱与 kT/C 交叉核算。真实 PLL 一个参考周期内的边沿斜率和噪声可能不同，此 fixture 不足以签核其所有边沿的噪声。

仅记录链接和有限的技术释义，不分发第三方培训材料或受限文档副本。
