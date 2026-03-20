# 安装说明

## 快速安装

### 方法 1：自动安装（推荐）

1. 解压 zip 文件：
   ```bash
   unzip mijia-smart-reminder-v*.zip
   cd mijia-smart-reminder
   ```

2. 运行安装脚本：
   ```bash
   bash install.sh
   ```

### 方法 2：手动安装

1. 解压到 WorkBuddy skills 目录：
   ```bash
   unzip mijia-smart-reminder-v*.zip -d ~/.workbuddy/skills/
   ```

2. 初始化配置：
   ```bash
   bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh
   ```

---

## 验证安装

安装成功后，在 WorkBuddy 聊天框中输入：

```
/skills
```

应该能看到 `mijia-smart-reminder` 在列表中。

---

## 开始使用

1. 在 WorkBuddy 中说：
   ```
   配置米家账号
   ```

2. 或直接运行：
   ```bash
   bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh
   ```

3. 创建你的第一个提醒：
   ```
   我需要每天早上10点提醒我喝水
   ```

---

## 文件说明

- `SKILL.md` - 完整的功能说明和工作流程
- `README.md` - 快速开始指南
- `SETUP_GUIDE.md` - 详细的配置指南
- `scripts/` - 所有可执行脚本
- `config.example.json` - 配置文件示例
- `reminders.example.json` - 提醒数据示例

---

## 需要帮助？

1. 查看 README.md 的常见问题
2. 查看 SETUP_GUIDE.md 的详细配置说明
3. 运行诊断脚本：
   ```bash
   bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/check-mijia-status.sh
   ```
