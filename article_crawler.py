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


# 线程本地会话（每个线程独立 Session，避免多线程 Cookie 串扰）
import threading as _threading
_thread_local = _threading.local()

def _get_session():
    """获取当前线程专用的 requests.Session"""
    if not hasattr(_thread_local, 'session'):
        _thread_local.session = requests.Session()
    return _thread_local.session

# 常用 User-Agent 列表
_user_agents = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.2210.91 Safari/537.36'
]


def fetch_page(url):
    """获取网页内容（会话保持 + 动态 Referer + 智能重试）"""
    import random
    import time
    
    # 根据目标 URL 自动生成 Referer（而不是硬编码）
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    
    max_retries = 3
    retry_delay = 5
    disable_compression = False
    
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': random.choice(_user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': referer,
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            if disable_compression:
                headers['Accept-Encoding'] = 'identity'
            
            # 随机延迟（0.1~0.5 秒），平衡防爬与抓取速度
            time.sleep(random.uniform(0.1, 0.5))
            
            response = _get_session().get(url, headers=headers, timeout=20)
            
            # 针对 403/429 使用更长的退避
            if response.status_code in (403, 429):
                wait = retry_delay * (attempt + 2)
                logger.warning(f"收到 {response.status_code}，疑似反爬，{wait}秒后重试...")
                time.sleep(wait)
                continue
            
            response.raise_for_status()
            
            # 改进的编码检测：优先从 meta charset 提取，其次 apparent_encoding，最后 utf-8
            # 这比单纯依赖 apparent_encoding 更准确且更快
            try:
                content_bytes = response.content
            except Exception as dec_err:
                dec_err_str = str(dec_err).lower()
                if isinstance(dec_err, requests.exceptions.ContentDecodingError) or "decompress" in dec_err_str or "zlib" in dec_err_str or "incorrect header check" in dec_err_str:
                    logger.warning(f"读取网页内容解压缩失败 ({dec_err})，url: {url}，将尝试禁用压缩重新请求。")
                    disable_compression = True
                    continue
                raise

            # 先用 ascii/utf-8 尝试解码头部以查找 meta 标签
            header_str = content_bytes[:2048].decode('utf-8', errors='ignore')
            meta_charset = re.search(r'<meta.*?charset=["\']?([a-zA-Z0-9\-_]+)["\']?', header_str, re.IGNORECASE)
            if not meta_charset:
                meta_charset = re.search(r'<meta.*?content=["\'].*?charset=([a-zA-Z0-9\-_]+)["\']?', header_str, re.IGNORECASE)
                
            if meta_charset:
                response.encoding = meta_charset.group(1)
            else:
                response.encoding = response.apparent_encoding or 'utf-8'
                
            return response.text
        except requests.exceptions.RequestException as e:
            err_str = str(e).lower()
            if isinstance(e, requests.exceptions.ContentDecodingError) or "decompress" in err_str or "zlib" in err_str or "incorrect header check" in err_str:
                logger.warning(f"请求网页时解压缩失败 ({e})，url: {url}，将尝试禁用压缩重新请求。")
                disable_compression = True
                continue
                
            logger.error(f"获取网页失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 1.5
            else:
                logger.error(f"多次尝试后仍无法获取网页: {url}")
                raise


def extract_book_title(soup, url):
    """从网页中提取书名"""
    import re
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    
    # 1. 优先从 breadcrumb 或 导航链接匹配目录页链接的 text
    path_parts = [p for p in parsed.path.split('/') if p]
    book_id = None
    if path_parts:
        last_part = path_parts[-1]
        is_chapter = False
        if last_part.endswith(('.html', '.htm', '.shtml')):
            is_chapter = True
        elif last_part.isdigit() and len(path_parts) >= 3:
            is_chapter = True
            
        if is_chapter and len(path_parts) >= 2:
            book_id = path_parts[-2]
        else:
            book_id = path_parts[-1]

    if book_id and book_id not in ('book', 'novel', 'read', 'txt', 'html'):
        for a in soup.find_all('a'):
            href = a.get('href')
            if href and book_id in href:
                text = a.get_text(strip=True)
                if text and not re.search(r'目录|首页|下一章|上一章|下一页|上一页|返回|列表|主页|加入书架|书页', text):
                    clean_text = text.strip()
                    if clean_text and len(clean_text) < 50:
                        return clean_text

    # 2. 尝试从 title 标签匹配
    title_el = soup.title
    if title_el:
        raw_title = title_el.get_text(strip=True)
        # 用常见的分割符进行切分
        for sep in ['_', '-', '–', '|']:
            parts = raw_title.split(sep)
            if len(parts) >= 2:
                for p in parts:
                    p_clean = p.strip()
                    # 排除章节号
                    if re.search(r'第.*?章|第.*?节|第.*?回|第.*?折', p_clean):
                        continue
                    # 排除纯网站广告/版权说明
                    if re.search(r'新?笔趣阁|小说网|书盟|中文网|起点|创世|纵横|晋江|txt下载|pdf下载|epub下载|下载', p_clean):
                        continue
                    # 剔除修饰词
                    p_clean = re.sub(r'最新章节列表|最新章节|最新章节|免费阅读|无弹窗|全文阅读|官网|官方|手机版|在线阅读|阅读|书页|小说', '', p_clean).strip()
                    if p_clean and len(p_clean) < 50:
                        return p_clean

    # 3. 兜底：如果是目录页本身，获取 h1
    h1_el = soup.select_one('h1')
    if h1_el:
        text = h1_el.get_text(strip=True)
        if text and not re.search(r'目录|章节|列表|下一章|上一章|最新章节', text):
            return text

    return "未知书籍"


def parse_article(html_content, url):
    """解析文章内容"""
    soup = BeautifulSoup(html_content, 'lxml')
    
    # 提前全局剔除干扰标签 (极限优化)，减少在提取正文时的干扰
    for tag in soup(['script', 'style', 'noscript', 'iframe', 'embed', 'footer', 'header', 'nav', 'aside', 'form', 'button', 'input']):
        tag.decompose()
    # 剔除常见的干扰CSS类 (如侧边栏、评论区、广告区域)
    for tag in soup.find_all(class_=re.compile(r'comment|sidebar|ad-|ads-|advert|widget|share|qr', re.I)):
        tag.decompose()
    
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
    
    # 特殊处理bqgns.com网站，正文在window.__NUXT__对象中
    if 'bqgns.com' in url:
        # 从HTML中提取window.__NUXT__对象
        nuxt_match = re.search(r'window\.__NUXT__=(.*?);</script>', html_content, re.DOTALL)
        if nuxt_match:
            nuxt_data_str = nuxt_match.group(1)
            try:
                # 1. 简化解析，直接查找正文内容，避免复杂的NUXT数据解析
                # 查找正文选择器
                content_selectors = [
                    '#chaptercontent',  # bqgns.com常用的正文ID
                    '.chapter-content',  # 通用正文类名
                    '.content',          # 通用正文类名
                    '.read-content'      # 阅读内容类名
                ]
                
                for selector in content_selectors:
                    elements = soup.select(selector)
                    if elements:
                        # 清理正文内容
                        for tag in elements[0](['script', 'style', 'noscript', 'iframe', 'embed', 'div.ad', 'div.ads', 'div.advertisement', '.chapter-nav', '.read-nav', '.bottom-navigation']):
                            tag.decompose()
                        
                        # 获取正文内容
                        paragraphs = []
                        for child in elements[0].contents:
                            if child.name is None:  # 文本节点
                                text = child.strip()
                                if text:
                                    paragraphs.append(text)
                            elif child.name in ['p', 'div', 'br']:  # 段落相关标签
                                text = child.get_text(strip=True)
                                if text:
                                    paragraphs.append(text)
                        
                        if paragraphs:
                            content = '\n\n'.join(paragraphs)
                            # 精确移除 bqgns.com 注入的 "go" 水印词（仅匹配独立单词，避免破坏正文）
                            content = re.sub(r'(?<![\u4e00-\u9fff\w])go(?![\u4e00-\u9fff\w])', '', content)
                            break
            except Exception as e:
                logger.error(f"解析bqgns.com的正文内容失败: {e}")
    
    # 如果从NUXT对象中没有提取到内容
    if not content:
        # 1. 优先尝试常见的正文容器选择器
        content_selectors = [
            '#content', '#chaptercontent', '#BookText', '#nr_title', '.article-content', 
            '.content', '.post-content', '.article-body', '.main-content', '.entry-content', 
            '.article-text', '.chapter-content', '.read-content', '.text', 'article', '.main-text'
        ]
        
        main_box = None
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                # 为了防止误命中外层大容器，检查内部文本长度
                if len(elements[0].get_text(strip=True)) > 200:
                    main_box = elements[0]
                    break
                    
        # 2. 备用算法：基于文本密度的通用抽取算法 (适用于未知网站结构)
        # 思路：找到包含最多文本且文本密度最高的 div/section/article 标签
        if not main_box:
            candidates = soup.find_all(['div', 'section', 'article', 'td'])
            max_score = -1
            
            for candidate in candidates:
                text_len = len(candidate.get_text(strip=True))
                # 过滤掉内容太少的块
                if text_len < 300:
                    continue
                # 计算节点深度和直接 a 标签的影响（非正文特征）
                a_tags = candidate.find_all('a')
                a_len = sum(len(a.get_text(strip=True)) for a in a_tags)
                
                # 如果超链接文本占比过高（>30%），很可能是目录或列表，不是正文
                if a_len > 0 and (a_len / text_len) > 0.3:
                    continue
                    
                # 基础分数 = 文本长度
                score = text_len
                # 惩罚：大量空白字符和超链接
                score -= a_len * 2
                
                if score > max_score:
                    max_score = score
                    main_box = candidate
                    
        # 3. 如果找到了大概率的正文容器，提取段落
        if main_box:
            # 清理剩余的干扰元素（在前置清理基础上额外清理）
            for tag in main_box(['div.ad', 'div.ads', 'div.advertisement', '.chapter-nav', '.read-nav', '.bottom-navigation']):
                tag.decompose()
                
            paragraphs = []
            
            # 遍历所有子节点，提取文本和段落
            for child in main_box.contents:
                if child.name is None:  # 文本节点
                    text = child.strip()
                    if text:
                        paragraphs.append(text)
                elif child.name in ['p', 'div', 'br', 'span']:  # 段落相关标签
                    # 对于标签内的文字，如果是包含内部换行的块，也予以打散保留
                    text = child.get_text(strip=True)
                    if text:
                        paragraphs.append(text)
            
            if paragraphs:
                content = '\n\n'.join(paragraphs)
            else:
                raw_content = main_box.get_text()
                content = raw_content.strip()
                content = re.sub(r'(?![\n])\s+', ' ', content)
                content = re.sub(r'\n+', '\n\n', content)
        else:
            # 极限兜底：提取整个页面的所有 p 标签
            paragraphs = soup.find_all('p')
            if paragraphs:
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 5])
    
    # ========== 内容清洗 ==========
    if content:
        # 过滤广告/推广及无用混淆文本
        ad_patterns = [
            r'加入书签',
            r'推荐票',
            r'月票',
            r'打赏',
            r'点击.*?(下载|安装|阅读)',
            r'手机.*?阅读',
            r'app.*?阅读',
            r'扫码.*?(下载|关注)',
            r'公众号',
            r'搜索.*?笔趣',
            r'最新章节',
            r'百度搜索',
            r'本站.*?地址',
            r'收藏本站',
            r'www\.\S+\.(com|net|org|cn)',
            r'https?://\S+',
            r'本章未完，请翻页',
            r'点击下一页继续阅读',
            r'本章已阅读完毕',
            r'请退出转码页面',
            r'最新域名',
            r'最新网址',
            r'为您提供最快的?更新',
            r'网页版章节内容慢',
            r'内容加载失败',
            r'内容丢失',
            r'无防盗.*?(无防盗)?',
            r'无弹窗.*?阅读',
            r'章节错误.*?举报',
            r'记住.*?网址',
            r'顶点小说',
            r'精彩小说',
            r'友情提示',
            r'温馨提示',
            r'公告：',
        ]
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append(line)
                continue
            # 跳过纯广告及混淆行（短于 70 字符且匹配广告模式，防误杀）
            if len(stripped) < 70 and any(re.search(p, stripped, re.IGNORECASE) for p in ad_patterns):
                continue
            cleaned_lines.append(line)
        content = '\n'.join(cleaned_lines)
        
        # 合并被错误分割的段落（单个标点独占一行的情况）
        content = re.sub(r'\n\n([，。！？、；：""\'\'…—）」》】\)\.]{1,3})\n', r'\1\n', content)
        
        # 清理多余空行（3个以上换行合并为2个）
        content = re.sub(r'\n{3,}', '\n\n', content)
    
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
    
    # 特殊处理bqgns.com网站
    if 'bqgns.com' in url:
        try:
            # 查找bqgns.com特定的下一章选择器
            next_link = soup.select_one('.next a[title="下一章"]')
            if not next_link:
                # 备用选择器
                next_link = soup.select_one('.v-bottom-navigation a[href]:contains("下一章")')
            if not next_link:
                # 查找所有包含下一章的链接
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    if '下一章' in link.get_text() or link.get('title') == '下一章':
                        next_link = link
                        break
            
            if next_link and next_link.has_attr('href'):
                next_chapter_url = next_link['href']
                # 如果是相对链接，转换为绝对链接
                if not next_chapter_url.startswith('http'):
                    from urllib.parse import urljoin as _urljoin
                    next_chapter_url = _urljoin(url, next_chapter_url)
                logger.info(f"通过bqgns.com特定选择器找到下一章链接: {next_chapter_url}")
        except Exception as e:
            logger.debug(f"尝试bqgns.com选择器失败: {e}")
    
    # 如果没有找到，使用通用选择器
    if not next_chapter_url:
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
    
    # 移除基于URL数字增减和列表索引的猜测逻辑，仅保留基于明确特征的 DOM 提取，防止错误跨章和死循环
    if next_chapter_url:
        logger.info(f"最终下一章链接: {next_chapter_url}")
    else:
        logger.warning(f"未找到下一章链接")
    
    # 提取上一章链接
    prev_chapter_url = ''
    
    # 特殊处理bqgns.com网站
    if 'bqgns.com' in url:
        try:
            # 查找bqgns.com特定的上一章选择器
            prev_link = soup.select_one('.next a[title="上一章"]')
            if not prev_link:
                # 备用选择器
                prev_link = soup.select_one('.v-bottom-navigation a[href]:contains("上一章")')
            if not prev_link:
                # 查找所有包含上一章的链接
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    if '上一章' in link.get_text() or link.get('title') == '上一章':
                        prev_link = link
                        break
            
            if prev_link and prev_link.has_attr('href'):
                prev_chapter_url = prev_link['href']
                # 如果是相对链接，转换为绝对链接
                if not prev_chapter_url.startswith('http'):
                    from urllib.parse import urljoin
                    prev_chapter_url = urljoin(url, prev_chapter_url)
                logger.info(f"通过bqgns.com特定选择器找到上一章链接: {prev_chapter_url}")
        except Exception as e:
            logger.debug(f"尝试bqgns.com选择器失败: {e}")
    
    # 如果没有找到，使用通用选择器
    if not prev_chapter_url:
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
    
    # 移除基于URL数字增减和列表索引的猜测逻辑，仅保留基于明确特征的 DOM 提取
    
    # 最终日志记录
    if prev_chapter_url:
        logger.info(f"最终上一章链接: {prev_chapter_url}")
    else:
        logger.warning(f"未找到上一章链接")
        
    # 只清理无效锚点（fragment），保留 query 参数（部分网站章节 URL 依赖 query）
    from urllib.parse import urlparse, urlunparse
    def clean_url(u):
        if not u: return u
        parsed = urlparse(u)
        return urlunparse(parsed._replace(fragment=''))  # 只去 fragment，保留 query
    
    next_chapter_url = clean_url(next_chapter_url)
    prev_chapter_url = clean_url(prev_chapter_url)
    
    return {
        'title': title,
        'content': content,
        'publish_time': publish_time,
        'author': author,
        'url': url,
        'next_chapter_url': next_chapter_url,
        'prev_chapter_url': prev_chapter_url
    }


def get_toc_chapters(start_url, direction, count):
    """
    自适应地解析小说目录，并获取目标范围内的所有章节 URL 和标题。
    返回: 包含 (abs_url, chapter_title, toc_index) 元组的列表。
    """
    import re
    from urllib.parse import urlparse, urlunparse, urljoin
    from bs4 import BeautifulSoup
    
    logger.info(f"开始尝试自适应解析目录，起点 URL: {start_url}")
    
    try:
        # 1. 抓取当前章节页面以寻找目录页链接
        html_start = fetch_page(start_url)
        soup_start = BeautifulSoup(html_start, 'lxml')
        
        # 寻找目录页链接
        toc_url = None
        
        # 优先从a标签文本找
        for a in soup_start.find_all('a'):
            href = a.get('href')
            if not href:
                continue
            text = a.get_text(strip=True)
            # 匹配 "目录", "章节列表", "返回目录", "返回书页", "返回书", "书页" 等
            if re.search(r'目录|章节列表|返回目录|返回书页|书页|主页|回目录', text):
                candidate_url = urljoin(start_url, href)
                # 排除一些明显不是的
                if 'javascript' not in href and candidate_url != start_url:
                    toc_url = candidate_url
                    break
        
        # 备选：如果没找到，使用 URL 结构剥离最后一级
        if not toc_url:
            parsed_start = urlparse(start_url)
            path_parts = parsed_start.path.strip('/').split('/')
            if len(path_parts) >= 2:
                parent_path = '/' + '/'.join(path_parts[:-1]) + '/'
                toc_url = urlunparse((parsed_start.scheme, parsed_start.netloc, parent_path, '', '', ''))
                logger.info(f"未找到目录链接，尝试使用URL层级推导目录: {toc_url}")
            else:
                toc_url = start_url # 兜底
                
        if not toc_url or toc_url == start_url:
            logger.warning("未能找到有效的目录 URL，降级到顺序抓取模式")
            return None
            
        logger.info(f"找到目录页 URL: {toc_url}")
        
        current_toc_url = toc_url
        visited_toc_urls = set()
        all_links = []
        parsed_toc = urlparse(toc_url)
        
        max_toc_pages = 100
        toc_pages_fetched = 0
        
        while current_toc_url and current_toc_url not in visited_toc_urls and toc_pages_fetched < max_toc_pages:
            visited_toc_urls.add(current_toc_url)
            toc_pages_fetched += 1
            
            logger.info(f"正在抓取并解析目录页第 {toc_pages_fetched} 页: {current_toc_url}")
            try:
                html_toc = fetch_page(current_toc_url)
            except Exception as e:
                logger.error(f"抓取目录第 {toc_pages_fetched} 页失败 {current_toc_url}: {e}")
                break
                
            soup_toc = BeautifulSoup(html_toc, 'lxml')
            
            # 提取当前目录页中的章节链接
            for a in soup_toc.find_all('a'):
                href = a.get('href')
                if not href or 'javascript' in href:
                    continue
                abs_url = urljoin(current_toc_url, href)
                # 确保是同域链接
                parsed_abs = urlparse(abs_url)
                if parsed_abs.netloc != parsed_toc.netloc:
                    continue
                    
                text = a.get_text(strip=True)
                # 过滤掉过短或过长的非标题文本
                if not text or len(text) > 80:
                    continue
                    
                # 过滤掉返回首页、书架等常见非章节导航链接
                if re.search(r'首页|书架|书页|登录|注册|书库|作者|排行|加入书签|返回|目录', text):
                    continue
                    
                all_links.append((abs_url, text))
                
            # 寻找“下一页”的目录分页链接
            next_toc_url = None
            for a in soup_toc.find_all('a'):
                text = a.get_text(strip=True)
                href = a.get('href')
                if href and 'javascript' not in href and ('下一页' in text or '下页' in text):
                    # 避免在目录页误配到正文翻页链接，确保链接看起来像目录的分页
                    cand_url = urljoin(current_toc_url, href)
                    # 限制和目录 URL 路径一致，或者包含 sort/page 参数等
                    if urlparse(cand_url).path == parsed_toc.path or 'page=' in href or 'sort=' in href:
                        next_toc_url = cand_url
                        break
            
            current_toc_url = next_toc_url
            
        # 对解析到的链接进行过滤和去重
        toc_chapters = []
        seen_urls = set()
        
        # 寻找与当前页 URL 最相似的链接集
        # 提取当前页面的文件名或者路径前缀作为相似特征
        start_path_parts = parsed_toc.path.strip('/').split('/')
        
        for url, title in all_links:
            if url in seen_urls:
                continue
                
            # 判断是否可能是章节链接：
            # 1. 标题含有 章节 标志；或者
            # 2. 标题以数字/中文数字开头；或者
            # 3. 链接与 start_url 的路径有很高的相似度
            is_chapter = False
            
            # 检查标题特征
            if re.search(r'第.*?章|第.*?节|第.*?回|引子|序章|楔子|前言|后记', title):
                is_chapter = True
            elif re.match(r'^[\d一二三四五六七八九十百千万两零]+', title.strip()):
                is_chapter = True
                
            # 检查 URL 相似度 (例如路径的相似部分)
            # 比如 start_url: /book/50045/257, candidate: /book/50045/258
            parsed_cand = urlparse(url)
            cand_parts = parsed_cand.path.strip('/').split('/')
            
            # 如果是 bqgns.com 类型的结构
            if len(cand_parts) >= 2 and len(start_path_parts) >= 2:
                # 检查倒数第二级是否相同（如 bookid 相同）
                if cand_parts[-2] == start_path_parts[-1] or (len(cand_parts) > 2 and len(start_path_parts) > 2 and cand_parts[-2] == start_path_parts[-2]):
                    is_chapter = True
            
            # 如果没有任何特征匹配，但 URL 路径包含数字，且跟 start_url 同域，我们也予以保留作为备选
            if not is_chapter:
                # 检查是否包含数字文件名
                if re.search(r'/\d+(?:_\d+)?(?:\.html?)?$', parsed_cand.path):
                    is_chapter = True
                    
            if is_chapter:
                toc_chapters.append((url, title))
                seen_urls.add(url)
                
        if not toc_chapters:
            logger.warning("在目录页未匹配到任何章节链接，降级到顺序抓取模式")
            return None
            
        logger.info(f"目录页解析完成，共找到 {len(toc_chapters)} 个章节链接")
        
        # 3. 定位起点 URL 在目录中的索引
        start_idx = -1
        # 先尝试完全匹配 URL
        for i, (url, title) in enumerate(toc_chapters):
            if url == start_url or url.replace('https://', 'http://') == start_url.replace('https://', 'http://'):
                start_idx = i
                break
                
        # 若完全匹配失败，尝试通过 URL 路径的最后部分匹配（如章节 ID 或文件名）
        if start_idx == -1:
            start_path = urlparse(start_url).path.rstrip('/')
            for i, (url, title) in enumerate(toc_chapters):
                if urlparse(url).path.rstrip('/') == start_path:
                    start_idx = i
                    break
                    
        # 若依然失败，尝试通过标题匹配
        if start_idx == -1:
            # 获取当前文章标题作为参考（从 soup_start 提取标题）
            start_title = ""
            for selector in ['h1', 'title']:
                el = soup_start.select_one(selector)
                if el:
                    start_title = el.get_text(strip=True)
                    if selector == 'title' and '_' in start_title:
                        start_title = start_title.split('_')[0]
                    break
            if start_title:
                start_title_clean = re.sub(r'\s+', '', start_title)
                for i, (url, title) in enumerate(toc_chapters):
                    if re.sub(r'\s+', '', title) == start_title_clean or start_title_clean in re.sub(r'\s+', '', title):
                        start_idx = i
                        break
                        
        if start_idx == -1:
            logger.warning("在目录中无法定位起点章节，降级到顺序抓取模式")
            return None
            
        logger.info(f"成功定位起点章节在目录中的索引: {start_idx} (章节: {toc_chapters[start_idx][1]})")
        
        # 4. 根据方向和数量切片
        result = []
        
        # 传出格式：[(url, title, toc_index), ...]，toc_index 是 1-based index (即 i + 1)
        if direction == 'next':
            end_idx = min(start_idx + count + 1, len(toc_chapters))
            for i in range(start_idx + 1, end_idx):
                url, title = toc_chapters[i]
                result.append((url, title, i + 1))
        elif direction == 'prev':
            start_pos = max(start_idx - count, 0)
            for i in range(start_idx - 1, start_pos - 1, -1):
                url, title = toc_chapters[i]
                result.append((url, title, i + 1))
        
        logger.info(f"切片完成，切片方向: {direction}, 切片数量: {len(result)}")
        return result
        
    except Exception as e:
        logger.error(f"自适应解析目录时出错: {e}", exc_info=True)
        return None


def chinese_to_arabic(chinese_num):
    """将中文数字转换为阿拉伯数字"""
    chinese_nums = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }
    
    if isinstance(chinese_num, int):
        return chinese_num
    
    # 如果已经是阿拉伯数字字符串，直接转换
    if chinese_num.isdigit():
        return int(chinese_num)
    
    # 处理空字符串情况
    if not chinese_num:
        return 0
    
    # 替换"两"为"二"，方便统一处理
    chinese_num = chinese_num.replace('两', '二')
    
    result = 0
    temp = 0
    
    # 中文数字转换逻辑
    for i, char in enumerate(chinese_num):
        if char in chinese_nums:
            num = chinese_nums[char]
            
            if num >= 10:  # 处理十、百、千、万
                if temp == 0:
                    temp = 1
                result += temp * num
                temp = 0
            else:  # 处理零到九
                if char == '零':
                    # 零后面的数字需要重置temp，但不影响result
                    if temp > 0:
                        result += temp
                        temp = 0
                else:
                    temp = temp * 10 + num
        else:
            continue
    
    # 处理最后剩下的temp
    result += temp
    return result


def extract_chapter_number(title, url=None):
    """从章节标题中提取章节号，支持中文数字、数字前缀及URL提取"""
    import re
    if not title:
        return None
        
    # 去除标题中的多余空格，避免空格导致匹配失败
    cleaned_title = re.sub(r'\s+', '', title)
    
    # 模式 1: "第123章", "第 一百二 十 章", "第一千零一回", "第250节"
    pattern1 = r'第([\d一二三四五六七八九十百千万两零]+)[章节回部分节]?'
    match1 = re.search(pattern1, cleaned_title)
    if match1:
        num_str = match1.group(1)
        val = chinese_to_arabic(num_str)
        if val > 0:
            return val
            
    # 模式 2: "一、标题", "1. 标题", "100 标题"
    # 匹配开头是数字或中文数字，后面紧跟标点符号或空格的情况
    pattern2 = r'^([\d一二三四五六七八九十百千万两零]+)[、\.\s_]'
    match2 = re.search(pattern2, title.strip())
    if match2:
        num_str = match2.group(1)
        val = chinese_to_arabic(num_str)
        if val > 0:
            return val
            
    # 模式 3: "第123"
    pattern3 = r'第\s*(\d+)'
    match3 = re.search(pattern3, title)
    if match3:
        return int(match3.group(1))

    # 模式 4: 直接从URL中提取章节号（作为备选方案）
    if url:
        # 优先匹配bqgns.com的URL格式：/book/50045/257
        url_pattern = r'/book/\d+/(\d+)'
        url_match = re.search(url_pattern, url)
        if url_match:
            val = int(url_match.group(1))
            if val < 100000:
                return val
        
        # 匹配笔趣阁等网站的URL格式：/biqu42484/21341278.html
        biquge_pattern = r'/([^/]+)/(\d+)(?:_2)?\.html$'
        biquge_match = re.search(biquge_pattern, url)
        if biquge_match:
            val = int(biquge_match.group(2))
            if val < 100000:
                return val

    # 模式 5: 匹配纯数字格式，如"123. 标题"
    pattern5 = r'^(\d+)\.'
    match5 = re.search(pattern5, title)
    if match5:
        return int(match5.group(1))
    
    # 模式 6: 匹配数字+标题格式，如"123 标题"
    pattern6 = r'^(\d+)\s'
    match6 = re.search(pattern6, title)
    if match6:
        return int(match6.group(1))
    
    # 最终备选方案：从URL路径中提取最后一个数字
    if url:
        url_pattern = r'(\d+)(?:_\d+)?(?:\.html?)?$'
        url_match = re.search(url_pattern, url)
        if url_match:
            val = int(url_match.group(1))
            if val < 100000:
                return val
    
    # 最后的最终备选方案：标题中包含的第一个纯数字且小于100000
    digits_match = re.search(r'\d+', title)
    if digits_match:
        val = int(digits_match.group(0))
        if val < 100000:
            return val
            
    return None


def sanitize_filename(filename):
    """生成安全的文件名"""
    # 移除特殊字符
    filename = re.sub(r'[<>:":/\\|?*]', '', filename)
    # 移除多余的空格
    filename = re.sub(r'\s+', ' ', filename)
    # 限制文件名长度
    if len(filename) > 100:
        filename = filename[:100]
    return filename.strip()


def write_article(article, output_dir, output_format, append=False, existing_file=None, index=None):
    """将文章内容写入文件"""
    import os
    import time
    import re
    from datetime import datetime
    
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
            
            # 从标题或URL中提取章节号
            chapter_num = extract_chapter_number(article['title'], article['url'])
            
            # 优先使用有效的章节号（不超过100000）格式化为5位前缀，
            # 其次使用传入的 index 序号，最后使用毫秒时间戳。
            if chapter_num is not None and chapter_num < 100000:
                prefix = f"{chapter_num:05d}_"
            elif index is not None:
                prefix = f"{index:05d}_"
            else:
                # 备用：使用时间戳生成前缀
                timestamp = int(time.time() * 1000)
                prefix = f"{timestamp:013d}_"
            
            # 添加前缀到文件名
            base_filename = prefix + base_filename
        else:
            # 如果没有标题，使用当前时间戳，确保排序正确
            timestamp = int(time.time() * 1000)
            base_filename = f"{timestamp:013d}_article_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
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
    
    # 已爬取章节跟踪集合
    crawled_chapters = set()  # 用于存储已爬取的章节号
    crawled_urls = set()  # 用于存储已爬取的URL，防止无法提取章节号时重复爬取
    
    # 持久化重复章节检测：从文件读取已爬取的章节号和URL
    import os
    import json
    crawl_history_file = os.path.join(args.output_dir, '.crawl_history.json')
    if os.path.exists(crawl_history_file):
        try:
            with open(crawl_history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
                crawled_chapters = set(history_data.get('chapters', []))
                crawled_urls = set(history_data.get('urls', []))
            logger.info(f"从文件加载已爬取章节数: {len(crawled_chapters)}")
            logger.info(f"从文件加载已爬取URL数: {len(crawled_urls)}")
        except Exception as e:
            logger.error(f"读取爬取历史文件失败: {e}")
            crawled_chapters = set()
            crawled_urls = set()
    
    # 1. 首先爬取当前章节
    logger.info(f"开始爬取当前章节: {current_url}")
    try:
        # 检查URL是否已爬取
        if current_url in crawled_urls:
            logger.info(f"URL {current_url} 已爬取，跳过")
            # 只请求一次，复用结果
            html_content = fetch_page(current_url)
            current_article = parse_article(html_content, current_url)
        else:
            # 获取网页内容
            html_content = fetch_page(current_url)
            logger.info("网页获取成功")
            
            # 解析文章内容
            article = parse_article(html_content, current_url)
            logger.info(f"文章解析成功，标题: {article['title']}")
            
            # 提取章节号
            chapter_num = extract_chapter_number(article['title'], article['url'])
            
            # 用户明确请求的章节，只按 URL 去重，不按章节号去重
            # （章节号去重仅用于自动翻页的 prev/next 章节，防止循环）
            # 保存当前章节
            current_file_path = write_article(article, args.output_dir, args.format)
            current_chapter_title = article['title']
            actual_chapters_fetched += 1
            # 添加到已爬取集合
            if chapter_num is not None:
                crawled_chapters.add(chapter_num)
            crawled_urls.add(current_url)
            # 保存当前章节信息，用于后续爬取（复用已解析结果，避免重复请求）
            current_article = article
    except Exception as e:
        logger.error(f"爬取当前章节失败: {e}")
        logger.info("爬取任务结束")
        return
    
    # 2. 向前爬取上一章
    if prev_chapters_to_fetch > 0:
        logger.info(f"开始向前爬取 {prev_chapters_to_fetch} 章")
        # 从当前章节开始爬取，确保包括当前章节
        prev_url = current_url
        prev_chapters_fetched = 0
        prev_chapter_title = current_chapter_title
        prev_file_path = None
        
        while prev_chapters_fetched < prev_chapters_to_fetch and prev_url:
            logger.info(f"开始爬取上一章 {prev_chapters_fetched + 1}/{prev_chapters_to_fetch}: {prev_url}")
            
            try:
                # 检查URL是否已爬取
                if prev_url in crawled_urls:
                    logger.info(f"URL {prev_url} 已爬取，跳过")
                    # 只请求一次，复用结果获取上一章链接
                    _skip_article = parse_article(fetch_page(prev_url), prev_url)
                    if _skip_article['prev_chapter_url']:
                        prev_url = _skip_article['prev_chapter_url']
                    else:
                        logger.warning(f"未找到上一章链接，向前爬取结束")
                        break
                    continue
                
                # 获取网页内容
                html_content = fetch_page(prev_url)
                logger.info("网页获取成功")
                
                # 解析文章内容
                article = parse_article(html_content, prev_url)
                logger.info(f"文章解析成功，标题: {article['title']}")
                
                # 提取章节号
                chapter_num = extract_chapter_number(article['title'], article['url'])
                
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
                    # 添加到已爬取集合
                    if chapter_num is not None:
                        crawled_chapters.add(chapter_num)
                    crawled_urls.add(prev_url)
                
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
                # 检查URL是否已爬取
                if next_url in crawled_urls:
                    logger.info(f"URL {next_url} 已爬取，跳过")
                    # 必须获取下一章链接，否则 next_url 永远不更新会死循环
                    _skip_article = parse_article(fetch_page(next_url), next_url)
                    if _skip_article['next_chapter_url']:
                        next_url = _skip_article['next_chapter_url']
                        next_chapters_fetched += 1  # 跳过也算推进一章
                    else:
                        logger.warning(f"已爬取章节 {next_url} 无下一章链接，向后爬取结束")
                        break
                    continue
                
                # 获取网页内容
                html_content = fetch_page(next_url)
                logger.info("网页获取成功")
                
                # 解析文章内容
                article = parse_article(html_content, next_url)
                logger.info(f"文章解析成功，标题: {article['title']}")
                
                # 提取章节号
                chapter_num = extract_chapter_number(article['title'], article['url'])
                
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
                    # 添加到已爬取集合
                    if chapter_num is not None:
                        crawled_chapters.add(chapter_num)
                    crawled_urls.add(next_url)
                
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
    
    # 持久化重复章节检测：保存已爬取的章节号和URL到JSON文件
    import os
    import json
    crawl_history_file = os.path.join(args.output_dir, '.crawl_history.json')
    try:
        history_data = {
            'chapters': list(crawled_chapters),
            'urls': list(crawled_urls)
        }
        with open(crawl_history_file, 'w', encoding='utf-8') as f:
            json.dump(history_data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存爬取历史到文件: {crawl_history_file}")
    except Exception as e:
        logger.error(f"保存爬取历史文件失败: {e}")
    
    logger.info("爬取任务完成")
    logger.info(f"总共爬取章节数: {len(crawled_chapters)}")
    logger.info(f"总共爬取URL数: {len(crawled_urls)}")
    logger.info(f"已爬取章节列表: {sorted(crawled_chapters)}")

if __name__ == '__main__':
    main()