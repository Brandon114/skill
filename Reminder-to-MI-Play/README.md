# 用小爱音箱定时播报提醒 - 快速开始指南

## 3 分钟快速上手

### 第一步：初始化配置（首次使用必做）

打开终端，运行配置脚本：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh
```

脚本会交互式地请求以下信息：
- 米家账号（邮箱或手机号）
- 米家密码
- 服务器选择（中国/美国/欧洲/印度）
- 选择主播报设备（如客厅音箱）

✅ 完成后，配置文件会自动保存到：
```
~/.workbuddy/skills/mijia-smart-reminder/data/config.json
```

### 第二步：创建第一个提醒

在 WorkBuddy 中，对 AI 说：

```
我需要每天早上10点提醒我喝水
```

或者手动运行脚本：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/add-reminder.sh
```

然后按照提示填写：
- 提醒内容
- 提醒时间
- 播报设备

### 第三步：测试播报

在 WorkBuddy 中说：

```
播报一下我的提醒
```

或手动运行：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/list-reminders.sh
```

查看所有提醒，然后：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/broadcast-reminder.sh <提醒ID>
```

---

## 常用命令

| 需求 | 命令 | 说明 |
|------|------|------|
| 首次配置 | `bash scripts/setup-mijia.sh` | 配置米家账号 |
| 创建提醒 | `bash scripts/add-reminder.sh` | 添加新提醒 |
| 查看提醒 | `bash scripts/list-reminders.sh` | 列出所有提醒 |
| 编辑提醒 | `bash scripts/update-reminder.sh` | 修改或删除提醒 |
| 手动播报 | `bash scripts/broadcast-reminder.sh <ID>` | 立即播报 |
| 检查连接 | `bash scripts/check-mijia-status.sh` | 诊断米家连接 |

---

## 配置文件位置

所有数据存储在 `~/.workbuddy/skills/mijia-smart-reminder/data/` 目录：

```
data/
├── config.json          # 米家账号配置（首次运行 setup 生成）
├── reminders.json       # 提醒列表
└── logs/
    └── broadcast-log.txt # 播报历史
```

---

## 支持的提醒类型

| 类型 | 说明 | 示例 |
|------|------|------|
| daily | 每天固定时间 | 每天 10:00 |
| workdays | 工作日固定时间 | 周一到周五 10:00 |
| weekly | 每周指定日期 | 每周一 15:00 |
| once | 一次性提醒 | 明天 14:30 |

---

## 故障排除

### 问题1：提示 "未找到配置文件"

**解决**：运行初始化脚本
```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh
```

### 问题2：提醒没有声音

**检查清单**：
1. 小爱音箱是否连接网络？
2. 音量是否调至合适水平？
3. 运行诊断脚本：
   ```bash
   bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/check-mijia-status.sh
   ```

### 问题3：播报失败

**查看日志**：
```bash
cat ~/.workbuddy/skills/mijia-smart-reminder/data/logs/broadcast-log.txt
```

---

## 隐私与安全

- ✅ 密码仅存储本地，永不上传
- ✅ 配置文件权限为 600（仅所有者可读）
- ✅ 提醒数据完全私密
- ⚠️ 不要在公共计算机上保存配置

---

## 下一步

- 阅读 `SKILL.md` 了解完整功能
- 查看 `config.example.json` 了解配置格式
- 查看 `reminders.example.json` 了解数据结构

---

**需要帮助？** 在 WorkBuddy 中输入：`/mijia-smart-reminder --help`
