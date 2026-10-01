# CMOS低摆幅接口与TSPC重定时器

当前TT研究候选：`rf_one32_v12.scs` + 既有 `jitter_v11/cmos_tspc_buffered_v11.scs` + `tspc_retimer_v12.scs`。只实现固定÷4，未完成六档控制、确定复位/停钟保持或PVT签核。

| 子电路 | 引脚 | 电路与当前参数 |
|---|---|---|
| rf_one32_v12 | rf clk vdd vss | C=1pF耦合，R=20kΩ输出到输入自偏置；反相器WN32µm/WP80µm，L180nm |
| cmos_tspc_buffered_v11（既有） | clk q1 data vdd vss | 两个TSPC÷2，级间隔离缓冲；RF到data为÷4 |
| tspc_retimer_v12 | data clk out vdd vss | 9T TSPC，scale2；两个输出反相器oscale2，外部10fF |

`tspc_inv_v12`沿用项目中9T TSPC拓扑，将MOS宽度和扩散面积/周长参数化。重定时输出相对输入数据逻辑反相；本轮验证的是连续时钟分频与边沿输出，不是任意数据/使能序列功能。内部动态节点无新增保持器。

接收器直接驱动分频及重定时时钟，真实电容负载不可省略。加大重定时单元到scale3/4的试案没有获得有效噪声结果，不能直接采用。单级接收器慢角摆幅不足；已连接实际LC的TT候选使用新TB显式`ibias=100u`，旧VCO R2源文件和80µA默认值保持原样。

目录中其余`rf_*`网表是完整保存的探索试案，不代表推荐设计。多级DC链多数功能失败，多级AC链即便功能通过也有ps量级附加噪声；各自输入、结果和排除原因见[集成验证](../../integration/cmos_v12/README.md)。

电阻、电容和电感RLC仍按项目既定工作假设；MOS来自项目PDK。偏置发生器、布局寄生、可靠性和面积未完成。
