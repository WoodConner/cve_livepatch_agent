#!/bin/bash
# 监控 QEMU 编译进度

echo "========================================="
echo "QEMU 11.0.0 编译进度监控"
echo "========================================="
echo ""

BUILD_DIR="/home/wood/cve_livepatch_agent/qemu_build/qemu-11.0.0/build"

if [ ! -d "$BUILD_DIR" ]; then
    echo "错误: 构建目录不存在"
    exit 1
fi

echo "构建目录: $BUILD_DIR"
echo ""

# 检查编译进度
while true; do
    # 统计已编译的目标文件
    OBJ_COUNT=$(find "$BUILD_DIR" -name "*.o" 2>/dev/null | wc -l)

    # 检查是否完成
    if [ -f "$BUILD_DIR/qemu-system-x86_64" ]; then
        echo ""
        echo "✅ QEMU 编译完成！"
        echo ""
        echo "可执行文件: $BUILD_DIR/qemu-system-x86_64"
        echo ""
        echo "下一步: 运行 'sudo ninja -C build install' 安装 QEMU"
        break
    fi

    # 显示进度
    echo -ne "\r已编译目标文件: $OBJ_COUNT 个 | $(date '+%H:%M:%S')"

    sleep 5
done

echo ""
echo "========================================="
