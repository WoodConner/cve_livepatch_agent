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
