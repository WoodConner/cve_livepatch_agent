#!/usr/bin/env python3
"""
补丁改写智能体
使用 LLM 理解补丁语义并改写以满足 kpatch 约束
"""

import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import openai

logger = logging.getLogger(__name__)


class PatchRewriter:
    """补丁改写智能体"""

    def __init__(self, config: Dict):
        """
        初始化补丁改写器

        Args:
            config: 配置字典
        """
        self.config = config
        self.llm_config = config.get('llm', {})

        # 配置 OpenAI 客户端（兼容百炼平台）
        self.client = openai.OpenAI(
            api_key=self.llm_config.get('api_key', ''),
            base_url=self.llm_config.get('api_base', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        )

        self.model = self.llm_config.get('model', 'qwen-max')
        self.temperature = self.llm_config.get('temperature', 0.7)
        self.max_tokens = self.llm_config.get('max_tokens', 4096)

        # 改写历史记录
        self.rewrite_history = []

    def rewrite_patch(
        self,
        patch_content: str,
        error_analysis: Dict,
        context: Optional[Dict] = None,
        attempt: int = 1
    ) -> Tuple[bool, str, str]:
        """
        改写补丁以满足 kpatch 约束

        Args:
            patch_content: 原始补丁内容
            error_analysis: 错误分析结果
            context: 额外上下文信息
            attempt: 当前尝试次数

        Returns:
            (是否成功, 改写后的补丁, 改写说明)
        """
        try:
            logger.info(f"开始改写补丁 (第 {attempt} 次尝试)")

            # 构建提示词
            prompt = self._build_rewrite_prompt(
                patch_content,
                error_analysis,
                context,
                attempt
            )

            # 调用 LLM
            response = self._call_llm(prompt)

            if not response:
                return (False, patch_content, "LLM 调用失败")

            # 解析响应
            rewritten_patch, explanation = self._parse_llm_response(response)

            if not rewritten_patch:
                return (False, patch_content, "无法解析 LLM 响应")

            # 记录改写历史
            self._record_rewrite(
                original=patch_content,
                rewritten=rewritten_patch,
                explanation=explanation,
                error_analysis=error_analysis,
                attempt=attempt
            )

            logger.info("补丁改写完成")
            return (True, rewritten_patch, explanation)

        except Exception as e:
            logger.error(f"补丁改写异常: {e}")
            return (False, patch_content, str(e))

    def _build_rewrite_prompt(
        self,
        patch_content: str,
        error_analysis: Dict,
        context: Optional[Dict],
        attempt: int
    ) -> str:
        """构建 LLM 提示词"""

        # 基础提示词
        prompt = f"""你是一个 Linux 内核热补丁专家，精通 kpatch 工具的使用和约束条件。

## 任务
需要改写以下内核补丁，使其满足 kpatch 工具的所有约束条件，同时保持原有的修复语义。

## 原始补丁
```diff
{patch_content}
```

## 构建错误分析
"""

        # 添加错误信息
        if error_analysis.get('error_category'):
            prompt += f"- **错误类别**: {error_analysis['error_category'].value}\n"

        prompt += f"- **严重程度**: {error_analysis.get('severity', 'unknown')}\n"

        if error_analysis.get('error_messages'):
            prompt += "\n**错误信息**:\n"
            for msg in error_analysis['error_messages'][:5]:
                prompt += f"  - {msg}\n"

        if error_analysis.get('suggestions'):
            prompt += "\n**修复建议**:\n"
            for i, sug in enumerate(error_analysis['suggestions'], 1):
                prompt += f"  {i}. {sug}\n"

        # 添加 kpatch 约束说明
        prompt += """
## kpatch 核心约束条件

1. **不能修改初始化函数**
   - 不能修改标记为 `__init` 或 `__exit` 的函数
   - 不能修改只在初始化阶段调用的函数
   - **解决方案**: 将修改移至运行时函数，或创建新的运行时函数

2. **不能修改静态数据**
   - 不能修改全局静态变量
   - 不能修改静态局部变量（会导致 section 变化）
   - **解决方案**: 改为动态分配，或使用函数参数传递

3. **不能修改缺少 fentry 调用的函数**
   - 某些小函数或内联函数可能没有 fentry hook 点
   - **解决方案**: 修改调用该函数的上层函数，或使用其他 hook 机制

4. **不能导致 ABI 变化**
   - 不能修改导出符号的函数签名
   - 不能修改公共数据结构的大小或布局
   - **解决方案**: 使用包装函数，或添加新字段而非修改现有字段

5. **不能导致 section 变化**
   - 避免修改静态局部变量
   - 保持函数的 section 属性不变
   - **解决方案**: 使用动态分配替代静态分配

## 改写要求

1. **保持语义等价**: 改写后的补丁必须实现与原补丁相同的修复效果
2. **最小化修改**: 只改写必要的部分，保持其他代码不变
3. **符合内核编码规范**: 遵循 Linux 内核的编码风格
4. **添加必要注释**: 在关键改动处添加简短注释说明
5. **完整性**: 输出完整的补丁，包括所有必要的上下文行

"""

        # 添加上下文信息
        if context:
            prompt += "\n## 额外上下文\n"
            if 'cve_id' in context:
                prompt += f"- CVE ID: {context['cve_id']}\n"
            if 'kernel_version' in context:
                prompt += f"- 目标内核版本: {context['kernel_version']}\n"
            if 'changed_files' in context:
                prompt += f"- 修改的文件: {', '.join(context['changed_files'])}\n"

        # 如果是多次尝试，添加历史信息
        if attempt > 1:
            prompt += f"\n## 注意\n这是第 {attempt} 次改写尝试。之前的尝试仍然失败，请采用不同的策略。\n"

        # 输出格式说明
        prompt += """
## 输出格式

请按以下格式输出：

### 改写说明
[简要说明你做了哪些改动以及为什么这样改]

### 改写后的补丁
```diff
[完整的改写后的补丁内容，使用标准 unified diff 格式]
```

现在请开始改写补丁。
"""

        return prompt

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用 LLM"""
        try:
            logger.debug("调用 LLM...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个 Linux 内核热补丁专家，精通 kpatch 工具和内核开发。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.debug(f"LLM 响应长度: {len(content)} 字符")
                return content

            return None

        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
            return None

    def _parse_llm_response(self, response: str) -> Tuple[Optional[str], str]:
        """
        解析 LLM 响应

        Returns:
            (补丁内容, 改写说明)
        """
        try:
            # 提取改写说明
            explanation = ""
            if "### 改写说明" in response or "改写说明" in response:
                parts = response.split("### 改写后的补丁")
                if len(parts) > 0:
                    explanation = parts[0].replace("### 改写说明", "").strip()

            # 提取补丁内容
            patch_content = None

            # 方法 1: 从代码块中提取
            import re
            code_blocks = re.findall(r'```(?:diff)?\n(.*?)```', response, re.DOTALL)
            if code_blocks:
                # 选择最长的代码块（通常是完整补丁）
                patch_content = max(code_blocks, key=len).strip()

            # 方法 2: 如果没有代码块，尝试查找 diff 标记
            if not patch_content:
                if 'diff --git' in response or '--- a/' in response:
                    # 从第一个 diff 标记开始提取
                    start_patterns = ['diff --git', '--- a/', '--- ']
                    for pattern in start_patterns:
                        if pattern in response:
                            start_idx = response.index(pattern)
                            patch_content = response[start_idx:].strip()
                            break

            if patch_content:
                return (patch_content, explanation)

            logger.warning("无法从 LLM 响应中提取补丁内容")
            return (None, explanation)

        except Exception as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            return (None, "")

    def _record_rewrite(
        self,
        original: str,
        rewritten: str,
        explanation: str,
        error_analysis: Dict,
        attempt: int
    ):
        """记录改写历史"""
        record = {
            'attempt': attempt,
            'original_patch': original,
            'rewritten_patch': rewritten,
            'explanation': explanation,
            'error_category': error_analysis.get('error_category').value if error_analysis.get('error_category') else None,
            'error_severity': error_analysis.get('severity'),
        }

        self.rewrite_history.append(record)

    def get_rewrite_history(self) -> List[Dict]:
        """获取改写历史"""
        return self.rewrite_history

    def save_rewrite_history(self, output_path: str):
        """保存改写历史到文件"""
        try:
            with open(output_path, 'w') as f:
                json.dump(self.rewrite_history, f, indent=2, ensure_ascii=False)
            logger.info(f"改写历史已保存到: {output_path}")
        except Exception as e:
            logger.error(f"保存改写历史失败: {e}")


class RewriteStrategySelector:
    """改写策略选择器"""

    def __init__(self):
        """初始化策略选择器"""
        self.strategies = {}

    def select_strategy(self, error_category: str) -> Optional[str]:
        """
        根据错误类别选择改写策略

        Args:
            error_category: 错误类别

        Returns:
            策略名称
        """
        strategy_map = {
            'init_function': 'move_to_runtime',
            'static_data': 'dynamic_allocation',
            'function_inline': 'add_noinline',
            'missing_fentry': 'modify_caller',
            'abi_change': 'wrapper_function',
            'section_change': 'avoid_static_local',
        }

        return strategy_map.get(error_category)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    config = {
        'llm': {
            'api_key': 'your-api-key',
            'api_base': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'model': 'qwen-max',
            'temperature': 0.7,
            'max_tokens': 4096,
        }
    }

    rewriter = PatchRewriter(config)
    print("补丁改写器初始化成功")
