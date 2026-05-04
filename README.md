# Mini OpenClaw

一个从 0 手写的简版 OpenClaw：本地优先的个人 AI 助手网关。它保留 OpenClaw 的核心形态：Gateway 统一接入消息通道、Agent 管理会话与记忆、工具注册表执行本地能力，并通过 CLI/HTTP 提供最小可运行体验。

## 功能

- `OpenClawGateway`：接收 inbound message，分发给 Agent，记录事件和投递结果。
- `ClawAgent`：无需外部模型即可响应 `/help`、`/status`、`/remember`、`/recall`、`/tool`。
- `MemoryStore`：按 session 保存对话历史和显式记忆。
- `ToolRegistry`：内置 `echo`、`time`、`calc` 三个本地工具。
- HTTP Gateway：提供 `/health`、`/message`、`/sessions`、`/events` 四个接口。

## 快速开始

无需安装依赖，Python 3.11+ 即可运行：

```bash
python3 -m mini_openclaw chat
```

聊天示例：

```text
you> /help
you> /remember name=Molty
you> /recall
you> /tool calc {"expr":"1 + 2 * 3"}
```

直接发送一条消息：

```bash
python3 -m mini_openclaw send --message "/status"
```

启动 HTTP Gateway：

```bash
python3 -m mini_openclaw serve --port 18789
```

发送 HTTP 消息：

```bash
curl -s http://127.0.0.1:18789/message \
  -H 'content-type: application/json' \
  -d '{"channel":"console","from":"me","text":"/tool echo {\"text\":\"hello\"}"}'
```

## 项目结构

```text
mini_openclaw/
  agent.py      # 规则 Agent
  gateway.py    # 本地 Gateway 控制面
  memory.py     # 会话记忆
  tools.py      # 工具注册表与默认工具
  server.py     # HTTP Gateway
  __main__.py   # 命令行入口
test/
  test_core.py  # 核心行为测试
```

## 命令

- `python3 -m unittest discover -s test`：运行测试。
- `python3 -m mini_openclaw doctor`：检查本地配置。
- `python3 -m mini_openclaw chat`：启动交互式 console 通道。
- `python3 -m mini_openclaw serve --port 18789`：启动 HTTP Gateway。
- `python3 -m mini_openclaw send --message "/help"`：直接处理一条消息。
