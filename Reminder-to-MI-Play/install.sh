#!/bin/bash

# 米家智能提醒 Skill - 自动安装脚本

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}米家智能提醒 Skill 安装程序${NC}"
echo ""

# 检查 .workbuddy 目录
SKILLS_DIR="$HOME/.workbuddy/skills"
if [ ! -d "$SKILLS_DIR" ]; then
    echo -e "${BLUE}创建 .workbuddy/skills 目录...${NC}"
    mkdir -p "$SKILLS_DIR"
fi

# 复制 Skill
DEST_DIR="$SKILLS_DIR/mijia-smart-reminder"
if [ -d "$DEST_DIR" ]; then
    echo -e "检测到已存在的安装，是否要覆盖？(y/N): "
    read -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}保持现有安装${NC}"
        exit 0
    fi
    rm -rf "$DEST_DIR"
fi

echo -e "${BLUE}复制文件到 $DEST_DIR...${NC}"
cp -r "$SCRIPT_DIR" "$DEST_DIR"

echo -e "${GREEN}✓ 安装成功！${NC}"
echo ""
echo -e "${BLUE}下一步：${NC}"
echo "1. 返回 WorkBuddy"
echo "2. 在聊天框中说：'配置米家账号'"
echo "3. 或手动运行："
echo "   bash ~/.workbuddy/skills/mijia-smart-reminder/scripts/setup-mijia.sh"
echo ""
