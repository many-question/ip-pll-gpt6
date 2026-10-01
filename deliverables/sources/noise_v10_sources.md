# noise_v10 来源和开关验证

使用日期：2026-10-02。

- 已安装 Spectre 21.1.0.509.isr12 的 `spectre -h options`：本地 `research/spectre_help/options_noise_v10.txt`。确认 `noiseon_inst`、`noiseoff_inst` 适用于 pnoise，噪声类型选择为 all。本轮日志进一步明确两种实例列表互斥，后续只填写其中一种。
- [Cadence 官方论坛：How to make a block Noise-less while doing Noise analysis in Spectre](https://community.cadence.com/cadence_technology_forums/f/rf-design/32451/how-to-make-a-block-noise-less-while-doing-noise-analysis-in-spectre)：确认可按子电路实例选择噪声，文本网表使用点分层次名。实际开关语义最终以本轮安装版本的日志、全关和逐项贡献检验为准。
- 本项目 `output_v9` 已发布电路、粗/细网格 PSS 与器件噪声原始 PSF：基线为原极性、scale2 双 CML 和四级 AC 恢复/末级驱动。v9 粗网格用于相同设置的逐项对照，不能把 v9 精度通过转移给修改后的电路。
- 本项目 `interface_v5/tank_waveform_v5.va` 的既有仿真 VCO 电压形状回放。该源为理想无噪声电压源，不能代表实际 VCO 阻抗、噪声、Q 或加载功耗。
- 指定服务器 PDK 顶层 `c018bcd_gen2_v1d6.scs` 本轮再次核对 SHA-256：`d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。使用 TT、stat_noise、tt_bbmvar；不发布模型。

本轮变更为自有电路的定向试验，不借用外部论文指标。不通过理想器件替换来关噪声；保留完整确定性电路和负载，逐一核查相同周期工作点、关闭分区的零贡献以及独立谱的方差闭合。偏置发生器、实际 VCO、参考/主环路和 FLL 不在这个输出夹具中。
