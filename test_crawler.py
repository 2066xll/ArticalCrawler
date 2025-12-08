#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import shutil
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 测试用例配置
TEST_CASES = [
    {
        'id': 'TC001',
        'name': '基本爬取功能测试',
        'command': 'python3 article_crawler.py https://www.22biqu.com/biqu42484/21341278.html -f md',
        'expected_files': 1,
        'description': '验证脚本能够正确爬取单个章节'
    },
    {
        'id': 'TC002',
        'name': '下一章爬取功能测试',
        'command': 'python3 article_crawler.py https://www.22biqu.com/biqu42484/21341278.html -n 1 -f md',
        'expected_files': 2,
        'description': '验证脚本能够正确爬取当前章节和下一章'
    },
    {
        'id': 'TC003',
        'name': '_2.html格式章节测试',
        'command': 'python3 article_crawler.py https://www.22biqu.com/biqu42484/21341278_2.html -n 1 -f md',
        'expected_files': 2,
        'description': '验证脚本能够正确处理_2.html格式的章节'
    },
    {
        'id': 'TC004',
        'name': '不连续章节编码测试',
        'command': 'python3 article_crawler.py https://www.22biqu.com/biqu42484/21341292_2.html -n 1 -f md',
        'expected_files': 2,
        'description': '验证脚本能够正确处理章节URL数字编码不连续的情况'
    },
    {
        'id': 'TC005',
        'name': '连续爬取多个章节测试',
        'command': 'python3 article_crawler.py https://www.22biqu.com/biqu42484/21341278.html -n 2 -f md',
        'expected_files': 3,
        'description': '验证脚本能够连续爬取多个章节'
    }
]

# 输出目录
OUTPUT_DIR = './output'


def clear_output_dir():
    """清理输出目录"""
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"已清理输出目录: {OUTPUT_DIR}")


def get_output_file_count():
    """获取输出目录中的文件数量"""
    if not os.path.exists(OUTPUT_DIR):
        return 0
    return len([f for f in os.listdir(OUTPUT_DIR) if os.path.isfile(os.path.join(OUTPUT_DIR, f))])


def run_test_case(test_case):
    """执行单个测试用例"""
    logger.info(f"开始执行测试用例: {test_case['id']} - {test_case['name']}")
    logger.info(f"测试命令: {test_case['command']}")
    
    # 清理输出目录
    clear_output_dir()
    
    # 执行命令
    result = subprocess.run(test_case['command'], shell=True, capture_output=True, text=True)
    
    # 获取输出文件数量
    file_count = get_output_file_count()
    
    # 验证结果
    passed = file_count == test_case['expected_files']
    
    # 记录结果
    test_result = {
        'test_case': test_case,
        'passed': passed,
        'return_code': result.returncode,
        'stdout': result.stdout,
        'stderr': result.stderr,
        'file_count': file_count,
        'expected_count': test_case['expected_files']
    }
    
    if passed:
        logger.info(f"测试用例通过: {test_case['id']} - {test_case['name']}")
        logger.info(f"输出文件数量: {file_count} (预期: {test_case['expected_files']})")
    else:
        logger.error(f"测试用例失败: {test_case['id']} - {test_case['name']}")
        logger.error(f"输出文件数量: {file_count} (预期: {test_case['expected_files']})")
        logger.error(f"命令返回码: {result.returncode}")
        logger.error(f"标准输出: {result.stdout}")
        logger.error(f"标准错误: {result.stderr}")
    
    return test_result


def generate_test_report(test_results):
    """生成测试报告"""
    logger.info("\n" + "="*50)
    logger.info("测试报告")
    logger.info("="*50)
    
    # 统计结果
    total = len(test_results)
    passed = sum(1 for r in test_results if r['passed'])
    failed = total - passed
    pass_rate = (passed / total) * 100 if total > 0 else 0
    
    logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"测试用例总数: {total}")
    logger.info(f"通过数量: {passed}")
    logger.info(f"失败数量: {failed}")
    logger.info(f"通过率: {pass_rate:.2f}%")
    
    logger.info("\n" + "-"*50)
    logger.info("测试用例执行结果")
    logger.info("-"*50)
    
    for result in test_results:
        status = "通过" if result['passed'] else "失败"
        logger.info(f"{result['test_case']['id']} - {result['test_case']['name']}: {status}")
        logger.info(f"  预期文件数: {result['expected_count']}, 实际文件数: {result['file_count']}")
        if not result['passed']:
            logger.info(f"  命令返回码: {result['return_code']}")
    
    logger.info("\n" + "="*50)
    
    # 生成详细报告文件
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*50 + "\n")
        f.write("测试报告\n")
        f.write("="*50 + "\n\n")
        
        f.write(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"测试用例总数: {total}\n")
        f.write(f"通过数量: {passed}\n")
        f.write(f"失败数量: {failed}\n")
        f.write(f"通过率: {pass_rate:.2f}%\n\n")
        
        f.write("-"*50 + "\n")
        f.write("测试用例执行结果\n")
        f.write("-"*50 + "\n\n")
        
        for result in test_results:
            f.write(f"测试用例ID: {result['test_case']['id']}\n")
            f.write(f"测试名称: {result['test_case']['name']}\n")
            f.write(f"测试描述: {result['test_case']['description']}\n")
            f.write(f"测试命令: {result['test_case']['command']}\n")
            f.write(f"预期文件数: {result['expected_count']}\n")
            f.write(f"实际文件数: {result['file_count']}\n")
            f.write(f"测试结果: {'通过' if result['passed'] else '失败'}\n")
            f.write(f"命令返回码: {result['return_code']}\n")
            f.write(f"标准输出: {result['stdout']}\n")
            f.write(f"标准错误: {result['stderr']}\n")
            f.write("\n" + "-"*30 + "\n\n")
    
    logger.info(f"测试报告已生成: {report_file}")


def main():
    """主函数"""
    logger.info("开始执行测试套件")
    
    # 执行所有测试用例
    test_results = []
    for test_case in TEST_CASES:
        result = run_test_case(test_case)
        test_results.append(result)
    
    # 生成测试报告
    generate_test_report(test_results)
    
    # 保留输出目录，便于查看爬取结果
    logger.info(f"测试结果已保存在目录: {OUTPUT_DIR}")
    logger.info("测试套件执行完毕")

if __name__ == '__main__':
    main()
