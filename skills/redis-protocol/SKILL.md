---
name: "redis-protocol"
description: "Use for SSRF-to-Redis, gopher payload construction, and Redis protocol probing tasks. Prefer small, explainable validation steps and report blockers instead of repeating equivalent routes."
---

# Redis Protocol

适用于 SSRF 打 Redis / gopher 构造 / Redis 协议探测类题目的容器内技能。

## 目标
- 判断目标是否能访问本地 Redis
- 判断支持 `redis://` 还是需要 `gopher://`
- 将 Redis 交互拆成可验证的小步骤，而不是一次性构造超长 payload

## 工作方式
1. 先确认协议支持情况：
   - `redis://127.0.0.1:6379`
   - `gopher://127.0.0.1:6379/_...`
2. 如果是 gopher，先验证最小命令是否有行为差异，例如 `PING`。
3. 构造 payload 时优先保持：
   - 可解释
   - 可分步
   - 能从回显或 side effect 判断成败
4. 如果目标不可用、连接重置、长时间超时，不要继续复制相同路线；应回报为 blocker 或 waiting。

## 输出偏好
- 说明当前 payload 在 Redis 语义上对应什么命令
- 标记失败是编码问题、协议问题还是目标可用性问题
- 若已知当前路线价值下降，优先收敛而不是再开近似 agent
