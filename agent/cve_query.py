#!/usr/bin/env python3
"""
CVE 查询和补丁获取模块
支持从 NVD、Linux CVE 邮件列表和 stable 仓库获取补丁
"""

import re
import requests
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import subprocess
import json

logger = logging.getLogger(__name__)


class CVEQuery:
    """CVE 查询类"""

    def __init__(self, config: Dict):
        """
        初始化 CVE 查询器

        Args:
            config: 配置字典
        """
        self.config = config
        self.nvd_api_key = config.get('nvd_api_key', '')
        self.cache_dir = Path(config.get('cache_dir', 'data/cve_cache'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Linux stable 仓库
        self.linux_stable_url = "https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git"

    def query_cve(self, cve_id: str) -> Optional[Dict]:
        """
        查询 CVE 信息

        Args:
            cve_id: CVE 编号 (如 CVE-2024-12345)

        Returns:
            CVE 信息字典，失败返回 None
        """
        try:
            logger.info(f"查询 CVE: {cve_id}")

            # 检查缓存
            cache_file = self.cache_dir / f"{cve_id}.json"
            if cache_file.exists():
                logger.info(f"从缓存加载: {cache_file}")
                with open(cache_file, 'r') as f:
                    return json.load(f)

            # 从 NVD 查询
            cve_info = self._query_nvd(cve_id)

            if cve_info:
                # 保存到缓存
                with open(cache_file, 'w') as f:
                    json.dump(cve_info, f, indent=2)

            return cve_info

        except Exception as e:
            logger.error(f"查询 CVE 失败: {e}")
            return None

    def _query_nvd(self, cve_id: str) -> Optional[Dict]:
        """
        从 NVD 数据库查询 CVE

        Args:
            cve_id: CVE 编号

        Returns:
            CVE 信息字典
        """
        try:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            params = {'cveId': cve_id}

            headers = {}
            if self.nvd_api_key:
                headers['apiKey'] = self.nvd_api_key

            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            if 'vulnerabilities' in data and len(data['vulnerabilities']) > 0:
                vuln = data['vulnerabilities'][0]['cve']

                cve_info = {
                    'id': cve_id,
                    'description': vuln.get('descriptions', [{}])[0].get('value', ''),
                    'published': vuln.get('published', ''),
                    'severity': self._extract_severity(vuln),
                    'references': [ref.get('url') for ref in vuln.get('references', [])],
                }

                logger.info(f"成功从 NVD 获取 CVE 信息: {cve_id}")
                return cve_info

            return None

        except Exception as e:
            logger.error(f"NVD 查询失败: {e}")
            return None

    def _extract_severity(self, vuln_data: Dict) -> str:
        """提取严重程度"""
        try:
            metrics = vuln_data.get('metrics', {})
            if 'cvssMetricV31' in metrics:
                return metrics['cvssMetricV31'][0]['cvssData']['baseSeverity']
            elif 'cvssMetricV2' in metrics:
                return metrics['cvssMetricV2'][0]['baseSeverity']
        except:
            pass
        return 'UNKNOWN'

    def find_upstream_commits(self, cve_id: str, kernel_version: str = "6.6") -> List[Dict]:
        """
        查找上游修复提交

        Args:
            cve_id: CVE 编号
            kernel_version: 目标内核版本

        Returns:
            提交信息列表
        """
        try:
            logger.info(f"查找 {cve_id} 的上游修复提交 (内核版本: {kernel_version})")

            commits = []

            # 方法 1: 从 CVE 信息中的引用链接提取
            cve_info = self.query_cve(cve_id)
            if cve_info and 'references' in cve_info:
                for ref in cve_info['references']:
                    if 'git.kernel.org' in ref or 'github.com/torvalds/linux' in ref:
                        commit_id = self._extract_commit_id(ref)
                        if commit_id:
                            commits.append({
                                'commit_id': commit_id,
                                'url': ref,
                                'source': 'cve_reference'
                            })

            # 方法 2: 搜索 Linux stable 仓库
            stable_commits = self._search_stable_repo(cve_id, kernel_version)
            commits.extend(stable_commits)

            # 方法 3: 搜索 Linux CVE 邮件列表
            # (这里可以添加邮件列表搜索逻辑)

            logger.info(f"找到 {len(commits)} 个相关提交")
            return commits

        except Exception as e:
            logger.error(f"查找上游提交失败: {e}")
            return []

    def _extract_commit_id(self, url: str) -> Optional[str]:
        """从 URL 中提取 commit ID"""
        patterns = [
            r'/commit/([0-9a-f]{40})',
            r'/commit/([0-9a-f]{12,40})',
            r'id=([0-9a-f]{40})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        return None

    def _search_stable_repo(self, cve_id: str, kernel_version: str) -> List[Dict]:
        """
        在 stable 仓库中搜索相关提交

        Args:
            cve_id: CVE 编号
            kernel_version: 内核版本

        Returns:
            提交列表
        """
        try:
            # 使用 git log 搜索包含 CVE ID 的提交
            cmd = [
                'git', 'log',
                '--all',
                '--grep', cve_id,
                '--pretty=format:%H|%s|%an|%ad',
                '--date=short'
            ]

            # 如果本地有 Linux 仓库，使用本地仓库
            linux_repo = self.config.get('linux_repo_path', 'data/linux')
            if Path(linux_repo).exists():
                result = subprocess.run(
                    cmd,
                    cwd=linux_repo,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0 and result.stdout:
                    commits = []
                    for line in result.stdout.strip().split('\n'):
                        if line:
                            parts = line.split('|')
                            if len(parts) >= 4:
                                commits.append({
                                    'commit_id': parts[0],
                                    'subject': parts[1],
                                    'author': parts[2],
                                    'date': parts[3],
                                    'source': 'stable_repo'
                                })
                    return commits

        except Exception as e:
            logger.debug(f"搜索 stable 仓库失败: {e}")

        return []

    def download_patch(self, commit_id: str, output_path: str) -> bool:
        """
        下载补丁文件

        Args:
            commit_id: 提交 ID
            output_path: 输出路径

        Returns:
            是否下载成功
        """
        try:
            logger.info(f"下载补丁: {commit_id}")

            # 方法 1: 从 git.kernel.org 下载
            patch_url = f"{self.linux_stable_url}/patch/?id={commit_id}"

            response = requests.get(patch_url, timeout=60)
            response.raise_for_status()

            # 保存补丁
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w') as f:
                f.write(response.text)

            logger.info(f"补丁已保存到: {output_path}")
            return True

        except Exception as e:
            logger.error(f"下载补丁失败: {e}")

            # 方法 2: 如果有本地仓库，使用 git format-patch
            return self._export_patch_from_local(commit_id, output_path)

    def _export_patch_from_local(self, commit_id: str, output_path: str) -> bool:
        """从本地仓库导出补丁"""
        try:
            linux_repo = self.config.get('linux_repo_path', 'data/linux')
            if not Path(linux_repo).exists():
                return False

            cmd = ['git', 'show', commit_id]
            result = subprocess.run(
                cmd,
                cwd=linux_repo,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                with open(output_path, 'w') as f:
                    f.write(result.stdout)
                logger.info(f"从本地仓库导出补丁: {output_path}")
                return True

        except Exception as e:
            logger.debug(f"从本地仓库导出补丁失败: {e}")

        return False

    def get_patch_for_kernel_version(self, cve_id: str, kernel_version: str) -> Optional[str]:
        """
        获取适用于特定内核版本的补丁

        Args:
            cve_id: CVE 编号
            kernel_version: 内核版本 (如 "6.6.102")

        Returns:
            补丁文件路径，失败返回 None
        """
        try:
            logger.info(f"获取 {cve_id} 针对内核 {kernel_version} 的补丁")

            # 查找上游提交
            commits = self.find_upstream_commits(cve_id, kernel_version)

            if not commits:
                logger.warning(f"未找到 {cve_id} 的修复提交")
                return None

            # 下载第一个找到的补丁
            commit = commits[0]
            patch_file = self.cache_dir / f"{cve_id}_{commit['commit_id'][:12]}.patch"

            if self.download_patch(commit['commit_id'], str(patch_file)):
                return str(patch_file)

            return None

        except Exception as e:
            logger.error(f"获取补丁失败: {e}")
            return None

    def batch_query_cves(self, cve_list: List[str]) -> Dict[str, Dict]:
        """
        批量查询 CVE

        Args:
            cve_list: CVE 编号列表

        Returns:
            CVE 信息字典 {cve_id: cve_info}
        """
        results = {}

        for cve_id in cve_list:
            cve_info = self.query_cve(cve_id)
            if cve_info:
                results[cve_id] = cve_info

        return results


class PatchAdapter:
    """补丁适配器 - 将上游补丁适配到目标内核版本"""

    def __init__(self, target_kernel_version: str):
        """
        初始化补丁适配器

        Args:
            target_kernel_version: 目标内核版本
        """
        self.target_version = target_kernel_version

    def adapt_patch(self, patch_content: str) -> str:
        """
        适配补丁到目标内核版本

        Args:
            patch_content: 原始补丁内容

        Returns:
            适配后的补丁内容
        """
        # 这里可以实现补丁适配逻辑
        # 例如：调整文件路径、函数名、API 变化等

        logger.info(f"适配补丁到内核版本 {self.target_version}")

        # 目前直接返回原始补丁
        # 实际应用中需要根据内核版本差异进行智能适配
        return patch_content

    def check_compatibility(self, patch_content: str) -> Tuple[bool, List[str]]:
        """
        检查补丁与目标内核的兼容性

        Args:
            patch_content: 补丁内容

        Returns:
            (是否兼容, 不兼容原因列表)
        """
        issues = []

        # 检查文件路径是否存在
        # 检查函数签名是否匹配
        # 检查 API 是否可用
        # 等等...

        is_compatible = len(issues) == 0
        return (is_compatible, issues)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    config = {
        'cache_dir': '/tmp/cve_cache',
        'linux_repo_path': '/path/to/linux',
    }

    query = CVEQuery(config)

    # 测试查询 CVE
    cve_info = query.query_cve("CVE-2024-26581")
    if cve_info:
        print(f"CVE ID: {cve_info['id']}")
        print(f"描述: {cve_info['description'][:100]}...")
        print(f"严重程度: {cve_info['severity']}")
