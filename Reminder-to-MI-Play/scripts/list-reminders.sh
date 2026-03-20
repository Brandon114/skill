#!/bin/bash

# 米家智能提醒 - 列出所有提醒
# 功能：显示当前所有提醒及其状态
# 使用：bash scripts/list-reminders.sh

set -e

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
DATA_DIR="$SKILL_DIR/data"
REMINDERS_FILE="$DATA_DIR/reminders.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   提醒列表${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查提醒文件
if [ ! -f "$REMINDERS_FILE" ]; then
    echo -e "${YELLOW}⚠️  还没有创建任何提醒${NC}"
    echo ""
    echo "创建第一个提醒："
    echo "  bash scripts/add-reminder.sh"
    exit 0
fi

# 读取并显示提醒
if command -v jq &> /dev/null; then
    count=$(jq 'length' "$REMINDERS_FILE" 2>/dev/null || echo "0")
else
    # 备选计数方法
    count=$(grep -c '"id"' "$REMINDERS_FILE" 2>/dev/null || echo "0")
fi

if [ "$count" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  还没有创建任何提醒${NC}"
    exit 0
fi

echo -e "${GREEN}找到 $count 个提醒${NC}"
echo ""

# 解析并显示每个提醒（使用 jq 或备选方法）
if command -v jq &> /dev/null; then
    jq -r '.[] | 
        "ID: \(.id)\n" +
        "  内容：\(.content)\n" +
        "  时间：\(.schedule.type) \(.schedule.time)\n" +
        "  设备：\(.device)\n" +
        "  优先级：\(.priority)\n" +
        "  状态：\(.status)\n"' "$REMINDERS_FILE"
else
    # 简化版本显示
    echo "提醒数据文件位置："
    echo "  $REMINDERS_FILE"
    echo ""
    echo "提醒数据样本："
    head -20 "$REMINDERS_FILE"
fi

echo ""
echo -e "${BLUE}常见操作：${NC}"
echo "  • 编辑提醒：bash scripts/update-reminder.sh"
echo "  • 手动播报：bash scripts/broadcast-reminder.sh <ID>"
echo "  • 检查连接：bash scripts/check-mijia-status.sh"
echo ""
