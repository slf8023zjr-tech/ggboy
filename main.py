
import os
import json
from typing import List, Dict, Any, Union
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.tools import BaseTool
# from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from agent_state import AgentState
from tool.tools import ALL_TOOLS

MAX_HISTORY = 4   # 只保留最近 4 条（或你喜欢的数量）
PPIO_API_KEY="sk_"
llm = ChatTongyi(
    model="qwen-max", 
    temperature=0,
    api_key="sk-",  
    
)

# 绑定工具到 LLM
llm_with_tools = llm.bind_tools(ALL_TOOLS)

# --- 2. Prompt Template ---
SYSTEM_PROMPT = """
你是一个名为 OpenManus 的高级 AI 代理，旨在帮助用户完成复杂的任务，严格遵守思考步骤。
你的工作流程遵循 React (Reasoning and Acting) 循环。
你拥有三层工具调用能力：
1.  **第1层 (原子化)**: 直接调用 `file_read`, `file_write`, `shell_exec`, `search_info`, `plan_task`。
2.  **第2层 (沙箱工具)**: 通过调用 `shell_exec` 来执行预装的命令行工具（例如：`manus-md-to-pdf`, `manus-speech-to-text`）。
3.  **第3层 (代码包与 API)**: 通过调用 `code_exec` 来执行 Python 代码，用于复杂计算、数据处理或 API 调用。

**你的思考步骤 (Thought)**:
1.  **分析用户请求**：确定任务目标。
2.  **选择工具**：根据任务选择最合适的工具。
3.  **制定计划**：如果任务复杂，需要分解步骤。
4.  **决定行动**：生成工具调用（Function Call JSON）或给出最终答案。

**最终答案 (Final Answer)**:
当你认为任务已完成，或者无法继续时，请直接给出最终答案，不要再进行工具调用。

**当前状态**:
- 历史对话记录: {chat_history}
- 上次工具执行结果: {last_tool_result}
"""

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("placeholder", "{chat_history}"),
        ("human", "{input}"),
    ]
)

# --- 3. Graph Nodes ---



# import json
# from langchain_core.messages import AIMessage

# def planner_node(state: AgentState) -> AgentState:
#     goal = state["input"]
#     context = "根据用户目标，制定详细计划"

#     last_tool_result = state.get("last_tool_result", "")

#     formatted = prompt.format(
#         input=goal,
#         goal=goal,
#         context=context,
#         last_tool_result=last_tool_result,
#     )

#     response = llm.invoke(formatted)

#     content = response.content
#     try:
#         if isinstance(content, str):
#             text = content.strip()
#         else:
#             text = "".join(
#                 part["text"] if isinstance(part, dict) and "text" in part else str(part)
#                 for part in content  # type: ignore
#             ).strip()

#         if text.startswith("```"):
#             text = text.strip("`")
#             first_brace = text.find("{")
#             last_brace = text.rfind("}")
#             if first_brace != -1 and last_brace != -1:
#                 text = text[first_brace : last_brace + 1]

#         plan_obj = json.loads(text)

#     except Exception as e:
#         plan_obj = {
#             "goal": goal,
#             "steps": [
#                 {
#                     "index": 1,
#                     "title": "无法解析 JSON，返回原始内容",
#                     "description": f"原始 LLM 输出为：{content}",
#                     "expected_output": "请上层 Agent 重新请求规划或提示模型修正格式。"
#                 }
#             ],
#             "error": f"JSON parse error: {type(e).__name__}: {e}",
#         }

#     print("计划任务结果:")
#     print(json.dumps(plan_obj, indent=2, ensure_ascii=False))

#     # ⭐ 关键修改：把 plan 存成一条 AIMessage 的列表
#     plan_msg = AIMessage(
#         content=json.dumps(plan_obj, ensure_ascii=False)
#     )

#     new_state: AgentState = {
#         **state,
#         "raw_response": response,
#         "plan": [plan_msg],          # 👈 这里变成 list[BaseMessage]
#         "last_tool_result": last_tool_result,
#     }
#     return new_state



def call_llm(state: AgentState) -> Dict[str, Any]:
    """
    调用 LLM 进行推理，生成下一步的思考、工具调用或最终答案。
    """
    print("--- Node: call_llm ---")
    
    # 准备输入消息
    messages = state["chat_history"] + [HumanMessage(content=state["input"])]
    
    # 如果是工具执行后的返回，需要将工具结果添加到消息历史中
    if state.get("last_tool_result"):
        # 找到上一个 AIMessage (包含工具调用的那个)
        last_ai_message = next((msg for msg in reversed(messages) if isinstance(msg, AIMessage) and msg.tool_calls), None)
        
        if last_ai_message:
            # 创建 ToolMessage
            tool_messages = []
            for i, tool_call in enumerate(last_ai_message.tool_calls):
                # 假设我们只处理上一个工具调用的结果
                tool_messages.append(ToolMessage(
                    content=state["last_tool_result"],
                    tool_call_id=tool_call["id"],
                ))
            
            # 将工具消息添加到历史中，然后是用户输入
            messages = state["chat_history"] + tool_messages + [HumanMessage(content=state["input"])]
        else:
            # 如果没有找到工具调用，说明是第一次运行或状态异常，直接用用户输入
            messages = state["chat_history"] + [HumanMessage(content=state["input"])]

    # 格式化系统提示词
    formatted_prompt = prompt.format(
        chat_history=messages,
        input=state["input"],
        last_tool_result=state.get("last_tool_result", "无")
    )
    
    # 调用 LLM
    response = llm_with_tools.invoke(formatted_prompt)
    # print(f"LLM Raw Response:\n{response}")
    
    # 更新状态
    new_messages = state["chat_history"] + [response] # <-- Added plan to chat history
    
    # 检查是否是最终答案
    # 如果没有工具调用，即使 content 为空也应该作为最终答案
    final_answer = None
    if not response.tool_calls:
        # 即使 content 为空字符串，也认为这是一个答案（避免陷入循环）
        final_answer = response.content if response.content else "[LLM返回空响应]"
    if len(new_messages) > MAX_HISTORY:
        new_messages = new_messages[-MAX_HISTORY:]
    return {
        "chat_history": new_messages,
        "agent_outcome": response,
        "final_answer": final_answer,
        "last_tool_result": None, # 清空上次工具结果
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
        # 理论上不应该发生，因为边已经处理了这种情况
        return {"last_tool_result": "Error: call_tool node reached without tool calls."}

    # 假设我们只处理第一个工具调用
    tool_call = tool_calls[0]
    tool_name = tool_call["name"]
    tool_args = tool_call["args"]
    plan = tool_call.get("plan", None)
    
    print(f"Executing Tool: {tool_name} with args: {tool_args}")
    
    # 查找并执行工具
    tool_func = next((t for t in ALL_TOOLS if t.name == tool_name), None)
    
    if not tool_func:
        result = f"Error: Tool '{tool_name}' not found."
    else:
        try:
            # 执行工具函数
            result = tool_func.invoke(tool_args)
            if tool_name == "plan_task":
                # 如果是 plan_task 工具，格式化输出为可读文本
                plan = json.loads(result)
                print("计划任务结果:")
                print(json.dumps(json.loads(result), indent=2, ensure_ascii=False))
        except Exception as e:
            result = f"Tool Execution Error in '{tool_name}': {type(e).__name__}: {e}"
    result_str = str(result)
    print(f"Tool Result: {result_str[:100]}...")
    
    # 更新状态
    return {
        "plan": plan,
        "last_tool_name": tool_name,
        "last_tool_result": result,
        "input": state["input"], # 保持用户输入不变，以便 LLM 知道要继续解决哪个问题
        "chat_history": state["chat_history"] # 历史消息已在 call_llm 中更新
    }

# --- 4. Graph Edges (Conditional Logic) ---

def should_continue(state: AgentState) -> str:
    """
    根据 LLM 的输出决定下一步是继续调用工具还是结束。
    """
    print("--- Edge: should_continue ---")
    
    # 检查是否达到最大迭代次数（防止无限循环）
    MAX_ITERATIONS = 10
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        print(f"Max iterations ({MAX_ITERATIONS}) reached. Ending.")
        return "end"
    
    # 检查 LLM 是否建议工具调用（优先检查）
    agent_outcome = state.get("agent_outcome")
    # print(" agent_outcome", agent_outcome)
    if isinstance(agent_outcome, BaseMessage):
        tool_calls = getattr(agent_outcome, 'tool_calls', None)
        if tool_calls:
            print(f"✅ Tool call suggested: {tool_calls[0]['name']}. Continuing to call_tool.")
            return "continue"
    
    # 检查 LLM 是否给出了最终答案
    final_answer = state.get("final_answer")
    if final_answer:
        print(f"✅ Final answer found: {final_answer[:100]}...")
        return "end"
    
    # 默认情况下结束
    print("❌ No tool call and no final answer. Ending.")
    print(f"   agent_outcome: {agent_outcome}")
    print(f"   final_answer: {final_answer}")
    return "end"

# --- 5. Build the Graph ---

def build_graph():
    
    
    # create_react_agent()
    workflow = StateGraph(AgentState)

    # 1. 定义节点
    workflow.add_node("llm", call_llm)
    workflow.add_node("tool", call_tool)
    # workflow.add_node("planner", planner_node)

    # 2. 设置入口
    workflow.set_entry_point("llm")
    
    # workflow.add_edge("planner", "llm")

    # 3. 定义边
    # 从 LLM 节点出发，根据 should_continue 的结果决定下一步
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "tool", # 如果需要工具，转到 tool 节点
            "end": END           # 如果是最终答案或达到限制，结束
        }
    )

    # 从 Tool 节点出发，执行完工具后，总是返回 LLM 进行下一步推理
    workflow.add_edge("tool", "llm")

    # 4. 编译图
    app = workflow.compile()
    return app

# --- 6. Main Execution ---

if __name__ == "__main__":
    from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

    # 编译 Agent
    app = build_graph()
    print("--- OpenManus LangGraph Agent Initialized ---")
    print("现在可以直接和 Agent 对话了，输入 exit/quit 结束会话。\n")

    # 持久化对话历史 & 迭代计数
    chat_history: list[BaseMessage] = []
    iteration = 0

    while True:
        try:
            user_input = input("你：").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[系统] 会话结束，再见～")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "q"}:
            print("[系统] 已退出对话。")
            break

        # 构造状态（这一部分字段必须和 AgentState 对齐）
        state = {
            "input": user_input,
            "chat_history": chat_history,
            "final_answer": None,
            "last_tool_name": None,
            "last_tool_result": None,
            "iteration": iteration,
        }

        # 👇 方式一：一步到位拿最终结果（推荐日常使用）
        result_state = app.invoke(state)

        # 如果你更想看中间 ReAct 过程，可以改用 stream：
        # result_state = None
        # for step in app.stream(state):
        #     # step 是一个 {node_name: partial_state} 的增量
        #     result_state = list(step.values())[-1]
        #     # 想调试的话，这里可以打印每一步：
        #     # print(step, "\n---")
        #
        # assert result_state is not None

        answer = result_state.get("final_answer") or "（Agent 没有返回 final_answer 字段……）"
        print(f"Agent：{answer}\n")

        # 更新对话历史，供下一轮使用
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=answer))

        # 同步迭代计数（如果图里有更新的话）
        iteration = result_state.get("iteration", iteration + 1)

