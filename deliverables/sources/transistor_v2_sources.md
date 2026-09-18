# 分频、FLL 与 PSS/Pnoise 所用依据

1. 项目已配置的 TSMC180 BCD Gen2 V1.6 模型，核心 `nch/pch`、`tt/ss/ff`、`stat_noise`，变容 `tt_bbmvar`。根模型 SHA-256 为 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。仅记录接口和 hash，未交付模型正文。
2. 服务器已安装 Spectre 21.1 的 `spectre -h pss`、`pnoise`、`jitterevent`、`noise` 官方帮助。实际读取副本保存在 `research/spectre_help/`，不将整份授权文档复制到交付面。用于自主 PSS 端口、PM 单边谱、载波功率、采样边沿噪声和 `Jee` 的单位核对。实际噪声结果来自本项目运行，帮助文档本身不构成性能证据。
3. [Yosys 官方文档](https://yosyshq.readthedocs.io/projects/yosys/en/latest/) 与 [YoWASP 项目](https://yowasp.org/)；本项目使用 Yosys 0.69 的通用门综合输出，映射脚本及 CMOS 门为自有实现。综合使用 `synth`、`dffunmap`、`abc -g AND,OR,XOR,XNOR,MUX`，不包含第三方工艺单元库。工具副本与缓存位于项目 `research/tools/`，综合日志为 `research/fll_synthesis.log`。
4. 已安装 virtuoso-bridge 的 runner、PSF parser 和本轮读取的 EDA/Spectre 技能。用于项目限定路径、不可变输入、日志与波形回收；结果单位和积分另由本项目脚本交叉核验。

Johnson 环尺寸、交流偏置与门控、FLL 搜索算法、MOS 单元连接、重定时尺寸、偏置滤波以及噪声预算回填均为本项目设计或计算，不能从工具说明推导出电路达标。
