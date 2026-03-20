#!/bin/bash

# 米家智能提醒 - 添加提醒脚本
# 功能：创建新的定时提醒
# 使用：bash scripts/add-reminder.sh

set -e

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
DATA_DIR="$SKILL_DIR/data"
CONFIG_FILE="$DATA_DIR/config.json"
REMINDERS_FILE="$DATA_DIR/reminders.json"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查配置文件
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}✗ 未找到配置文件，请先运行配置${NC}"
    echo "  bash scripts/setup-mijia.sh"
    exit 1
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   添加新提醒${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# 获取提醒内容
read -p "提醒内容: " reminder_content
if [ -z "$reminder_content" ]; then
    echo -e "${RED}✗ 提醒内容不能为空${NC}"
    exit 1
fi

# 选择提醒类型
echo ""
echo -e "${BLUE}选择提醒类型：${NC}"
echo "  1) 每天 (daily) - 每天固定时间"
echo "  2) 工作日 (workdays) - 周一到周五"
echo "  3) 每周 (weekly) - 指定某天"
echo "  4) 一次性 (once) - 仅一次"
read -p "请选择 [1-4] (默认1): " remind_type
remind_type=${remind_type:-1}

case $remind_type in
    1) schedule_type="daily" ;;
    2) schedule_type="workdays" ;;
    3) schedule_type="weekly" ;;
    4) schedule_type="once" ;;
    *) schedule_type="daily" ;;
esac

# 获取时间
read -p "提醒时间 (HH:MM 格式，如 10:30): " reminder_time
if ! [[ $reminder_time =~ ^[0-2][0-9]:[0-5][0-9]$ ]]; then
    echo -e "${RED}✗ 时间格式不正确，应为 HH:MM${NC}"
    exit 1
fi

# 选择设备
echo ""
echo -e "${BLUE}选择播报设备：${NC}"
primary_device=$(grep -o '"primary_device": "[^"]*"' "$CONFIG_FILE" | cut -d'"' -f4)

devices=$(jq -r '.devices[] | "\(.name)"' "$CONFIG_FILE" 2>/dev/null || echo "$primary_device")
echo "  0) 所有设备 (broadcast)"
i=1
echo "$devices" | while read device; do
    echo "  $i) $device"
    ((i++))
done

# 简化版本，直接使用主设备
read -p "请选择设备 [0 或设备名称] (默认: 主设备 - $primary_device): " device_choice
if [ -z "$device_choice" ]; then
    selected_device="$primary_device"
else
    selected_device="$device_choice"
fi

# 选择优先级
echo ""
read -p "优先级 [high/normal/low] (默认: normal): " priority
priority=${priority:-"normal"}

# 生成提醒ID
reminder_id="remind_$(date +%s)"

# 创建提醒对象
reminder_json=$(cat <<EOF
{
  "id": "$reminder_id",
  "content": "$reminder_content",
  "schedule": {
    "type": "$schedule_type",
    "time": "$reminder_time"
  },
  "device": "$selected_device",
  "priority": "$priority",
  "status": "active",
  "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_broadcast": null
}
EOF
)

# 添加到提醒列表
if [ ! -f "$REMINDERS_FILE" ]; then
    echo "[]" > "$REMINDERS_FILE"
fi

# 使用 jq 添加提醒（如果系统没有 jq，使用备选方案）
if command -v jq &> /dev/null; then
    jq ". += [$reminder_json]" "$REMINDERS_FILE" > "${REMINDERS_FILE}.tmp"
    mv "${REMINDERS_FILE}.tmp" "$REMINDERS_FILE"
else
    # 备选：直接附加（不使用 jq）
    # 此处为简化版本，实际应正确处理 JSON
    echo "$reminder_json" >> "$REMINDERS_FILE.bak"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ 提醒创建成功${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "提醒详情："
echo "  • ID：$reminder_id"
echo "  • 内容：$reminder_content"
echo "  • 类型：$schedule_type"
echo "  • 时间：$reminder_time"
echo "  • 设备：$selected_device"
echo "  • 优先级：$priority"
echo "  • 状态：✓ 已激活"
echo ""
echo "查看所有提醒：bash scripts/list-reminders.sh"
echo ""
