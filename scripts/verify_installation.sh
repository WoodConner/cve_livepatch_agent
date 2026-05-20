#!/bin/bash
# 验证 CVE 热补丁智能体系统安装

set -e

echo "========================================="
echo "CVE 热补丁智能体系统 - 安装验证"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

ERRORS=0

echo "1. 检查 Python 环境"
echo "-------------------"
check_command python3 "Python 3 已安装" || ((ERRORS++))
python3 --version

# 检查 Python 包
echo ""
echo "2. 检查 Python 依赖"
echo "-------------------"
for pkg in openai paramiko requests yaml; do
    if python3 -c "import $pkg" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $pkg"
    else
        echo -e "${RED}✗${NC} $pkg"
        ((ERRORS++))
    fi
done

echo ""
echo "3. 检查 QEMU 安装"
echo "-------------------"
check_command /usr/local/qemu/bin/qemu-system-x86_64 "QEMU 系统模拟器" || ((ERRORS++))
check_command /usr/local/qemu/bin/qemu-img "QEMU 镜像工具" || ((ERRORS++))
/usr/local/qemu/bin/qemu-system-x86_64 --version | head -1

echo ""
echo "4. 检查 Anolis OS 内核包"
echo "-------------------"
check_file "data/anolis_packages/kernel-6.6.102-5.2.an23.x86_64.rpm" "内核 RPM 包" || ((ERRORS++))
check_file "data/anolis_packages/kernel-devel-6.6.102-5.2.an23.x86_64.rpm" "内核开发包" || ((ERRORS++))
check_file "data/anolis_packages/kernel-debuginfo-6.6.102-5.2.an23.x86_64.rpm" "内核调试信息包" || ((ERRORS++))
check_file "data/anolis_packages/kernel-6.6.102-5.2.an23.src.rpm" "内核源码包" || ((ERRORS++))

echo ""
echo "5. 检查项目结构"
echo "-------------------"
check_dir "agent" "智能体模块目录" || ((ERRORS++))
check_dir "tools" "工具模块目录" || ((ERRORS++))
check_dir "configs" "配置文件目录" || ((ERRORS++))
check_dir "scripts" "脚本目录" || ((ERRORS++))
check_file "agent/main.py" "主程序" || ((ERRORS++))
check_file "agent/qemu_manager.py" "QEMU 管理器" || ((ERRORS++))
check_file "agent/cve_query.py" "CVE 查询模块" || ((ERRORS++))
check_file "agent/patch_rewriter.py" "补丁改写模块" || ((ERRORS++))
check_file "tools/kpatch_wrapper.py" "kpatch 封装" || ((ERRORS++))
check_file "configs/agent_config.yaml" "配置文件" || ((ERRORS++))

echo ""
echo "6. 检查 Git 仓库"
echo "-------------------"
if [ -d ".git" ]; then
    echo -e "${GREEN}✓${NC} Git 仓库已初始化"
    REMOTE=$(git remote get-url origin 2>/dev/null || echo "未设置")
    echo "  远程仓库: $REMOTE"
    BRANCH=$(git branch --show-current)
    echo "  当前分支: $BRANCH"
else
    echo -e "${RED}✗${NC} Git 仓库未初始化"
    ((ERRORS++))
fi

echo ""
echo "7. 检查环境变量"
echo "-------------------"
if [ -n "$DASHSCOPE_API_KEY" ]; then
    echo -e "${GREEN}✓${NC} DASHSCOPE_API_KEY 已设置"
else
    echo -e "${YELLOW}⚠${NC} DASHSCOPE_API_KEY 未设置（需要时请设置）"
fi

echo ""
echo "========================================="
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！系统已就绪。${NC}"
    echo ""
    echo "下一步："
    echo "  1. 设置 API Key: export DASHSCOPE_API_KEY='your-key'"
    echo "  2. 创建虚拟机镜像: ./scripts/setup_qemu_vm.sh"
    echo "  3. 运行测试: python3 agent/main.py --cve CVE-2024-26581"
else
    echo -e "${RED}✗ 发现 $ERRORS 个问题，请修复后重试。${NC}"
    exit 1
fi
echo "========================================="
