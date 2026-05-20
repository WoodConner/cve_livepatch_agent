#!/bin/bash
# 监控 ISO 下载进度并自动启动虚拟机安装

OUTPUT_FILE="/tmp/claude-0/-home-wood/d6b819f7-c820-4e8f-9712-fe397a63fa5b/tasks/byysjc4jd.output"
ISO_FILE="/home/wood/cve_livepatch_agent/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"

echo "========================================="
echo "监控 Anolis OS ISO 下载进度"
echo "========================================="
echo ""

while true; do
    if [ -f "$OUTPUT_FILE" ]; then
        # 获取最新进度
        PROGRESS=$(tail -3 "$OUTPUT_FILE" | grep -oP '\d+%' | tail -1)

        if [ -n "$PROGRESS" ]; then
            echo -ne "\r下载进度: $PROGRESS"
        fi

        # 检查是否下载完成
        if grep -q "saved" "$OUTPUT_FILE" 2>/dev/null; then
            echo ""
            echo ""
            echo "✓ ISO 下载完成！"

            if [ -f "$ISO_FILE" ]; then
                SIZE=$(du -h "$ISO_FILE" | cut -f1)
                echo "✓ 文件大小: $SIZE"
                echo "✓ 文件路径: $ISO_FILE"
                echo ""
                echo "下一步: 安装 Anolis OS 到虚拟机"
                echo "运行: cd /home/wood/cve_livepatch_agent && ./scripts/install_anolis_vm.sh"
            fi
            break
        fi
    fi

    sleep 5
done

echo ""
echo "========================================="
