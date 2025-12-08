#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, '/Users/sunrize/Documents/文章爬取')

# 导入article_crawler模块
import article_crawler

# 设置日志级别为DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# 测试不同URL格式的下一章链接提取
test_urls = [
    'https://www.22biqu.com/biqu42484/21341278.html',
    'https://www.22biqu.com/biqu42484/21341278_2.html',
    'https://www.22biqu.com/biqu42484/21341279.html',
    'https://www.22biqu.com/biqu42484/21341292_2.html'
]

# 简单的HTML模板
test_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>测试</title>
</head>
<body>
    <div id="content">
        测试内容
    </div>
</body>
</html>
'''

print("测试下一章链接提取:")
print("=" * 50)

for url in test_urls:
    print(f"\n原URL: {url}")
    result = article_crawler.parse_article(test_html, url)
    print(f"下一章链接: {result['next_chapter_url']}")
    print(f"期望链接: {url.replace('_2.html', '.html').replace('.html', '_2.html') if '_' not in url else url.replace('_2.html', str(int(url.split('_2.html')[0].split('/')[-1]) + 1) + '.html')}")
    print("-" * 30)
