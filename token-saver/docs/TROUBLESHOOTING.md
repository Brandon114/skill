# Token-Saver 故障排除指南

本文档帮助您解决使用 Token-Saver Skill 时遇到的问题。

---

## 📋 目录

1. [常见问题](#常见问题)
2. [安装问题](#安装问题)
3. [运行问题](#运行问题)
4. [配置问题](#配置问题)
5. [脚本生成问题](#脚本生成问题)
6. [获取帮助](#获取帮助)

---

## 常见问题

### Q1: Token-Saver 没有响应？

**症状**：输入了请求，但没有看到 Token-Saver 的优化建议。

**可能原因**：
1. Skill 未正确加载
2. 功能被禁用（配置文件中设置为 `false`）
3. 当前对话轮次或 token 未达到阈值

**解决方法**：
```bash
# 1. 检查 skill 是否存在
ls -la ~/.codebuddy/skills/token-saver/

# 2. 检查配置
cat ~/.codebuddy/skills/token-saver/config/settings.yaml

# 3. 确认功能已启用
# input_optimization: true
# enable_pattern_detection: true
```

---

### Q2: 模式检测没有触发？

**症状**：重复执行了 5 次相同操作，但没有看到脚本生成建议。

**可能原因**：
1. `pattern_threshold` 设置过高
2. `enable_pattern_detection` 被禁用
3. 操作不完全相同（相似度 < 80%）

**解决方法**：
```yaml
# 编辑 config/settings.yaml
token_saver:
  enable_pattern_detection: true
  pattern_threshold: 3  # 改为 3 次（默认）
```

---

### Q3: 生成的脚本无法运行？

**症状**：Token-Saver 生成了脚本，但运行时报错。

**可能原因**：
1. 脚本是模板，需要根据实际情况修改
2. 缺少执行权限
3. 依赖未安装

**解决方法**：
```bash
# 1. 添加执行权限
chmod +x script_name.sh

# 2. 查看脚本内容，根据实际情况修改
cat script_name.sh

# 3. 安装依赖（如果是 Python 脚本）
pip3 install -r requirements.txt
```

---

## 安装问题

### 问题 1：Skill 未加载

**错误信息**：无（只是功能不可用）

**检查步骤**：
```bash
# 1. 检查目录结构
ls -la /Users/admin/WorkBuddy/skill/token-saver/

# 2. 查看 CodeBuddy 日志
tail -f ~/.codebuddy/logs/codebuddy.log

# 3. 重新加载 Skill
# 在 CodeBuddy 中执行：/reload-skills
```

**解决方案**：
1. 确认目录结构完整（参见 [文件结构](#文件结构)）
2. 重启 CodeBuddy
3. 检查 `skill.yaml` 格式是否正确

---

### 问题 2：权限错误

**错误信息**：`Permission denied` 或 `无法读取配置文件`

**解决方法**：
```bash
# 1. 检查文件权限
ls -la /Users/admin/WorkBuddy/skill/token-saver/

# 2. 修复权限
chmod -R 755 /Users/admin/WorkBuddy/skill/token-saver/

# 3. 确认当前用户有读写权限
whoami
```

---

## 运行问题

### 问题 1：Token 估算不准确

**症状**：显示的 token 数量与实际相差较大。

**原因**：Token 估算基于简单规则（中文 1.5 字符/token，英文 4 字符/token），实际可能因模型而异。

**改进方法**：
```python
# 编辑 scripts/token_counter.py
# 根据实际使用情况调整参数

def _estimate_tokens(self, text: str) -> int:
    """估算 token 数量（改进版）"""
    # 更精细的估算逻辑
    # TODO: 根据实际 API 返回调整
    pass
```

---

### 问题 2：误报重复操作

**症状**：不同的操作被误判为重复。

**解决方法**：
```yaml
# 编辑 config/settings.yaml
token_saver:
  # 提高相似度阈值（默认 0.8 = 80%）
  pattern_similarity_threshold: 0.9  # 改为 90%
```

---

## 配置问题

### 问题 1：配置文件格式错误

**错误信息**：`YAML format error` 或配置项未生效。

**检查方法**：
```bash
# 使用 Python 验证 YAML 格式
python3 -c "import yaml; yaml.safe_load(open('config/settings.yaml'))"

# 如果有错误，会显示具体行号
```

**常见错误**：
1. 缩进不正确（必须使用空格，不能用 Tab）
2. 冒号后缺少空格（`key:value` → `key: value`）
3. 列表格式错误（`[item1, item2]` → `- item1`)

---

### 问题 2：配置修改未生效

**原因**：修改配置后需要重启 CodeBuddy。

**解决方法**：
1. 保存 `settings.yaml`
2. 重启 CodeBuddy
3. 或执行 `/reload-skills` 命令（如果支持）

---

## 脚本生成问题

### 问题 1：生成的脚本不符合预期

**症状**：脚本内容过于简单或逻辑错误。

**原因**：脚本生成器基于模板，需要手动完善。

**改进方法**：
1. 编辑 `templates/` 目录下的模板文件
2. 添加更多逻辑到生成的脚本中
3. 提交 Issue 或 Pull Request 改进模板

---

### 问题 2：脚本类型选择错误

**症状**：应该生成 Python 脚本，但生成了 Bash 脚本。

**解决方法**：
```yaml
# 编辑 config/settings.yaml
token_saver:
  # 手动指定脚本类型
  preferred_script_type: "python"  # bash/python/codebuddy_command
```

或在提示时手动选择脚本类型。

---

## 获取帮助

### 1. 查看日志

```bash
# CodeBuddy 日志
tail -f ~/.codebuddy/logs/codebuddy.log

# Token-Saver 日志（如果启用了文件日志）
tail -f /path/to/project/.token-saver.log
```

### 2. 调试模式

```yaml
# 编辑 config/settings.yaml
token_saver:
  logging:
    level: "DEBUG"  # 改为 DEBUG 模式
    save_to_file: true
```

### 3. 提交 Issue

如果以上方法都无法解决问题，请提交 Issue：

1. 访问：https://github.com/brandon/token-saver-skill/issues
2. 描述问题，附上：
   - 错误信息
   - 配置文件内容
   - 复现步骤

### 4. 社区帮助

- 加入讨论区：[链接]
- 邮件联系：author@example.com

---

## 📁 文件结构

完整的 Token-Saver 目录结构：

```
token-saver/
├── skill.yaml                 ✅ 必须
├── prompt-template.md        ✅ 必须
├── scripts/                  ✅ 必须
│   ├── input_optimizer.py
│   ├── context_manager.py
│   ├── output_controller.py
│   ├── file_optimizer.py
│   ├── token_counter.py
│   └── pattern_detector.py
├── templates/                ✅ 必须
│   ├── bash_script.template
│   ├── python_script.template
│   └── codebuddy_command.template
├── config/                   ✅ 必须
│   └── settings.yaml
├── docs/                     ⭕ 可选
│   ├── API.md
│   ├── EXAMPLES.md
│   └── TROUBLESHOOTING.md
└── README.md                 ⭕ 可选
```

**图例**：
- ✅ 必须：缺少会导致功能不完整
- ⭕ 可选：用于文档和参考

---

## 🔗 相关链接

- [主文档](../README.md)
- [API 文档](./API.md)
- [使用示例](./EXAMPLES.md)
- [GitHub 仓库](https://github.com/brandon/token-saver-skill)

---

**仍然有问题？** 不要犹豫，提交 Issue 或联系作者！🙏
