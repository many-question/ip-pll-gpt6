# 噪声方法核查（2026-10-04）

本页记录实际参考的方法来源，不作为本电路性能证据。

- 本机已回收的 Spectre 21.1 帮助：项目 `research/spectre_help/pss.txt`、`pnoise.txt`、`jitterevent.txt`。PSS 的稳定段、周期求解和 PNoise 是不同阶段；失败运行生成的状态文件不能仅凭文件存在而复用。当前流程要求完成日志、周期轨迹和源文件 SHA 同时通过。
- [Cadence：PLL + PSS + PNOISE convergence](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/48474/pll-pss-pnoise-convergence)。驱动 PLL 应使用受迫周期解；全部内部信号须与共同周期相容。原生检查点不能在 tran 与 PSS 两种分析之间混用。本项目使用的文本终态只是初值种子，重启扰动必须重新稳定。
- [Cadence：Measuring Noise in Digital Circuits](https://community.cadence.com/cadence_blogs_8/b/cic/posts/spectre-tech-tips-measuring-noise-in-digital-circuits)。数字边沿使用 sampled edge crossing；fullspectrum 仍需核查 PSS 的频率覆盖。本项目还会检查 maxacfreq、步长、边带及不同输出边沿，不能只改变 maxsideband 就宣称收敛。
- [Cadence：Pnoise on signal at multiple of the fundamental](https://community.cadence.com/cadence_technology_forums/f/custom-ic-design/56829/pnoise-on-signal-at-multiple-of-the-fundamental)。输出频率高于 PSS 基频时使用 sample ratio 的适用说明。内部帮助定义其为采样频率/PSS基频；本项目局部链使用6，4MHz锁定核心使用246。

工具实测校准仍见 `results/noise_measurement_fixture.json`、`results/pss_reuse_validation.json`。局部链在精确 PSS 谐波处存在 flicker 警告，邻近有限频率检查也未完全关闭；现有 logarithmic-grid 积分仅为暂定数值。用户排除的是离散杂散，这不授权删除谐波邻近的随机噪声。

当前的 Gear2、2µs稳定段属于数值收敛诊断；相位瞬态、Newton异常电压和无噪声仿真中的边沿变化都不能算作随机抖动。
