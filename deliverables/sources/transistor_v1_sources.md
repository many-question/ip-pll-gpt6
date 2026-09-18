# 本轮实际使用的依据

1. 项目已配置的 TSMC180 BCD Gen2 V1.6 Spectre 模型及 usage 文件。直接在服务器依赖路径读取接口、使用 `tt/ss/ff`、`stat_noise` 和细调的 `tt_bbmvar` section。模型 SHA-256 记录于实验摘要；未将受限模型正文复制到交付目录。此依据支持器件仿真，不支持工艺电感、理想阵列电容或版图面积结论。
2. Behzad Razavi, “TSPC Logic,” IEEE Solid-State Circuits Magazine, Fall 2016, DOI 10.1109/MSSC.2016.2603228。[作者公开 PDF](https://www.seas.ucla.edu/brweb/papers/Journals/BRFall16TSPC.pdf)，访问 2026-09-18。使用 Fig. 6(c) 核对 9T 反相 TSPC 触发器连接，比较其慢角行为；该候选在本项目条件下失败。文章也讨论动态时钟锁存的竞态，不能从文献直接推定本 PDK/1.2 V 的最高速度。研究副本位于本项目 `research/sources/Razavi_TSPC_2016.pdf`。
3. 本项目已读取的 `skills/eda-servers`、`skills/virtuoso` 和用户级 `spectre` 技能，以及已安装 virtuoso-bridge 的 runner/parser 源码。用于正常 EDA 路径、不可变上传快照、PSF 回收和结果解析。

电路尺寸、RC 选取、CML 共模/负载扫描、相位与电荷积分测量为本项目推导和实验。文献与模型接口不替代本项目的功能、噪声或可靠性验证。
