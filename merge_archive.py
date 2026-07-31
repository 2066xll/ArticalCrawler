#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
归档文件夹文件合并程序
将归档文件夹下的所有章节文件按章节顺序合并成一个文件
"""

import os
import re
import sys

def get_chapter_number(filename):
    """
    从文件名中提取章节号
    支持多种文件名格式：
    - 00691_第六百九十一章 学府之变.txt
    - 第一千零一章 灵相宫.txt
    """
    # 首先尝试从数字前缀提取（如00691_）
    prefix_match = re.match(r'^(\d+)_', filename)
    if prefix_match:
        return int(prefix_match.group(1))
    
    # 尝试从章节标题中提取（如第六百九十一章、第123章）
    chapter_match = re.search(r'第([\d一二三四五六七八九十百千万两零]+)[章节回]', filename)
    if chapter_match:
        try:
            # 引入项目已实现的中文数字转换模块
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from article_crawler import chinese_to_arabic
            return chinese_to_arabic(chapter_match.group(1))
        except Exception:
            pass
            
    # 阿拉伯数字兜底提取
    arabic_match = re.search(r'第(\d+)章', filename)
    if arabic_match:
        return int(arabic_match.group(1))
    
    # 如果都匹配不到，返回0
    return 0

def merge_archive_files(archive_dir, output_file):
    """
    合并归档文件夹下的所有文件
    
    参数：
        archive_dir: 归档文件夹路径
        output_file: 输出文件路径
    """
    # 检查归档文件夹是否存在
    if not os.path.exists(archive_dir):
        print(f"错误：归档文件夹 '{archive_dir}' 不存在")
        return False
    
    # 获取归档文件夹下的所有txt文件
    all_files = [f for f in os.listdir(archive_dir) if f.endswith('.txt')]
    if not all_files:
        print(f"错误：归档文件夹 '{archive_dir}' 中没有txt文件")
        return False
    
    # 按章节号排序
    sorted_files = sorted(all_files, key=lambda f: get_chapter_number(f))
    
    # 合并文件
    total_chapters = len(sorted_files)
    print(f"开始合并 {total_chapters} 个章节文件...")
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for i, filename in enumerate(sorted_files):
            file_path = os.path.join(archive_dir, filename)
            print(f"合并第 {i+1}/{total_chapters} 章：{filename}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as in_f:
                    # 读取文件内容
                    content = in_f.read()
                    # 写入输出文件
                    out_f.write(content)
                    # 在章节之间添加分隔符
                    if i < total_chapters - 1:
                        out_f.write('\n\n')
            except Exception as e:
                print(f"错误：读取文件 '{filename}' 时出错 - {e}")
                return False
    
    print(f"合并完成！输出文件：{output_file}")
    print(f"共合并 {total_chapters} 个章节")
    return True

def main():
    """
    主函数
    """
    # 默认参数
    archive_dir = './归档'
    output_file = './合并后的文章.txt'
    
    # 处理命令行参数
    if len(sys.argv) > 1:
        archive_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # 调用合并函数
    success = merge_archive_files(archive_dir, output_file)
    if success:
        print("\n✓ 合并成功！")
        return 0
    else:
        print("\n✗ 合并失败！")
        return 1

if __name__ == '__main__':
    sys.exit(main())
