# 内核 CVE 热补丁自动生成智能体

## 项目概述

本项目实现了一个基于 QEMU 的自动化系统，用于将上游 CVE 修复补丁转换为可加载的内核热补丁（livepatch）。系统使用大语言模型智能改写补丁以满足 kpatch 工具链的约束条件。

## 核心特性

- ✅ **真实 QEMU 环境**：基于 Anolis OS 23.4 的完整虚拟化环境
- ✅ **自动化补丁处理**：从 CVE 查询到热补丁生成的全流程自动化
- ✅ **智能补丁改写**：使用 LLM 理解修复意图并改写补丁以满足 kpatch 约束
- ✅ **多轮迭代优化**：基于构建错误自动驱动补丁改写（最多 5 轮）
- ✅ **完整验证流程**：自动构建、加载、卸载和功能验证
- ✅ **结构化报告**：详细的 JSON 报告和可追溯的构建日志

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     CVE Livepatch Agent                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐      ┌──────────────────┐              │
│  │  CVE Query     │─────▶│  Patch Download  │              │
│  │  Module        │      │  Module          │              │
│  └────────────────┘      └──────────────────┘              │
│           │                       │                          │
│           ▼                       ▼                          │
│  ┌─────────────────────────────────────────┐               │
│  │     Patch Rewriter (LLM-powered)        │               │
│  │  - 语义理解                              │               │
│  │  - kpatch 约束分析                       │               │
│  │  - 智能改写策略                          │               │
│  └─────────────────────────────────────────┘               │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────┐               │
│  │      QEMU Build Environment             │               │
│  │  - Anolis OS 23.4 虚拟机                │               │
│  │  - kernel-6.6.102-5.2.an23              │               │
│  │  - kpatch 工具链                        │               │
│  └─────────────────────────────────────────┘               │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────────────────────────────┐               │
│  │      Verification Module                │               │
│  │  - 热补丁加载测试                        │               │
│  │  - 功能验证                              │               │
│  │  - 结果归因分类                          │               │
│  └─────────────────────────────────────────┘               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd /home/wood/cve_livepatch_agent

# 安装系统依赖
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils python3-pip

# 安装 Python 依赖
pip3 install -r requirements.txt

# 设置环境变量（百炼平台 API Key）
export DASHSCOPE_API_KEY="your-api-key-here"
```

### 2. 下载 Anolis OS 软件包

```bash
# 下载内核相关软件包
./scripts/download_anolis_packages.sh
```

### 3. 创建 QEMU 虚拟机

```bash
# 设置虚拟机环境
./scripts/setup_qemu_vm.sh

# 下载 Anolis OS ISO 镜像
wget https://mirrors.openanolis.cn/anolis/23.4/isos/GA/x86_64/AnolisOS-23.4-x86_64-dvd.iso \
  -O data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso

# 启动虚拟机进行安装（图形界面）
qemu-system-x86_64 \
  -name anolis-livepatch \
  -m 4G \
  -smp 4 \
  -hda qemu/images/anolis.qcow2 \
  -cdrom data/anolis_packages/AnolisOS-23.4-x86_64-dvd.iso \
  -boot d \
  -enable-kvm \
  -vga std

# 安装完成后，启动虚拟机并初始化
./qemu/start_vm.sh

# 在虚拟机内运行（通过 SSH 或控制台）
bash /path/to/vm_init.sh
```

### 4. 测试环境

```bash
# 测试环境是否正确配置
./scripts/test_environment.sh
```

### 5. 运行智能体

```bash
# 处理单个 CVE
python3 agent/main.py --config configs/agent_config.yaml --cve CVE-2024-26581

# 批量处理 CVE 列表
python3 agent/main.py --config configs/agent_config.yaml --cve-list data/cve_list.txt

# 调试模式
python3 agent/main.py --config configs/agent_config.yaml --cve CVE-2024-26581 --log-level DEBUG
```

## 目录结构

```
cve_livepatch_agent/
├── agent/                      # 智能体核心代码
│   ├── main.py                # 主入口程序
│   ├── cve_query.py           # CVE 查询模块
│   ├── patch_rewriter.py      # 补丁改写模块（LLM）
│   └── qemu_manager.py        # QEMU 虚拟机管理
├── tools/                      # 工具模块
│   └── kpatch_wrapper.py      # kpatch 工具封装
├── qemu/                       # QEMU 相关文件
│   ├── images/                # 虚拟机镜像
│   ├── scripts/               # 虚拟机内脚本
│   │   └── vm_init.sh        # 虚拟机初始化脚本
│   ├── ssh_keys/              # SSH 密钥
│   └── start_vm.sh            # 快速启动脚本
├── configs/                    # 配置文件
│   └── agent_config.yaml      # 智能体配置
├── data/                       # 数据目录
│   ├── cve_cache/             # CVE 信息缓存
│   ├── cve_list.txt           # CVE 列表
│   ├── anolis_packages/       # Anolis OS 软件包
│   └── linux/                 # Linux 内核仓库（可选）
├── logs/                       # 日志目录
│   ├── agent.log              # 运行日志
│   └── reports/               # 结构化报告
├── scripts/                    # 辅助脚本
│   ├── download_anolis_packages.sh  # 下载软件包
│   ├── setup_qemu_vm.sh            # 设置虚拟机
│   └── test_environment.sh         # 测试环境
├── requirements.txt            # Python 依赖
└── README.md                   # 本文档
```

## 工作流程

### 完整流程图

```
开始
  │
  ▼
输入 CVE 编号
  │
  ▼
┌─────────────────┐
│ 1. 查询 CVE 信息 │
│  - NVD 数据库    │
│  - Linux 邮件列表│
└─────────────────┘
  │
  ▼
┌─────────────────┐
│ 2. 获取上游补丁  │
│  - 定位修复提交  │
│  - 下载 patch    │
└─────────────────┘
  │
  ▼
┌─────────────────────────────┐
│ 3. 多轮迭代构建（最多5轮）    │
│                              │
│  ┌─────────────────────┐   │
│  │ 3.1 上传补丁到虚拟机 │   │
│  └─────────────────────┘   │
│           │                  │
│           ▼                  │
│  ┌─────────────────────┐   │
│  │ 3.2 kpatch-build    │   │
│  └─────────────────────┘   │
│           │                  │
│           ▼                  │
│      构建成功？              │
│      ┌───┴───┐              │
│     是│      │否             │
│      │      ▼               │
│      │  ┌─────────────┐    │
│      │  │ 3.3 错误分析 │    │
│      │  └─────────────┘    │
│      │      │               │
│      │      ▼               │
│      │  ┌─────────────┐    │
│      │  │ 3.4 LLM改写  │    │
│      │  └─────────────┘    │
│      │      │               │
│      │      └──────┐        │
│      │             │        │
│      │      达到最大轮次？   │
│      │      ┌───┴───┐      │
│      │     否│      │是     │
│      │      └──────▶失败    │
│      │                      │
└──────┼──────────────────────┘
       │
       ▼
┌─────────────────┐
│ 4. 验证热补丁    │
│  - 加载测试      │
│  - 卸载测试      │
└─────────────────┘
  │
  ▼
┌─────────────────┐
│ 5. 生成报告      │
│  - JSON 结果     │
│  - 构建日志      │
└─────────────────┘
  │
  ▼
结束
```

## kpatch 约束处理策略

系统能够智能处理以下 kpatch 限制：

| 约束类型 | 问题描述 | 改写策略 |
|---------|---------|---------|
| **初始化函数** | 不能修改 `__init` 函数 | 将修改移至运行时函数 |
| **静态数据** | 不能修改静态变量 | 改为动态分配或函数参数 |
| **函数内联** | 内联函数无法 hook | 添加 `noinline` 属性 |
| **缺少 fentry** | 小函数没有 hook 点 | 修改调用者或使用 kprobe |
| **ABI 变化** | 结构体大小改变 | 使用包装函数保持兼容 |
| **Section 变化** | 静态局部变量修改 | 使用动态分配 |

## 配置说明

### agent_config.yaml

```yaml
# CVE 查询配置
cve_query:
  cache_dir: data/cve_cache
  linux_repo_path: data/linux
  nvd_api_key: ""  # 可选

# LLM 配置（百炼平台）
patch_rewriter:
  llm:
    api_key: ${DASHSCOPE_API_KEY}
    api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
    model: qwen-max
    temperature: 0.7
    max_tokens: 4096

# QEMU 配置
qemu:
  vm_name: anolis-livepatch
  image_path: qemu/images/anolis.qcow2
  memory: 4G
  cpus: 4
  ssh_port: 2222

# 构建配置
max_retry_rounds: 5
kernel_version: 6.6.102-5.2.an23
```

## 输出结果

### JSON 报告格式

```json
{
  "cve_id": "CVE-2024-26581",
  "start_time": "2026-05-19T10:00:00",
  "end_time": "2026-05-19T10:15:00",
  "success": true,
  "cve_info": {
    "description": "...",
    "severity": "HIGH"
  },
  "attempts": [
    {
      "attempt": 1,
      "build_success": false,
      "error_analysis": {
        "error_category": "init_function",
        "severity": "high"
      }
    },
    {
      "attempt": 2,
      "build_success": true,
      "module_path": "/root/livepatch_work/livepatch-CVE-2024-26581-2.ko"
    }
  ],
  "verification": {
    "load_success": true,
    "unload_success": true
  }
}
```

## 性能指标

根据赛题要求，系统目标：

- ✅ **热补丁生成成功率**: ≥60%
- ✅ **语义一致性**: 改写补丁保持与上游修复意图一致
- ✅ **效率指标**: 平均每个补丁尝试轮次 ≤5 次

## 故障排除

### QEMU 启动失败

```bash
# 检查 KVM 支持
lsmod | grep kvm

# 如果没有 KVM，移除 -enable-kvm 参数
```

### SSH 连接失败

```bash
# 检查虚拟机网络配置
# 确保 SSH 服务已启动
systemctl status sshd

# 检查端口转发
netstat -tlnp | grep 2222
```

### kpatch-build 失败

```bash
# 在虚拟机内检查内核源码
ls -la /root/kernel-source

# 检查 kpatch 安装
kpatch-build --version

# 查看详细构建日志
```

### LLM 调用失败

```bash
# 检查 API Key
echo $DASHSCOPE_API_KEY

# 测试 API 连接
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-max","messages":[{"role":"user","content":"test"}]}'
```

## 参考资料

- [kpatch 官方文档](https://github.com/dynup/kpatch)
- [kpatch 补丁作者指南](https://github.com/dynup/kpatch/blob/master/doc/patch-author-guide.md)
- [Linux livepatch 文档](https://docs.kernel.org/livepatch/livepatch.html)
- [Anolis OS 镜像仓库](https://mirrors.openanolis.cn/)
- [百炼平台文档](https://help.aliyun.com/zh/model-studio/)
- [NVD CVE 数据库](https://nvd.nist.gov/)

## 开发团队

本项目为 2026 年全国大学生计算机系统能力大赛操作系统设计赛参赛作品。

## 许可证

MIT License

## 更新日志

### v1.0.0 (2026-05-19)
- ✅ 完成基础架构设计
- ✅ 实现 QEMU 虚拟机管理模块
- ✅ 实现 CVE 查询和补丁获取系统
- ✅ 实现基于 LLM 的补丁改写智能体
- ✅ 实现 kpatch 工具链集成
- ✅ 实现多轮迭代构建和验证流程
- ✅ 完成配置文件和辅助脚本
