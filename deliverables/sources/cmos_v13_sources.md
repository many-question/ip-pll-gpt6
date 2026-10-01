# CMOS v13 来源

本轮主要依据已发布cmos_v12及本项目真实器件仿真，未引入外部工艺性能保证。

- `cmos_v12`：单级接收器、TSPC重定时、181.186fs基线及实际LC接入条件；所有对比保留原测量边界。
- `jitter_v11/cmos_tspc_buffered_v11.scs`及`transistor_v1/cells.scs`：固定÷4和基本MOS电路。`vco_v4`提供R2/Q5基线，`accuracy_v7`提供实际参考/采样/CP负载。
- [B. Razavi, “TSPC Logic,” IEEE Solid-State Circuits Magazine, 8(4),10–13,2016, DOI10.1109/MSSC.2016.2603228](https://seas.ucla.edu/brweb/papers/Journals/BRFall16TSPC.pdf)。2026-10-02复读Fig.6、8、9，用于核对9T连接、构建7T ratioed对照及形成时序竞争假设；没有移植论文性能。PDF已在项目research/sources中，哈希见literature_basis.json；不将PDF复制到share。
- Spectre21.1实际日志/PSF、模型根文件SHA256 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`本轮重新核实。三次noiseon误放分析行的SFE-106警告与拒绝校验均保留，修正后独立谱闭合。

探索性搜索另找到E-TSPC资料，但未据其数值设计或作性能结论。真正影响本轮实现的外部拓扑来源只有上述Razavi原文。

服务器身份和项目路径重新核验；独立Spectre可用，GUI隧道未开启。使用既有EDA服务器与Spectre技能；没有新安装工具或复制PDK、license、密钥到交付面。
