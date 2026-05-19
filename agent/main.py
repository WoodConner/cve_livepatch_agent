#!/usr/bin/env python3
"""
主程序入口
协调各模块完成 CVE 热补丁自动生成流程
"""

import argparse
import logging
import yaml
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from cve_query import CVEQuery
from patch_rewriter import PatchRewriter
from qemu_manager import QEMUManager
from tools.kpatch_wrapper import KpatchWrapper

logger = logging.getLogger(__name__)


class LivepatchAgent:
    """热补丁生成智能体"""

    def __init__(self, config_path: str):
        """
        初始化智能体

        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # 初始化各模块
        self.cve_query = CVEQuery(self.config.get('cve_query', {}))
        self.patch_rewriter = PatchRewriter(self.config.get('patch_rewriter', {}))
        self.qemu_manager = QEMUManager(self.config.get('qemu', {}))
        self.kpatch_wrapper = KpatchWrapper()

        # 配置参数
        self.max_retry = self.config.get('max_retry_rounds', 5)
        self.kernel_version = self.config.get('kernel_version', '6.6.102-5.2.an23')
        self.kernel_src_path = self.config.get('kernel_src_path', '/root/kernel-source')
        self.work_dir = self.config.get('work_dir', '/root/livepatch_work')

        # 结果统计
        self.results = []

    def process_cve(self, cve_id: str) -> Dict:
        """
        处理单个 CVE

        Args:
            cve_id: CVE 编号

        Returns:
            处理结果字典
        """
        logger.info(f"{'='*60}")
        logger.info(f"开始处理 CVE: {cve_id}")
        logger.info(f"{'='*60}")

        result = {
            'cve_id': cve_id,
            'start_time': datetime.now().isoformat(),
            'success': False,
            'attempts': [],
            'final_patch': None,
            'livepatch_module': None,
            'error_message': None,
        }

        try:
            # 步骤 1: 查询 CVE 信息
            logger.info("步骤 1: 查询 CVE 信息")
            cve_info = self.cve_query.query_cve(cve_id)
            if not cve_info:
                result['error_message'] = "无法查询到 CVE 信息"
                return result

            result['cve_info'] = cve_info
            logger.info(f"CVE 描述: {cve_info.get('description', '')[:100]}...")

            # 步骤 2: 获取上游补丁
            logger.info("步骤 2: 获取上游补丁")
            patch_file = self.cve_query.get_patch_for_kernel_version(
                cve_id,
                self.kernel_version
            )

            if not patch_file:
                result['error_message'] = "无法获取上游补丁"
                return result

            with open(patch_file, 'r') as f:
                original_patch = f.read()

            result['original_patch_file'] = patch_file
            logger.info(f"补丁已下载: {patch_file}")

            # 步骤 3: 多轮迭代构建
            logger.info("步骤 3: 开始多轮迭代构建")
            current_patch = original_patch
            build_success = False

            for attempt in range(1, self.max_retry + 1):
                logger.info(f"\n--- 第 {attempt}/{self.max_retry} 次尝试 ---")

                attempt_result = self._attempt_build(
                    cve_id=cve_id,
                    patch_content=current_patch,
                    attempt=attempt,
                    context={
                        'cve_id': cve_id,
                        'kernel_version': self.kernel_version,
                    }
                )

                result['attempts'].append(attempt_result)

                if attempt_result['build_success']:
                    logger.info("✅ 热补丁构建成功！")
                    build_success = True
                    result['success'] = True
                    result['final_patch'] = current_patch
                    result['livepatch_module'] = attempt_result['module_path']
                    break

                # 如果构建失败，改写补丁
                if attempt < self.max_retry:
                    logger.info("构建失败，准备改写补丁...")

                    error_analysis = attempt_result['error_analysis']
                    rewrite_success, rewritten_patch, explanation = self.patch_rewriter.rewrite_patch(
                        patch_content=current_patch,
                        error_analysis=error_analysis,
                        context={'cve_id': cve_id, 'kernel_version': self.kernel_version},
                        attempt=attempt + 1
                    )

                    if rewrite_success:
                        logger.info(f"补丁改写完成: {explanation[:100]}...")
                        current_patch = rewritten_patch
                    else:
                        logger.error("补丁改写失败")
                        result['error_message'] = "补丁改写失败"
                        break

            if not build_success:
                result['error_message'] = f"经过 {self.max_retry} 次尝试仍未成功"

            # 步骤 4: 验证热补丁（如果构建成功）
            if build_success:
                logger.info("步骤 4: 验证热补丁")
                verification_result = self._verify_livepatch(
                    result['livepatch_module']
                )
                result['verification'] = verification_result

                if not verification_result['load_success']:
                    result['success'] = False
                    result['error_message'] = "热补丁加载失败"

        except Exception as e:
            logger.error(f"处理 CVE 异常: {e}", exc_info=True)
            result['error_message'] = str(e)

        finally:
            result['end_time'] = datetime.now().isoformat()

        return result

    def _attempt_build(
        self,
        cve_id: str,
        patch_content: str,
        attempt: int,
        context: Dict
    ) -> Dict:
        """
        尝试构建热补丁

        Args:
            cve_id: CVE 编号
            patch_content: 补丁内容
            attempt: 尝试次数
            context: 上下文信息

        Returns:
            尝试结果字典
        """
        result = {
            'attempt': attempt,
            'build_success': False,
            'error_analysis': {},
            'build_log': '',
            'module_path': None,
        }

        try:
            # 保存补丁到虚拟机
            patch_filename = f"{cve_id}_attempt_{attempt}.patch"
            local_patch_path = f"/tmp/{patch_filename}"
            remote_patch_path = f"{self.work_dir}/{patch_filename}"

            with open(local_patch_path, 'w') as f:
                f.write(patch_content)

            # 上传补丁到虚拟机
            if not self.qemu_manager.upload_file(local_patch_path, remote_patch_path):
                result['error_analysis'] = {
                    'error_category': 'upload_failed',
                    'error_messages': ['上传补丁到虚拟机失败'],
                }
                return result

            # 在虚拟机中构建热补丁
            build_success, build_log = self.qemu_manager.build_livepatch(
                patch_path=remote_patch_path,
                kernel_src=self.kernel_src_path,
                output_dir=self.work_dir
            )

            result['build_log'] = build_log
            result['build_success'] = build_success

            # 分析构建错误
            if not build_success:
                error_analysis = self.kpatch_wrapper.analyze_build_error(build_log)
                result['error_analysis'] = error_analysis
                logger.warning(f"构建失败: {error_analysis.get('error_category')}")
            else:
                # 查找生成的模块文件
                module_name = f"livepatch-{cve_id}-{attempt}.ko"
                result['module_path'] = f"{self.work_dir}/{module_name}"

        except Exception as e:
            logger.error(f"构建尝试异常: {e}")
            result['error_analysis'] = {
                'error_category': 'exception',
                'error_messages': [str(e)],
            }

        return result

    def _verify_livepatch(self, module_path: str) -> Dict:
        """
        验证热补丁

        Args:
            module_path: 模块路径（虚拟机内）

        Returns:
            验证结果字典
        """
        result = {
            'load_success': False,
            'unload_success': False,
            'load_output': '',
            'unload_output': '',
        }

        try:
            # 加载热补丁
            logger.info("加载热补丁...")
            load_success, load_output = self.qemu_manager.load_livepatch(module_path)
            result['load_success'] = load_success
            result['load_output'] = load_output

            if not load_success:
                logger.error(f"热补丁加载失败: {load_output}")
                return result

            # 列出已加载的热补丁
            patches = self.qemu_manager.list_livepatches()
            logger.info(f"当前已加载的热补丁: {patches}")

            # 卸载热补丁
            logger.info("卸载热补丁...")
            module_name = Path(module_path).stem
            unload_success, unload_output = self.qemu_manager.unload_livepatch(module_name)
            result['unload_success'] = unload_success
            result['unload_output'] = unload_output

            if not unload_success:
                logger.warning(f"热补丁卸载失败: {unload_output}")

        except Exception as e:
            logger.error(f"验证热补丁异常: {e}")
            result['error'] = str(e)

        return result

    def process_cve_list(self, cve_list: List[str]) -> List[Dict]:
        """
        批量处理 CVE 列表

        Args:
            cve_list: CVE 编号列表

        Returns:
            处理结果列表
        """
        logger.info(f"开始批量处理 {len(cve_list)} 个 CVE")

        results = []
        for i, cve_id in enumerate(cve_list, 1):
            logger.info(f"\n处理进度: {i}/{len(cve_list)}")
            result = self.process_cve(cve_id)
            results.append(result)

            # 保存中间结果
            self._save_results(results)

        return results

    def _save_results(self, results: List[Dict]):
        """保存结果到文件"""
        try:
            output_dir = Path(self.config.get('output_dir', 'logs/reports'))
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = output_dir / f"results_{timestamp}.json"

            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            logger.info(f"结果已保存到: {output_file}")

        except Exception as e:
            logger.error(f"保存结果失败: {e}")

    def generate_report(self, results: List[Dict]) -> str:
        """
        生成汇总报告

        Args:
            results: 处理结果列表

        Returns:
            报告内容
        """
        total = len(results)
        success = sum(1 for r in results if r['success'])
        success_rate = (success / total * 100) if total > 0 else 0

        report = f"""
# CVE 热补丁生成报告

## 总体统计
- 总 CVE 数量: {total}
- 成功生成: {success}
- 失败数量: {total - success}
- 成功率: {success_rate:.2f}%

## 详细结果
"""

        for result in results:
            status = "✅ 成功" if result['success'] else "❌ 失败"
            attempts = len(result['attempts'])

            report += f"\n### {result['cve_id']} - {status}\n"
            report += f"- 尝试次数: {attempts}\n"

            if result['success']:
                report += f"- 热补丁模块: {result['livepatch_module']}\n"
            else:
                report += f"- 失败原因: {result.get('error_message', '未知')}\n"

        return report

    def start(self):
        """启动虚拟机环境"""
        logger.info("启动 QEMU 虚拟机...")
        if not self.qemu_manager.start_vm():
            logger.error("虚拟机启动失败")
            sys.exit(1)

        logger.info("虚拟机启动成功")

    def stop(self):
        """停止虚拟机环境"""
        logger.info("停止 QEMU 虚拟机...")
        self.qemu_manager.stop_vm()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CVE 热补丁自动生成智能体")
    parser.add_argument('--config', type=str, default='configs/agent_config.yaml',
                        help='配置文件路径')
    parser.add_argument('--cve', type=str, help='单个 CVE 编号')
    parser.add_argument('--cve-list', type=str, help='CVE 列表文件路径')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='日志级别')

    args = parser.parse_args()

    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/agent.log')
        ]
    )

    # 创建智能体
    agent = LivepatchAgent(args.config)

    try:
        # 启动虚拟机
        agent.start()

        # 处理 CVE
        if args.cve:
            # 处理单个 CVE
            result = agent.process_cve(args.cve)
            results = [result]

        elif args.cve_list:
            # 批量处理
            with open(args.cve_list, 'r') as f:
                cve_list = [line.strip() for line in f if line.strip()]

            results = agent.process_cve_list(cve_list)

        else:
            logger.error("请指定 --cve 或 --cve-list 参数")
            sys.exit(1)

        # 生成报告
        report = agent.generate_report(results)
        print("\n" + report)

        # 保存最终结果
        agent._save_results(results)

    finally:
        # 停止虚拟机
        agent.stop()


if __name__ == "__main__":
    main()
