#!/bin/bash
# 下载 Anolis OS 相关软件包

set -e

MIRROR_BASE="https://mirrors.openanolis.cn/anolis/23.4/os"
KERNEL_VERSION="6.6.102-5.2.an23"
DOWNLOAD_DIR="data/anolis_packages"

echo "========================================="
echo "下载 Anolis OS 内核相关软件包"
echo "========================================="
echo ""
echo "内核版本: ${KERNEL_VERSION}"
echo "下载目录: ${DOWNLOAD_DIR}"
echo ""

# 创建下载目录
mkdir -p "${DOWNLOAD_DIR}"

# 软件包列表
declare -A PACKAGES=(
    ["kernel-source"]="${MIRROR_BASE}/source/Packages/kernel-${KERNEL_VERSION}.src.rpm"
    ["kernel"]="${MIRROR_BASE}/x86_64/os/Packages/kernel-${KERNEL_VERSION}.x86_64.rpm"
    ["kernel-devel"]="${MIRROR_BASE}/x86_64/os/Packages/kernel-devel-${KERNEL_VERSION}.x86_64.rpm"
    ["kernel-debuginfo"]="${MIRROR_BASE}/x86_64/debug/Packages/kernel-debuginfo-${KERNEL_VERSION}.x86_64.rpm"
)

# 下载函数
download_package() {
    local name=$1
    local url=$2
    local filename=$(basename "${url}")
    local filepath="${DOWNLOAD_DIR}/${filename}"

    if [ -f "${filepath}" ]; then
        echo "✓ ${name} 已存在，跳过下载"
        return 0
    fi

    echo "→ 下载 ${name}..."
    if wget -q --show-progress -O "${filepath}" "${url}"; then
        echo "✓ ${name} 下载完成"
        return 0
    else
        echo "✗ ${name} 下载失败"
        return 1
    fi
}

# 下载所有软件包
echo "开始下载软件包..."
echo ""

for name in "${!PACKAGES[@]}"; do
    download_package "${name}" "${PACKAGES[$name]}"
    echo ""
done

echo "========================================="
echo "下载完成！"
echo "========================================="
echo ""
echo "软件包位置: ${DOWNLOAD_DIR}"
echo ""
echo "下一步："
echo "1. 运行 ./scripts/setup_qemu_vm.sh 创建虚拟机"
echo "2. 运行 ./scripts/extract_kernel_source.sh 解压内核源码"
echo ""
