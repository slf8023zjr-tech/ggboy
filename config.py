
import os

# --- Configuration for Tongyi Model ---

# DashScope API Key. If set to None, it will try to read from the DASHSCOPE_API_KEY environment variable.
# 您提供的 Key 已硬编码在 main.py 中，但最佳实践是放在这里或环境变量中。
DASHSCOPE_API_KEY = "sk-7105444cad4d4699806f10612e4c9a25"

# The model to use for the Agent. For Tongyi, "qwen-turbo" is a good choice.
AGENT_MODEL = "qwen-turbo"

# Maximum number of iterations for the React loop to prevent infinite loops
MAX_ITERATIONS = 10