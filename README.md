# 内核 CVE 热补丁自动生成智能体

## 项目概述

本项目实现了一个基于 QEMU 的自动化系统，用于将上游 CVE 修复补丁转换为可加载的内核热补丁（livepatch）。系统使用大语言模型智能改写补丁以满足 kpatch 工具链的约束条件。

## 核心特性

- **真实 QEMU 环境**：基于 Anolis OS 23.4 的完整虚拟化环境
- **自动化补丁处理**：从 CVE 查询到热补丁生成的全流程自动化
- **智能补丁改写**：使用 LLM 理解修复意图并改写补丁以满足 kpatch 约束
- **多轮迭代优化**：基于构建错误自动驱动补丁改写
- **完整验证流程**：自动构建、加载、卸载和功能验证
- **结构化报告**：详细的 JSON 报告和可追溯的构建日志

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     CVE Livepatch Agent                      │
├─────────────────────────────────────────────────────────────┤
│  1. CVE Query Module                                         │
│     - NVD/Linux CVE 数据库查询                               │
│     - 上游补丁定位和下载                                      │
│                                                              │
│  2. Patch Rewriting Agent (LLM-powered)                     │
│     - 补丁语义理解                                           │
│     - kpatch 约束分析                                        │
│     - 智能改写策略生成                                        │
│                                                              │
│  3. QEMU Build Environment                                   │
│     - Anolis OS 23.4 虚拟机                                  │
│     - kernel-6.6.102-5.2.an23 源码树                         │
│     - kpatch 工具链                                          │
│                                                              │
│  4. Verification Module                                      │
│     - 热补丁加载测试                                          │
│     - 功能回归验证                                            │
│     - 结果归因分类                                            │
└─────────────────────────────────────────────────────────────┘
```

## 技术栈

- **虚拟化**: QEMU/KVM
- **目标系统**: Anolis OS 23.4 (kernel 6.6.102-5.2.an23)
- **热补丁工具**: kpatch
- **LLM**: Qwen 系列模型（通过百炼平台）
- **编程语言**: Python 3.10+
- **通信协议**: MCP (Model Context Protocol)

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
sudo apt-get update
sudo apt-get install -y qemu-system-x86 qemu-utils python3-pip

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 下载 Anolis OS 镜像和内核包

```bash
cd /home/wood/cve_livepatch_agent
./scripts/download_anolis_packages.sh
```

### 3. 创建 QEMU 虚拟机

```bash
./scripts/setup_qemu_vm.sh
```

### 4. 运行智能体

```bash
# 处理单个 CVE
python agent/main.py --cve CVE-2024-XXXXX

# 批量处理 CVE 列表
python agent/main.py --cve-list data/cve_list.txt

# 使用配置文件
python agent/main.py --config configs/agent_config.yaml
```

## 目录结构

```
cve_livepatch_agent/
├── agent/                      # 智能体核心代码
│   ├── main.py                # 主入口
│   ├── cve_query.py           # CVE 查询模块
│   ├── patch_rewriter.py      # 补丁改写模块
│   ├── qemu_manager.py        # QEMU 虚拟机管理
│   └── verification.py        # 验证模块
├── qemu/                       # QEMU 相关文件
│   ├── images/                # 虚拟机镜像
│   ├── scripts/               # 虚拟机内脚本
│   └── ssh_keys/              # SSH 密钥
├── tools/                      # 工具脚本
│   ├── kpatch_wrapper.py      # kpatch 工具封装
│   └── error_analyzer.py      # 错误分析工具
├── configs/                    # 配置文件
│   ├── agent_config.yaml      # 智能体配置
│   ├── qemu_config.yaml       # QEMU 配置
│   └── llm_config.yaml        # LLM 配置
├── data/                       # 数据目录
│   ├── cve_list.txt           # CVE 列表
│   ├── patches/               # 下载的补丁
│   └── kernel_source/         # 内核源码
├── logs/                       # 日志目录
│   ├── build_logs/            # 构建日志
│   └── reports/               # 结构化报告
└── scripts/                    # 辅助脚本
    ├── download_anolis_packages.sh
    ├── setup_qemu_vm.sh
    └── test_environment.sh
```

## kpatch 约束处理策略

系统能够处理以下常见的 kpatch 限制：

1. **初始化函数修改**：将修改移至运行时函数
2. **静态数据修改**：转换为动态分配或函数内局部变量
3. **函数内联问题**：添加 `noinline` 属性或重构代码
4. **缺少 fentry 调用**：使用替代 hook 机制或重构
5. **ABI 变化**：保持数据结构兼容性或使用包装函数
6. **Section 变化**：避免修改静态局部变量

## 验收标准

- ✅ **构建验收**：修改后的 patch 可通过 kpatch-build 构建为热补丁模块
- ✅ **运行验收**：模块可成功加载/卸载，通过功能验证
- ✅ **结果产出**：每个补丁生成结构化 JSON 报告 + 完整日志

## 性能指标

- **热补丁生成成功率**: 目标 ≥60%
- **语义一致性**: 改写补丁保持与上游修复意图一致
- **效率指标**: 平均每个补丁尝试轮次 ≤5 次

## 配置说明

### agent_config.yaml

```yaml
max_retry_rounds: 5
timeout_per_round: 600  # 秒
enable_memory: true
memory_path: ./memory_data
```

### llm_config.yaml

```yaml
model: qwen-max
api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
api_key: ${DASHSCOPE_API_KEY}
temperature: 0.7
max_tokens: 4096
```

## 开发指南

### 添加新的改写策略

在 `agent/patch_rewriter.py` 中添加新的策略类：

```python
class NewRewriteStrategy(RewriteStrategy):
    def can_handle(self, error_type: str) -> bool:
        return error_type == "your_error_type"
    
    def rewrite(self, patch: str, error_info: dict) -> str:
        # 实现改写逻辑
        return modified_patch
```

### 扩展错误分析

在 `tools/error_analyzer.py` 中添加新的错误模式：

```python
ERROR_PATTERNS = {
    "new_error": {
        "pattern": r"your regex pattern",
        "category": "kpatch_constraint",
        "severity": "high"
    }
}
```

## 故障排除

### QEMU 启动失败

```bash
# 检查 KVM 支持
lsmod | grep kvm

# 检查 QEMU 版本
qemu-system-x86_64 --version
```

### kpatch-build 失败

```bash
# 检查内核源码完整性
cd data/kernel_source
make mrproper
make oldconfig
```

### SSH 连接问题

```bash
# 重新生成 SSH 密钥
ssh-keygen -t rsa -f qemu/ssh_keys/id_rsa -N ""
```

## 参考资料

- [kpatch 官方文档](https://github.com/dynup/kpatch)
- [Linux livepatch 文档](https://docs.kernel.org/livepatch/livepatch.html)
- [Anolis OS 镜像仓库](https://mirrors.openanolis.cn/)
- [百炼平台文档](https://help.aliyun.com/zh/model-studio/)

## 许可证

MIT License

## 贡献者

- 项目团队

## 更新日志

### v1.0.0 (2026-05-19)
- 初始版本发布
- 实现基础 QEMU 环境
- 集成 kpatch 工具链
- 实现 LLM 驱动的补丁改写
