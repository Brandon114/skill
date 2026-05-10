# Token-Saver API 文档

本文档描述 Token-Saver Skill 的 API 接口和使用方法。

---

## 📋 目录

1. [输入优化器 API](#输入优化器-API)
2. [上下文管理器 API](#上下文管理器-API)
3. [输出控制器 API](#输出控制器-API)
4. [文件读取优化器 API](#文件读取优化器-API)
5. [模式检测器 API](#模式检测器-API)
6. [脚本生成器 API](#脚本生成器-API)

---

## 输入优化器 API

### `optimize(text: str) -> Dict`

优化用户输入，移除冗余表达。

**参数**：
- `text` (str): 原始输入文本

**返回**：
```python
{
    'original': str,           # 原始文本
    'optimized': str,          # 优化后文本
    'original_tokens': int,    # 原始预估 tokens
    'optimized_tokens': int,   # 优化后预估 tokens
    'saved_tokens': int,       # 节省的 tokens
    'saved_percent': float     # 节省百分比
}
```

**示例**：
```python
from scripts.input_optimizer import InputOptimizer

optimizer = InputOptimizer()
result = optimizer.optimize("请帮我详细地分析一下这个代码")
print(result['optimized'])  # "分析代码"
print(result['saved_tokens'])  # 45
```

---

## 上下文管理器 API

### `check_context(messages: List[Dict]) -> Dict`

检查上下文状态，判断是否需要提醒用户。

**参数**：
- `messages` (List[Dict]): 对话消息列表

**返回**：
```python
{
    'should_warn': bool,        # 是否需要提醒
    'rounds': int,             # 当前轮次
    'estimated_tokens': int,   # 预估总 tokens
    'suggestions': List[str]   # 建议操作列表
}
```

**示例**：
```python
from scripts.context_manager import ContextManager

manager = ContextManager(threshold_rounds=20, threshold_tokens=8000)
result = manager.check_context(messages)

if result['should_warn']:
    print("建议操作:")
    for suggestion in result['suggestions']:
        print(f"  - {suggestion}")
```

---

## 输出控制器 API

### `get_output_mode(user_input: str) -> OutputMode`

获取当前任务应该使用的输出模式。

**参数**：
- `user_input` (str): 用户输入

**返回**：
- `OutputMode.SHORT` - 简短模式
- `OutputMode.NORMAL` - 正常模式
- `OutputMode.DETAIL` - 详细模式
- `OutputMode.DEBUG` - 调试模式

**示例**：
```python
from scripts.output_controller import OutputController, TaskType

controller = OutputController()
mode = controller.get_output_mode("这个代码有 bug，帮我修复")
print(mode)  # OutputMode.DETAIL
```

---

## 文件读取优化器 API

### `should_use_cache(file_path: str, current_round: int) -> Tuple[bool, Optional[str]]`

判断是否应该使用缓存。

**参数**：
- `file_path` (str): 文件路径
- `current_round` (int): 当前轮次

**返回**：
- `bool`: 是否使用缓存
- `str or None`: 缓存内容（如果可用）

**示例**：
```python
from scripts.file_optimizer import FileOptimizer

optimizer = FileOptimizer(cache_expiry_rounds=3)
use_cache, content = optimizer.should_use_cache("/path/to/file.py", current_round=5)

if use_cache:
    print("使用缓存内容")
else:
    print("需要重新读取")
```

---

## 模式检测器 API ⭐

### `analyze_request(user_input: str, tool_calls: List[Dict]) -> Optional[DetectedPattern]`

分析用户请求，检测重复模式。

**参数**：
- `user_input` (str): 用户输入
- `tool_calls` (List[Dict]): 工具调用列表

**返回**：
- `DetectedPattern` or `None`: 如果检测到模式，返回模式信息

**示例**：
```python
from scripts.pattern_detector import PatternDetector, ScriptGenerator

detector = PatternDetector(threshold=3)
generator = ScriptGenerator()

# 模拟重复请求
for text in ["检查 A", "检查 B", "检查 C"]:
    result = detector.analyze_request(text, [])
    
    if result:
        print(f"✅ 检测到重复模式！")
        print(f"类型: {result.pattern_type.value}")
        
        # 生成脚本
        script_content, filename = generator.generate_script(result)
        print(f"生成的脚本: {filename}")
```

---

## 脚本生成器 API

### `generate_script(pattern: DetectedPattern) -> Tuple[str, str]`

根据检测到的模式生成脚本。

**参数**：
- `pattern` (DetectedPattern): 检测到的模式

**返回**：
- `str`: 脚本内容
- `str`: 脚本文件名

**示例**：
```python
# 接上例
script_content, filename = generator.generate_script(result)

# 保存脚本
with open(f"/path/to/scripts/{filename}", 'w') as f:
    f.write(script_content)

print(f"✅ 脚本已保存: {filename}")
```

---

## 🔗 完整示例

```python
from scripts.input_optimizer import InputOptimizer
from scripts.context_manager import ContextManager
from scripts.output_controller import OutputController
from scripts.file_optimizer import FileOptimizer
from scripts.pattern_detector import PatternDetector, ScriptGenerator

# 1. 优化输入
optimizer = InputOptimizer()
result = optimizer.optimize(user_input)
if result['saved_tokens'] > 20:
    print(f"💡 建议优化输入，可节省 {result['saved_tokens']} tokens")

# 2. 检查上下文
manager = ContextManager()
context_result = manager.check_context(messages)
if context_result['should_warn']:
    print("⚠️ 对话较长，建议压缩")

# 3. 获取输出模式
controller = OutputController()
mode = controller.get_output_mode(user_input)
print(f"推荐输出模式: {mode.value}")

# 4. 检测重复模式
detector = PatternDetector(threshold=3)
pattern = detector.analyze_request(user_input, tool_calls)

if pattern:
    print(f"🤖 检测到重复模式！可节省 {pattern.estimated_savings} tokens")
    
    # 5. 生成脚本
    generator = ScriptGenerator()
    script_content, filename = generator.generate_script(pattern)
    print(f"生成的脚本: {filename}")
```

---

## 📊 配置参考

详见 `config/settings.yaml` 文件。

---

**需要更多帮助？** 查看 [EXAMPLES.md](./EXAMPLES.md) 或提交 Issue。
