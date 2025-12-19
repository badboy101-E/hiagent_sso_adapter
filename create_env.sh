#!/bin/bash
# 创建 .env 环境变量文件脚本

echo "=========================================="
echo "创建环境变量配置文件"
echo "=========================================="

# 检查 .env 文件是否已存在
if [ -f ".env" ]; then
    echo "警告: .env 文件已存在"
    read -p "是否要覆盖现有文件? (y/N): " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "已取消操作"
        exit 0
    fi
fi

# 复制示例文件
cp env.example .env

echo ""
echo "✓ 已创建 .env 文件"
echo ""
echo "请编辑 .env 文件，确保以下配置正确："
echo "  1. TENANT_ID - 租户ID（从HiAgent环境获取）"
echo "  2. 数据库配置（已配置，如需修改请编辑）"
echo ""
echo "编辑命令："
echo "  vi .env"
echo "  或"
echo "  nano .env"
echo ""

