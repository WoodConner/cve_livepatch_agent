#!/bin/bash
# Install Anolis OS using Kickstart

set -e

QEMU_BIN="/usr/local/qemu/bin/qemu-system-x86_64"
VM_IMAGE="/home/wood/cve_livepatch_agent/qemu/images/anolis.qcow2"
ISO_FILE="/home/wood/cve_livepatch_agent/data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso"
KERNEL="/home/wood/cve_livepatch_agent/qemu/vmlinuz"
INITRD="/home/wood/cve_livepatch_agent/qemu/initrd.img"
KS_FILE="/home/wood/cve_livepatch_agent/qemu/ks.cfg"

echo "Starting Anolis OS installation with Kickstart..."
echo "This will take 15-30 minutes"
echo ""

$QEMU_BIN \
    -name "anolis-kickstart" \
    -cpu qemu64,+ssse3,+sse4.1,+sse4.2 \
    -m 4G \
    -smp 4 \
    -hda "$VM_IMAGE" \
    -cdrom "$ISO_FILE" \
    -kernel "$KERNEL" \
    -initrd "$INITRD" \
    -append "inst.text inst.ks=http://10.0.2.2:8000/ks.cfg console=ttyS0,115200n8" \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device e1000,netdev=net0 \
    -nographic \
    2>&1 | tee /home/wood/cve_livepatch_agent/logs/kickstart_install.log
