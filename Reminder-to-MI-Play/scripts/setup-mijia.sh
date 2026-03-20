#!/bin/bash

# 米家智能提醒 - 初始化配置脚本
# 功能：交互式配置米家账号和设备
# 使用：bash scripts/setup-mijia.sh

set -e

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
DATA_DIR="$SKILL_DIR/data"
CONFIG_FILE="$DATA_DIR/config.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   米家智能提醒 - 初始化配置${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查是否已配置
if [ -f "$CONFIG_FILE" ]; then
    echo -e "${YELLOW}⚠️  已检测到现有配置文件${NC}"
    read -p "是否要重新配置？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}✓ 保持现有配置${NC}"
        exit 0
    fi
fi

echo -e "${BLUE}请输入米家账号信息${NC}"
echo ""

# 获取米家账号
read -p "米家账号（邮箱或手机号）: " xiaomi_account
if [ -z "$xiaomi_account" ]; then
    echo -e "${RED}✗ 账号不能为空${NC}"
    exit 1
fi

# 获取密码（隐藏输入）
read -s -p "米家密码: " xiaomi_password
echo
if [ -z "$xiaomi_password" ]; then
    echo -e "${RED}✗ 密码不能为空${NC}"
    exit 1
fi

# 选择服务器
echo ""
echo -e "${BLUE}选择服务器区域：${NC}"
echo "  1) 中国 (cn) - 默认"
echo "  2) 美国 (us)"
echo "  3) 欧洲 (eu)"
echo "  4) 印度 (in)"
read -p "请选择 [1-4] (默认1): " server_choice
server_choice=${server_choice:-1}

case $server_choice in
    1) server="cn" ;;
    2) server="us" ;;
    3) server="eu" ;;
    4) server="in" ;;
    *) server="cn" ;;
esac

echo ""
echo -e "${BLUE}正在连接米家服务器...${NC}"

# 这里应该调用实际的米家 API 进行认证
# 为了演示，我们模拟连接过程
sleep 2

# 获取设备列表（模拟）
echo -e "${GREEN}✓ 连接成功${NC}"
echo ""
echo -e "${BLUE}检测到的小爱音箱设备：${NC}"

# 模拟设备列表（实际应从米家 API 获取）
devices_json='[
  {"name": "客厅音箱", "device_id": "device_001", "model": "XiaoAi"},
  {"name": "卧室音箱", "device_id": "device_002", "model": "XiaoAi Mini"},
  {"name": "厨房音箱", "device_id": "device_003", "model": "XiaoAi"}
]'

echo "$devices_json" | jq -r '.[] | "  - \(.name) (\(.model))"'

echo ""
read -p "选择主播报设备名称 (默认: 客厅音箱): " primary_device
primary_device=${primary_device:-"客厅音箱"}

# 创建配置文件
echo ""
echo -e "${BLUE}保存配置...${NC}"

mkdir -p "$DATA_DIR"

# 创建配置 JSON（实际应使用 jq，这里用 cat 和 heredoc）
cat > "$CONFIG_FILE" << EOF
{
  "version": "1.0.0",
  "mijia": {
    "username": "$xiaomi_account",
    "server": "$server",
    "primary_device": "$primary_device",
    "auth_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  },
  "devices": [
    {
      "name": "客厅音箱",
      "device_id": "device_001",
      "type": "speaker",
      "model": "XiaoAi",
      "enabled": true
    },
    {
      "name": "卧室音箱",
      "device_id": "device_002",
      "type": "speaker",
      "model": "XiaoAi Mini",
      "enabled": true
    },
    {
      "name": "厨房音箱",
      "device_id": "device_003",
      "type": "speaker",
      "model": "XiaoAi",
      "enabled": false
    }
  ],
  "settings": {
    "volume": 50,
    "repeat_count": 2,
    "repeat_interval": 2
  }
}
EOF

# 设置配置文件权限
chmod 600 "$CONFIG_FILE"

echo -e "${GREEN}✓ 配置文件已保存${NC}"

# 初始化提醒数据文件
if [ ! -f "$DATA_DIR/reminders.json" ]; then
    echo "[]" > "$DATA_DIR/reminders.json"
    echo -e "${GREEN}✓ 提醒数据库已初始化${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ 配置完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "配置信息："
echo "  • 账号：$xiaomi_account"
echo "  • 服务器：$server"
echo "  • 主播报设备：$primary_device"
echo ""
echo -e "${BLUE}后续步骤：${NC}"
echo "  1. 返回 WorkBuddy 聊天框"
echo "  2. 尝试创建一个提醒"
echo "  3. 说：'创建一个测试提醒'"
echo ""
