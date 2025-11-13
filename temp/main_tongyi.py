import os
import json
from typing import List, Dict, Any

from langchain_community.llms import Tongyi
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END

from agent_state import AgentState
from tools import ALL_TOOLS
from config import AGENT_MODEL, MAX_ITERATIONS, DASHSCOPE_API_KEY

# --- 1. LLM Setup ---
# 设置 DASHSCOPE_API_KEY 环境变量
if DASHSCOPE_API_KEY:
    os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY

# 使用 Tongyi 模型
# 注意：Tongyi 模型是 LLM 类型，不支持 OpenAI 格式的 Function Calling。
# 我们将通过 prompt 指导它输出特定格式的 JSON 来模拟工具调用。
llm = Tongyi(
    model=AGENT_MODEL, 
    temperature=0,
)

# --- 2. Prompt Template ---
SYSTEM_PROMPT = """
你是一个名为 OpenManus 的高级 AI 代理，旨在帮助用户完成复杂的任务。
你的工作流程遵循 React (Reasoning and Acting) 循环。
你拥有三层工具调用能力：
1.  **第1层 (原子化)**: 直接调用 `file_read`, `file_write`, `shell_exec`, `search_info`。
2.  **第2层 (沙箱工具)**: 通过调用 `shell_exec` 来执行预装的命令行工具（例如：`manus-md-to-pdf`）。
3.  **第3层 (代码包与 API)**: 通过调用 `code_exec` 来执行 Python 代码，用于复杂计算、数据处理或 API 调用。

**由于当前模型不支持标准的 Function Calling JSON 格式，你需要以特定的 Markdown 格式输出你的行动。**

**行动格式**:
如果你需要使用工具，请以以下格式输出，且仅输出一个 action 块：
```action
{{"tool_name": "工具名称", "tool_args": {{"参数1": "值1", "参数2": "值2"}}}}
```
**注意**: `tool_name` 必须是 `file_read`, `file_write`, `shell_exec`, `search_info`, 或 `code_exec` 之一。

**你的思考步骤 (Thought)**:
1.  **分析用户请求**：确定任务目标。
2.  **选择工具**：根据任务选择最合适的工具。
3.  **制定计划**：如果任务复杂，需要分解步骤。
4.  **决定行动**：生成上述 `action` 格式的 Markdown 代码块，或给出最终答案。

**最终答案 (Final Answer)**:
当你认为任务已完成，或者无法继续时，请直接给出最终答案，不要再进行工具调用。

**当前状态**:
- 历史对话记录:
{CHAT_HISTORY}
- 上次工具执行结果: {LAST_TOOL_RESULT}
"""

# --- 3. Graph Nodes ---

def call_llm(state: AgentState) -> Dict[str, Any]:
    """
    调用 LLM 进行推理，生成下一步的思考、工具调用或最终答案。
    """
    print("--- Node: call_llm ---")
    
    # 1. 构建历史消息字符串
    history_str = ""
    for msg in state["chat_history"]:
        if isinstance(msg, HumanMessage):
            history_str += f"用户: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            history_str += f"AI: {msg.content}\n"
    
    if state.get("last_tool_result"):
        history_str += f"工具 {state['last_tool_name']} 执行结果: {state['last_tool_result']}\n"

    # 2. 组合最终输入（使用大写占位符避免 JSON 中的大括号冲突）
    final_input = SYSTEM_PROMPT.format(
        CHAT_HISTORY=history_str,
        LAST_TOOL_RESULT=state.get("last_tool_result", "无")
    ) + f"\n用户输入: {state['input']}"
    
    # 调用 LLM
    response = llm.invoke(final_input)
    print(f"LLM Raw Response:\n{response}")

    # --- 手动解析 Tongyi 的输出 ---
    tool_calls = []
    final_answer = None
    content = response

    if "```action" in response:
        try:
            action_start = response.find("```action") + len("```action")
            action_end = response.find("```", action_start)
            action_json_str = response[action_start:action_end].strip()
            action_data = json.loads(action_json_str)
            
            tool_calls.append({
                "name": action_data["tool_name"],
                "args": action_data["tool_args"],
                "id": f"call_{os.urandom(8).hex()}"
            })
            content = response[:response.find("```action")]
        except Exception as e:
            print(f"Warning: Failed to parse action JSON: {e}")

    if not tool_calls:
        final_answer = content
        
    ai_message = AIMessage(content=content, tool_calls=tool_calls)
    
    return {
        "chat_history": state["chat_history"] + [ai_message],
        "agent_outcome": ai_message,
        "final_answer": final_answer,
        "last_tool_result": None,
        "iteration": state.get("iteration", 0) + 1
    }

def call_tool(state: AgentState) -> Dict[str, Any]:
    """
    执行 LLM 建议的工具调用。
    """
    print("--- Node: call_tool ---")
    agent_outcome = state["agent_outcome"]
    tool_calls = agent_outcome.tool_calls
    
    if not tool_calls:
        return {"last_tool_result": "Error: call_tool node reached without tool calls."}

    tool_call = tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    
    print(f"Executing Tool: {tool_name} with args: {tool_args}")
    
    tool_func = next((t for t in ALL_TOOLS if t.name == tool_name), None)
    
    if not tool_func:
        result = f"Error: Tool '{tool_name}' not found."
    else:
        try:
            result = tool_func.invoke(tool_args)
        except Exception as e:
            result = f"Tool Execution Error in '{tool_name}': {type(e).__name__}: {e}"
            
    print(f"Tool Result: {result[:100]}...")
    
    return {
        "last_tool_name": tool_name,
        "last_tool_result": result,
    }

# --- 4. Graph Edges (Conditional Logic) ---
def should_continue(state: AgentState) -> str:
    print("--- Edge: should_continue ---")
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        print(f"Max iterations ({MAX_ITERATIONS}) reached. Ending.")
        return "end"
    if state.get("final_answer"):
        print("Final answer found. Ending.")
        return "end"
    agent_outcome = state.get("agent_outcome")
    if isinstance(agent_outcome, BaseMessage) and agent_outcome.tool_calls:
        print(f"Tool call suggested: {agent_outcome.tool_calls[0]['name']}. Continuing to call_tool.")
        return "continue"
    print("No tool call and no final answer. Ending.")
    return "end"

# --- 5. Build the Graph ---
def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("llm", call_llm)
    workflow.add_node("tool", call_tool)
    workflow.set_entry_point("llm")
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {"continue": "tool", "end": END}
    )
    workflow.add_edge("tool", "llm")
    return workflow.compile()

# --- 6. Main Execution ---
if __name__ == "__main__":
    app = build_graph()
    print("--- OpenManus LangGraph Agent Initialized (Using Tongyi) ---")
    
    # 交互式循环 - 接收用户输入
    print("\n" + "="*70)
    print("🤖 OpenManus Agent 交互模式（Tongyi 模型 + 工具调用）")
    print("="*70)
    print("输入 'exit' 或 'quit' 退出程序\n")
    
    chat_history = []
    
    while True:
        # 获取用户输入
        user_input = input("\n👤 你: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("👋 再见！")
            break
        
        # 创建初始状态
        initial_state = {
            "input": user_input,
            "chat_history": chat_history,
            "final_answer": None,
            "last_tool_name": None,
            "last_tool_result": None,
            "iteration": 0,
            "agent_outcome": None,
        }
        
        print("\n" + "-"*70)
        print("🔄 Agent 处理中...\n")
        
        try:
            # 运行 Agent
            for s in app.stream(initial_state):
                pass  # 让底层处理流程输出调试信息
            
            # 获取最终状态
            result = app.invoke(initial_state)
            
            # 更新聊天历史
            chat_history = result.get("chat_history", chat_history)
            
            # 显示结果
            print("\n" + "-"*70)
            print(f"🤖 代理回复: {result.get('final_answer', '无法生成答案')}")
            
            if result.get('last_tool_result'):
                print(f"\n🔧 工具执行结果:\n{result['last_tool_result']}")
            
            print(f"\n⏱️  迭代次数: {result.get('iteration', 0)}")
            print("-"*70)
        
        except Exception as e:
            print(f"\n❌ 错误: {type(e).__name__}: {e}")
            print("-"*70)
            continue