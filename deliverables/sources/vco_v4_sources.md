# VCO 修复的来源与计算边界

1. 人类在本项目对话中要求先修复 VCO，并已允许在 PDK 缺少电感时采用常见 RLC 网络和文献 Q 作初步建模。既有需求和验收边界保持不变，见 DEC-0001…0005。
2. 电感网络及 Q 的文献出处沿用 [v3 来源记录](transistor_v3_sources.md)。本轮未把 Q 从 5 提高来换取通过结果；Q=3/8 仍仅作敏感性研究。MOS 尺寸、电容分配、底板 PMOS 和分段尾电流均为本项目自行设计、通过仿真选择的参数。
3. PDK 根模型文件 `c018bcd_gen2_v1d6.scs` 的 SHA-256 再次核实为 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。使用既有 TSMC180BCD Gen2 `nch`、`pch`、`nmoscap` 接口及 tt/ss/ff、对应 bbmvar 角。PDK 正文不进入交付仓库。
4. [Cadence：How to Migrate to Spectre X](https://community.cadence.com/cadence_blogs_8/b/cic/posts/spectre-tech-tips-how-to-migrate-to-spectre-x) 与 [Using the Spectre Strobe Feature](https://community.cadence.com/cadence_blogs_8/b/cic/posts/spectre-tech-tips-using-the-spectre-strobe-feature)：确认 Spectre X 默认可能忽略 `maxstep`，需 `-preset_override=maxstep`。本项目保留了未覆盖该设置时的频率偏差，随后以实际日志检查生效参数，并与严格 APS 运行比较；不能仅凭网表里的数值宣称精度。
5. [Cadence 关于振荡器加分频器的 PSS 讨论](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/48474/pll-pss-pnoise-convergence/1376874)：采用最低频率输出作自主 PSS 的振荡节点，并按公共基频选择 Pnoise 相应谐波。完整 PLL 有外部参考时则是受驱系统，不能套用该自主设置。收敛由本项目实际结果判断，来源本身不是仿真通过证据。
6. 实际 Spectre 版本的 `pss` / `pnoise` 帮助保存在项目内部 `research/spectre_help/`。PM 输出沿用已核实的 SSB 约定，以差分基波峰值的平方除以 2 作载波功率归一化；逐器件 PSD 求和另行交叉检查。未将独立振荡器相噪积分冒充 PLL 输出抖动。
7. 小信号启动检查为本项目独立推导：对称 DC 点注入差分 AC 电流，求 `Ydiff=I/(vp-vn)`，在虚部过零处提取实部；同时将核心两端的漏、栅端口电流计入有源负电导，分离其余损耗。增益比大于 1 是局部启动条件，不代替实际加载的幅度和分频验证。

上述网页于 2026-09-18/19 查阅；运行日志、输入 hash、实际器件和波形结果是本轮数值结论的直接证据。
