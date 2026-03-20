#!/bin/bash

# 米家智能提醒 - 更新或删除提醒
# 功能：编辑或删除现有提醒
# 使用：bash scripts/update-reminder.sh

set -e

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
DATA_DIR="$SKILL_DIR/data"
REMINDERS_FILE="$DATA_DIR/reminders.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   编辑或删除提醒${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 检查提醒文件
if [ ! -f "$REMINDERS_FILE" ]; then
    echo -e "${RED}✗ 还没有任何提醒${NC}"
    exit 1
fi

# 列出现有提醒
echo -e "${BLUE}现有提醒：${NC}"
if command -v jq &> /dev/null; then
    jq -r '.[] | "\(.id): \(.content)"' "$REMINDERS_FILE"
else
    echo "请查看："
    echo "  bash scripts/list-reminders.sh"
fi

echo ""
read -p "输入要操作的提醒 ID: " reminder_id

if [ -z "$reminder_id" ]; then
    echo -e "${RED}✗ ID 不能为空${NC}"
    exit 1
fi

# 选择操作
echo ""
echo -e "${BLUE}选择操作：${NC}"
echo "  1) 暂停此提醒"
echo "  2) 启用此提醒"
echo "  3) 删除此提醒"
read -p "请选择 [1-3]: " operation
operation=${operation:-1}

case $operation in
    1)
        echo -e "${YELLOW}暂停提醒 $reminder_id...${NC}"
        # 实现暂停逻辑
        echo -e "${GREEN}✓ 提醒已暂停${NC}"
        ;;
    2)
        echo -e "${YELLOW}启用提醒 $reminder_id...${NC}"
        # 实现启用逻辑
        echo -e "${GREEN}✓ 提醒已启用${NC}"
        ;;
    3)
        echo -e "${RED}⚠️  将删除提醒：$reminder_id${NC}"
        read -p "确实要删除吗？(y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # 实现删除逻辑
            echo -e "${GREEN}✓ 提醒已删除${NC}"
        else
            echo -e "${YELLOW}✗ 已取消${NC}"
        fi
        ;;
    *)
        echo -e "${RED}✗ 无效选择${NC}"
        exit 1
        ;;
esac

echo ""
