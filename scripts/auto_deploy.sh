#!/bin/bash
# 完整的自动化部署脚本 - 从 ISO 下载完成到测试运行

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "${SCRIPT_DIR}")"

echo "========================================="
echo "CVE 热补丁智能体 - 完整自动化部署"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 步骤 1: 等待 ISO 下载完成
log_info "步骤 1: 等待 ISO 下载完成..."
OUTPUT_FILE="/tmp/claude-0/-home-wood/d6b819f7-c820-4e8f-9712-fe397a63fa5b/tasks/byysjc4jd.output"
ISO_FILE="${PROJECT_DIR}/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"

while true; do
    if [ -f "$OUTPUT_FILE" ]; then
        PROGRESS=$(tail -3 "$OUTPUT_FILE" | grep -oP '\d+%' | tail -1)
        if [ -n "$PROGRESS" ]; then
            echo -ne "\r  下载进度: $PROGRESS"
        fi

        if grep -q "saved" "$OUTPUT_FILE" 2>/dev/null || [ -f "$ISO_FILE" ]; then
            echo ""
            log_info "ISO 下载完成！"
            break
        fi
    fi
    sleep 10
done

# 验证 ISO 文件
if [ ! -f "$ISO_FILE" ]; then
    log_error "ISO 文件不存在: $ISO_FILE"
    exit 1
fi

SIZE=$(du -h "$ISO_FILE" | cut -f1)
log_info "ISO 文件大小: $SIZE"

# 步骤 2: 安装 Anolis OS（使用预配置的方式）
log_info "步骤 2: 准备虚拟机安装..."

VM_IMAGE="${PROJECT_DIR}/qemu/images/anolis.qcow2"
QEMU_BIN="/usr/local/qemu/bin/qemu-system-x86_64"

# 由于 Kickstart 自动安装需要图形界面或长时间等待，
# 我们采用手动安装后的快照方式，或者使用预构建镜像

log_warn "注意: Anolis OS 需要手动安装或使用预构建镜像"
log_info "为了快速测试，我们将创建一个最小化的测试环境"

# 步骤 3: 创建测试环境脚本
log_info "步骤 3: 创建虚拟机初始化脚本..."

cat > "${PROJECT_DIR}/qemu/scripts/setup_vm_environment.sh" << 'EOFSCRIPT'
#!/bin/bash
# 在虚拟机内运行的初始化脚本

set -e

echo "========================================="
echo "初始化 Anolis OS 虚拟机环境"
echo "========================================="

# 更新系统
echo "更新系统..."
yum update -y

# 安装开发工具
echo "安装开发工具..."
yum groupinstall -y "Development Tools"

# 安装必要的包
echo "安装必要的包..."
yum install -y \
    gcc make \
    elfutils-libelf-devel \
    openssl-devel \
    rpm-build rpmdevtools \
    git wget curl \
    vim net-tools \
    ccache \
    kernel-devel \
    kernel-debuginfo

# 克隆并安装 kpatch
echo "安装 kpatch..."
cd /root
if [ ! -d "kpatch" ]; then
    git clone https://github.com/dynup/kpatch.git
fi
cd kpatch
make clean
make
make install

# 验证 kpatch
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
echo "虚拟机环境初始化完成！"
echo "========================================="
EOFSCRIPT

chmod +x "${PROJECT_DIR}/qemu/scripts/setup_vm_environment.sh"
log_info "虚拟机初始化脚本已创建"

# 步骤 4: 创建快速启动指南
cat > "${PROJECT_DIR}/QUICKSTART.md" << 'EOF'
# 快速启动指南

## 当前状态
- ✅ QEMU 已安装
- ✅ ISO 已下载
- ✅ 虚拟机磁盘已创建
- ⏳ 需要安装 Anolis OS

## 手动安装步骤

### 1. 启动虚拟机安装 Anolis OS

```bash
/usr/local/qemu/bin/qemu-system-x86_64 \
    -name anolis-livepatch \
    -m 4G \
    -smp 4 \
    -hda qemu/images/anolis.qcow2 \
    -cdrom data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso \
    -boot d \
    -enable-kvm \
    -net nic \
    -net user,hostfwd=tcp::2222-:22 \
    -vnc :0
```

在另一个终端使用 VNC 查看安装界面：
```bash
vncviewer localhost:5900
```

安装时设置：
- Root 密码: anolis
- 主机名: anolis-livepatch
- 网络: 启用 DHCP
- 软件选择: Minimal Install + Development Tools

### 2. 安装完成后，启动虚拟机

```bash
./qemu/start_vm.sh
```

### 3. SSH 连接到虚拟机

```bash
ssh -p 2222 root@localhost
# 密码: anolis
```

### 4. 在虚拟机内运行初始化脚本

将脚本传输到虚拟机：
```bash
scp -P 2222 qemu/scripts/setup_vm_environment.sh root@localhost:/root/
```

在虚拟机内执行：
```bash
ssh -p 2222 root@localhost
chmod +x /root/setup_vm_environment.sh
/root/setup_vm_environment.sh
```

### 5. 传输内核包到虚拟机

```bash
scp -P 2222 data/anolis_packages/kernel-*.rpm root@localhost:/root/
```

在虚拟机内安装：
```bash
ssh -p 2222 root@localhost
cd /root
rpm -ivh kernel-6.6.102-5.2.an23.x86_64.rpm
rpm -ivh kernel-devel-6.6.102-5.2.an23.x86_64.rpm
rpm -ivh kernel-debuginfo-6.6.102-5.2.an23.x86_64.rpm
rpm -ivh kernel-6.6.102-5.2.an23.src.rpm
```

### 6. 运行测试

在主机上：
```bash
# 设置环境变量（如果还没设置）
export ANTHROPIC_BASE_URL="https://ccvibe.vip"
export ANTHROPIC_AUTH_TOKEN="sk-d66ce975670970901f0b67d827b87ec41275d784b2c3822ccf9a0dec150940a4"

# 运行测试
python3 agent/main.py --cve CVE-2024-26581
```

## 自动化选项（推荐用于生产环境）

如果你有预构建的 Anolis OS 镜像，可以直接替换 `qemu/images/anolis.qcow2`，
然后从步骤 2 开始。
EOF

log_info "快速启动指南已创建: ${PROJECT_DIR}/QUICKSTART.md"

echo ""
echo "========================================="
log_info "准备工作完成！"
echo "========================================="
echo ""
log_warn "由于 Anolis OS 需要图形界面安装，请按照以下步骤操作："
echo ""
echo "1. 查看快速启动指南:"
echo "   cat ${PROJECT_DIR}/QUICKSTART.md"
echo ""
echo "2. 或者使用自动化安装脚本（需要 VNC）:"
echo "   ${SCRIPT_DIR}/install_anolis_vm.sh"
echo ""
echo "3. 如果你有预构建的 Anolis OS qcow2 镜像，可以直接替换:"
echo "   cp your-anolis.qcow2 ${VM_IMAGE}"
echo ""
