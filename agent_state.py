from typing import TypedDict, List, Annotated, Union, Optional, Any
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from operator import add

from typing import TypedDict, List, Annotated, Union, Optional, Any
from langchain_core.messages import BaseMessage
from operator import add

class AgentState(TypedDict):
    """
    Represents the state of our LangGraph Agent.
    """
    # The user's initial input or the latest message in the conversation
    input: str

    # A list of all messages in the conversation history
    chat_history: Annotated[List[BaseMessage], add]

    # The final answer from the agent
    final_answer: Annotated[Optional[str], lambda x, y: y]

    # The name of the tool that was just executed
    last_tool_name: Annotated[Optional[str], lambda x, y: y]

    # The result of the last tool execution
    # 建议这里其实用 Any 更稳一点，如果你后面想返回 dict / 结构化数据：
    last_tool_result: Annotated[Optional[Any], lambda x, y: y]

    # The current iteration count (for debugging/limiting loops)
    iteration: Annotated[int, lambda x, y: y]

    # The LLM's output (AIMessage with potential tool_calls)
    agent_outcome: Annotated[Optional[Any], lambda x, y: y]

    # ====== 新增：任务的“总计划” ======
    # 例如：
    # {
    #   "goal": "...",
    #   "steps": [
    #       {"index": 1, "title": "...", "description": "...", "expected_output": "..."},
    #       ...
    #   ]
    # }
    plan: Annotated[Optional[dict], lambda x, y: y]
    goal: Annotated[Optional[dict], lambda x, y: y]
    



