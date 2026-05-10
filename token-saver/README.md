# Token-Saver Skill

**智能 Token 优化助手** - 自动节省 token 用量，识别重复模式并生成可复用脚本。

作者: Brandon  
版本: 1.0.0  
许可证: MIT

---

## ✨ 功能特性

### 🎯 核心功能

1. **输入优化器** (Input Optimizer)
   - 自动检测冗余表达（"请帮我..."、"详细地..."等）
   - 提供精简建议，显示预估 token 节省量
   - 识别重复提问，避免重复回答

2. **上下文管理器** (Context Manager)
   - 监控对话轮次和 token 消耗
   - 对话过长时主动提醒用户压缩或开启新对话
   - 帮助保存关键信息到 memory

3. **输出控制器** (Output Controller)
   - 根据任务类型自动选择输出模式
   - 支持手动切换：short / normal / detail / debug
   - 智能调整详细程度，避免过度输出

4. **文件读取优化器** (File Optimizer)
   - 智能缓存：3 轮内不重复读取同一文件
   - 片段读取：大文件只读取相关代码行（±10 行）
   - 批量读取：并行读取多个文件
   - 格式过滤：避免读取二进制文件

5. **重复检测器** (Repetition Detector)
   - 检测并阻止重复的工具调用
   - 防止相似的文件读取
   - 避免重复的代码执行

6. **模式检测器与脚本生成器** ⭐ (Pattern Detector & Script Generator)
   - **自动识别重复操作模式**（完全相同的请求、相似意图、操作序列）
   - **评估可脚本化性**
   - **自动生成可复用的脚本**（Bash / Python / CodeBuddy 命令）
   - **询问用户确认后保存**
   - **预估节省量并跟踪效果**

7. **Token 使用可视化** (Token Dashboard)
   - 实时显示 token 消耗情况
   - 区分输入、输出、工具调用的消耗
   - 预估 API 成本（支持多种模型）

---

## 🚀 快速开始

### 安装

1. **下载 skill**
   ```bash
   # 方式 1：从 GitHub 克隆（如果已发布）
   git clone https://github.com/brandon/token-saver-skill.git
   
   # 方式 2：手动下载并解压
   # 将 token-saver/ 目录放到您的 CodeBuddy skills 目录
   ```

2. **放置到正确位置**
   ```bash
   # 选项 A：用户级 skill（推荐）
   cp -r token-saver ~/.codebuddy/skills/
   
   # 选项 B：项目级 skill
   cp -r token-saver /path/to/your/project/.codebuddy/skills/
   ```

3. **重启 CodeBuddy**
   - 重启后，skill 会自动加载

---

## 📋 使用示例

### 示例 1：输入优化

**用户原始输入**（冗长）：
```
"你好，我遇到了一个问题，就是我的代码在运行的时候会报错，
具体的错误信息我也不知道怎么描述，反正就是不太对劲，
你能不能帮我详细地检查一下我的代码，包括每一个函数，
每一个变量，每一个逻辑流程，然后告诉我到底哪里出错了，
最好还能给我一些改进建议..."
```

**Token-Saver 优化后**：
```
💡 Token 优化建议：
原始输入 (预估 180 tokens)：
  "你好，我遇到了一个问题，就是我的代码在运行的时候会报错..."
  
建议修改为 (预估 35 tokens)：
  "检查代码报错原因，提供修复建议"
  
预计节省：145 tokens (80%)
```

---

### 示例 2：上下文管理提醒

**当对话变长时**：
```
⚠️ 上下文管理提醒：
当前对话：23 轮，预估 12,500 tokens
建议操作：
  1. 使用 /compact 压缩历史记录
  2. 将关键信息保存到 memory：
     - 项目路径：/path/to/project
     - 当前问题：修复登录 bug
  3. 开启新对话处理新任务
```

---

### 示例 3：输出模式自动切换

**用户请求**：`"解释一下什么是递归"`

**Token-Saver 判断**：概念解释 → 中等模式

**输出**（节省 ~300 tokens）：
```
递归是函数调用自身的技术。

示例（Python）：
def factorial(n):
    if n == 1:
        return 1
    return n * factorial(n-1)

核心要点：
- 必须有终止条件
- 每次调用应接近终止条件
- 注意栈溢出风险

需要详细讲解？我可以展开说明工作原理、应用场景和常见陷阱。
```

---

### 示例 4：模式检测与脚本生成 ⭐

**场景**：用户连续 3 次请求检查不同文件的语法

**用户重复请求**：
```
1. "检查 main.py 有没有语法错误"
2. "检查 utils.py 有没有语法错误"
3. "检查 config.py 有没有语法错误"
```

**Token-Saver 检测到模式**：
```
🤖 检测到重复操作模式！

我发现您在最近 10 轮对话中，重复执行了类似的操作 3 次：
  1. "检查 main.py 语法"
  2. "检查 utils.py 语法"
  3. "检查 config.py 语法"

💡 建议：
  我可以为您生成一个批量检查脚本，下次您只需要说：
  "运行语法检查" 即可完成所有操作。

📊 预期收益：
  - 每次节省：~600 tokens
  - 如果重复 10 次：节省 ~6,000 tokens

❓ 是否生成脚本？
  [是] 生成并保存到项目目录
  [否] 本次不生成
  [总是] 以后自动生成，无需询问
```

**用户选择"是"后，生成的脚本** (`batch_syntax_check.sh`)：
```bash
#!/bin/bash
# 自动生成的脚本 - 批量语法检查
# 触发原因：检测到重复的文件检查请求 (3 次)

files=("main.py" "utils.py" "config.py")

for file in "${files[@]}"; do
  echo "检查 $file ..."
  python3 -m py_compile "$file"
  if [ $? -eq 0 ]; then
    echo "✅ $file 语法正确"
  else
    echo "❌ $file 存在语法错误"
  fi
done
```

**优化后的交互**：
```
用户："运行语法检查"
AI：  （直接运行脚本，返回所有结果）

预估节省：
  原始：3 次对话 × 600 tokens = 1,800 tokens
  脚本：1 次对话 × 200 tokens = 200 tokens
  节省：1,600 tokens (89%)
```

---

## ⚙️ 配置

配置文件位置：`token-saver/config/settings.yaml`

### 主要配置项

```yaml
token_saver:
  # 输入优化
  input_optimization: true
  max_input_length: 500
  
  # 上下文管理
  auto_compact_suggestion: true
  compact_threshold_rounds: 20
  compact_threshold_tokens: 8000
  
  # 输出控制
  default_output_mode: "auto"
  
  # 文件读取优化
  enable_file_cache: true
  cache_expiry_rounds: 3
  
  # 模式检测与脚本生成
  enable_pattern_detection: true
  pattern_threshold: 3  # 重复 3 次以上触发
  auto_generate_scripts: false  # 是否自动生成（无需询问）
```

### 调整配置

编辑 `config/settings.yaml`，修改对应项，然后重启 CodeBuddy。

---

## 🛠️ 高级用法

### 1. 手动切换输出模式

```
用户："@token-saver mode short"
AI： ✅ 已切换到简短输出模式

用户："@token-saver mode detail"
AI： ✅ 已切换到详细输出模式
```

### 2. 查看 Token 使用统计

```
用户："显示 token 统计"
AI：
📊 Token 使用统计：
  - 本次对话：8,450 tokens
  - 输入消耗：2,100 tokens (25%)
  - 输出消耗：4,800 tokens (57%)
  - 工具调用：1,550 tokens (18%)
  
💰 预估成本 (GPT-4)：$0.25
```

### 3. 管理生成的脚本

```
用户："查看生成的脚本"
AI：
📂 已生成的脚本：
  1. batch_syntax_check.sh
  2. batch_analyze_data.py
  3. auto_generated_command.yaml
  
您可以：
  - "运行脚本 X"
  - "删除脚本 X"
  - "查看脚本 X"
```

---

## 📁 文件结构

```
token-saver/
├── skill.yaml                 # Skill 元数据
├── prompt-template.md        # 核心提示词模板
├── scripts/                  # Python 脚本
│   ├── input_optimizer.py    # 输入优化器
│   ├── context_manager.py    # 上下文管理器
│   ├── output_controller.py  # 输出控制器
│   ├── file_optimizer.py     # 文件读取优化器
│   ├── token_counter.py      # Token 计数器
│   └── pattern_detector.py  # 模式检测器（核心）
├── templates/                # 脚本模板
│   ├── bash_script.template
│   ├── python_script.template
│   └── codebuddy_command.template
├── config/                   # 配置文件
│   └── settings.yaml
├── docs/                     # 文档
│   ├── API.md
│   ├── EXAMPLES.md
│   └── TROUBLESHOOTING.md
└── README.md                 # 本文件
```

---

## 🔧 故障排除

### 问题 1：Skill 未加载

**症状**：无法使用 token-saver 的功能

**解决方法**：
1. 检查 skill 是否放在正确目录
2. 重启 CodeBuddy
3. 查看日志：`~/.codebuddy/logs/codebuddy.log`

### 问题 2：模式检测不工作

**症状**：重复操作未被检测到

**解决方法**：
1. 检查配置：`enable_pattern_detection: true`
2. 确认重复次数达到阈值（默认 3 次）
3. 查看日志，确认模式检测器是否运行

### 问题 3：生成的脚本有误

**症状**：自动生成的脚本无法运行

**解决方法**：
1. 脚本是模板，需要根据实际情况修改
2. 在 `settings.yaml` 中设置 `auto_generate_scripts: false`，改为手动确认
3. 提交 Issue 报告问题

---

## 📊 效果展示

### 实际节省案例

| 场景 | 原始 Token 消耗 | 优化后 Token 消耗 | 节省量 | 节省率 |
|------|----------------|------------------|--------|--------|
| 冗长输入 | 500 | 100 | 400 | 80% |
| 重复文件读取 | 2000 | 200 | 1800 | 90% |
| 长对话未压缩 | 15000 | 5000 | 10000 | 67% |
| 重复操作（3次） | 3000 | 500 | 2500 | 83% |

---

## 🤝 贡献

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/AmazingFeature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/AmazingFeature`
5. 提交 Pull Request

---

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

## 📧 联系

- 作者：Brandon
- GitHub：[您的 GitHub 账号]
- 邮箱：[您的邮箱]

---

## ⚡ 致谢

感谢所有贡献者的努力！🙏

---

**⭐ 如果这个 skill 对您有帮助，请给它一个星标！**
