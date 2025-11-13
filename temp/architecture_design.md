# OpenManus LangGraph 架构设计

## 1. 目标
使用 LangGraph 实现一个类似于 OpenManus 的 Agent 循环（React 模式），并集成一个三层工具调用（Function Calling）机制。

## 2. 三层工具调用机制

| 层级 | 名称 | 描述 | 调用方式 | 示例工具 |
| :--- | :--- | :--- | :--- | :--- |
| **第1层** | **原子化函数调用 (Function Calling)** | 核心、原子化的基础工具，直接暴露给 LLM。输入输出格式清晰、出错率低。 | LLM 直接生成 Function Call JSON | `file_read`, `file_write`, `shell_exec`, `search_info` |
| **第2层** | **沙箱工具 (Sandbox Utilities)** | 预装在沙箱中的命令行工具，通过第1层的 `shell_exec` 工具间接调用。 | LLM 调用 `shell_exec`，并传入相应的命令行工具和参数。 | `manus-md-to-pdf`, `manus-speech-to-text`, `manus-mcp-cli` |
| **第3层** | **代码包与 API (Packages & APIs)** | 用于执行复杂逻辑、数据处理或调用外部 API 的 Python 代码。通过一个特殊的“代码执行”工具来即时编写和运行。 | LLM 调用 `code_exec` 工具，传入要执行的 Python 代码。 | `requests` 库调用 API, `pandas` 数据处理, `matplotlib` 绘图 |

## 3. LangGraph Agent 循环 (React 模式)

我们将使用 LangGraph 实现一个状态机，模拟 Agent 的思考-行动-观察循环（React）。

### 3.1. 状态 (State)
Agent 的状态将是一个字典，包含以下关键信息：
- `input`: 用户的原始输入。
- `chat_history`: 历史对话记录。
- `agent_outcome`: LLM 的最新输出（包括思考、行动或最终答案）。
- `tool_calls`: LLM 建议执行的工具调用列表。
- `tool_results`: 工具执行后的结果。
- `final_answer`: Agent 确定的最终答案。

### 3.2. 节点 (Nodes)
1.  **`call_llm`**: 调用 LLM (GPT-4.1-mini/nano 或 Gemini-2.5-flash) 进行推理，生成下一步的思考、工具调用或最终答案。
2.  **`call_tool`**: 根据 LLM 的输出，执行相应的工具调用。这个节点将负责处理三层工具调用的逻辑。
3.  **`end_node`**: 结束循环，返回最终答案。

### 3.3. 边 (Edges)
1.  **`call_llm` -> `call_tool`**: 如果 LLM 决定使用工具。
2.  **`call_llm` -> `end_node`**: 如果 LLM 决定给出最终答案。
3.  **`call_tool` -> `call_llm`**: 工具执行完毕后，将结果返回给 LLM 进行下一步推理。

## 4. 实现细节

### 4.1. 第1层工具实现
我们将创建 Python 函数来封装这些原子操作，并使用 LangChain 的 `tool` 装饰器进行注册。

### 4.2. 第3层代码执行实现
我们将实现一个 `code_exec` 工具，它将接收 Python 代码字符串，在一个安全的、隔离的环境（例如，使用 `exec` 或子进程）中执行，并捕获其输出和错误。

### 4.3. 沙箱模拟
由于我们运行在实际的沙箱环境中，第1层的 `shell_exec` 工具将直接使用 `default_api:shell` 工具来实现，从而自然地支持第2层的沙箱工具调用。

## 5. 项目结构
```
/openmanus_langgraph
├── main.py             # LangGraph 主程序和 Agent 循环定义
├── tools.py            # 三层工具的实现（第1层原子工具和第3层代码执行器）
├── agent_state.py      # LangGraph 状态定义
├── architecture_design.md # 本设计文档
└── README.md           # 项目说明和使用指南
```
