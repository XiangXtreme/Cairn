# High-Frequency Tools

这个 skill 的核心不是“爆破”，而是先确认认证面，再决定是否扩大动作。

## 默认顺序

1. `nc` / `curl` / `python3`
2. `netexec` / `smbmap` / `john`
3. `hydra` / `hashcat`
4. `responder`（只在明确内网链路场景）

## 认证与 SMB/AD

| 工具 | 用途 | 什么时候先用 |
|------|------|-------------|
| `netexec` | SMB/WinRM/AD 枚举与认证 | Windows/AD 目标的默认起手 |
| `smbmap` | SMB 共享与权限确认 | 已知 SMB 可达时 |
| `hydra` | 多协议口令尝试 | 协议、用户名面、失败反馈都清楚时 |
| `responder` | 内网投毒与凭据捕获 | 明确链路和场景后 |

## 哈希与密码

| 工具 | 用途 | 什么时候先用 |
|------|------|-------------|
| `john` | 轻量哈希破解 | 小规模或格式常见时 |
| `hashcat` | 更强的哈希破解 | 需要更重规则和算力时 |

## 常见起手组合

- SMB / AD: `netexec smb <target> ...` -> `smbmap -H <target> ...`
- 已知登录口: `nc`/`curl` 验证 -> 少量高价值凭据尝试 -> `hydra ...`
- 哈希样本: `john ...` -> `hashcat ...`

## Notes

- `hydra` 不应该是第一步
- `john` 往往比 `hashcat` 更适合第一轮
- 对不稳定目标不要做长时间大规模喷洒
- `responder` 不属于默认动作，必须先确认场景合理
