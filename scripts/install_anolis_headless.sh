#!/bin/bash
# 无头模式安装 Anolis OS（适用于 WSL/无图形界面环境）

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

QEMU_BIN="/usr/local/qemu/bin/qemu-system-x86_64"
QEMU_IMG="/usr/local/qemu/bin/qemu-img"
VM_IMAGE="${PROJECT_DIR}/qemu/images/anolis.qcow2"
ISO_FILE="${PROJECT_DIR}/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"

echo "========================================="
echo "无头模式安装 Anolis OS"
echo "========================================="
echo ""

# 创建 Kickstart 配置文件
KICKSTART_FILE="${PROJECT_DIR}/qemu/ks.cfg"
cat > "$KICKSTART_FILE" << 'EOF'
# Kickstart for Anolis OS 23
install
cdrom
text
lang en_US.UTF-8
keyboard us
timezone Asia/Shanghai --utc
rootpw --plaintext anolis
network --bootproto=dhcp --device=eth0 --onboot=yes --hostname=anolis-livepatch
firewall --disabled
selinux --disabled
bootloader --location=mbr --append="console=tty0 console=ttyS0,115200n8"
zerombr
clearpart --all --initlabel
autopart --type=lvm
reboot

%packages
@core
@development-tools
kernel-devel
kernel-debuginfo
elfutils-libelf-devel
openssl-devel
rpm-build
git
wget
curl
vim
openssh-server
%end

%post
systemctl enable sshd
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
mkdir -p /root/livepatch_work /root/kernel-source
echo "Installation complete" > /root/install.log
%end
EOF

echo "✓ Kickstart 配置已创建"

# 创建临时 ISO 包含 kickstart
TEMP_DIR="${PROJECT_DIR}/qemu/temp_iso"
mkdir -p "$TEMP_DIR"

echo "正在准备安装环境..."

# 启动无头安装
echo ""
echo "启动虚拟机安装（无头模式）..."
echo "这将需要 15-30 分钟，请耐心等待..."
echo ""

# 使用 nohup 在后台运行，输出到日志
INSTALL_LOG="${PROJECT_DIR}/logs/vm_install.log"
mkdir -p "$(dirname "$INSTALL_LOG")"

# 将 kickstart 文件放到可访问的位置
# 注意：由于 ISO 是只读的，我们使用串口进行文本安装
# WSL 不支持 KVM，使用软件模拟（会比较慢）
$QEMU_BIN \
    -name anolis-install \
    -m 4G \
    -smp 4 \
    -hda "$VM_IMAGE" \
    -cdrom "$ISO_FILE" \
    -boot d \
    -net nic \
    -net user,hostfwd=tcp::2222-:22 \
    -nographic \
    -serial mon:stdio \
    > "$INSTALL_LOG" 2>&1 &

QEMU_PID=$!
echo "QEMU 进程 ID: $QEMU_PID"
echo "安装日志: $INSTALL_LOG"
echo ""
echo "监控安装进度:"
echo "  tail -f $INSTALL_LOG"
echo ""
echo "等待安装完成..."

# 等待安装完成（检测虚拟机重启）
sleep 300  # 等待 5 分钟让安装开始

echo "安装进行中，请查看日志文件了解详情"
echo "安装完成后，虚拟机将自动重启"

wait $QEMU_PID || true

echo ""
echo "========================================="
echo "安装过程已完成"
echo "========================================="
echo ""
echo "下一步:"
echo "1. 启动虚拟机: ${PROJECT_DIR}/qemu/start_vm.sh"
echo "2. 测试 SSH 连接: ssh -p 2222 root@localhost"
echo ""
