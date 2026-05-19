#!/bin/bash
# 测试环境脚本

set -e

echo "========================================="
echo "测试 CVE 热补丁生成环境"
echo "========================================="
echo ""

# 检查 Python
echo "检查 Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ ${PYTHON_VERSION}"
else
    echo "✗ 未安装 Python 3"
    exit 1
fi

# 检查 QEMU
echo ""
echo "检查 QEMU..."
if command -v qemu-system-x86_64 &> /dev/null; then
    QEMU_VERSION=$(qemu-system-x86_64 --version | head -n1)
    echo "✓ ${QEMU_VERSION}"
else
    echo "✗ 未安装 QEMU"
    exit 1
fi

# 检查 KVM
echo ""
echo "检查 KVM..."
if [ -e /dev/kvm ]; then
    echo "✓ KVM 可用"
else
    echo "⚠ KVM 不可用 (性能会受影响)"
fi

# 检查 Python 依赖
echo ""
echo "检查 Python 依赖..."
python3 -c "import openai" 2>/dev/null && echo "✓ openai" || echo "✗ openai (运行 pip install -r requirements.txt)"
python3 -c "import paramiko" 2>/dev/null && echo "✓ paramiko" || echo "✗ paramiko"
python3 -c "import yaml" 2>/dev/null && echo "✓ PyYAML" || echo "✗ PyYAML"
python3 -c "import requests" 2>/dev/null && echo "✓ requests" || echo "✗ requests"

# 检查目录结构
echo ""
echo "检查目录结构..."
DIRS=("agent" "tools" "configs" "data" "logs" "qemu" "scripts")
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✓ $dir/"
    else
        echo "✗ $dir/ (缺失)"
    fi
done

# 检查配置文件
echo ""
echo "检查配置文件..."
if [ -f "configs/agent_config.yaml" ]; then
    echo "✓ configs/agent_config.yaml"
else
    echo "✗ configs/agent_config.yaml (缺失)"
fi

# 检查环境变量
echo ""
echo "检查环境变量..."
if [ -n "${DASHSCOPE_API_KEY}" ]; then
    echo "✓ DASHSCOPE_API_KEY 已设置"
else
    echo "⚠ DASHSCOPE_API_KEY 未设置 (需要用于 LLM 调用)"
fi

echo ""
echo "========================================="
echo "环境检查完成"
echo "========================================="
echo ""
echo "如果所有检查都通过，可以开始使用智能体"
echo ""
