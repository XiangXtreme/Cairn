---
name: "cairn-web-surface"
description: "Use for Cairn web enumeration, HTTP attack surface mapping, exposed-service validation, and common web attacks such as content discovery, parameter fuzzing, SSRF, file handling, and SQL injection. Prefer minimal validation with curl, whatweb, ffuf, or naabu before heavier tools like sqlmap, masscan, or nmap."
---

# Cairn Web Surface

处理 Cairn 里最常见的 Web 和暴露面问题。它覆盖站点指纹、目录与参数面发现、上传与文件行为、SSRF、SQLi，以及最初一轮端口与服务确认。

## 什么时候用

- 目标是 URL、站点、接口、参数、上传点、文件读取点
- 目标是一个 IP/域名，但当前最重要的是先确认开放面和服务语义
- 需要在 `curl`、`whatweb`、`ffuf`、`naabu`、`sqlmap` 这类高频工具之间快速选型

如果主要问题已经变成凭据、SMB、AD、哈希，切到 `$cairn-creds-smb`。  
如果主要问题已经变成 Prompt、MCP、Agent 行为，切到 `$cairn-agent-mcp-safety`。

## 快速路由

| 信号 | 起手 | 目标 |
|------|------|------|
| 未知 Web 站点 | `curl` -> `whatweb` -> `ffuf` | 先看响应，再看指纹，再做轻量目录发现 |
| 参数可控 | `curl` -> `wfuzz` -> `sqlmap` | 先确认差异，再扩 payload，最后自动化 |
| 上传 / 文件行为 | `curl` -> `python3` | 先确认扩展名、解析、路径、回显差异 |
| IP/域名开放面未知 | `naabu` -> `nc`/`curl` -> `nmap`(能力允许时) | 先找开放面，再确认服务语义 |
| 域名资产面 | `amass` -> `curl`/`whatweb` | 先扩资产，再回到 HTTP 行为 |

## 执行循环

1. 先判断当前是 HTTP 面、参数面、文件面，还是开放服务面
2. 只做一个最低成本的验证动作
3. 只在差异已经成立后才上 fuzz 或自动化工具
4. 输出一条新 fact，长输出放文件
5. 如果工具失败，明确失败类型后再换路

## 工具顺序

- 默认兜底：`curl` `python3` `nc`
- 轻量发现：`whatweb` `ffuf` `dirsearch` `gobuster` `naabu`
- 补充确认：`wfuzz` `nikto` `amass` `wget`
- 重工具后置：`sqlmap` `masscan` `nmap`

## 关键规则

- `curl` 永远先于大规模 fuzz
- `ffuf` / `dirsearch` / `gobuster` 选一个先跑，不要重复堆近义动作
- `sqlmap` 只在已经有注入迹象时再上
- `masscan` 结果一定要复核
- `nmap` 在当前环境里可能 `permission-limited`

## 输出偏好

```text
scene: web-surface | service-surface
tool: ...
evidence-goal: ...
result: ...
next: ...
```

## 参考

- 工具表与起手组合见 [references/high-frequency-tools.md](references/high-frequency-tools.md)
