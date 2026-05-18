# Cairn Agent Surface

这个参考文件只服务于当前仓库，不追求泛化。

## 本地锚点

- [docs/specs/server-protocol.md](../../../docs/specs/server-protocol.md)
  - 看 Fact / Intent / Hint / Project.reason 的语义
  - 看 `bootstrap` 约定、open intent、complete / reopen / heartbeat 这些行为边界
- [cairn/src/cairn/dispatcher/prompts/default/bootstrap.md](../../../cairn/src/cairn/dispatcher/prompts/default/bootstrap.md)
  - 看 bootstrap 阶段的任务定义和输出契约
- [cairn/src/cairn/dispatcher/prompts/default/explore.md](../../../cairn/src/cairn/dispatcher/prompts/default/explore.md)
  - 看 intent-scoped 探索的输出要求
- [cairn/src/cairn/dispatcher/prompts/default/reason.md](../../../cairn/src/cairn/dispatcher/prompts/default/reason.md)
  - 看 complete 与 propose-intent 的判定逻辑

## 先确认什么

1. 当前问题属于哪一层：
   - Prompt 面
   - Tool / MCP 面
   - 协议语义面
   - 调度与阶段切换面
2. 当前要证实的是：
   - 真实行为
   - 还是只是文本上的设计假设

## 最小验证思路

- Prompt 面：
  - 看系统要求是否强依赖 raw JSON、固定字段、固定阶段输出
  - 验证用户可控内容是否会让响应偏离契约
- Tool / MCP 面：
  - 验证工具返回值是否会被当作可信指令再次喂回模型
  - 验证参数、返回、异常链路是否会污染推理
- 协议语义面：
  - 验证恶意或误导性的 Fact / Hint / Intent 是否会让消费者错误 conclude
  - 验证 reason lease、open intent、heartbeat 的边界理解是否一致

## 高频工具

- `rg`：快速定位协议实现、prompt 文件、配置入口
- `git`：看变更、看历史上下文
- `curl`：接口最小交互
- `python3`：构造请求、模拟输入、处理响应

## Notes

- Prompt 文本不是漏洞本身，行为结果才是
- “可能会 drift” 不是 fact；“已经被诱导输出错误 JSON” 才是 fact
- 长响应和长对话放文件，不要直接塞进 fact 描述
