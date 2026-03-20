#!/bin/bash

# 米家智能提醒 - 检查连接状态
# 功能：检查米家连接和设备状态
# 使用：bash scripts/check-mijia-status.sh

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
DATA_DIR="$SKILL_DIR/data"
CONFIG_FILE="$DATA_DIR/config.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   米家连接状态诊断${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ 未找到配置文件${NC}"
    echo ""
    echo "需要先进行初始化配置："
    echo "  bash scripts/setup-mijia.sh"
    exit 1
fi

echo -e "${GREEN}✓ 配置文件已找到${NC}"
echo ""

# 解析配置
if command -v jq &> /dev/null; then
    username=$(jq -r '.mijia.username' "$CONFIG_FILE")
    server=$(jq -r '.mijia.server' "$CONFIG_FILE")
    primary_device=$(jq -r '.mijia.primary_device' "$CONFIG_FILE")
    device_count=$(jq '.devices | length' "$CONFIG_FILE")
else
    username="[无法读取]"
    server="[无法读取]"
    primary_device="[无法读取]"
    device_count="[无法读取]"
fi

echo -e "${BLUE}配置信息：${NC}"
echo "  • 账号：$username"
echo "  • 服务器：$server"
echo "  • 设备数量：$device_count"
echo "  • 主播报设备：$primary_device"
echo ""

# 检查连接
echo -e "${BLUE}检查网络连接...${NC}"
if ping -c 1 api.xiaomi.com > /dev/null 2>&1 || ping -c 1 1.1.1.1 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 网络连接正常${NC}"
else
    echo -e "${YELLOW}⚠️  网络连接可能有问题${NC}"
fi

echo ""
echo -e "${BLUE}设备列表：${NC}"

if command -v jq &> /dev/null; then
    jq -r '.devices[] | 
        "  " + (.enabled | if . then "✓" else "✗" end) + 
        " \(.name) (\(.model)) - \(.device_id)"' "$CONFIG_FILE"
else
    echo "  请查看配置文件：$CONFIG_FILE"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ 诊断完成${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 建议
if [ "$server" = "cn" ]; then
    echo -e "${CYAN}💡 提示：使用中国服务器，确保网络可访问 api.xiaomi.com${NC}"
fi

echo ""
echo "下一步："
echo "  • 创建新提醒：bash scripts/add-reminder.sh"
echo "  • 查看所有提醒：bash scripts/list-reminders.sh"
echo ""
