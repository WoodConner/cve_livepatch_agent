#!/usr/bin/env python3
"""
快速测试脚本 - 不需要 QEMU 环境
测试 CVE 查询和补丁下载功能
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.cve_query import CVEQuery
import logging

logging.basicConfig(level=logging.INFO)

def test_cve_query():
    """测试 CVE 查询功能"""
    print("=" * 60)
    print("测试 CVE 查询功能")
    print("=" * 60)

    config = {
        'cache_dir': 'data/cve_cache',
        'linux_repo_path': 'data/linux',
    }

    query = CVEQuery(config)

    # 测试查询 CVE
    cve_id = "CVE-2024-26581"
    print(f"\n查询 CVE: {cve_id}")

    cve_info = query.query_cve(cve_id)

    if cve_info:
        print(f"\n✅ CVE 查询成功!")
        print(f"CVE ID: {cve_info['id']}")
        print(f"描述: {cve_info.get('description', '')[:200]}...")
        print(f"严重程度: {cve_info.get('severity', 'UNKNOWN')}")
        print(f"发布日期: {cve_info.get('published', 'N/A')}")
        print(f"参考链接数量: {len(cve_info.get('references', []))}")
    else:
        print("\n❌ CVE 查询失败")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_cve_query()
