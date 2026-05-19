#!/bin/bash
# 安装 QEMU 和相关依赖

echo "========================================="
echo "安装 QEMU 和相关依赖"
echo "========================================="
echo ""

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用 root 权限运行此脚本"
    echo "使用: sudo ./scripts/install_qemu.sh"
    exit 1
fi

echo "更新软件包列表..."
apt-get update

echo ""
echo "安装 QEMU 和相关工具..."
apt-get install -y \
    qemu-system-x86 \
    qemu-utils \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils

echo ""
echo "检查安装结果..."
if command -v qemu-system-x86_64 &> /dev/null; then
    QEMU_VERSION=$(qemu-system-x86_64 --version | head -n1)
    echo "✓ QEMU 安装成功: ${QEMU_VERSION}"
else
    echo "✗ QEMU 安装失败"
    exit 1
fi

echo ""
echo "检查 KVM 支持..."
if [ -e /dev/kvm ]; then
    echo "✓ KVM 可用"
else
    echo "⚠ KVM 不可用 (WSL 环境下正常，性能会受影响)"
fi

echo ""
echo "========================================="
echo "安装完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 运行 ./scripts/setup_qemu_vm.sh 创建虚拟机"
echo "2. 运行 ./scripts/test_environment.sh 测试环境"
echo ""
