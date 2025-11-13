from langchain_community.llms import Tongyi
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional, List, Dict, Any
from operator import add
import os
from tools import ALL_TOOLS
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage

# 设置环境变量
os.environ["DASHSCOPE_API_KEY"] = 'sk-7105444cad4d4699806f10612e4c9a25'

# 使用 TypedDict 和 Annotated 定义状态 schema
class AgentState(TypedDict):
    input: str
    chat_history: Annotated[List[BaseMessage], add]
    final_answer: Annotated[Optional[str], lambda x, y: y]
    last_tool_name: Annotated[Optional[str], lambda x, y: y]
    last_tool_result: Annotated[Optional[str], lambda x, y: y]
    iteration: Annotated[int, lambda x, y: y]
    agent_outcome: Annotated[Optional[Any], lambda x, y: y]  # LLM 的输出

model = Tongyi()

# ========== LLM 节点 ==========
def call_llm(state: AgentState) -> Dict[str, Any]:
    """调用 LLM 进行推理，生成下一步的思考、工具调用或最终答案"""
    print("\n--- Node: call_llm ---")
    
    # 获取用户输入
    user_input = state["input"]
    
    # 调用模型
    print(f"📝 处理输入: {user_input}")
    response = model.invoke(user_input)
    
    print(f"🤖 LLM 响应: {response[:100]}..." if len(response) > 100 else f"🤖 LLM 响应: {response}")
    
    # 构造新的聊天历史
    new_messages = state["chat_history"] + [
        HumanMessage(content=user_input),
        AIMessage(content=response)
    ]
    
    # 检查是否有工具调用标记（简单启发式方法）
    # 在实际应用中，LLM 应该返回结构化的工具调用格式
    has_tool_call = False
    tool_calls = []
    
    # 更新状态
    return {
        "chat_history": new_messages,
        "agent_outcome": response,
        "final_answer": None if has_tool_call else response,
        "iteration": state["iteration"] + 1
    }

# ========== 工具执行节点 ==========
def call_tool(state: AgentState) -> Dict[str, Any]:
    """执行 LLM 建议的工具调用"""
    print("\n--- Node: call_tool ---")
    
    agent_outcome = state["agent_outcome"]
    
    # 简单演示：解析响应中的工具名称
    # 在实际应用中应该有更完善的工具调用格式
    tools_names = [tool.name for tool in ALL_TOOLS]
    
    tool_name = None
    tool_args = {}
    
    # 检查响应中是否包含工具名称
    for tool in tools_names:
        if tool in agent_outcome.lower():
            tool_name = tool
            break
    
    if not tool_name:
        print("⚠️  未检测到工具调用")
        return {
            "last_tool_name": None,
            "last_tool_result": "未检测到工具调用"
        }
    
    print(f"🔧 执行工具: {tool_name}")
    
    # 查找工具
    tool_func = next((t for t in ALL_TOOLS if t.name == tool_name), None)
    
    if not tool_func:
        result = f"❌ 错误: 工具 '{tool_name}' 不存在"
    else:
        try:
            # 根据工具类型构造参数
            if tool_name == "file_read":
                result = tool_func.invoke({"path": "./styudy.py"})
            elif tool_name == "code_exec":
                result = tool_func.invoke({"code": "print('Hello from code_exec!')"})
            elif tool_name == "search_info":
                result = tool_func.invoke({"queries": ["Tongyi LLM", "LangGraph"]})
            else:
                result = tool_func.invoke({})
        except Exception as e:
            result = f"❌ 工具执行错误: {type(e).__name__}: {e}"
    
    print(f"✅ 工具结果: {result[:100]}..." if len(result) > 100 else f"✅ 工具结果: {result}")
    
    return {
        "last_tool_name": tool_name,
        "last_tool_result": result,
        "iteration": state["iteration"] + 1,
        "chat_history": state["chat_history"] + [ToolMessage(content=result, tool_call_id="")]
    }

# ========== 条件判断函数 ==========
def should_continue(state: AgentState) -> str:
    """根据 LLM 的输出决定下一步：继续调用工具还是结束"""
    print("\n--- Edge: should_continue ---")
    
    # 检查是否达到最大迭代次数
    MAX_ITERATIONS = 5
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        print(f"⏹️  达到最大迭代次数 ({MAX_ITERATIONS})")
        return "end"
    
    # 检查是否已有最终答案
    if state.get("final_answer"):
        print("✅ 最终答案已生成，结束")
        return "end"
    
    # 检查是否需要工具
    agent_outcome = state.get("agent_outcome", "")
    tools_names = [tool.name for tool in ALL_TOOLS]
    
    # 简单启发式方法：检查响应中是否包含工具名称
    for tool in tools_names:
        if tool in agent_outcome.lower():
            print(f"🔧 检测到工具调用: {tool}，继续...")
            return "continue"
    
    print("📌 未检测到工具调用，结束")
    return "end"

# ========== 构建图 ==========
def build_graph():
    """构建 LangGraph 工作流"""
    workflow = StateGraph(AgentState)

    # 1. 定义节点
    workflow.add_node("llm", call_llm)
    workflow.add_node("tool", call_tool)

    # 2. 设置入口
    workflow.set_entry_point("llm")

    # 3. 定义条件边
    workflow.add_conditional_edges(
        "llm",
        should_continue,
        {
            "continue": "tool",  # 如果需要工具，转到 tool 节点
            "end": END           # 如果是最终答案或达到限制，结束
        }
    )

    # 从 Tool 节点返回 LLM 进行下一步推理
    workflow.add_edge("tool", "llm")

    # 4. 编译图
    app = workflow.compile()
    return app

# ========== 主程序 ==========
if __name__ == "__main__":
    print("=" * 70)
    print("🤖 OpenManus Agent (Tongyi + LangGraph + 工具调用)")
    print("=" * 70)
    
    # 构建图
    app = build_graph()
    
    # 交互式循环
    chat_history = []
    
    while True:
        print("\n" + "=" * 70)
        user_input = input("你: ").strip()
        
        if not user_input:
            continue
        
        if user_input.lower() in ['exit', 'quit', '退出']:
            print("再见！")
            break
        
        # 创建初始状态
        initial_state = {
            "input": user_input,
            "chat_history": chat_history,
            "final_answer": None,
            "last_tool_name": None,
            "last_tool_result": None,
            "iteration": 0,
            "agent_outcome": None
        }
        
        # 运行 Agent
        try:
            result = app.invoke(initial_state)
            
            # 更新聊天历史
            chat_history = result.get("chat_history", chat_history)
            
            # 输出结果
            print("\n" + "=" * 70)
            print(f"🤖 代理: {result.get('final_answer', '无法生成答案')}")
            if result.get('last_tool_result'):
                print(f"🔧 最后工具结果: {result['last_tool_result'][:200]}...")
            print(f"⏱️  迭代次数: {result.get('iteration', 0)}")
            print("=" * 70)
        
        except Exception as e:
            print(f"❌ 错误: {type(e).__name__}: {e}")
            continue
