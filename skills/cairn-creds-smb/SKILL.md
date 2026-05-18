---
name: "cairn-creds-smb"
description: "Use for Cairn credential attacks, login-surface validation, SMB and AD enumeration, share access checks, password-spray decisions, and hash cracking. Prefer confirming reachability and trying small high-value credential sets before broader hydra or hashcat runs."
---

# Cairn Creds SMB

处理 Cairn 里和认证面有关的高频问题：登录入口、凭据、SMB/WinRM/AD、共享权限，以及哈希破解。

## 什么时候用

- 已经拿到用户名、口令、token、哈希、票据
- 目标是 SSH、SMB、HTTP 登录、WinRM 或域环境
- 需要判断先上 `netexec`、`smbmap`、`hydra`、`john` 还是 `hashcat`

如果当前更像 Web 参数/SSRF/SQLi/开放服务问题，切到 `$cairn-web-surface`。  
如果当前更像 Agent、Prompt、MCP 行为问题，切到 `$cairn-agent-mcp-safety`。

## 快速路由

| 信号 | 起手 | 目标 |
|------|------|------|
| SMB / AD 目标 | `netexec` -> `smbmap` | 先确认认证面，再看共享权限 |
| 已知登录入口 | `nc`/`curl` -> 少量凭据尝试 | 先确认协议和回显，再决定是否爆破 |
| 已有哈希样本 | `john` -> `hashcat` | 先轻量验证格式和弱口令，再决定是否上重任务 |
| 明确内网投毒场景 | `responder` | 只在链路与目标都明确时再使用 |

## 执行循环

1. 先确认服务可达，且真的存在认证面
2. 先试少量高价值凭据，不要上来就大规模字典
3. 认证成立后优先拿权限证明、共享证明、用户上下文
4. 哈希先用 `john` 跑一轮，再决定是否转 `hashcat`
5. 若目标不稳定，收敛动作面，不扩大尝试

## 工具顺序

- 默认兜底：`nc` `curl` `python3`
- 轻量认证与共享确认：`netexec` `smbmap` `john`
- 重工具后置：`hydra` `hashcat`
- 场景敏感：`responder`

## 关键规则

- `hydra` 只在协议、用户名面、失败反馈都清楚时再上
- `netexec` / `smbmap` 优先于盲目 SMB 爆破
- `john` 优先于 `hashcat`
- `responder` 只在明确的内网链路场景里使用
- 不要把“不稳定目标”变成“长时间无意义喷洒”

## 输出偏好

```text
scene: creds | smb-ad | hashes
tool: ...
evidence-goal: ...
result: ...
next: ...
```

## 参考

- 工具表与协议起手顺序见 [references/high-frequency-tools.md](references/high-frequency-tools.md)
