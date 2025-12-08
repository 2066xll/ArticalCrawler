#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import re
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='文章爬取工具')
    parser.add_argument('url', help='要爬取的文章链接')
    parser.add_argument('-f', '--format', choices=['txt', 'md'], default='txt', help='输出格式，默认txt')
    parser.add_argument('-o', '--output-dir', default='./output', help='输出目录，默认当前目录下的output文件夹')
    parser.add_argument('-n', '--chapters', type=int, default=1, help='要爬取的章节数量，默认1表示只获取当前章节，2表示当前章节+下一章，以此类推')
    parser.add_argument('-p', '--prev-chapters', type=int, default=0, help='要向前爬取的章节数量，默认0表示不爬取上一章')
    return parser.parse_args()


def fetch_page(url):
    """获取网页内容"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # 检查请求是否成功
        response.encoding = response.apparent_encoding  # 自动检测编码
        return response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"获取网页失败: {e}")
        raise


def parse_article(html_content, url):
    """解析文章内容"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 提取文章标题
    title = ''
    # 优化标题提取逻辑，优先选择带有title类的h1标签
    title_selectors = [
        'h1.title',  # 优先选择带有title类的h1标签
        'h2.title', 
        '.article-title', 
        '.title',
        'h1',        # 然后选择普通h1标签
        'title'      # 最后从title标签提取
    ]
    
    for selector in title_selectors:
        elements = soup.select(selector)
        if elements:
            title = elements[0].get_text(strip=True)
            # 如果是从title标签提取的，可能需要进一步处理
            if selector == 'title':
                # 处理小说网站title格式，如"第1575章 是吗_一剑独尊_笔趣阁"
                if '_' in title:
                    title = title.split('_')[0]
            break
    
    # 提取文章正文
    content = ''
    # 增强正文选择器，添加小说网站常用的选择器
    content_selectors = [
        '#content',  # 笔趣阁等小说网站常用的id
        '.article-content', '.content', '.post-content', '.article-body',
        '.main-content', '.entry-content', '.article-text',
        '.chapter-content', '.read-content', '.text'  # 小说网站常用的正文类名
    ]
    
    for selector in content_selectors:
        elements = soup.select(selector)
        if elements:
            # 清理正文内容 - 只清理广告和冗余元素，保留原文结构
            for tag in elements[0](['script', 'style', 'noscript', 'iframe', 'embed', 'div.ad', 'div.ads', 'div.advertisement', '.chapter-nav', '.read-nav']):
                tag.decompose()
            
            # 获取div内的所有文本节点，保留段落格式
            paragraphs = []
            
            # 处理小说网站常见的正文格式：直接在div内用换行分隔段落
            # 遍历div的所有子节点
            for child in elements[0].contents:
                if child.name is None:  # 文本节点
                    text = child.strip()
                    if text:
                        paragraphs.append(text)
                elif child.name in ['p', 'div', 'br']:  # 段落相关标签
                    text = child.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
                
            # 将段落用两个换行连接
            if paragraphs:
                content = '\n\n'.join(paragraphs)
            else:
                # 备用方案：直接获取文本并处理
                raw_content = elements[0].get_text()
                # 清理首尾空白
                content = raw_content.strip()
                # 将连续的空白字符替换为单个空格，但保留换行
                content = re.sub(r'(?![\n])\s+', ' ', content)
                # 将多个换行替换为两个换行
                content = re.sub(r'\n+', '\n\n', content)
            break
    
    # 如果没有找到正文，尝试提取所有p标签
    if not content:
        paragraphs = soup.find_all('p')
        if paragraphs:
            content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    
    # 提取发布时间
    publish_time = ''
    time_selectors = [
        '.publish-time', '.post-time', '.article-time', '.time',
        '.date', '[datetime]', '.updated', '.entry-date'
    ]
    
    for selector in time_selectors:
        elements = soup.select(selector)
        if elements:
            if elements[0].has_attr('datetime'):
                publish_time = elements[0]['datetime']
            else:
                publish_time = elements[0].get_text(strip=True)
            break
    
    # 提取作者
    author = ''
    author_selectors = [
        '.author', '.post-author', '.article-author', '.byline',
        '.writer', '.source', '.by-author'
    ]
    
    for selector in author_selectors:
        elements = soup.select(selector)
        if elements:
            author = elements[0].get_text(strip=True)
            break
    
    # 提取下一章链接
    next_chapter_url = ''
    
    # 增强针对笔趣阁的下一章链接提取
    # 1. 优先查找笔趣阁常见的下一章选择器
    biquge_selectors = [
        # 笔趣阁特定的选择器
        '.chapter-control .next a',      # 笔趣阁常见的章节控制区
        '.chapter-bottom .next a',       # 章节底部导航
        '.content_read .page_chapter a.next',  # 内容阅读区导航
        '.page_chapter a.next',          # 章节导航
        '#next_url a',                   # 下一章链接
        '.novel-content .next-chapter a', # 小说内容区下一章
        '.chapter-nav a:last-child',      # 章节导航的最后一个链接
        '.chapter-nav a:nth-last-child(2)', # 章节导航的倒数第二个链接
        
        # 通用下一章选择器
        '.next-chapter a',
        '.next a',
        '.chapter-next a',
        '.nextpage a',
        '.pager-next a',
        '.chapter-nav a',
        '#next a',
        '.j_chapterNext a',
        'a.next-chapter',
        'a.next',
        'a.chapter-next',
        'a.nextpage',
        'a.pager-next',
        'a#next',
        'a.j_chapterNext',
    ]
    
    for selector in biquge_selectors:
        try:
            next_link = soup.select_one(selector)
            if next_link and next_link.has_attr('href'):
                next_chapter_url = next_link['href']
                # 如果是相对链接，转换为绝对链接
                if not next_chapter_url.startswith('http'):
                    from urllib.parse import urljoin
                    next_chapter_url = urljoin(url, next_chapter_url)
                logger.info(f"通过选择器 {selector} 找到下一章链接: {next_chapter_url}")
                break
        except Exception as e:
            logger.debug(f"尝试选择器 {selector} 失败: {e}")
    
    # 2. 如果没有找到，尝试使用最新的:-soup-contains选择器
    if not next_chapter_url:
        contains_selectors = [
            'a:-soup-contains(下一章)',
            'a:-soup-contains(下节)',
            'a:-soup-contains(Next)',
            'a:-soup-contains(NEXT)',
            'a:-soup-contains(next)',
            'a:-soup-contains(下一页)',
            'a:-soup-contains(继续阅读)',
            'a:-soup-contains(下部分)',
            'a:-soup-contains(下章)',
            'a:-soup-contains(下一篇)'
        ]
        
        for selector in contains_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.has_attr('href'):
                    next_chapter_url = next_link['href']
                    # 如果是相对链接，转换为绝对链接
                    if not next_chapter_url.startswith('http'):
                        from urllib.parse import urljoin
                        next_chapter_url = urljoin(url, next_chapter_url)
                    logger.info(f"通过文本选择器 {selector} 找到下一章链接: {next_chapter_url}")
                    break
            except Exception as e:
                logger.debug(f"尝试文本选择器 {selector} 失败: {e}")
    
    # 3. 如果没有找到，尝试查找包含下一章文本的所有a标签
    if not next_chapter_url:
        try:
            all_links = soup.find_all('a')
            logger.debug(f"找到 {len(all_links)} 个a标签")
            for link in all_links:
                link_text = link.get_text(strip=True)
                if any(keyword in link_text for keyword in ['下一章', '下节', 'Next', 'NEXT', 'next', '下一页', '继续阅读', '下部分', '下章', '下一篇']):
                    if link.has_attr('href'):
                        next_chapter_url = link['href']
                        # 如果是相对链接，转换为绝对链接
                        if not next_chapter_url.startswith('http'):
                            from urllib.parse import urljoin
                            next_chapter_url = urljoin(url, next_chapter_url)
                        logger.info(f"通过遍历a标签找到下一章链接: {next_chapter_url}")
                        break
        except Exception as e:
            logger.debug(f"尝试查找包含文本的链接失败: {e}")
    
    # 4. 如果没有找到，尝试查找所有href属性包含特定模式的链接
    if not next_chapter_url:
        try:
            all_links = soup.find_all('a', href=True)
            # 查找所有符合章节链接格式的链接
            chapter_links = []
            current_url_num = None
            
            # 提取当前URL的数字部分
            current_match = re.search(r'(\d+)', url)
            if current_match:
                current_url_num = int(current_match.group(1))
            
            for link in all_links:
                href = link['href']
                match = re.search(r'(\d+)(_2)?\.html$', href)
                if match:
                    from urllib.parse import urljoin
                    full_url = urljoin(url, href)
                    # 排除当前链接
                    if full_url != url:
                        # 提取链接中的数字部分
                        link_num = int(match.group(1))
                        chapter_links.append({
                            'url': full_url,
                            'num': link_num,
                            'href': href,
                            'is_second_part': '_2' in href
                        })
            
            # 如果找到了多个章节链接，选择最可能的下一章
            if chapter_links:
                # 按数字大小排序
                chapter_links.sort(key=lambda x: x['num'])
                
                # 尝试找到大于当前URL数字的最小数字
                next_link = None
                for link in chapter_links:
                    if current_url_num and link['num'] > current_url_num:
                        next_link = link
                        break
                
                # 如果找到了符合条件的链接，使用它
                if next_link:
                    next_chapter_url = next_link['url']
                    logger.info(f"通过href模式匹配找到下一章链接: {next_chapter_url}")
                elif chapter_links:
                    # 如果没有找到更大的数字，选择最后一个链接
                    next_chapter_url = chapter_links[-1]['url']
                    logger.info(f"通过href模式匹配找到下一章链接: {next_chapter_url}")
        except Exception as e:
            logger.debug(f"尝试通过href模式匹配失败: {e}")
    
    # 5. 最后的备选方案：查找页面中的章节导航
    if not next_chapter_url:
        try:
            # 查找页面中的章节列表或导航
            chapter_nav_selectors = [
                '.chapter-list',
                '.chapter-nav',
                '.chapter-control',
                '.page_chapter',
                '#chapter-list',
                '.chapter-content'
            ]
            
            current_chapter_title = title
            
            for selector in chapter_nav_selectors:
                nav_element = soup.select_one(selector)
                if nav_element:
                    # 查找所有链接
                    nav_links = nav_element.find_all('a', href=True)
                    if nav_links:
                        # 遍历所有链接，查找当前章节的下一章
                        found_current = False
                        for i, link in enumerate(nav_links):
                            link_title = link.get_text(strip=True)
                            # 如果找到当前章节的标题，返回下一个链接
                            if current_chapter_title in link_title:
                                found_current = True
                                if i + 1 < len(nav_links):
                                    next_link = nav_links[i + 1]
                                    next_chapter_url = urljoin(url, next_link['href'])
                                    logger.info(f"通过章节导航找到下一章链接: {next_chapter_url}")
                                    break
                        if found_current and next_chapter_url:
                            break
        except Exception as e:
            logger.debug(f"尝试通过章节导航查找失败: {e}")
    
    # 最终日志记录
    if next_chapter_url:
        logger.info(f"最终下一章链接: {next_chapter_url}")
    else:
        logger.warning(f"未找到下一章链接")
    
    # 提取上一章链接
    prev_chapter_url = ''
    
    # 增强针对笔趣阁的上一章链接提取
    # 1. 优先查找笔趣阁常见的上一章选择器
    biquge_prev_selectors = [
        # 笔趣阁特定的选择器
        '.chapter-control .prev a',      # 笔趣阁常见的章节控制区
        '.chapter-bottom .prev a',       # 章节底部导航
        '.content_read .page_chapter a.prev',  # 内容阅读区导航
        '.page_chapter a.prev',          # 章节导航
        '#prev_url a',                   # 上一章链接
        '.novel-content .prev-chapter a', # 小说内容区上一章
        '.chapter-nav a:first-child',      # 章节导航的第一个链接
        '.chapter-nav a:nth-child(2)',     # 章节导航的第二个链接
        
        # 通用上一章选择器
        '.prev-chapter a',
        '.prev a',
        '.previous a',
        '.chapter-prev a',
        '.prevpage a',
        '.pager-prev a',
        '#prev a',
        '.j_chapterPrev a',
        'a.prev-chapter',
        'a.prev',
        'a.previous',
        'a.chapter-prev',
        'a.prevpage',
        'a.pager-prev',
        'a#prev',
        'a.j_chapterPrev',
    ]
    
    for selector in biquge_prev_selectors:
        try:
            prev_link = soup.select_one(selector)
            if prev_link and prev_link.has_attr('href'):
                prev_chapter_url = prev_link['href']
                # 如果是相对链接，转换为绝对链接
                if not prev_chapter_url.startswith('http'):
                    from urllib.parse import urljoin
                    prev_chapter_url = urljoin(url, prev_chapter_url)
                logger.info(f"通过选择器 {selector} 找到上一章链接: {prev_chapter_url}")
                break
        except Exception as e:
            logger.debug(f"尝试选择器 {selector} 失败: {e}")
    
    # 2. 如果没有找到，尝试使用最新的:-soup-contains选择器
    if not prev_chapter_url:
        contains_prev_selectors = [
            'a:-soup-contains(上一章)',
            'a:-soup-contains(上节)',
            'a:-soup-contains(Previous)',
            'a:-soup-contains(PREVIOUS)',
            'a:-soup-contains(previous)',
            'a:-soup-contains(上一页)',
            'a:-soup-contains(上部分)',
            'a:-soup-contains(上章)',
            'a:-soup-contains(上一篇)'
        ]
        
        for selector in contains_prev_selectors:
            try:
                prev_link = soup.select_one(selector)
                if prev_link and prev_link.has_attr('href'):
                    prev_chapter_url = prev_link['href']
                    # 如果是相对链接，转换为绝对链接
                    if not prev_chapter_url.startswith('http'):
                        from urllib.parse import urljoin
                        prev_chapter_url = urljoin(url, prev_chapter_url)
                    logger.info(f"通过文本选择器 {selector} 找到上一章链接: {prev_chapter_url}")
                    break
            except Exception as e:
                logger.debug(f"尝试文本选择器 {selector} 失败: {e}")
    
    # 3. 如果没有找到，尝试查找包含上一章文本的所有a标签
    if not prev_chapter_url:
        try:
            all_links = soup.find_all('a')
            logger.debug(f"找到 {len(all_links)} 个a标签")
            for link in all_links:
                link_text = link.get_text(strip=True)
                if any(keyword in link_text for keyword in ['上一章', '上节', 'Previous', 'PREVIOUS', 'previous', '上一页', '上部分', '上章', '上一篇']):
                    if link.has_attr('href'):
                        prev_chapter_url = link['href']
                        # 如果是相对链接，转换为绝对链接
                        if not prev_chapter_url.startswith('http'):
                            from urllib.parse import urljoin
                            prev_chapter_url = urljoin(url, prev_chapter_url)
                        logger.info(f"通过遍历a标签找到上一章链接: {prev_chapter_url}")
                        break
        except Exception as e:
            logger.debug(f"尝试查找包含文本的链接失败: {e}")
    
    # 4. 如果没有找到，尝试查找所有href属性包含特定模式的链接
    if not prev_chapter_url:
        try:
            all_links = soup.find_all('a', href=True)
            # 查找所有符合章节链接格式的链接
            chapter_links = []
            current_url_num = None
            
            # 提取当前URL的数字部分
            current_match = re.search(r'(\d+)', url)
            if current_match:
                current_url_num = int(current_match.group(1))
            
            for link in all_links:
                href = link['href']
                match = re.search(r'(\d+)(_2)?\.html$', href)
                if match:
                    from urllib.parse import urljoin
                    full_url = urljoin(url, href)
                    # 排除当前链接
                    if full_url != url:
                        # 提取链接中的数字部分
                        link_num = int(match.group(1))
                        chapter_links.append({
                            'url': full_url,
                            'num': link_num,
                            'href': href,
                            'is_second_part': '_2' in href
                        })
            
            # 如果找到了多个章节链接，选择最可能的上一章
            if chapter_links:
                # 按数字大小排序
                chapter_links.sort(key=lambda x: x['num'], reverse=True)
                
                # 尝试找到小于当前URL数字的最大数字
                prev_link = None
                for link in chapter_links:
                    if current_url_num and link['num'] < current_url_num:
                        prev_link = link
                        break
                
                # 如果找到了符合条件的链接，使用它
                if prev_link:
                    prev_chapter_url = prev_link['url']
                    logger.info(f"通过href模式匹配找到上一章链接: {prev_chapter_url}")
                elif chapter_links:
                    # 如果没有找到更小的数字，选择第一个链接
                    prev_chapter_url = chapter_links[-1]['url']
                    logger.info(f"通过href模式匹配找到上一章链接: {prev_chapter_url}")
        except Exception as e:
            logger.debug(f"尝试通过href模式匹配失败: {e}")
    
    # 5. 最后的备选方案：查找页面中的章节导航
    if not prev_chapter_url:
        try:
            # 查找页面中的章节列表或导航
            chapter_nav_selectors = [
                '.chapter-list',
                '.chapter-nav',
                '.chapter-control',
                '.page_chapter',
                '#chapter-list',
                '.chapter-content'
            ]
            
            current_chapter_title = title
            
            for selector in chapter_nav_selectors:
                nav_element = soup.select_one(selector)
                if nav_element:
                    # 查找所有链接
                    nav_links = nav_element.find_all('a', href=True)
                    if nav_links:
                        # 遍历所有链接，查找当前章节的上一章
                        found_current = False
                        for i, link in enumerate(nav_links):
                            link_title = link.get_text(strip=True)
                            # 如果找到当前章节的标题，返回前一个链接
                            if current_chapter_title in link_title:
                                found_current = True
                                if i - 1 >= 0:
                                    prev_link = nav_links[i - 1]
                                    prev_chapter_url = urljoin(url, prev_link['href'])
                                    logger.info(f"通过章节导航找到上一章链接: {prev_chapter_url}")
                                    break
                        if found_current and prev_chapter_url:
                            break
        except Exception as e:
            logger.debug(f"尝试通过章节导航查找失败: {e}")
    
    # 最终日志记录
    if prev_chapter_url:
        logger.info(f"最终上一章链接: {prev_chapter_url}")
    else:
        logger.warning(f"未找到上一章链接")
    
    return {
        'title': title,
        'content': content,
        'publish_time': publish_time,
        'author': author,
        'url': url,
        'next_chapter_url': next_chapter_url,
        'prev_chapter_url': prev_chapter_url
    }


def sanitize_filename(filename):
    """生成安全的文件名"""
    # 移除特殊字符
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # 移除多余的空格
    filename = re.sub(r'\s+', ' ', filename)
    # 限制文件名长度
    if len(filename) > 100:
        filename = filename[:100]
    return filename.strip()


def write_article(article, output_dir, output_format, append=False, existing_file=None):
    """将文章内容写入文件"""
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 如果是追加内容，使用现有文件
    if append and existing_file:
        file_path = existing_file
        filename = os.path.basename(file_path)
    else:
        # 生成文件名
        if article['title']:
            base_filename = sanitize_filename(article['title'])
        else:
            # 如果没有标题，使用当前时间戳
            base_filename = f"article_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 处理文件名重复问题
        filename = base_filename
        file_path = os.path.join(output_dir, f"{filename}.{output_format}")
        
        # 如果文件已存在，添加序号
        counter = 1
        while os.path.exists(file_path):
            filename = f"{base_filename}_{counter}"
            file_path = os.path.join(output_dir, f"{filename}.{output_format}")
            counter += 1
        
        # 添加文件扩展名
        filename += f".{output_format}"
    
    # 生成文件内容
    if output_format == 'md':
        if append:
            # Markdown格式，追加内容
            content = f"\n\n---\n\n**原文链接**: {article['url']}\n\n{article['content']}"
        else:
            # Markdown格式，新文件
            content = f"# {article['title']}\n\n"
            if article['author']:
                content += f"**作者**: {article['author']}\n\n"
            if article['publish_time']:
                content += f"**发布时间**: {article['publish_time']}\n\n"
            content += f"**原文链接**: {article['url']}\n\n"
            content += "---\n\n"
            content += article['content']
    else:
        if append:
            # TXT格式，追加内容
            content = f"\n\n{article['content']}"
        else:
            # TXT格式，新文件
            content = f"{article['title']}\n\n"
            if article['author']:
                content += f"作者: {article['author']}\n"
            if article['publish_time']:
                content += f"发布时间: {article['publish_time']}\n"
            content += f"原文链接: {article['url']}\n\n"
            content += "=" * 50 + "\n\n"
            content += article['content']
    
    # 写入文件
    try:
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        if append:
            logger.info(f"文章内容已追加到: {file_path}")
        else:
            logger.info(f"文章已保存到: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"写入文件失败: {e}")
        raise


def main():
    """主函数"""
    args = parse_args()
    
    current_url = args.url
    # 总共要爬取的章节数量，直接使用用户输入的章节数
    chapters_to_fetch = args.chapters  # 符合用户期望：输入3就爬取3章
    prev_chapters_to_fetch = args.prev_chapters  # 要向前爬取的章节数
    
    # 章节跟踪
    current_chapter_title = None
    current_file_path = None
    actual_chapters_fetched = 0  # 实际获取的完整章节数
    
    # 1. 首先爬取当前章节
    logger.info(f"开始爬取当前章节: {current_url}")
    try:
        # 获取网页内容
        html_content = fetch_page(current_url)
        logger.info("网页获取成功")
        
        # 解析文章内容
        article = parse_article(html_content, current_url)
        logger.info(f"文章解析成功，标题: {article['title']}")
        
        # 保存当前章节
        current_file_path = write_article(article, args.output_dir, args.format)
        current_chapter_title = article['title']
        actual_chapters_fetched += 1  # 只有新章节才增加计数
        
        # 保存当前章节的信息，用于后续爬取
        current_article = article
    except Exception as e:
        logger.error(f"爬取当前章节失败: {e}")
        logger.info("爬取任务结束")
        return
    
    # 2. 向前爬取上一章
    if prev_chapters_to_fetch > 0:
        logger.info(f"开始向前爬取 {prev_chapters_to_fetch} 章")
        prev_url = current_article['prev_chapter_url']
        prev_chapters_fetched = 0
        prev_chapter_title = current_chapter_title
        prev_file_path = None
        
        while prev_chapters_fetched < prev_chapters_to_fetch and prev_url:
            logger.info(f"开始爬取上一章 {prev_chapters_fetched + 1}/{prev_chapters_to_fetch}: {prev_url}")
            
            try:
                # 获取网页内容
                html_content = fetch_page(prev_url)
                logger.info("网页获取成功")
                
                # 解析文章内容
                article = parse_article(html_content, prev_url)
                logger.info(f"文章解析成功，标题: {article['title']}")
                
                # 检查是否是同一章节的不同部分
                is_same_chapter = False
                if prev_chapter_title == article['title'] and prev_file_path:
                    # 同一章节的不同部分，追加内容
                    is_same_chapter = True
                    write_article(article, args.output_dir, args.format, append=True, existing_file=prev_file_path)
                else:
                    # 新的章节，创建新文件
                    prev_file_path = write_article(article, args.output_dir, args.format)
                    prev_chapter_title = article['title']
                    prev_chapters_fetched += 1  # 只有新章节才增加计数
                
                # 如果还有章节要爬取，获取上一章链接
                if prev_chapters_fetched < prev_chapters_to_fetch:
                    if article['prev_chapter_url']:
                        logger.info(f"获取上一章链接: {article['prev_chapter_url']}")
                        prev_url = article['prev_chapter_url']
                    else:
                        logger.warning(f"未找到上一章链接，向前爬取结束")
                        break
                
            except Exception as e:
                logger.error(f"向前爬取失败: {e}")
                break
    
    # 3. 向后爬取剩余章节
    if chapters_to_fetch > 1:  # 已经爬取了当前章节，所以只需要再爬取 chapters_to_fetch - 1 章
        logger.info(f"开始向后爬取 {chapters_to_fetch - 1} 章")
        next_url = current_article['next_chapter_url']
        next_chapters_fetched = 0
        next_chapter_title = current_chapter_title
        next_file_path = current_file_path
        
        while next_chapters_fetched < chapters_to_fetch - 1 and next_url:
            logger.info(f"开始爬取下一章 {next_chapters_fetched + 1}/{chapters_to_fetch - 1}: {next_url}")
            
            try:
                # 获取网页内容
                html_content = fetch_page(next_url)
                logger.info("网页获取成功")
                
                # 解析文章内容
                article = parse_article(html_content, next_url)
                logger.info(f"文章解析成功，标题: {article['title']}")
                
                # 检查是否是同一章节的不同部分
                is_same_chapter = False
                if next_chapter_title == article['title'] and next_file_path:
                    # 同一章节的不同部分，追加内容
                    is_same_chapter = True
                    write_article(article, args.output_dir, args.format, append=True, existing_file=next_file_path)
                else:
                    # 新的章节，创建新文件
                    next_file_path = write_article(article, args.output_dir, args.format)
                    next_chapter_title = article['title']
                    next_chapters_fetched += 1  # 只有新章节才增加计数
                
                # 如果还有章节要爬取，获取下一章链接
                if next_chapters_fetched < chapters_to_fetch - 1:
                    if article['next_chapter_url']:
                        logger.info(f"获取下一章链接: {article['next_chapter_url']}")
                        next_url = article['next_chapter_url']
                    else:
                        logger.warning(f"未找到下一章链接，向后爬取结束")
                        break
                
            except Exception as e:
                logger.error(f"向后爬取失败: {e}")
                break
    
    logger.info("爬取任务完成")

if __name__ == '__main__':
    main()