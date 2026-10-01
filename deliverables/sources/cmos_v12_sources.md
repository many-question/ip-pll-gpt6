# CMOS v12 来源

本轮为本项目电路仿真研究，没有新增外部工艺性能保证或文献数值。

- `jitter_v11`：CMOS有缓冲TSPC÷4、C2MOS对照和旧噪声积分/独立noise-on解析器。
- `transistor_v1/cells.scs`：180nm MOS反相器及9T TSPC拓扑。新TSPC重定时对宽度/扩散参数作比例缩放，未宣称标准单元或库级时序签核。
- `vco_v4/lc_vco_repaired.scs`：R2/Q5工作假设。新100/120µA偏置试案只在新TB显式覆盖，未更改旧默认参数或PDK无源假设。
- `accuracy_v7/tb/clamp8_mid_pss.scs`：quiet10采样接口、24MHz参考缓冲、实际采样器/CP/时序负载。本轮控制和CP输出钳位，因此不继承其闭环结论。
- `interface_v5/tank_waveform_v5.va`：已保存20次谐波RF电压回放；无源阻抗、无源噪声，不能当成完整LC噪声等效。
- Spectre21.1实际运行日志和PSF：采样边沿pnoise、Jee、器件STRUCT PSD及PSS检查。模型根文件SHA256为`d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`，本轮重新核对；完整输入/结果哈希在raw_manifest。

2026-10-02重新核实`jielu@thu-xia`可用，GUI隧道关闭但独立Spectre可用。使用项目`skills/eda-servers`及用户已有Spectre技能和环境。没有复制密钥、PDK或license到share。远端工程和全部回收数据保持在本项目范围。
