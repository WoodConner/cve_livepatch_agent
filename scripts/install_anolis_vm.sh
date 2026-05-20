#!/bin/bash
# 自动化安装 Anolis OS 到 QEMU 虚拟机

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

QEMU_BIN="/usr/local/qemu/bin/qemu-system-x86_64"
VM_IMAGE="${PROJECT_DIR}/qemu/images/anolis.qcow2"
ISO_FILE="${PROJECT_DIR}/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"

echo "========================================="
echo "自动化安装 Anolis OS 到 QEMU 虚拟机"
echo "========================================="
echo ""

# 检查文件
if [ ! -f "$QEMU_BIN" ]; then
    echo "❌ 错误: QEMU 未安装"
    exit 1
fi

if [ ! -f "$VM_IMAGE" ]; then
    echo "❌ 错误: 虚拟机磁盘镜像不存在"
    echo "请先运行: ./scripts/setup_qemu_vm.sh"
    exit 1
fi

if [ ! -f "$ISO_FILE" ]; then
    echo "❌ 错误: ISO 镜像不存在"
    echo "ISO 路径: $ISO_FILE"
    exit 1
fi

echo "✓ QEMU: $QEMU_BIN"
echo "✓ 虚拟机镜像: $VM_IMAGE"
echo "✓ ISO 镜像: $ISO_FILE"
echo ""

# 创建 kickstart 自动安装配置
KICKSTART_FILE="${PROJECT_DIR}/qemu/anolis-ks.cfg"
cat > "$KICKSTART_FILE" << 'EOF'
# Anolis OS Kickstart 自动安装配置

# 系统语言
lang en_US.UTF-8

# 键盘布局
keyboard us

# 时区
timezone Asia/Shanghai --utc

# Root 密码
rootpw --plaintext anolis

# 网络配置
network --bootproto=dhcp --device=eth0 --onboot=yes --hostname=anolis-livepatch

# 防火墙
firewall --disabled

# SELinux
selinux --disabled

# 安装方式
install
cdrom

# 清除所有分区
clearpart --all --initlabel

# 自动分区
autopart --type=lvm

# 引导加载器
bootloader --location=mbr

# 重启
reboot

# 软件包选择
%packages
@core
@development
gcc
make
git
wget
curl
vim
openssh-server
kernel-devel
kernel-debuginfo
elfutils-libelf-devel
openssl-devel
rpm-build
rpmdevtools
ccache
%end

# 安装后脚本
%post
# 启用 SSH
systemctl enable sshd
systemctl start sshd

# 允许 root SSH 登录
sed -i 's/#PermitRootLogin yes/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# 创建工作目录
mkdir -p /root/livepatch_work
mkdir -p /root/kernel-source

echo "Anolis OS 安装完成！" > /root/install_complete.txt
%end
EOF

echo "✓ Kickstart 配置已创建: $KICKSTART_FILE"
echo ""

echo "启动虚拟机进行自动安装..."
echo "注意: 这将需要 10-20 分钟"
echo ""
echo "安装过程中可以通过 VNC 查看进度"
echo "VNC 端口: 5900"
echo ""

# 启动虚拟机进行安装
$QEMU_BIN \
    -name anolis-livepatch-install \
    -m 4G \
    -smp 4 \
    -hda "$VM_IMAGE" \
    -cdrom "$ISO_FILE" \
    -boot d \
    -enable-kvm \
    -net nic \
    -net user,hostfwd=tcp::2222-:22 \
    -vnc :0 \
    -nographic

echo ""
echo "========================================="
echo "虚拟机安装完成！"
echo "========================================="
echo ""
echo "下一步:"
echo "1. 启动虚拟机: ${PROJECT_DIR}/qemu/start_vm.sh"
echo "2. SSH 连接: ssh -p 2222 root@localhost (密码: anolis)"
echo "3. 安装 kpatch"
echo ""
