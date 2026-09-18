# Spectre 顶层行为验证

本交付包含 10 个功能模块的 Verilog-A、一个独立 TB 监视器、53 份 Spectre 网表、运行/测量脚本。目标是跑通真实反馈连接、自主捕获和输出链。**证据等级为行为仿真，不是 TSMC180 晶体管级性能验证。**

主环直接采样差分 VCO 波形，以脉冲电流驱动连续时间无源 R/C 滤波器。辅助 FLL 使用实际 VCO 时钟计数完成粗调、模拟预充和交接。输出只由同一 VCO 进行对称计数分频及下降沿重定时产生。TB 中 `pll_monitor` 从输出边沿独立测频、测占空比，不参与 PLL 控制。

## 复现

在项目根目录，使用已安装的 virtuoso-bridge 及已配置的用户级连接环境。脚本不创建项目 `.env`。服务器工作根固定在项目授权的 `/home/jielu/TSMC180/MP/IP-PLL-GPT6/simulation/va_v1`，每次计算使用独立子目录。

```powershell
python share/deliverables/integration/va_v1/build_tb.py
python share/deliverables/integration/va_v1/run_spectre.py --run-id newmodules --suite modules
python share/deliverables/integration/va_v1/run_spectre.py --run-id newtop --suite top
python share/deliverables/integration/va_v1/analyze.py --runs newmodules newtop --out research/runs/spectre_va/validation_new.json
```

`run-id` 必须未使用过。`--cases top_k41` 可运行单项；`--suite all33` 运行全部 33 个名义频点，耗时明显更长。`--suite top` 是本轮采用的 6 个代表频点加恢复、重配和精度复核，共 9 个顶层测试，不等于全部 33 点 Spectre 验证。全部 33 点已由 Python 覆盖。

若使用 GitHub 交付仓库的独立克隆，将上述命令的 `share/` 前缀去掉；脚本会把新结果保存到该克隆下的 `research/`。`--suite modules` 包含 16 个模块测试及新增的主环 Python/VA 轨迹对照测试。

本机环境通过现有桥接 IPv6 SSH 配置连接计算节点；默认 `thu-sui` IPv4 入口在本轮探测超时，不应据此判断服务器或 Spectre 不可用。实际 Spectre 版本为 21.1.0.509.isr12，使用基础单核模式，无需打开 Virtuoso GUI。

本轮本地版本：Python 3.11.9、numpy 2.4.4、scipy 1.17.0、matplotlib 3.10.8、已安装 virtuoso-bridge 0.1.0。工具连接及 Cadence 环境由用户级配置提供，不随交付仓库复制。

运行脚本保存输入快照、输入 SHA-256、服务器输入一致性检查、Spectre 日志、原始 PSF ASCII、压缩 NumPy 波形和 JSON 索引到 `research/runs/spectre_va/<run-id>`。公开交付保留精简结果；原始文件留在本项目，校验值列于结果清单。首次 modules01 的 192 个远端输入已另行逐个核验，本地快照全部一致。

## 验证口径

- 名义：1.2 V、27 °C；24 MHz 参考，输入 0–1.2 V、10 ps 转换、约 50% 占空比；输出临时负载 10 fF、输出模型电阻 50 Ω。这些源/负载条件尚未获得器件或应用规格确认。
- Python 候选 B 的主环参数：Kvco=20 MHz/V、Kpd=2.4 µA/rad、差分 VCO 幅度 0.4 V、R≈22.222 kΩ、C1≈28.648 pF、C2≈1.910 pF。VA 脉冲有 10 ps 转换，Python 矩形脉冲理想化其边沿。
- 256 个等电容粗调码，名义粗调中心 2.64–4.00 GHz，是本轮增加保护范围后的假设；需求使用频段仍为 2.688–3.936 GHz。
- FLL 测频窗 32 个参考周期，分辨率 0.75 MHz；滤波器以 10 Ω 有限电阻预充。交接后先确认频率，再连续确认 32 次小相位误差，才输出 `locked`。
- 名义顶层运行 25 µs；20–25 µs 独立测量实际输出边沿。工作检查：频率误差 <1 ppm、采样正弦相位误差 <0.01、占空比 50%±0.05 个百分点、无 setup/hold 违例、控制电压在 0.2–1.0 V。这里的检查门限不是新增或冻结的项目验收规格。
- 扰动测试在 20 µs 给 VCO 加 −24 MHz；重配测试在 20 µs 将 K/M 从 9/14 改成 41/4。两者观察至 40 µs，38–40 µs 检查输出。频点切换期间输出无有效性/无毛刺保证，使用者必须看 `locked`。
- 精度复核将 VCO 每周期最低步数从 16 加到 32，并收紧全局 reltol 到 2×10⁻⁷；必须比较结果且检查实际日志设置，不能只凭求解器正常退出判断正确。
- 模块负例：加长分频传播延迟到 115 ps，要求重定时监视器检出 setup 违例；不尝试用行为赋值模拟亚稳态。

## 结果与限制

本轮接受 26 项 Spectre 测试，全部通过。六种分频比覆盖表、锁定时间和实际波形见 [结果摘要](results/RESULTS.md)，逐项数值与门限见 `results/validation.json`，精度比较和回收清单见 `results/summary.json` 及 manifest 文件。

VA 未加入随机噪声；本轮不从确定性求解误差计算“抖动”。已有 <200 fs 的假设结果来自 Python v1，仍有积分窗口、实际源相噪与同步边沿周期平稳噪声的缺口。杂散未验证。没有供电电流、面积、PVT、器件余量或版图达标结论。

锁定后看门狗每 256 周期打开 32 周期测频窗，启用占比为 12.5%。原 0.05 mW FLL 锁定预算仅是分配，若其他静态开销忽略，这要求开启窗口内平均功耗不超过约 0.4 mW；需由实际高速计数电路核实。模型不会用理想行为源的供电电流冒充功耗。

Python 与 VA 的初始参考沿、有限预充/转换时间不同，量化测频可能选择相邻的粗调码；判定依据是正确目标频率、主环锁定和电压/时序余量，不要求相邻可用粗调码完全相同。
