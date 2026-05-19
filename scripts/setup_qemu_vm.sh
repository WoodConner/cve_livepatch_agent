#!/bin/bash
# 设置 QEMU 虚拟机环境

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"
QEMU_DIR="${PROJECT_DIR}/qemu"
IMAGE_DIR="${QEMU_DIR}/images"
SSH_KEY_DIR="${QEMU_DIR}/ssh_keys"

echo "========================================="
echo "设置 QEMU 虚拟机环境"
echo "========================================="
echo ""

# 检查 QEMU 是否安装
if ! command -v qemu-system-x86_64 &> /dev/null; then
    echo "错误: 未安装 QEMU"
    echo "请运行: sudo apt-get install qemu-system-x86 qemu-utils"
    exit 1
fi

echo "✓ QEMU 已安装"

# 创建目录
mkdir -p "${IMAGE_DIR}"
mkdir -p "${SSH_KEY_DIR}"
mkdir -p "${QEMU_DIR}/scripts"

# 生成 SSH 密钥
if [ ! -f "${SSH_KEY_DIR}/id_rsa" ]; then
    echo ""
    echo "生成 SSH 密钥..."
    ssh-keygen -t rsa -b 4096 -f "${SSH_KEY_DIR}/id_rsa" -N "" -C "livepatch-agent"
    echo "✓ SSH 密钥已生成"
else
    echo "✓ SSH 密钥已存在"
fi

# 检查 Anolis OS 镜像
ANOLIS_ISO="${PROJECT_DIR}/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"
VM_IMAGE="${IMAGE_DIR}/anolis.qcow2"

if [ ! -f "${VM_IMAGE}" ]; then
    echo ""
    echo "创建虚拟机磁盘镜像..."
    qemu-img create -f qcow2 "${VM_IMAGE}" 40G
    echo "✓ 虚拟机磁盘镜像已创建: ${VM_IMAGE}"

    echo ""
    echo "注意: 需要手动安装 Anolis OS"
    echo ""
    echo "安装步骤："
    echo "1. 下载 Anolis OS 23.4 ISO 镜像"
    echo "   wget https://mirrors.openanolis.cn/anolis/23.4/isos/GA/x86_64/AnolisOS-23.4-x86_64-dvd.iso"
    echo ""
    echo "2. 启动虚拟机进行安装："
    echo "   qemu-system-x86_64 \\"
    echo "     -name anolis-livepatch \\"
    echo "     -m 4G \\"
    echo "     -smp 4 \\"
    echo "     -hda ${VM_IMAGE} \\"
    echo "     -cdrom ${ANOLIS_ISO} \\"
    echo "     -boot d \\"
    echo "     -enable-kvm \\"
    echo "     -vga std"
    echo ""
    echo "3. 安装完成后，配置 SSH 和网络"
    echo ""
else
    echo "✓ 虚拟机镜像已存在: ${VM_IMAGE}"
fi

# 创建虚拟机内初始化脚本
cat > "${QEMU_DIR}/scripts/vm_init.sh" << 'EOF'
#!/bin/bash
# 虚拟机内初始化脚本

set -e

echo "========================================="
echo "初始化 Anolis OS 虚拟机"
echo "========================================="

# 更新系统
echo "更新系统..."
yum update -y

# 安装基础工具
echo "安装基础工具..."
yum install -y \
    gcc make \
    elfutils-libelf-devel \
    openssl-devel \
    rpm-build rpmdevtools \
    git wget curl \
    vim net-tools \
    ccache

# 安装 kpatch
echo "安装 kpatch..."
cd /root
if [ ! -d "kpatch" ]; then
    git clone https://github.com/dynup/kpatch.git
fi
cd kpatch
make && make install

# 验证 kpatch 安装
if kpatch-build --version; then
    echo "✓ kpatch 安装成功"
else
    echo "✗ kpatch 安装失败"
    exit 1
fi

# 创建工作目录
mkdir -p /root/livepatch_work
mkdir -p /root/kernel-source

echo ""
echo "========================================="
echo "虚拟机初始化完成！"
echo "========================================="
EOF

chmod +x "${QEMU_DIR}/scripts/vm_init.sh"

# 创建快速启动脚本
cat > "${QEMU_DIR}/start_vm.sh" << EOF
#!/bin/bash
# 快速启动虚拟机

qemu-system-x86_64 \\
    -name anolis-livepatch \\
    -m 4G \\
    -smp 4 \\
    -hda ${VM_IMAGE} \\
    -net nic \\
    -net user,hostfwd=tcp::2222-:22 \\
    -enable-kvm \\
    -nographic \\
    -serial mon:stdio
EOF

chmod +x "${QEMU_DIR}/start_vm.sh"

echo ""
echo "========================================="
echo "QEMU 环境设置完成！"
echo "========================================="
echo ""
echo "下一步："
echo "1. 下载并安装 Anolis OS (如果尚未安装)"
echo "2. 启动虚拟机: ${QEMU_DIR}/start_vm.sh"
echo "3. 在虚拟机内运行初始化脚本"
echo "4. 配置 SSH 密钥认证"
echo ""
