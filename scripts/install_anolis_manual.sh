#!/bin/bash
# 手动安装 Anolis OS - 通过串口交互

set -e

QEMU_BIN="/usr/local/qemu/bin/qemu-system-x86_64"
VM_IMAGE="/home/wood/cve_livepatch_agent/qemu/images/anolis.qcow2"
ISO_FILE="/home/wood/cve_livepatch_agent/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"

if [ ! -f "$QEMU_BIN" ]; then
    echo "错误: QEMU 未找到"
    exit 1
fi

if [ ! -f "$ISO_FILE" ]; then
    echo "错误: ISO 文件未找到"
    exit 1
fi

echo "启动 Anolis OS 安装程序..."
echo "提示: 在安装界面中："
echo "  1. 选择 'Install Anolis OS 23'"
echo "  2. 等待进入文本安装界面"
echo "  3. 按照提示完成安装"
echo ""
echo "使用 Ctrl+A 然后按 X 退出 QEMU"
echo ""

# 启动安装，使用串口输出
$QEMU_BIN \
    -name "anolis-install" \
    -m 4G \
    -smp 4 \
    -hda "$VM_IMAGE" \
    -cdrom "$ISO_FILE" \
    -boot d \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device e1000,netdev=net0 \
    -nographic \
    -serial mon:stdio
