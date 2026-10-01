# output_v8 来源与条件

访问/验证日期：2026-10-01。

1. 本项目 `transistor_v2/retimer_scaled.scs`、`receiver.scs`、`limiter_chain.scs`，以及 `closure_v6/divider_bank_v6_clamp.scs`：复用已有项目自有晶体管电路。先前理想时钟的噪声结果只作历史背景，未用来替代此次实际接收器结果。
2. 本项目 `interface_v5/tank_waveform_v5.va` 及该轮来源说明：回放既有实测形状的差分VCO电压，3.936 GHz。是理想无噪声电压源，不是实际VCO阻抗、输出功耗或噪声模型。
3. 指定服务器 PDK `c018bcd_gen2_v1d6.scs`，顶层SHA-256 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。使用TT、stat_noise与tt_bbmvar；仅存引用和运行证据，不分发工艺模型。
4. 已安装 Spectre 21.1.0.509.isr12 的PSS、pnoise、jitterevent、命令行帮助：本地项目 `research/spectre_help/`。显式检查实际日志中的maxstep、reltol、traponly和绝对容差。裸 `-preset_override` 为安装版帮助规定的全选项覆盖形式。
5. 本轮 `accuracy_v7` 的RC采样归一化检查：提示在PSS基频低于输出频率时Jee自动积分上限可能不等于目标带宽。本轮输出fixture采用984 MHz PSS/ratio1，仍独立读取ASD与slew，显式积分10 kHz–492 MHz并比较Jee。

新接收器为本项目试验性电路，未声称源于已发表的达标设计。电阻/电容理想，偏置电流源发生器、实际参考源、RF源阻抗与布局寄生未纳入。所有模块噪声贡献由PSF器件STRUCT的total PSD求和并校验，不以缺失值代替零。
