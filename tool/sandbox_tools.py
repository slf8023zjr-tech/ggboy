# tool/sandbox_tools.py
from dotenv import load_dotenv
from ppio_sandbox.code_interpreter import Sandbox
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import os
import threading

load_dotenv()

# --- 1. 全局单例 Sandbox（避免每次调用都新建一个实例耗时又烧钱） ---

_sbx = None
_sbx_lock = threading.Lock()


def get_sandbox() -> Sandbox:
    """
    懒加载 + 单例：第一次调用时创建 PPIO Sandbox，后续复用。
    """
    global _sbx
    if _sbx is None:
        with _sbx_lock:
            if _sbx is None:
                api_key = os.getenv("PPIO_API_KEY")
                if not api_key:
                    raise RuntimeError(
                        "环境变量 PPIO_API_KEY 未设置，请在 .env 中添加 PPIO_API_KEY=xxx"
                    )
                _sbx = Sandbox.create()
    return _sbx


# --- 2. 定义工具入参 schema（方便 Tongyi 做 function calling） ---

class SandboxCodeExecArgs(BaseModel):
    code: str = Field(
        ...,
        description="要在沙箱中执行的完整 Python 代码字符串，比如 print('hello world')",
    )


# --- 3. LangChain 工具：给 LLM 调用的入口 ---

@tool("sandbox_code_exec", args_schema=SandboxCodeExecArgs)
def sandbox_code_exec(code: str) -> str:
    """
    在 PPIO 沙箱中执行一段 Python 代码，返回执行日志（转成字符串）。
    """
    sbx = get_sandbox()
    execution = sbx.run_code(code)

    logs = getattr(execution, "logs", "")
    # 防止 logs 不是字符串（比如 Logs 对象）
    if not isinstance(logs, str):
        logs = str(logs)

    return logs or "[sandbox 无输出]"



# --- 4.（可选）列出沙箱文件的工具 ---

class SandboxListFilesArgs(BaseModel):
    path: str = Field(
        "/",
        description="要列出的目录路径，默认为根目录 '/'",
    )


@tool("sandbox_list_files", args_schema=SandboxListFilesArgs)
def sandbox_list_files(path: str = "/") -> str:
    """
    列出沙箱文件系统中某个目录下的文件。
    """
    sbx = get_sandbox()
    files = sbx.files.list(path)
    return f"目录 {path} 下的文件：{files}"


# --- 5.（可选）提供一个关闭沙箱的工具 ---

@tool("sandbox_kill")
def sandbox_kill() -> str:
    """
    关闭当前沙箱实例，一般用于长时间会话结束后手动释放资源。
    再次调用 sandbox 工具时会自动重新创建。
    """
    global _sbx
    if _sbx is not None:
        _sbx.kill()
        _sbx = None
        return "当前 PPIO Sandbox 已关闭，后续调用会自动重新创建。"
    return "当前没有活跃的 Sandbox 实例。"
