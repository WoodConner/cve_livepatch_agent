# Claude Code 增强配置

本项目集成了类似 Claude Code 的 hooks 和 skills 系统，用于自动化开发工作流。

## 目录结构

```
.claude/
├── hooks/              # Git 风格的钩子脚本
│   ├── pre-commit     # 提交前检查
│   ├── post-commit    # 提交后任务
│   └── pre-push       # 推送前验证
└── skills/            # 专用任务脚本
    ├── cve-analyze    # CVE 分析和补丁生成
    ├── patch-verify   # 补丁验证
    └── env-check      # 环境检查
```

## Hooks 使用说明

### 1. pre-commit（提交前检查）

**功能：**
- 检查代码中的 API 密钥泄露
- 验证 Python 语法
- 运行代码格式检查
- 执行快速测试

**使用方法：**
```bash
# 自动触发（在 git commit 时）
git commit -m "your message"

# 手动运行
.claude/hooks/pre-commit
```

**配置：**
如需跳过某些检查，可以设置环境变量：
```bash
SKIP_SYNTAX_CHECK=1 git commit -m "message"
```

### 2. post-commit（提交后任务）

**功能：**
- 生成提交统计信息
- 自动更新 CHANGELOG.md
- 检查是否需要更新版本号
- 运行快速测试

**使用方法：**
```bash
# 自动触发（在 git commit 后）
git commit -m "your message"

# 查看统计信息
cat .claude/last_commit_stats.txt
```

### 3. pre-push（推送前验证）

**功能：**
- 运行完整测试套件
- 检查未提交的更改
- 验证分支名称
- 检查大文件
- 验证 requirements.txt

**使用方法：**
```bash
# 自动触发（在 git push 时）
git push origin main

# 手动运行
.claude/hooks/pre-push
```

## Skills 使用说明

### 1. cve-analyze（CVE 分析）

**功能：**
- 查询 CVE 信息
- 下载相关补丁
- 使用 Claude API 智能改写补丁
- 生成分析报告

**使用方法：**
```bash
# 基本用法
.claude/skills/cve-analyze CVE-2024-26581

# 指定输出目录
.claude/skills/cve-analyze CVE-2024-26581 --output ./my_output

# 详细输出
.claude/skills/cve-analyze CVE-2024-26581 --verbose

# 自定义配置
.claude/skills/cve-analyze CVE-2024-26581 --config my_config.yaml
```

**输出：**
- `{CVE_ID}_report.txt`: 分析报告
- `{CVE_ID}_rewritten.patch`: 改写后的补丁（如果启用）

**环境变量：**
- `ANTHROPIC_AUTH_TOKEN`: Claude API 认证令牌（必需）
- `ANTHROPIC_BASE_URL`: API 基础 URL（可选）

### 2. patch-verify（补丁验证）

**功能：**
- 检查补丁语法
- 分析补丁内容（修改的文件、函数、行数）
- 检查 kpatch 兼容性
- 测试补丁是否可应用

**使用方法：**
```bash
# 基本验证
.claude/skills/patch-verify path/to/patch.patch

# 完整验证（包括应用测试）
.claude/skills/patch-verify path/to/patch.patch --full

# 指定内核源码路径
.claude/skills/patch-verify path/to/patch.patch --kernel-src /usr/src/kernels/6.6.102
```

**输出示例：**
```
🔍 验证补丁: CVE-2024-26581.patch
============================================================

[1/4] 语法检查
  → 检查补丁语法...
    ✅ 补丁语法正确

[2/4] 内容分析
  → 分析补丁修改...
    文件修改: 1 个
      - net/netfilter/nf_tables_api.c
    函数修改: 2 个
      - nft_chain_validate()
      - nft_table_validate()
    行数变化: +15 -3

[3/4] 兼容性检查
  → 检查 kpatch 兼容性...
    ✅ 未发现明显兼容性问题

[4/4] 应用测试（跳过，使用 --full 启用）

============================================================
✅ 验证通过
```

### 3. env-check（环境检查）

**功能：**
- 检查系统工具（git, gcc, make, qemu, kpatch）
- 检查 Python 环境和依赖包
- 验证环境变量
- 检查项目文件完整性
- 检查内核文件

**使用方法：**
```bash
# 运行环境检查
.claude/skills/env-check
```

**输出示例：**
```
🔍 环境检查
======================================================================

[1/5] 系统工具
  ✅ git                       git version 2.43.0
  ✅ gcc                       gcc (Ubuntu 13.2.0-23ubuntu4) 13.2.0
  ✅ make                      GNU Make 4.3
  ✅ qemu-system-x86_64        QEMU emulator version 11.0.0
  ⚠️  kpatch                   kpatch 0.9.11
     └─ 版本可能不符合要求

[2/5] Python 环境
  ✅ Python 版本:            3.12.3
  ✅ anthropic               0.18.1
  ✅ yaml                    6.0.2
  ✅ requests                2.32.3

[3/5] 环境变量
  ✅ ANTHROPIC_AUTH_TOKEN    sk-ant-api...
  ⚠️  ANTHROPIC_BASE_URL     未设置（可选）

[4/5] 项目文件
  ✅ 配置文件                 1234 bytes
  ✅ 主程序                   5678 bytes
  ✅ CVE 查询模块             3456 bytes
  ✅ 补丁改写模块             4567 bytes
  ✅ 依赖列表                 234 bytes

[5/5] 内核文件
  ✅ 内核源码目录             3 items
  ✅ 内核模块目录             12 items

======================================================================
✅ 环境检查通过！所有必需组件已就绪。
```

## 安装 Hooks

要启用 Git hooks，需要将它们链接到 `.git/hooks/` 目录：

```bash
# 进入项目根目录
cd /path/to/cve_livepatch_agent

# 创建符号链接
ln -sf ../../.claude/hooks/pre-commit .git/hooks/pre-commit
ln -sf ../../.claude/hooks/post-commit .git/hooks/post-commit
ln -sf ../../.claude/hooks/pre-push .git/hooks/pre-push

# 确保可执行
chmod +x .git/hooks/*
```

## 工作流示例

### 完整的 CVE 修复流程

```bash
# 1. 检查环境
.claude/skills/env-check

# 2. 分析 CVE
.claude/skills/cve-analyze CVE-2024-26581 --output ./output

# 3. 验证补丁
.claude/skills/patch-verify ./output/CVE-2024-26581_rewritten.patch --full

# 4. 提交更改（自动触发 pre-commit 和 post-commit hooks）
git add .
git commit -m "fix: apply patch for CVE-2024-26581"

# 5. 推送（自动触发 pre-push hook）
git push origin main
```

### 日常开发流程

```bash
# 1. 修改代码
vim agent/patch_rewriter.py

# 2. 提交（自动检查）
git add agent/patch_rewriter.py
git commit -m "refactor: improve patch rewriting logic"
# → pre-commit 自动检查代码质量
# → post-commit 自动生成统计

# 3. 推送（自动验证）
git push origin feature-branch
# → pre-push 自动运行测试
```

## 自定义配置

### 禁用特定检查

在 `.git/hooks/` 中编辑对应的 hook 文件，注释掉不需要的检查。

### 添加自定义 Skill

创建新的 skill 脚本：

```bash
# 创建新 skill
cat > .claude/skills/my-skill << 'EOF'
#!/usr/bin/env python3
"""
Skill: 我的自定义任务
"""
import sys

def main():
    print("执行自定义任务...")
    return 0

if __name__ == '__main__':
    sys.exit(main())
EOF

# 添加执行权限
chmod +x .claude/skills/my-skill

# 使用
.claude/skills/my-skill
```

## 故障排除

### Hooks 不执行

```bash
# 检查 hooks 是否可执行
ls -la .git/hooks/

# 重新设置权限
chmod +x .git/hooks/*

# 检查符号链接
ls -la .git/hooks/pre-commit
```

### Skills 找不到模块

```bash
# 确保在项目根目录运行
cd /path/to/cve_livepatch_agent

# 或设置 PYTHONPATH
export PYTHONPATH=/path/to/cve_livepatch_agent:$PYTHONPATH
```

### API 认证失败

```bash
# 检查环境变量
echo $ANTHROPIC_AUTH_TOKEN

# 重新设置
export ANTHROPIC_AUTH_TOKEN="your-token-here"
```

## 最佳实践

1. **定期运行环境检查**：在开始工作前运行 `env-check`
2. **使用 CVE 分析工具**：标准化 CVE 处理流程
3. **验证所有补丁**：提交前使用 `patch-verify` 检查
4. **保持 hooks 更新**：根据项目需求调整 hooks
5. **记录自定义配置**：在团队中共享配置经验

## 参考资料

- [Git Hooks 文档](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)
- [kpatch 文档](https://github.com/dynup/kpatch)
- [Claude API 文档](https://docs.anthropic.com/)
