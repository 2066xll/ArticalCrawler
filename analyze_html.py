#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from bs4 import BeautifulSoup

# 目标URL
url = 'https://www.22biqu.com/biqu42484/21341278.html'

# 请求头
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 发送请求
try:
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    
    # 解析HTML
    soup = BeautifulSoup(response.text, 'lxml')
    
    print('=== 网页结构分析 ===')
    
    # 分析标题
    print('\n1. 标题分析:')
    print('title标签:', soup.title.get_text())
    
    # 分析h1标签
    print('\n2. h1标签:')
    for h1 in soup.find_all('h1'):
        print(f'内容: {h1.get_text()}')
        print(f'属性: {h1.attrs}')
    
    # 分析h2标签
    print('\n3. h2标签:')
    for h2 in soup.find_all('h2'):
        print(f'内容: {h2.get_text()}')
        print(f'属性: {h2.attrs}')
    
    # 分析正文内容
    print('\n4. 正文内容容器:')
    content_containers = ['#content', '.content', '.chapter-content', '.read-content']
    for selector in content_containers:
        container = soup.select_one(selector)
        if container:
            print(f'找到容器: {selector}')
            print(f'容器类型: {container.name}')
            print(f'容器类名: {container.get("class", "无")}')
            break
    else:
        print('未找到明显的正文容器')
    
    # 分析id为content的元素
    print('\n5. id="content"的元素:')
    content = soup.find(id='content')
    if content:
        print(f'类型: {content.name}')
        print(f'前100个字符: {content.get_text()[:100]}...')
    
    print('\n=== 分析完成 ===')
    
except Exception as e:
    print(f'分析出错: {e}')
