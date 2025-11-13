import os
from typing import List
import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from .sandbox_tools import (
    sandbox_code_exec,
    sandbox_list_files,
    sandbox_kill,
)
# --- Pydantic Schemas for Tool Inputs ---

class FileReadInput(BaseModel):
    """Input for file_read tool."""
    path: str = Field(description="The absolute path to the file to read.")
    range_start: int = Field(default=1, description="The starting line number (1-indexed).")
    range_end: int = Field(default=-1, description="The ending line number (-1 means to the end of the file).")

class FileWriteInput(BaseModel):
    """Input for file_write tool."""
    path: str = Field(description="The absolute path to the file to write to. If the file exists, it will be overwritten.")
    content: str = Field(description="The full content to write to the file.")

class ShellExecInput(BaseModel):
    """Input for shell_exec tool."""
    command: str = Field(description="The shell command to execute. Use '&&' to chain commands. For Layer 2 tools, the command should be the utility name followed by arguments (e.g., 'manus-md-to-pdf input.md output.pdf').")
    session: str = Field(default="default", description="The unique identifier for the shell session.")
    timeout: int = Field(default=30, description="Timeout in seconds for the command execution.")

class SearchInfoInput(BaseModel):
    """Input for search_info tool."""
    queries: List[str] = Field(description="Up to 3 query variants that express the same search intent.")

class CodeExecInput(BaseModel):
    """Input for code_exec tool (Layer 3)."""
    code: str = Field(description="The Python code to execute. The code will be run in a separate process. Use 'print()' to output results.")


class PlanTaskInput(BaseModel):
    """Input for plan_task tool."""
    goal: str = Field(description="The main goal or task the agent should accomplish.")
    steps: List[str] = Field(
        description="An ordered list of concrete steps to accomplish the goal. "
                    "Each step should be a short, actionable instruction."
    )

# --- Layer 1: Atomic Function Calling Tools ---

@tool(args_schema=FileReadInput)
def file_read(path: str, range_start: int = 1, range_end: int = -1) -> str:
    """
    Reads the content of a text file.
    This is a Layer 1 atomic tool.
    """
    try:
        # Simulate the file tool's read action
        # In a real system, this would call the file tool API
        # Try UTF-8 first, then fall back to other encodings
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            # Fall back to GBK encoding
            try:
                with open(path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
            except UnicodeDecodeError:
                # Last resort: use latin-1 which accepts all byte values
                with open(path, 'r', encoding='latin-1') as f:
                    lines = f.readlines()
        
        start = max(0, range_start - 1)
        end = len(lines) if range_end == -1 else min(len(lines), range_end)
        
        content = "".join(lines[start:end])
        
        if not content:
            return f"Error: File '{path}' is empty or the specified range is invalid."
            
        return f"Successfully read file '{path}' (lines {start+1}-{end}):\n---\n{content}\n---"
    except FileNotFoundError:
        return f"Error: File not found at path '{path}'."
    except Exception as e:
        return f"Error reading file '{path}': {e}"

@tool(args_schema=FileWriteInput)
def file_write(path: str, content: str) -> str:
    """
    Writes content to a text file, overwriting existing content.
    This is a Layer 1 atomic tool.
    """
    try:
        # Simulate the file tool's write action
        # In a real system, this would call the file tool API
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        # Always write as UTF-8 for consistency
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote content to file '{path}'."
    except Exception as e:
        return f"Error writing to file '{path}': {e}"

@tool(args_schema=ShellExecInput)
def shell_exec(command: str, session: str = "default", timeout: int = 30) -> str:
    """
    Executes a shell command in the sandbox. This is the gateway for Layer 2 tools.
    This is a Layer 1 atomic tool.
    """
    # NOTE: In a real OpenManus environment, this function would call the
    # 'default_api:shell' tool. Since we are running *within* the sandbox,
    # we will simulate the execution using the standard 'os.system' or 'subprocess'
    # for simplicity, but the LLM's *intent* is to use the sandbox shell.
    # For this demonstration, we will just return a simulated success message
    # to allow the flow to continue, as direct execution of shell commands
    # via a Python function in this context is complex and error-prone.
    
    # To make it more realistic, we will use the actual shell tool for a real execution
    # but since we are defining the tools for the LLM *inside* the main script,
    # we must rely on the LLM to call the tool and the main loop to execute it.
    # For the purpose of this file, we will define the function signature.
    
    # For the sake of a runnable example, we will simulate the output.
    # In the main LangGraph loop, the actual execution will be handled by the Agent.
    
    # Layer 2 tools are called via this Layer 1 tool.
    if command.startswith("manus-"):
        return f"Simulated Shell Execution (Layer 2 Tool): Executing command '{command}' in session '{session}' with timeout {timeout}s. Output: 'Layer 2 tool execution successful. Result saved to file or returned.'"
    
    # General shell command
    return f"Simulated Shell Execution (Layer 1 Tool): Executing command '{command}' in session '{session}' with timeout {timeout}s. Output: 'Command executed successfully. (Simulated)'"

@tool(args_schema=SearchInfoInput)
def search_info(queries: List[str]) -> str:
    """
    Searches for general web information.
    This is a Layer 1 atomic tool.
    """
    # Simulate the search tool's info action
    # In a real system, this would call the search tool API
    query_str = ", ".join(queries)
    return f"Simulated Search Result: Successfully searched for '{query_str}'. Found 3 relevant articles: [Article 1: LangGraph Basics], [Article 2: OpenManus Architecture], [Article 3: Function Calling in LLMs]."

# --- Layer 3: Code Execution Tool ---

@tool(args_schema=CodeExecInput)
def code_exec(code: str) -> str:
    """
    Executes arbitrary Python code in a sandboxed environment. This is the gateway for Layer 3.
    This is a Layer 3 tool, but exposed as a Layer 1-like function call to the LLM.
    """
    # NOTE: In a real system, this would involve a secure, isolated execution environment.
    # For this demonstration, we will use a simple exec() with output capture.
    # WARNING: Using exec() is inherently unsafe in a production environment.
    
    import io
    import sys
    
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output
    
    try:
        # Execute the code
        exec(code, {})
        output = redirected_output.getvalue()
        return f"Code Execution Successful (Layer 3):\n---\n{output}\n---"
    except Exception as e:
        return f"Code Execution Error (Layer 3):\n---\n{type(e).__name__}: {e}\n---"
    finally:
        sys.stdout = old_stdout
        
        
@tool(args_schema=PlanTaskInput)
def plan_task(goal: str, steps: List[str]) -> str:
    """
    Creates a structured plan for a given goal.
    This is a planning helper tool: the LLM decides the steps and uses this
    tool to record the plan in a consistent JSON format.
    """
    plan = {
        "goal": goal,
        "steps": [
            {
                "index": i + 1,
                "description": step
            }
            for i, step in enumerate(steps)
        ],
        "note": "This plan was generated by the LLM and recorded via the plan_task tool."
    }
    # 返回 JSON 字符串，方便 LLM 继续解析 / 调试
    return json.dumps(plan, ensure_ascii=False, indent=2)


# Combine all tools for the LLM
ALL_TOOLS = [file_read, file_write, shell_exec, search_info, code_exec, plan_task,sandbox_code_exec,sandbox_list_files,sandbox_kill,]