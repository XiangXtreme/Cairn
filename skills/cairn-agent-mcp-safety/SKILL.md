---
name: "cairn-agent-mcp-safety"
description: "Use for Cairn agent, prompt, and MCP safety tasks involving prompt boundaries, tool execution surfaces, JSON-only contracts, graph and protocol semantics, and LLM-driven workflows. Prefer reading the local Cairn protocol and dispatcher prompts, then validating behavior with minimal curl, python3, or repo inspection."
---

# Cairn Agent MCP Safety

处理 Cairn 里与 LLM、Agent、Prompt、MCP、工具链边界有关的任务。这个 skill 不追求泛化的 AI 安全百科，而是优先贴着当前仓库和当前行为面做最小验证。

## 什么时候用

- 目标涉及 Prompt 注入、角色边界、工具注入、RAG/MCP 暴露面
- 需要判断某个 Agent 是否会被错误路由、错误 conclude、错误 complete
- 需要基于 Cairn 自己的协议与 prompt 文件来设计验证动作

如果当前更像 Web 或服务暴露面，切到 `$cairn-web-surface`。  
如果当前更像凭据、SMB、哈希问题，切到 `$cairn-creds-smb`。

## 先看本地锚点

优先只读与你当前问题相关的本地文件：

- [docs/specs/server-protocol.md](../../docs/specs/server-protocol.md)
- [cairn/src/cairn/dispatcher/prompts/default/bootstrap.md](../../cairn/src/cairn/dispatcher/prompts/default/bootstrap.md)
- [cairn/src/cairn/dispatcher/prompts/default/explore.md](../../cairn/src/cairn/dispatcher/prompts/default/explore.md)
- [cairn/src/cairn/dispatcher/prompts/default/reason.md](../../cairn/src/cairn/dispatcher/prompts/default/reason.md)

## 快速路由

| 信号 | 起手 | 目标 |
|------|------|------|
| 要确认协议/图语义 | 读 `server-protocol.md` | 先明确 Fact/Intent/Hint/reason 的约束 |
| 要确认阶段性 Prompt 边界 | 读 `bootstrap` / `explore` / `reason` prompt | 先明确输入和输出契约 |
| 要确认接口或工具返回值行为 | `curl` / `python3` | 先做最小交互和边界验证 |
| 要确认本地实现入口 | `rg` / `git` | 先定位代码和配置落点 |

## 执行循环

1. 先判断是 Prompt 面、工具面、MCP 面，还是协议语义面
2. 先读最小必要的本地锚点文件
3. 只做一个最小验证动作
4. 只把“真实行为”写成 fact，不把推测写成 fact
5. 如果当前问题已经转成 Web 或凭据面，立即切换 skill

## 高频工具

- 仓库与实现定位：`rg` `git`
- 最小交互验证：`curl` `python3`
- 必要时再看前端或接口行为：浏览器、HTTP 抓取、最小脚本

## 关键规则

- Prompt 文本本身不是漏洞证明，行为结果才是
- JSON-only、raw-JSON 这类契约必须按真实响应验证
- 不要把“可能能注入”写成“已经注入成功”
- 长对话、长响应、长日志放文件，不要塞进 fact
- 设计验证动作前，先看当前阶段是 `bootstrap`、`explore`，还是 `reason`

## 输出偏好

```text
scene: prompt | tool | mcp | protocol
tool: ...
evidence-goal: ...
result: ...
next: ...
```

## 参考

- 项目内锚点与测试清单见 [references/cairn-agent-surface.md](references/cairn-agent-surface.md)
