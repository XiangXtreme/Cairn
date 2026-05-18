# High-Frequency Tools

在这个 skill 里，先想证据，再选工具。

## 默认顺序

1. `curl` / `python3` / `nc`
2. `whatweb` / `ffuf` / `dirsearch` / `gobuster` / `naabu`
3. `wfuzz` / `nikto` / `amass`
4. `sqlmap` / `masscan` / `nmap`

## Web 面

| 工具 | 用途 | 什么时候先用 |
|------|------|-------------|
| `curl` | 首包、状态码、头、重定向、差异观察 | 永远先用 |
| `whatweb` | 技术栈指纹 | 需要快速识别中间件或框架 |
| `ffuf` | 目录、文件、参数 fuzz | 目标行为稳定后 |
| `dirsearch` | 更稳的目录发现 | 想要现成规则和可读输出 |
| `gobuster` | 轻量爆破 | 想先跑一轮简单发现 |
| `wfuzz` | 参数和 payload 组合测试 | 参数面复杂时 |
| `nikto` | 常见问题扫描 | 想快速补一轮常规弱点 |
| `sqlmap` | SQLi 自动化枚举 | 已经看到注入迹象后 |

## 服务面

| 工具 | 用途 | 什么时候先用 |
|------|------|-------------|
| `naabu` | 快速端口发现 | 先确认开放面 |
| `nc` | 单端口连通与 banner | 已知端口时 |
| `curl` | HTTP/HTTPS 服务确认 | 服务疑似 HTTP 时 |
| `masscan` | 更快的端口扫面 | 速度优先、稍后会复核 |
| `nmap` | 服务探测和脚本能力 | 已确认权限允许后 |
| `amass` | 域名/子域发现 | 目标是域名资产时 |

## 常见起手组合

- 未知站点: `curl -iL <url>` -> `whatweb <url>` -> `ffuf -u <url>/FUZZ -w <wordlist>`
- 参数可控: `curl ...` -> `wfuzz ...` -> `sqlmap ...`
- 开放面未知: `naabu -host <target>` -> `nc -nv <host> <port>` -> `nmap ...`
- 资产面扩展: `amass enum ...` -> `curl` / `whatweb`

## Notes

- `nmap` 在当前环境中可能受容器权限限制
- `masscan` 发现的端口要做二次确认
- 不要在 `curl` 还没看懂响应前就直接大规模 fuzz
