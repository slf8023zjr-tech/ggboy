from ppio_sandbox.code_interpreter import Sandbox, SandboxQuery, SandboxState

# 创建一个沙箱，并设置元数据。
sandbox = Sandbox.create(
  metadata= {
    'name': 'My Sandbox',
  },
)

# 列出所有正在运行的沙箱。
running_sandboxes_paginator = Sandbox.list(
  query=SandboxQuery(
    state=[SandboxState.RUNNING],
  ),
)

running_sandboxes = running_sandboxes_paginator.next_items()

running_sandbox = running_sandboxes[0]
print('Running sandbox metadata:', running_sandbox.metadata)
print('Running sandbox id:', running_sandbox.sandbox_id)
print('Running sandbox started at:', running_sandbox.started_at)
print('Running sandbox template id:', running_sandbox.template_id)

# 输出结果：
# Running sandbox metadata: { name: 'My Sandbox' }
# Running sandbox id: i30sjldvvjx446kbkoofj-abf219fd
# Running sandbox started at: 2025-06-22T15:09:28.822Z
# Running sandbox template id: uhop43uji8fr7qkfbmsp

sandbox.kill()