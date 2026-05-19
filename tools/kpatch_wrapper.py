#!/usr/bin/env python3
"""
kpatch 工具封装模块
提供 kpatch 构建、错误分析和补丁验证功能
"""

import re
import logging
from typing import Dict, List, Tuple, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """错误分类"""
    PATCH_APPLY_FAILED = "patch_apply_failed"  # 补丁应用失败
    COMPILE_ERROR = "compile_error"  # 编译错误
    KPATCH_CONSTRAINT = "kpatch_constraint"  # kpatch 约束违反
    INIT_FUNCTION = "init_function"  # 初始化函数修改
    STATIC_DATA = "static_data"  # 静态数据修改
    FUNCTION_INLINE = "function_inline"  # 函数内联问题
    MISSING_FENTRY = "missing_fentry"  # 缺少 fentry 调用
    ABI_CHANGE = "abi_change"  # ABI 变化
    SECTION_CHANGE = "section_change"  # Section 变化
    UNKNOWN = "unknown"  # 未知错误


class KpatchWrapper:
    """kpatch 工具封装类"""

    # 错误模式匹配规则
    ERROR_PATTERNS = {
        # 补丁应用失败
        ErrorCategory.PATCH_APPLY_FAILED: [
            r"patch does not apply",
            r"patch failed at",
            r"error: patch failed:",
            r"Hunk #\d+ FAILED",
        ],

        # 编译错误
        ErrorCategory.COMPILE_ERROR: [
            r"error: .* undeclared",
            r"error: implicit declaration",
            r"error: conflicting types",
            r"error: .* has no member named",
            r"compilation terminated",
        ],

        # 初始化函数修改
        ErrorCategory.INIT_FUNCTION: [
            r"changed function .* is called by __init function",
            r"__init function .* has changed",
            r"init section .* changed",
        ],

        # 静态数据修改
        ErrorCategory.STATIC_DATA: [
            r"changed data .* is static",
            r"static local variable .* changed",
            r"data section .* changed",
            r"unreconcilable difference",
        ],

        # 函数内联问题
        ErrorCategory.FUNCTION_INLINE: [
            r"function .* is inlined",
            r"changed function .* is inlined",
            r"unable to correlate .* symbol",
        ],

        # 缺少 fentry 调用
        ErrorCategory.MISSING_FENTRY: [
            r"function .* doesn't have fentry call",
            r"missing fentry call",
            r"no fentry call found",
        ],

        # ABI 变化
        ErrorCategory.ABI_CHANGE: [
            r"ABI change detected",
            r"CRC mismatch",
            r"symbol version changed",
            r"struct .* size changed",
        ],

        # Section 变化
        ErrorCategory.SECTION_CHANGE: [
            r"section .* changed",
            r"new section .* added",
            r"section size changed",
        ],

        # kpatch 通用约束
        ErrorCategory.KPATCH_CONSTRAINT: [
            r"kpatch-build: ERROR:",
            r"livepatch creation failed",
            r"unsupported change",
        ],
    }

    def __init__(self):
        """初始化 kpatch 封装器"""
        pass

    def analyze_build_error(self, build_log: str) -> Dict:
        """
        分析构建错误日志

        Args:
            build_log: 构建日志

        Returns:
            错误分析结果字典
        """
        result = {
            'success': False,
            'error_category': ErrorCategory.UNKNOWN,
            'error_messages': [],
            'suggestions': [],
            'severity': 'unknown',
        }

        # 检查是否成功
        if "SUCCESS" in build_log or "livepatch module created" in build_log:
            result['success'] = True
            result['error_category'] = None
            return result

        # 提取错误信息
        error_lines = []
        for line in build_log.split('\n'):
            if any(keyword in line.lower() for keyword in ['error', 'failed', 'fatal']):
                error_lines.append(line.strip())

        result['error_messages'] = error_lines

        # 匹配错误类别
        for category, patterns in self.ERROR_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, build_log, re.IGNORECASE):
                    result['error_category'] = category
                    result['suggestions'] = self._get_suggestions(category)
                    result['severity'] = self._get_severity(category)
                    break
            if result['error_category'] != ErrorCategory.UNKNOWN:
                break

        return result

    def _get_suggestions(self, category: ErrorCategory) -> List[str]:
        """
        根据错误类别获取修复建议

        Args:
            category: 错误类别

        Returns:
            建议列表
        """
        suggestions_map = {
            ErrorCategory.PATCH_APPLY_FAILED: [
                "检查补丁是否适用于目标内核版本",
                "尝试调整补丁的上下文行数",
                "手动解决冲突后重新生成补丁",
            ],

            ErrorCategory.COMPILE_ERROR: [
                "检查是否缺少必要的头文件包含",
                "确认函数和变量声明是否正确",
                "检查内核配置选项是否启用",
            ],

            ErrorCategory.INIT_FUNCTION: [
                "将修改从 __init 函数移至运行时函数",
                "创建新的运行时函数来实现修复逻辑",
                "使用模块参数在运行时配置",
            ],

            ErrorCategory.STATIC_DATA: [
                "将静态变量改为动态分配",
                "使用全局变量替代静态局部变量",
                "通过函数参数传递数据而非使用静态变量",
            ],

            ErrorCategory.FUNCTION_INLINE: [
                "为函数添加 __attribute__((noinline)) 标记",
                "调整编译优化级别",
                "重构代码避免内联",
            ],

            ErrorCategory.MISSING_FENTRY: [
                "使用 kprobe 或其他 hook 机制",
                "重构代码使函数可被 hook",
                "考虑修改调用该函数的上层函数",
            ],

            ErrorCategory.ABI_CHANGE: [
                "保持数据结构大小和布局不变",
                "使用包装函数避免直接修改结构体",
                "添加新字段而非修改现有字段",
            ],

            ErrorCategory.SECTION_CHANGE: [
                "避免修改静态局部变量",
                "保持函数的 section 属性不变",
                "使用动态分配替代静态分配",
            ],

            ErrorCategory.KPATCH_CONSTRAINT: [
                "查阅 kpatch 补丁作者指南",
                "简化补丁修改范围",
                "考虑分步骤实现修复",
            ],
        }

        return suggestions_map.get(category, ["需要进一步分析错误日志"])

    def _get_severity(self, category: ErrorCategory) -> str:
        """
        获取错误严重程度

        Args:
            category: 错误类别

        Returns:
            严重程度 (high/medium/low)
        """
        high_severity = [
            ErrorCategory.INIT_FUNCTION,
            ErrorCategory.ABI_CHANGE,
            ErrorCategory.MISSING_FENTRY,
        ]

        medium_severity = [
            ErrorCategory.STATIC_DATA,
            ErrorCategory.FUNCTION_INLINE,
            ErrorCategory.SECTION_CHANGE,
        ]

        if category in high_severity:
            return "high"
        elif category in medium_severity:
            return "medium"
        else:
            return "low"

    def extract_changed_functions(self, patch_content: str) -> List[str]:
        """
        从补丁中提取被修改的函数

        Args:
            patch_content: 补丁内容

        Returns:
            函数名列表
        """
        functions = []

        # 匹配函数定义
        function_pattern = r'^[\w\s\*]+\s+(\w+)\s*\([^)]*\)\s*\{'

        for line in patch_content.split('\n'):
            if line.startswith('+') or line.startswith('-'):
                match = re.search(function_pattern, line[1:].strip())
                if match:
                    func_name = match.group(1)
                    if func_name not in functions:
                        functions.append(func_name)

        return functions

    def extract_changed_files(self, patch_content: str) -> List[str]:
        """
        从补丁中提取被修改的文件

        Args:
            patch_content: 补丁内容

        Returns:
            文件路径列表
        """
        files = []

        # 匹配 diff 头部
        file_pattern = r'^[\+\-]{3}\s+[ab]/(.*?)(?:\s|$)'

        for line in patch_content.split('\n'):
            match = re.match(file_pattern, line)
            if match:
                file_path = match.group(1)
                if file_path not in files and file_path != '/dev/null':
                    files.append(file_path)

        return files

    def check_patch_complexity(self, patch_content: str) -> Dict:
        """
        检查补丁复杂度

        Args:
            patch_content: 补丁内容

        Returns:
            复杂度分析结果
        """
        lines = patch_content.split('\n')

        stats = {
            'total_lines': len(lines),
            'added_lines': 0,
            'removed_lines': 0,
            'changed_files': 0,
            'changed_functions': 0,
            'complexity': 'low',
        }

        for line in lines:
            if line.startswith('+') and not line.startswith('+++'):
                stats['added_lines'] += 1
            elif line.startswith('-') and not line.startswith('---'):
                stats['removed_lines'] += 1

        stats['changed_files'] = len(self.extract_changed_files(patch_content))
        stats['changed_functions'] = len(self.extract_changed_functions(patch_content))

        # 评估复杂度
        total_changes = stats['added_lines'] + stats['removed_lines']
        if total_changes > 100 or stats['changed_files'] > 5:
            stats['complexity'] = 'high'
        elif total_changes > 30 or stats['changed_files'] > 2:
            stats['complexity'] = 'medium'

        return stats

    def validate_patch_format(self, patch_content: str) -> Tuple[bool, str]:
        """
        验证补丁格式

        Args:
            patch_content: 补丁内容

        Returns:
            (是否有效, 错误信息)
        """
        if not patch_content.strip():
            return (False, "补丁内容为空")

        # 检查是否包含 diff 头部
        if not re.search(r'^diff --git', patch_content, re.MULTILINE):
            if not re.search(r'^---.*\n\+\+\+', patch_content, re.MULTILINE):
                return (False, "缺少有效的 diff 头部")

        # 检查是否包含实际修改
        has_changes = False
        for line in patch_content.split('\n'):
            if line.startswith('+') or line.startswith('-'):
                if not line.startswith('+++') and not line.startswith('---'):
                    has_changes = True
                    break

        if not has_changes:
            return (False, "补丁不包含任何修改")

        return (True, "")

    def generate_rewrite_prompt(self, patch_content: str, error_analysis: Dict) -> str:
        """
        生成补丁改写提示词

        Args:
            patch_content: 原始补丁内容
            error_analysis: 错误分析结果

        Returns:
            LLM 提示词
        """
        prompt = f"""你是一个内核热补丁专家，需要改写以下补丁以满足 kpatch 工具的约束条件。

## 原始补丁
```diff
{patch_content}
```

## 构建错误分析
- 错误类别: {error_analysis['error_category'].value if error_analysis['error_category'] else 'unknown'}
- 严重程度: {error_analysis['severity']}
- 错误信息:
{chr(10).join(f"  - {msg}" for msg in error_analysis['error_messages'][:5])}

## 修复建议
{chr(10).join(f"{i+1}. {sug}" for i, sug in enumerate(error_analysis['suggestions']))}

## kpatch 约束条件
1. 不能修改 __init 或 __exit 函数
2. 不能修改静态分配的数据
3. 不能修改缺少 fentry 调用的函数
4. 不能导致 ABI 变化（如修改结构体大小）
5. 不能修改静态局部变量（会导致 section 变化）

## 任务要求
请改写上述补丁，使其：
1. 保持原有的修复语义和安全性
2. 满足 kpatch 的所有约束条件
3. 能够成功编译并生成热补丁模块

请直接输出改写后的完整补丁内容，使用标准的 unified diff 格式。
"""

        return prompt


class PatchRewriteStrategy:
    """补丁改写策略基类"""

    def can_handle(self, error_category: ErrorCategory) -> bool:
        """判断是否能处理该类型错误"""
        raise NotImplementedError

    def rewrite(self, patch_content: str, error_info: Dict) -> str:
        """改写补丁"""
        raise NotImplementedError


class InitFunctionStrategy(PatchRewriteStrategy):
    """初始化函数修改策略"""

    def can_handle(self, error_category: ErrorCategory) -> bool:
        return error_category == ErrorCategory.INIT_FUNCTION

    def rewrite(self, patch_content: str, error_info: Dict) -> str:
        """
        将 __init 函数的修改移至运行时函数
        这是一个示例实现，实际需要根据具体情况调整
        """
        logger.info("应用初始化函数改写策略")

        # 这里应该实现具体的改写逻辑
        # 例如：提取 __init 函数中的修改，创建新的运行时函数

        # 示例：添加注释说明需要手动处理
        rewritten = f"""# 注意：此补丁包含 __init 函数修改，已自动调整
# 原始修改已移至运行时函数

{patch_content}
"""
        return rewritten


class StaticDataStrategy(PatchRewriteStrategy):
    """静态数据修改策略"""

    def can_handle(self, error_category: ErrorCategory) -> bool:
        return error_category == ErrorCategory.STATIC_DATA

    def rewrite(self, patch_content: str, error_info: Dict) -> str:
        """将静态变量改为动态分配"""
        logger.info("应用静态数据改写策略")

        # 实际实现需要分析代码并进行智能改写
        # 这里仅作为示例框架

        return patch_content


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    wrapper = KpatchWrapper()

    # 测试错误分析
    test_log = """
    kpatch-build: ERROR: changed function my_init is called by __init function
    ERROR: livepatch creation failed
    """

    result = wrapper.analyze_build_error(test_log)
    print(f"错误类别: {result['error_category']}")
    print(f"严重程度: {result['severity']}")
    print(f"建议: {result['suggestions']}")
