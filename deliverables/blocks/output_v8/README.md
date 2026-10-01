# RF 时钟接收器研究电路

本目录保留首次将真实 GHz 接收器与原 C2MOS 重定时器连接的全部拓扑试案。器件均为已验证PDK模型引用；无PDK文件进入交付区。详细条件、负结果与指标见[集成证据](../../integration/output_v8/README.md)。

- `rf_clock_receiver_v8.scs`：单端AC输入、三级DC反相器。实际3.936 GHz负载下摆幅不足。
- `rf_mirror_receiver_v8.scs`：连续NMOS差分对、PMOS镜像负载与DC反相器链。后级偏置/带宽不足。
- `rf_mirror_gain2_v8.scs`、`rf_mirror_gain3_v8.scs`：交流耦合自偏置增益链，原逻辑摆幅判据未通过。
- `rf_mirror_gain4_v8.scs`、`rf_mirror_gain4small_v8.scs`：四级链在TT下通过频率/周期/摆幅筛选，但小尺寸版器件噪声不满足200 fs要求。

再生输入级试案直接复用 `transistor_v2/receiver.scs`；取消镜像前端的直接AC试案复用 `transistor_v2/limiter_chain.scs`。对应TB保存在 `integration/output_v8/tb/`，不是漏存器件。

直接AC四级链的大尺寸版本虽通过TT波形筛选，但单次线性化噪声约30 ps，未得到降噪改善且未完成数值加密；不把该结果当作有效低噪声候选。

这些均为研究候选，未冻结采用。不能把原理图功能通过当作全频点、PVT、setup/hold、亚稳态、噪声、功耗或版图签核。理想RF回放不能评估真实VCO加载和回注，IREF发生器与工艺无源仍待后续实现。
