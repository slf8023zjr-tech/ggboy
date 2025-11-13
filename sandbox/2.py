from ppio_sandbox.code_interpreter import Sandbox

sandbox = Sandbox.create()

# 列出所有沙箱（包括正在运行的和暂停的）
paginator = Sandbox.list()

firstPage = paginator.next_items()
if paginator.has_next:
    nextPage = paginator.next_items()

sandbox.kill()