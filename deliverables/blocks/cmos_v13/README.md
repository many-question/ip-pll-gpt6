# CMOS v13 电路

当前TT优化候选采用`rf_cc4_v13.scs`、原`jitter_v11/cmos_tspc_buffered_v11.scs`、`rtcomb_v13.scs`。拓扑仍为单级RF反相器、有缓冲9T TSPC固定÷4、9T TSPC重定时和两级输出缓冲。慢角未签核。

| 子电路 | 引脚 | 相对v12的变化 |
|---|---|---|
| rf_cc4_v13 | rf clk vdd vss | AC电容1→4pF，WN32/WP80µm、R20kΩ保持 |
| rtcomb_v13 | data clk out vdd vss | scale2/oscale2；FF MN1/MNC1为4.8µm、MP2为6µm；首缓冲WN3.2/WP4µm |
| rtout_v13 / rtpre_v13 | 同上 | 分别只修改输出支路或中间评估支路，用作受控对照 |

MOS长度均180nm，修改宽度时同步更新扩散面积和周长表达式。输出仍相对TSPC输入数据反相；本轮验收连续÷4时钟，不代表任意数据、复位和使能功能签核。电容、电阻、输出10fF和电感RLC仍是项目既定工作假设，4pF电容面积和PEX待落实。

其余文件是保留的失败或未采用研究试案：更宽/短链/交叉耦合RF接收器，分频缓冲门限/强度/级数变化，首FF局部尺寸，复位MOS，以及ratioed7T首FF。它们不能替代上述TT候选，也不能因存在网表而称已实现合格PVT方案。

`ratio7k1/ratio7k2`拓扑参考[Razavi, TSPC Logic, Fig.8](https://seas.ucla.edu/brweb/papers/Journals/BRFall16TSPC.pdf)，采用本项目自行选择的器件尺寸；试验出现错误分频，未采用，无性能数字迁移。

测量条件、实际LC负载、独立noise-on、失败原因与证据见[集成验证](../../integration/cmos_v13/README.md)。
