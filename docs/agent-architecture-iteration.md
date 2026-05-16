# Agent 架构设计迭代记录

本文档用于记录授权渗透测试场景下的 AI Agent 架构设计迭代。重点关注：为什么通用 Agent 不够稳定，哪些能力应该从 Agent 中外置到系统状态里，以及后续如何在规则、工具和 LLM worker 之间分工。

## 背景

在使用 Claude Code、Codex 这类通用 Agent 做授权渗透测试时，执行质量存在较大不确定性。

已观察到的问题：

- 同一个接口，有时会被深度测试，有时只正常提交一次数据就结束。
- Agent 可能漏掉常见测试项，例如模糊查询、SQL 注入、越权、未授权访问和业务逻辑测试。
- 页面测试容易发生偏移，Agent 可能反复测试同一个页面功能，同时漏掉其他功能点。
- 信息收集不完整会影响后续利用链推理。
- Agent 经常把大量时间花在 UI 交互细节上，真正测试接口的时间反而不多。

当前判断：这些问题主要不是“知识不足”导致的。Skill 和 Prompt 可以告诉 Agent 应该怎么测，但不能强制它测完、测准，也不能保证每个结论都有证据。

## 核心判断

未来方向不应该是构造一个更大的通用 Agent，而应该是构建一个面向渗透测试的专用 Agentic System。

通用模型和通用 Agent 仍然重要，但它们更适合成为系统里的 worker。系统应该负责：

- 资产状态
- API 资产清单
- 参数语义
- 测试覆盖率
- 任务生命周期
- 证据要求
- 重试与去重
- 跨步骤推理状态

Agent 应该处理需要判断和推理的部分，而不是独自承担完整控制循环。

## 软约束与硬约束

Skill、Prompt 和 Checklist 都属于软约束。

它们能告诉 Agent：

- SQL 注入应该如何测试。
- IDOR 需要切换账号验证。
- 文件上传需要检查扩展名、MIME 和内容检测。
- 搜索接口需要测试模糊查询和注入。

但它们不能稳定强制 Agent：

- 完成每个必测项。
- 避免重复做已完成的工作。
- 为每个结论提供证据。
- 将 UI 探索和 API 测试分离。
- 在上下文丢失后从稳定状态恢复。

因此系统需要硬约束：

- 结构化任务
- 显式任务状态
- 必填证据字段
- 可机器校验的完成条件
- 重试和重新派发规则
- 覆盖率统计

## 候选流水线

当前候选架构如下：

```text
流量采集
  -> 请求归一化、去重、聚类
  -> 参数语义分析
  -> 风险标签生成
  -> 测试矩阵生成
  -> 原子测试任务入队
  -> 工具优先执行
  -> Agent 复核异常结果
  -> 证据存储与 Fact 写回
  -> 利用链推理
```

## HTTP 请求处理

当前思路是：对 HTTP 请求进行参数拆解，并使用 LLM 判断参数可能的业务含义。这个方向有价值，但不应该把每条原始请求都直接交给大模型。

更合适的流程：

1. 用确定性代码解析请求。
2. 归一化接口。
3. 去重相似请求。
4. 按 method、path 模板、参数集合、鉴权上下文聚类。
5. 仅在需要语义判断时调用 LLM。

归一化示例：

```text
GET /api/user/123/order?page=1
GET /api/user/456/order?page=2
```

归一化后的资产：

```text
GET /api/user/{id}/order?page=
```

## 参数语义模型

LLM 可以辅助判断参数含义，但输出必须是结构化的。

示例：

```json
{
  "endpoint": "/api/user/{id}/order",
  "business_object": "用户订单列表",
  "parameters": [
    {
      "name": "id",
      "location": "path",
      "type_guess": "integer",
      "semantic": "user_id",
      "risk_tags": ["idor", "authz", "data_exposure"]
    },
    {
      "name": "page",
      "location": "query",
      "type_guess": "integer",
      "semantic": "pagination",
      "risk_tags": ["boundary", "type_confusion"]
    }
  ]
}
```

系统不应接受纯自然语言分析作为最终结果。如果模型无法判断参数语义，应返回 `unknown`，并附带置信度和判断依据。

## 测试矩阵生成

测试 list 不应只依赖 Prompt 关键词。关键词规则可以作为第一层，但测试矩阵应结合更多上下文：

- 参数名
- 参数位置
- HTTP 方法
- Content-Type
- 鉴权状态
- 业务对象
- 响应字段
- 账号角色
- 资源归属关系
- 已有事实

初始规则示例：

| 信号 | 候选测试项 |
| --- | --- |
| `id`、`userId`、`orderId`、路径 ID | IDOR、水平越权、资源枚举 |
| `q`、`search`、`keyword` | 模糊查询、SQL 注入、XSS、长度边界 |
| `sort`、`orderBy` | order by 注入、字段枚举、异常字段访问 |
| `file`、`avatar`、`upload` | 上传绕过、MIME 不一致、文件名 XSS、存储路径泄露 |
| `amount`、`price`、`coupon` | 金额篡改、负数、重放、优惠叠加 |
| `status`、`role`、`isAdmin` | 权限提升、状态机绕过、批量赋值 |

这些测试项应该进入系统任务队列，而不是停留在自然语言 todo list。

## 原子测试任务

测试 Agent 不应该收到“测试这个接口有没有 SQL 注入”这类宽泛指令，而应该收到明确的原子任务。

示例：

```json
{
  "id": "tc_1024",
  "asset": "/api/user/{id}/order",
  "method": "GET",
  "parameter": "id",
  "category": "idor_horizontal",
  "status": "pending",
  "accounts_required": ["user_a", "user_b"],
  "steps": [
    "请求 user_a 自己的资源",
    "请求 user_b 自己的资源",
    "用 user_b 的资源 id 替换 user_a 请求中的 id",
    "比较状态码、响应体和敏感字段"
  ],
  "required_evidence": [
    "baseline_a_request",
    "baseline_a_response",
    "baseline_b_request",
    "baseline_b_response",
    "mutated_request",
    "mutated_response",
    "authorization_conclusion"
  ],
  "executor": "http_tester",
  "reviewer": "agent"
}
```

如果缺少必填证据，系统应判定任务未完成，而不是接受 Agent 的口头结论。

## 职责划分

规则和确定性代码负责：

- HTTP 解析
- 接口归一化
- 请求去重
- 参数提取
- 基础类型推断
- 基础 payload 执行
- 状态码、响应长度、Header 对比
- 覆盖率追踪

工具负责：

- HTTP 重放
- Payload 变异
- 账号切换
- 时间测量
- 响应差异对比
- 可复现证据采集

LLM worker 负责：

- 业务语义推断
- 模糊参数含义判断
- 响应差异解释
- 业务逻辑漏洞假设生成
- 利用链推理
- 报告描述和证据解释

## 与 Cairn 的关系

Cairn 已经具备有价值的基础能力：

- `Fact`：已确认事实
- `Intent`：探索方向
- `Hint`：外部判断或提示
- Dispatcher：worker 调度、心跳、超时和写回

但在渗透测试场景中，Cairn 还需要一层领域模型：

- API 资产库
- 参数模型
- 风险标签
- 测试矩阵
- 原子测试任务队列
- 证据模型
- 覆盖率视图
- 多账号鉴权上下文

Cairn 可以继续作为编排层，渗透测试领域层负责生成和校验任务。

## Local Native Worker 方向

当前实现方向已经切换为本机进程执行。Dispatcher 不再依赖额外运行环境，而是直接调用本机 `claude`、`codex`、`pi`、`python` 和 `curl` 等 CLI。

这意味着 Cairn 的 runtime 层负责：

- 为每个项目创建 `.cairn-runtime/projects/{project_id}` 工作目录。
- 将 graph snapshot 写入项目工作目录。
- 用 Python `subprocess` 启动本机 worker 进程。
- 传递 worker 环境变量。
- 控制超时并终止进程树。
- 保持 Claude Code / Codex session resume 逻辑不变。

Local native 模式的优势：

- 可以直接复用本机已安装的 Claude Code、Codex、浏览器、Burp、Yakit 和代理环境。
- 不需要维护 worker 镜像。
- 更适合桌面安全测试工作流，尤其是需要和本机 GUI 工具联动时。

主要风险：

- 缺少强沙箱隔离，项目之间更容易互相污染。
- CLI session、缓存、配置文件可能混用。
- 本机工具权限更大，误操作影响范围更高。
- 不同用户机器环境差异更大，复现难度更高。

当前设计原则：

```text
Local worker 只负责执行。
项目隔离由工作目录、环境变量和进程管理实现。
安全测试资产、任务状态和证据仍由 Cairn/领域层管理。
```

## 关键设计风险

### Token 成本

如果每条原始请求都交给 LLM 分析，成本会快速膨胀。应先做请求去重、聚类和规则判断，再调用 LLM。

### 任务完成度不足

如果任务只是普通 todo 文本，Agent 仍可能跳过步骤。应使用结构化状态和必填证据字段。

### UI 偏移

API 测试不应依赖浏览器页面操作。浏览器主要负责流量发现和状态获取；接口测试应尽量通过 HTTP 重放直接执行。

### Agent 职责过宽

不要让一个 Agent 同时负责浏览、规划、测试、利用和报告。每个任务应尽量窄。

## 当前设计原则

采用以下原则：

```text
规则生成覆盖骨架。
工具执行可重复检查。
Agent 处理语义判断和困难情况。
系统负责状态和完成度。
```

## 待解决问题

- 第一个可用版本所需的最小资产 schema 是什么？
- 接口归一化应该在鉴权上下文分组之前还是之后完成？
- 系统如何建模多账号和资源归属关系？
- 哪些测试类型应优先实现为确定性工具？
- SQL 注入、IDOR、XSS 和业务逻辑测试分别需要哪些证据字段？
- 失败或无法判断的测试应如何重试，何时升级给更强模型？
- Cairn 的 `Fact` 应如何和领域证据记录关联？
- Local native runtime 如何进一步隔离不同项目的 CLI session 和缓存？
- Local native runtime 是否需要支持 Burp/Yakit/浏览器这类本机 GUI 工具的连接协议？

## 下一轮迭代项

- 定义 API 资产 schema。
- 定义参数语义 schema。
- 定义风险标签及其到测试类型的映射。
- 定义原子任务状态流转。
- 定义前四类测试的必填证据：SQL 注入、IDOR、未授权访问、模糊查询。
- 决定渗透测试领域层应如何接入现有 Cairn Server 和 Dispatcher。
- 设计 Local native runtime 与 Burp/Yakit/浏览器的连接协议。
