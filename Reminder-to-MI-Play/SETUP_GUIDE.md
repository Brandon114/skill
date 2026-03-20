# 米家智能提醒 - 配置详细指南

## 目录

1. [环境要求](#环境要求)
2. [获取米家账号](#获取米家账号)
3. [运行配置脚本](#运行配置脚本)
4. [配置文件详解](#配置文件详解)
5. [常见配置问题](#常见配置问题)

---

## 环境要求

### 硬件要求
- 至少一个米家智能音箱（推荐小爱音箱系列）
- 稳定的网络连接

### 软件要求
- macOS 或 Linux 系统（Windows 用户可使用 WSL）
- Bash 4.0 或更高版本
- 可选：`jq` 工具（用于 JSON 解析，推荐安装）

### 安装 jq（可选但推荐）

**macOS**：
```bash
brew install jq
```

**Linux**：
```bash
sudo apt-get install jq      # Ubuntu/Debian
sudo yum install jq          # CentOS/RHEL
```

---

## 获取米家账号

### 第一步：下载米家 App

- **iOS**：App Store 搜索"米家"
- **Android**：Google Play 或应用宝搜索"米家"

### 第二步：注册或登录

1. 打开米家 App
2. 点击"登录"
3. 选择登录方式：
   - 邮箱注册
   - 手机号注册
   - 微信登录
   - 支付宝登录

### 第三步：添加设备

1. 点击"+"添加设备
2. 搜索"小爱音箱"或你的具体型号
3. 按照提示连接到 WiFi
4. 添加到房间（如"客厅"）

---

## 运行配置脚本

### 快速配置（推荐）

打开终端，复制粘贴以下命令：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh
```

### 交互式配置流程

脚本会按以下顺序请求信息：

#### 1️⃣ 输入米家账号

```
米家账号（邮箱或手机号）: your_account@email.com
```

支持的格式：
- 邮箱：`user@email.com`
- 手机号：`+86 13800138000`

#### 2️⃣ 输入密码

```
米家密码: [密码将隐藏输入]
```

**安全提示**：
- 密码仅存储本地
- 不会上传至任何服务器
- 查看配置文件时密码不可见

#### 3️⃣ 选择服务器区域

```
选择服务器区域：
  1) 中国 (cn) - 默认
  2) 美国 (us)
  3) 欧洲 (eu)
  4) 印度 (in)
```

**选择指南**：
- 中国用户：选择 `1 (cn)`
- 欧洲用户：选择 `3 (eu)`
- 美国用户：选择 `2 (us)`
- 印度用户：选择 `4 (in)`

#### 4️⃣ 选择主播报设备

脚本会自动检测你的设备列表：

```
检测到的小爱音箱设备：
  - 客厅音箱 (XiaoAi)
  - 卧室音箱 (XiaoAi Mini)
  - 厨房音箱 (XiaoAi)

选择主播报设备名称 (默认: 客厅音箱): 客厅音箱
```

### 配置完成

配置成功后，你会看到：

```
✓ 配置完成！

配置信息：
  • 账号：your_account@email.com
  • 服务器：cn
  • 主播报设备：客厅音箱

后续步骤：
  1. 返回 WorkBuddy 聊天框
  2. 尝试创建一个提醒
  3. 说："创建一个测试提醒"
```

---

## 配置文件详解

### 文件位置

```
~/.workbuddy/skills/mijia-smart-reminder/data/config.json
```

### 文件结构示例

```json
{
  "version": "1.0.0",
  "mijia": {
    "username": "your_account@email.com",
    "server": "cn",
    "primary_device": "客厅音箱",
    "auth_time": "2026-03-19T10:30:00Z"
  },
  "devices": [
    {
      "name": "客厅音箱",
      "device_id": "device_001",
      "type": "speaker",
      "model": "XiaoAi",
      "enabled": true
    }
  ],
  "settings": {
    "volume": 50,
    "repeat_count": 2,
    "repeat_interval": 2
  }
}
```

### 字段说明

#### `mijia` 节点

| 字段 | 说明 | 示例 |
|------|------|------|
| `username` | 米家账号 | `user@email.com` |
| `server` | 服务器地区 | `cn` / `us` / `eu` / `in` |
| `primary_device` | 默认播报设备 | `客厅音箱` |
| `auth_time` | 认证时间 | `2026-03-19T10:30:00Z` |

#### `devices` 节点

| 字段 | 说明 | 示例 |
|------|------|------|
| `name` | 设备显示名称 | `客厅音箱` |
| `device_id` | 设备唯一 ID | `device_001` |
| `type` | 设备类型 | `speaker` |
| `model` | 设备型号 | `XiaoAi` / `XiaoAi Mini` |
| `enabled` | 是否启用 | `true` / `false` |

#### `settings` 节点

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `volume` | 播报音量 (0-100) | `50` |
| `repeat_count` | 重复次数 | `2` |
| `repeat_interval` | 重复间隔(秒) | `2` |

---

## 常见配置问题

### Q1：忘记了米家密码

**解决步骤**：

1. 打开米家 App
2. 点击"我的" → "设置" → "账号与安全"
3. 点击"修改密码"
4. 按照指引重置密码
5. 密码重置后，重新运行配置脚本：
   ```bash
   bash scripts/setup-mijia.sh
   ```
6. 选择"Y"重新配置

### Q2：账号登录失败

**可能原因和解决方案**：

1. **账号不正确**
   - 确认使用的是米家账号（不是小米账号）
   - 检查邮箱或手机号是否拼写正确

2. **网络问题**
   - 检查网络连接：`ping 1.1.1.1`
   - 尝试切换 WiFi 或移动网络
   - 检查防火墙是否阻止

3. **账号被锁定**
   - 米家 App 中登录几次失败后账号可能被暂时锁定
   - 等待 30 分钟后再试
   - 或在米家 App 中正常登录以解锁

### Q3：检测不到设备

**可能原因**：

1. **设备未连接到网络**
   - 检查小爱音箱是否连接到 WiFi
   - 检查 WiFi 信号强度
   - 重启音箱：断电 10 秒后重新通电

2. **设备不在同一网络**
   - 确保计算机和音箱连接同一 WiFi
   - 避免使用 5GHz 频段（某些旧设备不支持）

3. **米家 App 同步延迟**
   - 关闭并重新打开米家 App
   - 等待 1-2 分钟让设备列表同步
   - 重新运行配置脚本

### Q4：配置文件被误删除

**恢复方法**：

重新运行配置脚本（会覆盖现有配置）：
```bash
bash scripts/setup-mijia.sh
```

或手动恢复：
```bash
cp config.example.json ~/.workbuddy/skills/mijia-smart-reminder/data/config.json
# 然后编辑 config.json，填入你的真实信息
```

### Q5：更改设备或主播报设备

**步骤**：

1. 在米家 App 中修改设备配置
2. 重新运行配置脚本：
   ```bash
   bash scripts/setup-mijia.sh
   ```
3. 选择"Y"重新配置

---

## 安全最佳实践

### ✅ 推荐做法

- ✓ 定期检查配置文件权限（应为 600）
- ✓ 定期更新米家 App 和设备固件
- ✓ 在个人计算机上使用，避免在公共计算机配置
- ✓ 定期查看播报日志

### ❌ 禁止做法

- ✗ 不要在代码中硬编码密码
- ✗ 不要将配置文件分享给他人
- ✗ 不要在不信任的网络上修改配置
- ✗ 不要将密码保存在浏览器历史中

---

## 验证配置

配置完成后，检查连接状态：

```bash
bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/check-mijia-status.sh
```

应该看到类似输出：

```
✓ 配置文件已找到

配置信息：
  • 账号：your_account@email.com
  • 服务器：cn
  • 设备数量：3
  • 主播报设备：客厅音箱

✓ 网络连接正常

设备列表：
  ✓ 客厅音箱 (XiaoAi) - device_001
  ✓ 卧室音箱 (XiaoAi Mini) - device_002
  ✗ 厨房音箱 (XiaoAi) - device_003
```

---

## 需要帮助？

1. 查看脚本日志：
   ```bash
   cat ~/.workbuddy/skills/mijia-smart-reminder/data/logs/broadcast-log.txt
   ```

2. 在 WorkBuddy 中输入：
   ```
   /check-mijia-status
   ```

3. 查看完整文档：`SKILL.md`
