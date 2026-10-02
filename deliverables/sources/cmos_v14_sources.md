# CMOS v14实际使用的来源

- Behzad Razavi, “TSPC Logic,” IEEE Solid-State Circuits Magazine 8(4), 10–13 (2016), DOI 10.1109/MSSC.2016.2603228。[作者原文](https://seas.ucla.edu/brweb/papers/Journals/BRFall16TSPC.pdf)。本轮在线重取返回502，使用此前已保存的本地 `research/sources/Razavi_TSPC_2016.pdf` 并查看第3页图；Fig6/8/9用于核对节点与形成竞争、动态节点传递假设。没有把文献性能代入本设计。
- X. P. Yu et al., “Design and optimization of the extended true single-phase clock-based prescaler,” IEEE TMTT 54(11), 3828–3835 (2006), DOI 10.1109/TMTT.2006.884629。[机构原始条目](https://repository.sutd.edu.sg/esploro/outputs/journalArticle/Design-and-optimization-of-the-extended/9912392709846)。实际阅读摘要作为E-TSPC速度/功耗权衡的背景；另一全文链接访问403，未将未读全文当依据，未照搬其性能或声称使用其完整拓扑。
- 本项目v13/v14网表、独立节点保存、受控修改和Spectre21.1实际器件瞬态是所有修复与数值结论的直接来源。运行路径和哈希见 [raw_manifest.json](../integration/cmos_v14/results/raw_manifest.json)，波形统计见 [summary.json](../integration/cmos_v14/results/summary.json)。
- 获授权服务器上的TSMC180BCDGen2模型用于仿真及只读参数范围核对；模型入口SHA256 `d44aa9da7ba670f0b4cfb0198b019dc73abf8bae21b15f45ce5a30c7cb5973ff`。不发布PDK、参数摘录或license材料。

反馈延迟和缓冲修改是本项目研究候选，不是文献保证。新增电阻的噪声、RC容差与版图实现仍需实际验证。
