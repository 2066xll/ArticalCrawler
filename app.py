#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# PyInstaller 打包支持：检测运行环境
if getattr(sys, 'frozen', False):
    # 打包后：资源在 sys._MEIPASS 临时目录中（只读）
    BASE_DIR = os.path.dirname(sys.executable)  # 可执行文件所在目录（可写）
    RESOURCE_DIR = sys._MEIPASS  # type: ignore[attr-defined]  # 包内资源目录
else:
    # 开发环境：资源在脚本所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = BASE_DIR

# 确保 data 目录存在
log_dir = os.path.join(BASE_DIR, 'data')
try:
    os.makedirs(log_dir, exist_ok=True)
except Exception:
    pass

log_file = os.path.join(log_dir, 'app.log')

# 初始化日志记录，同时输出到控制台和文件
import logging
from logging.handlers import RotatingFileHandler

# 创建根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 清除已有的 handlers（避免重复输出）
for h in list(root_logger.handlers):
    root_logger.removeHandler(h)

log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 终端输出 Handler
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_format)
root_logger.addHandler(stream_handler)

# 文件输出 Handler，使用 RotatingFileHandler 限制日志大小，防止日志无限增大
file_handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=3, encoding='utf-8')
file_handler.setFormatter(log_format)
root_logger.addHandler(file_handler)

logger = logging.getLogger(__name__)
logger.info(f"日志初始化完成，日志文件路径: {log_file}")

import json
import threading
import time
import uuid
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response  # type: ignore[import]
import subprocess
import traceback

from article_crawler import fetch_page, parse_article

# 统一提取章节号的助手函数，支持 "第X章" 以及 "00001_" 前缀和中文数字
def get_chapter_number(fn):
    prefix_match = re.match(r'^(\d+)_', fn)
    if prefix_match:
        return int(prefix_match.group(1))
    match = re.search(r'第([\d一二三四五六七八九十百千万两零]+)[章节回]', fn)
    if match:
        try:
            from article_crawler import chinese_to_arabic
            return chinese_to_arabic(match.group(1))
        except Exception:
            pass
    return 999999

# 添加缓存支持
from functools import wraps
import hashlib
from typing import Any, Dict

# 简单的内存缓存
cache: Dict[str, Any] = {}
cache_expiry: Dict[str, float] = {}

# 缓存装饰器
def cache_decorator(expiry=30):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            key = hashlib.md5(f"{func.__name__}:{args}:{kwargs}".encode()).hexdigest()
            
            # 检查缓存是否存在且未过期
            current_time = time.time()
            if key in cache and current_time < cache_expiry.get(key, 0):
                return cache[key]
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 保存到缓存
            cache[key] = result
            cache_expiry[key] = current_time + expiry
            
            return result
        return wrapper
    return decorator

# 清除特定缓存
def clear_cache(func_name):
    keys_to_remove = []
    for key in cache:
        if func_name in key:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        del cache[key]  # type: ignore[arg-type]
        if key in cache_expiry:
            del cache_expiry[key]  # type: ignore[arg-type]

# API请求限制
# 简单的IP请求限制，记录每个IP的请求次数
api_requests = {}
API_RATE_LIMIT = 100  # 每个IP每分钟最多100次请求
RATE_LIMIT_WINDOW = 60  # 时间窗口（秒）

# API请求限制装饰器
def rate_limit_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # 获取客户端IP
        client_ip = request.remote_addr
        current_time = time.time()
        
        # 清理过期的请求记录
        if client_ip in api_requests:
            # 过滤掉过期的请求
            api_requests[client_ip] = [t for t in api_requests[client_ip] if current_time - t < RATE_LIMIT_WINDOW]
        
        # 检查请求次数
        if client_ip in api_requests and len(api_requests[client_ip]) >= API_RATE_LIMIT:
            return jsonify({
                'success': False,
                'error': 'API请求次数超过限制，请稍后再试'
            }), 429
        
        # 记录请求时间
        if client_ip not in api_requests:
            api_requests[client_ip] = []
        api_requests[client_ip].append(current_time)
        
        # 执行函数
        return func(*args, **kwargs)
    return wrapper



app = Flask(
    __name__,
    template_folder=os.path.join(RESOURCE_DIR, 'templates'),
    static_folder=os.path.join(RESOURCE_DIR, 'static'),
)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 添加CORS支持
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

# 处理OPTIONS请求（CORS预检）
@app.route('/api/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    return make_response('', 204)

@app.route('/api', methods=['OPTIONS'])
def handle_root_options():
    return make_response('', 204)

# 配置静态文件目录
FRONTEND_DIR = os.path.join(RESOURCE_DIR, 'frontend')
app.static_folder = FRONTEND_DIR
app.static_url_path = '/static'

# 任务状态存储
tasks = {}
# 任务运行状态控制映射：task_id -> { 'pause_event': Event, 'cancel_event': Event }
task_controls = {}

# 历史记录文件（使用绝对路径，避免相对路径问题）
HISTORY_FILE = os.path.join(BASE_DIR, 'data', 'history.json')
# 任务状态文件
TASKS_FILE = os.path.join(BASE_DIR, 'data', 'tasks.json')

# 确保 data 目录存在
try:
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
except Exception:
    pass

# 初始化历史记录文件
try:
    if not os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
except Exception as e:
    logger.warning(f'无法初始化历史记录文件: {e}')

# 初始化任务状态文件
try:
    if not os.path.exists(TASKS_FILE):
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
except Exception as e:
    logger.warning(f'无法初始化任务状态文件: {e}')

# 加载历史记录
def load_history():
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

# 保存历史记录
def save_history(history):
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f'保存历史记录失败: {e}')

# 加载任务状态
def load_tasks():
    global tasks
    try:
        with open(TASKS_FILE, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            # 重启后清理挂起/运行中的状态
            cleaned = False
            for tid, tinfo in tasks.items():
                if tinfo.get('status') in ('running', 'pending', 'paused'):
                    tinfo['status'] = 'stopped'
                    tinfo['error_msg'] = '服务器重启，任务中止。'
                    cleaned = True
            if cleaned:
                save_tasks()
    except Exception:
        tasks = {}

# 保存任务状态
def save_tasks():
    try:
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f'保存任务状态失败: {e}')

# 加载任务状态
load_tasks()

# 添加历史记录
def add_history(record):
    history = load_history()
    history.append(record)
    save_history(history)

# 异步执行爬取任务
def run_crawler(task_id, url, format, output_dir, next_chapters, prev_chapters):
    try:
        # 将相对路径转为基于 BASE_DIR 的绝对路径，保证写入成功
        if not os.path.isabs(output_dir):
            output_dir = os.path.normpath(os.path.join(BASE_DIR, output_dir))
        os.makedirs(output_dir, exist_ok=True)

        # —— 测试目录是否可写（可能被 macOS Data Vault / com.apple.provenance 锁定）——
        _probe = os.path.join(output_dir, '.write_probe')
        try:
            with open(_probe, 'w') as _pf:
                _pf.write('ok')
            os.remove(_probe)
        except (PermissionError, OSError):
            # 目录不可写，依次尝试备用目录
            for fallback in [
                os.path.expanduser('~/Desktop/文章爬取'),
                os.path.expanduser('~/Downloads/文章爬取'),
                '/tmp/文章爬取',
            ]:
                try:
                    os.makedirs(fallback, exist_ok=True)
                    _probe2 = os.path.join(fallback, '.write_probe')
                    with open(_probe2, 'w') as _pf2:
                        _pf2.write('ok')
                    os.remove(_probe2)
                    logger.warning(f"目录 {output_dir} 不可写（macOS 保护），切换到: {fallback}")
                    output_dir = fallback
                    break
                except (PermissionError, OSError):
                    continue
            else:
                raise PermissionError(f"所有候选目录均不可写，请在终端手动运行: xattr -d com.apple.provenance \"{output_dir}\"")

        # 初始化控制事件
        pause_event = threading.Event()
        pause_event.set()  # 默认不暂停
        cancel_event = threading.Event()
        task_controls[task_id] = {
            'pause_event': pause_event,
            'cancel_event': cancel_event
        }

        # 更新任务状态
        tasks[task_id]['status'] = 'running'
        tasks[task_id]['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['output_dir'] = output_dir  # 更新为绝对路径
        tasks[task_id]['completed_chapters'] = 0
        tasks[task_id]['total_chapters'] = 1 + next_chapters + prev_chapters
        tasks[task_id]['progress'] = 0
        tasks[task_id]['current_chapter_title'] = ''
        save_tasks()

        # 直接调用爬虫模块中的函数
        import article_crawler as _ac

        # 1. 爬取当前章节页面获取 HTML 提取书名
        logger.info(f"[{task_id[:8]}] 开始获取当前章: {url}")
        current_html = _ac.fetch_page(url)

        # 提取书名并自适应更新输出路径（按书名建立文件夹归档）
        book_title = "未知书籍"
        try:
            from bs4 import BeautifulSoup
            soup_start = BeautifulSoup(current_html, 'lxml')
            extracted_title = _ac.extract_book_title(soup_start, url)
            if extracted_title and extracted_title != "未知书籍":
                book_title = extracted_title
        except Exception as e:
            logger.warning(f"提取书名失败: {e}")

        if book_title and book_title != "未知书籍":
            safe_book_title = re.sub(r'[\\/:*?"<>|]', '_', book_title).strip()
            if safe_book_title:
                if not output_dir.endswith(safe_book_title):
                    output_dir = os.path.join(output_dir, safe_book_title)
                    os.makedirs(output_dir, exist_ok=True)
                    # 更新任务状态中及爬取历史文件路径为绝对子路径
                    tasks[task_id]['output_dir'] = output_dir
                    save_tasks()

        # 已爬取记录（防重复）
        crawled_urls: set = set()
        crawled_chapters: set = set()

        # 从持久化历史中恢复（此时 output_dir 已经包含书名）
        crawl_history_file = os.path.join(output_dir, '.crawl_history.json')
        if os.path.exists(crawl_history_file):
            try:
                import json as _json
                with open(crawl_history_file, 'r', encoding='utf-8') as _f:
                    _hist = _json.load(_f)
                    crawled_chapters = set(_hist.get('chapters', []))
                    crawled_urls = set(_hist.get('urls', []))
            except Exception:
                pass

        written_files: list = []

        # 解析文章数据
        current_article = _ac.parse_article(current_html, url)
        current_chapter_title = current_article['title']
        crawled_urls.add(url)
        
        # 尝试通过目录获取列表，以进行多线程并发和准确的 5 位前缀排序
        toc_next_list = None
        toc_prev_list = None
        
        # 仅在大批量任务（如总共下载章节数超过5章）时才启用目录解析并发下载，小规模任务直接顺序下载即可
        if (next_chapters + prev_chapters) >= 2:
            logger.info(f"任务章节数较多，尝试通过目录解析做并发爬取...")
            toc_next_list = _ac.get_toc_chapters(url, 'next', next_chapters, initial_html=current_html)
            toc_prev_list = _ac.get_toc_chapters(url, 'prev', prev_chapters, initial_html=current_html)
            
        # 判断自适应序号
        current_idx = None
        if toc_next_list:
            current_idx = toc_next_list[0][2] - 1
        elif toc_prev_list:
            current_idx = toc_prev_list[0][2] + 1
        else:
            # 顺序兜底的自适应序号
            parsed_num = _ac.extract_chapter_number(current_chapter_title, url)
            if parsed_num is not None and parsed_num < 100000:
                current_idx = parsed_num
            else:
                current_idx = prev_chapters + 1

        # 写入当前文章到磁盘
        current_file = _ac.write_article(current_article, output_dir, format, index=current_idx)
        written_files.append(os.path.basename(current_file))
        
        ch_num = _ac.extract_chapter_number(current_chapter_title, url)
        if ch_num is not None:
            crawled_chapters.add(ch_num)

        tasks[task_id]['completed_chapters'] = 1
        tasks[task_id]['current_chapter_title'] = current_chapter_title
        tasks[task_id]['progress'] = int((1 / (1 + next_chapters + prev_chapters)) * 100)
        save_tasks()

        # 2. 判断是否可以使用并发目录下载
        if toc_next_list is not None and toc_prev_list is not None:
            # 并发模式
            # 合并下载任务任务列表，每个元素为 (url, title, index)
            download_tasks = []
            if prev_chapters > 0:
                for item in toc_prev_list:
                    if item[0] not in crawled_urls:
                        download_tasks.append(item)
            if next_chapters > 0:
                for item in toc_next_list:
                    if item[0] not in crawled_urls:
                        download_tasks.append(item)

            total_chapters = 1 + len(download_tasks)
            tasks[task_id]['total_chapters'] = total_chapters
            tasks[task_id]['progress'] = int((1 / total_chapters) * 100)
            save_tasks()

            from concurrent.futures import ThreadPoolExecutor
            completed_lock = threading.Lock()
            last_saved_pct = -1

            def _download_worker(item):
                nonlocal last_saved_pct
                target_url, title, idx = item
                if cancel_event.is_set():
                    return
                pause_event.wait()
                if cancel_event.is_set():
                    return

                try:
                    html_content = _ac.fetch_page(target_url)
                    article_data = _ac.parse_article(html_content, target_url)
                    
                    if not article_data.get('is_valid', True):
                        logger.warning(f"跳过质量校验未通过的页面 ({target_url}): {article_data.get('validation_reason')}")
                        with completed_lock:
                            tasks[task_id]['completed_chapters'] += 1
                        return

                    fp = _ac.write_article(article_data, output_dir, format, index=idx)
                    
                    # 处理该章节可能存在的分页
                    next_page_url = article_data.get('next_chapter_url', '')
                    current_title = article_data.get('title', '')
                    page_count = 1
                    while next_page_url and page_count < 3:
                        if cancel_event.is_set():
                            break
                        pause_event.wait()
                        
                        try:
                            page_html = _ac.fetch_page(next_page_url)
                            page_art = _ac.parse_article(page_html, next_page_url)
                            if page_art.get('title') == current_title or (page_art.get('title') and current_title and page_art.get('title').replace(' ', '') == current_title.replace(' ', '')):
                                _ac.write_article(page_art, output_dir, format, append=True, existing_file=fp)
                                next_page_url = page_art.get('next_chapter_url', '')
                                page_count += 1
                            else:
                                break
                        except Exception:
                            break

                    with completed_lock:
                        written_files.append(os.path.basename(fp))
                        crawled_urls.add(target_url)
                        extracted_num = _ac.extract_chapter_number(article_data['title'], target_url)
                        if extracted_num is not None:
                            crawled_chapters.add(extracted_num)

                        tasks[task_id]['completed_chapters'] += 1
                        comp = tasks[task_id]['completed_chapters']
                        pct = int((comp / total_chapters) * 100)
                        tasks[task_id]['progress'] = pct
                        tasks[task_id]['current_chapter_title'] = article_data.get('title', '')
                        
                        # 进度变动 >= 1% 时才写入 tasks.json 节流，避免高频 I/O 阻塞
                        if pct >= last_saved_pct + 1 or comp == total_chapters:
                            tasks[task_id]['_last_saved_pct'] = pct
                            last_saved_pct = pct
                            save_tasks()
                except Exception as ex:
                    logger.error(f"并发下载章节失败 {target_url}: {ex}")

            # 启动线程池并发下载 (并发数 10)
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(_download_worker, download_tasks)
        else:
            # 顺序兜底模式
            total_chapters = 1 + prev_chapters + next_chapters
            
            # 向前顺序爬取
            if prev_chapters > 0:
                prev_url = current_article.get('prev_chapter_url', '')
                prev_fetched = 0
                prev_title = current_chapter_title
                prev_file = current_file
                while prev_fetched < prev_chapters and prev_url:
                    if cancel_event.is_set():
                        break
                    pause_event.wait()
                    
                    if prev_url in crawled_urls:
                        try:
                            _html = _ac.fetch_page(prev_url)
                            _art = _ac.parse_article(_html, prev_url)
                            prev_url = _art.get('prev_chapter_url', '')
                        except Exception:
                            break
                        continue
                    try:
                        art_html = _ac.fetch_page(prev_url)
                        art = _ac.parse_article(art_html, prev_url)
                        ch_num = _ac.extract_chapter_number(art['title'], prev_url)
                        
                        # 自适应序号
                        idx = current_idx - (prev_fetched + 1)
                        
                        if art['title'] == prev_title and prev_file:
                            _ac.write_article(art, output_dir, format,
                                              append=True, existing_file=prev_file)
                        else:
                            fp = _ac.write_article(art, output_dir, format, index=idx)
                            written_files.append(os.path.basename(fp))
                            prev_title = art['title']
                            prev_file = fp
                            prev_fetched += 1
                            
                        if ch_num is not None:
                            crawled_chapters.add(ch_num)
                        crawled_urls.add(prev_url)
                        prev_url = art.get('prev_chapter_url', '')
                        
                        # 推进进度
                        tasks[task_id]['completed_chapters'] += 1
                        comp = tasks[task_id]['completed_chapters']
                        tasks[task_id]['progress'] = int((comp / total_chapters) * 100)
                        tasks[task_id]['current_chapter_title'] = art.get('title', '')
                        save_tasks()
                    except Exception as e:
                        logger.error(f"向前顺序爬取失败: {e}")
                        break

            # 向后顺序爬取
            if next_chapters > 0:
                next_url = current_article.get('next_chapter_url', '')
                next_fetched = 0
                next_title = current_chapter_title
                next_file = current_file
                while next_fetched < next_chapters and next_url:
                    if cancel_event.is_set():
                        break
                    pause_event.wait()
                    
                    if next_url in crawled_urls:
                        try:
                            _html = _ac.fetch_page(next_url)
                            _art = _ac.parse_article(_html, next_url)
                            next_url = _art.get('next_chapter_url', '')
                            next_fetched += 1
                        except Exception:
                            break
                        continue
                    try:
                        art_html = _ac.fetch_page(next_url)
                        art = _ac.parse_article(art_html, next_url)
                        ch_num = _ac.extract_chapter_number(art['title'], next_url)
                        
                        # 自适应序号
                        idx = current_idx + (next_fetched + 1)
                        
                        if art['title'] == next_title and next_file:
                            _ac.write_article(art, output_dir, format,
                                              append=True, existing_file=next_file)
                        else:
                            fp = _ac.write_article(art, output_dir, format, index=idx)
                            written_files.append(os.path.basename(fp))
                            next_title = art['title']
                            next_file = fp
                            next_fetched += 1
                            
                        if ch_num is not None:
                            crawled_chapters.add(ch_num)
                        crawled_urls.add(next_url)
                        next_url = art.get('next_chapter_url', '')
                        
                        # 推进进度
                        tasks[task_id]['completed_chapters'] += 1
                        comp = tasks[task_id]['completed_chapters']
                        tasks[task_id]['progress'] = int((comp / total_chapters) * 100)
                        tasks[task_id]['current_chapter_title'] = art.get('title', '')
                        save_tasks()
                    except Exception as e:
                        logger.error(f"向后顺序爬取失败: {e}")
                        break

        # 判断是否中途退出
        if cancel_event.is_set():
            tasks[task_id]['status'] = 'stopped'
            tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_tasks()
            logger.info(f"[{task_id[:8]}] 任务被用户中止")
            return

        # 持久化爬取历史
        try:
            import json as _json
            with open(crawl_history_file, 'w', encoding='utf-8') as _f:
                _json.dump({'chapters': list(crawled_chapters),
                            'urls': list(crawled_urls)}, _f,
                           ensure_ascii=False, indent=2)
        except Exception:
            pass

        # 整理输出文件列表（自适应5位前缀排序）
        article_extensions = {'.txt', '.md', '.html', '.htm'}
        all_output_files = [
            f for f in os.listdir(output_dir)
            if os.path.isfile(os.path.join(output_dir, f))
            and not f.startswith('.')
            and os.path.splitext(f)[1].lower() in article_extensions
        ]

        def _sort_key(name):
            prefix_match = re.match(r'^(\d+)_', name)
            if prefix_match:
                return int(prefix_match.group(1))
            m = re.search(r'第([\d一二三四五六七八九十百千万两零]+)[章节回]', name)
            if m:
                try:
                    return _ac.chinese_to_arabic(m.group(1))
                except Exception:
                    pass
            return 999999

        sorted_files = sorted(all_output_files, key=_sort_key)

        # 更新任务结果为已完成
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['output_files'] = sorted_files
        tasks[task_id]['file_count'] = len(sorted_files)
        tasks[task_id]['progress'] = 100
        save_tasks()

        add_history({
            'id': task_id,
            'url': url,
            'format': format,
            'output_dir': output_dir,
            'next_chapters': next_chapters,
            'prev_chapters': prev_chapters,
            'status': 'completed',
            'start_time': tasks[task_id]['start_time'],
            'end_time': tasks[task_id]['end_time'],
            'file_count': len(sorted_files),
            'output_files': sorted_files
        })
        logger.info(f"[{task_id[:8]}] 爬取完成，共 {len(sorted_files)} 个文件")

    except Exception as e:
        logger.error(f"[{task_id[:8]}] 爬取任务异常: {e}", exc_info=True)
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['error'] = str(e)
        save_tasks()
        add_history({
            'id': task_id,
            'url': url,
            'format': format,
            'output_dir': output_dir,
            'next_chapters': next_chapters,
            'prev_chapters': prev_chapters,
            'status': 'failed',
            'start_time': tasks[task_id].get('start_time', ''),
            'end_time': tasks[task_id]['end_time'],
            'error': str(e)
        })
    finally:
        # 清理控制映射以释放内存
        if task_id in task_controls:
            del task_controls[task_id]
# 首页路由
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# 首页路由（带.html后缀）
@app.route('/index.html')
def index_html():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# 历史记录页面路由
@app.route('/history')
def history():
    return send_from_directory(FRONTEND_DIR, 'history.html')

# 历史记录页面路由（带.html后缀）
@app.route('/history.html')
def history_html():
    return send_from_directory(FRONTEND_DIR, 'history.html')

# 统计页面路由
@app.route('/stats')
def stats():
    return send_from_directory(FRONTEND_DIR, 'stats.html')

# 统计页面路由（带.html后缀）
@app.route('/stats.html')
def stats_html():
    return send_from_directory(FRONTEND_DIR, 'stats.html')

# 探测书名接口
@app.route('/api/probe_book_title', methods=['GET'])
@rate_limit_decorator
def probe_book_title():
    url = request.args.get('url')
    if not url:
        return jsonify({'success': False, 'error': 'URL不能为空'}), 400
    try:
        import article_crawler as _ac
        from bs4 import BeautifulSoup
        html = _ac.fetch_page(url)
        soup = BeautifulSoup(html, 'lxml')
        book_title = _ac.extract_book_title(soup, url)
        return jsonify({'success': True, 'book_title': book_title})
    except Exception as e:
        logger.error(f"探测书名失败 {url}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# 提交爬取任务
@app.route('/api/crawl', methods=['POST'])
@rate_limit_decorator
def crawl():
    try:
        data = request.json
        if not data:
            return jsonify({'error': '请求体不能为空'}), 400
            
        format = data.get('format', 'txt')
        output_dir = data.get('output_dir', './output')
        next_chapters = data.get('next_chapters', 0)
        prev_chapters = data.get('prev_chapters', 0)
        
        # 处理批量URL请求
        urls = data.get('urls', [])
        if not urls:
            # 兼容旧的单个URL请求
            url = data.get('url')
            if not url:
                return jsonify({'error': 'URL不能为空'}), 400
            urls = [url]
        
        # 生成任务ID列表
        task_ids = []
        
        # 为每个URL启动一个爬取任务
        for url in urls:
            # 生成任务ID
            task_id = str(uuid.uuid4())
            
            # 初始化任务状态
            tasks[task_id] = {
                'id': task_id,
                'url': url,
                'format': format,
                'output_dir': output_dir,
                'next_chapters': next_chapters,
                'prev_chapters': prev_chapters,
                'status': 'pending',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 启动异步爬取任务
            thread = threading.Thread(target=run_crawler, args=(task_id, url, format, output_dir, next_chapters, prev_chapters))
            thread.daemon = True
            thread.start()
            
            task_ids.append(task_id)
        
        # 保存任务状态
        save_tasks()
        
        return jsonify({'success': True, 'task_ids': task_ids})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 获取任务状态
@app.route('/api/task/<task_id>', methods=['GET'])
@rate_limit_decorator
def get_task_status(task_id):
    try:
        if task_id not in tasks:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
    
        return jsonify({'success': True, 'task': tasks[task_id]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 获取所有任务状态
@app.route('/api/tasks', methods=['GET'])
@rate_limit_decorator
@cache_decorator(expiry=5)  # 短时间缓存，因为任务状态会频繁变化
def get_all_tasks():
    try:
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 暂停任务的API
@app.route('/api/task/<task_id>/pause', methods=['POST'])
@rate_limit_decorator
def pause_task(task_id):
    try:
        if task_id not in tasks:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
        
        info = tasks[task_id]
        if info.get('status') != 'running':
            return jsonify({'success': False, 'error': '任务不在运行状态，无法暂停'}), 400
            
        if task_id in task_controls:
            task_controls[task_id]['pause_event'].clear()
            
        info['status'] = 'paused'
        save_tasks()
        return jsonify({'success': True, 'message': '任务暂停指令已发出'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 恢复任务的API
@app.route('/api/task/<task_id>/resume', methods=['POST'])
@rate_limit_decorator
def resume_task(task_id):
    try:
        if task_id not in tasks:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
            
        info = tasks[task_id]
        if info.get('status') != 'paused':
            return jsonify({'success': False, 'error': '任务未处于暂停状态，无法恢复'}), 400
            
        if task_id in task_controls:
            task_controls[task_id]['pause_event'].set()
            
        info['status'] = 'running'
        save_tasks()
        return jsonify({'success': True, 'message': '任务恢复指令已发出'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 停止任务的API
@app.route('/api/task/<task_id>/stop', methods=['POST'])
@rate_limit_decorator
def stop_task(task_id):
    try:
        if task_id not in tasks:
            return jsonify({'success': False, 'error': '任务不存在'}), 404
            
        info = tasks[task_id]
        if info.get('status') not in ('running', 'paused', 'pending'):
            return jsonify({'success': False, 'error': '任务未处于可停止状态'}), 400
            
        if task_id in task_controls:
            task_controls[task_id]['cancel_event'].set()
            task_controls[task_id]['pause_event'].set() # 确保 unblock wait()
            
        info['status'] = 'stopped'
        info['error_msg'] = '用户手动终止了下载任务。'
        save_tasks()
        return jsonify({'success': True, 'message': '任务已发送停止信号'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 获取历史记录
@app.route('/api/history', methods=['GET'])
@rate_limit_decorator
@cache_decorator(expiry=60)  # 较长时间缓存，历史记录变化不频繁
def get_history():
    try:
        history = load_history()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 下载文件
@app.route('/download/<path:filename>')
@rate_limit_decorator
def download_file(filename):
    # 获取文件所在目录
    directory = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(directory, file_name, as_attachment=True)

# 查看文章内容（API）
@app.route('/view/<path:filename>')
@rate_limit_decorator
@cache_decorator(expiry=300)  # 较长时间缓存，文章内容不会变化
def view_file(filename):
    try:
        # 完整文件路径——使用 BASE_DIR 而非 os.getcwd()，避免部署方式改变导致路径错误
        file_path = os.path.join(BASE_DIR, filename)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        file_type = ext[1:].lower()  # 去掉点号，转为小写
        
        return jsonify({
            'success': True,
            'filename': os.path.basename(filename),
            'file_type': file_type,
            'content': content
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'读取文件失败: {str(e)}'
        }), 500

# 静态文件路由
@app.route('/css/<path:filename>')
def static_css(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'css'), filename)

@app.route('/js/<path:filename>')
def static_js(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'js'), filename)

@app.route('/images/<path:filename>')
def static_images(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, 'images'), filename)

# 文章展示页面 - 返回静态HTML
@app.route('/article/<path:filename>')
def article_view(filename):
    return send_from_directory(FRONTEND_DIR, 'article.html')

# 在线阅读页面
@app.route('/read_online')
def read_online_view():
    return send_from_directory(FRONTEND_DIR, 'article.html')

# 在线解析API（无痕阅读）
@app.route('/api/parse_online', methods=['POST'])
@rate_limit_decorator
def parse_online():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': '请求体不能为空'}), 400
        
        url = data.get('url')
        if not url:
            return jsonify({'success': False, 'error': 'URL不能为空'}), 400
        
        # 实时抓取并解析
        try:
            html = fetch_page(url)
            if not html:
                return jsonify({'success': False, 'error': '无法获取网页内容'}), 500
                
            result = parse_article(html, url)
            title = result.get('title', '')
            content = result.get('content', '')
            next_url = result.get('next_chapter_url', '')
            prev_url = result.get('prev_chapter_url', '')
            author_info = result.get('author', '')
            publish_time = result.get('publish_time', '')
            
            if not title and not content:
                return jsonify({'success': False, 'error': '无法解析文章内容，可能是不支持的网站'}), 500
                
            # 组装返回数据，符合现有阅读器接口
            # 始终包含 == 分隔线，防止唤 extractBody 范回 fallback（少数网站标题为空时不包括分隔线）
            sep = '=' * 50
            if title or author_info:
                header = f"{title}\n{author_info}\n原文链接: {url}\n{sep}\n\n"
            else:
                # 即使没有标题也保留分隔线，避免前几行正文被吞
                header = "在线阅读\n原文链接: " + url + "\n" + sep + "\n\n"
            return jsonify({
                'success': True,
                'filename': url,
                'file_type': 'online',
                'content': header + content,
                'prev_article': prev_url if prev_url else None,
                'next_article': next_url if next_url else None,
                'chapter_list': [] # 在线模式暂不提供完整目录
            })
            
        except Exception as e:
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'解析失败: {str(e)}'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 扫描本地目录的API
@app.route('/api/scan', methods=['GET'])
@rate_limit_decorator
def scan_directory():
    try:
        results = []
        article_extensions = {'.txt', '.md', '.html', '.htm'}
        
        # 1. 动态收集要扫描的路径列表
        scan_targets = []
        
        # 优先从抓取历史中搜集成功存储的绝对路径
        try:
            history = load_history()
            for task in history:
                if task.get('status') == 'completed' and task.get('output_dir'):
                    out_dir = os.path.normpath(task['output_dir'])
                    if os.path.exists(out_dir) and out_dir not in [t[0] for t in scan_targets]:
                        # 确定名字
                        bname = os.path.basename(out_dir)
                        if bname in ('articles', 'output', '文章爬取'):
                            bname = '历史书架'
                        scan_targets.append((out_dir, bname))
        except Exception as he:
            logger.error(f"从历史载入扫描路径失败: {he}")

        # 其次尝试程序默认的相对路径
        for rpath, default_bname in [('articles', '默认书架'), ('output', '输出书架')]:
            abs_path = os.path.normpath(os.path.join(BASE_DIR, rpath))
            if os.path.exists(abs_path) and abs_path not in [t[0] for t in scan_targets]:
                scan_targets.append((abs_path, default_bname))
                
        # 其次尝试桌面/下载等常见回退路径
        for fallback_path in [
            os.path.expanduser('~/Desktop/文章爬取'),
            os.path.expanduser('~/Downloads/文章爬取'),
        ]:
            abs_path = os.path.normpath(fallback_path)
            if os.path.exists(abs_path) and abs_path not in [t[0] for t in scan_targets]:
                scan_targets.append((abs_path, '本地书库'))
        
        scanned_dirs = set()
        
        for abs_dir, default_book_name in scan_targets:
            for root, dirs, files in os.walk(abs_dir):
                # 过滤隐藏目录
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                
                # 规范化路径以避免重复扫描
                norm_root = os.path.normpath(root)
                if norm_root in scanned_dirs:
                    continue
                
                book_files = [
                    f for f in files 
                    if os.path.splitext(f)[1].lower() in article_extensions and not f.startswith('.')
                ]
                
                if book_files:
                    scanned_dirs.add(norm_root)
                    book_files.sort(key=get_chapter_number)
                    
                    # 确定书籍名称
                    rel_to_target = os.path.relpath(root, abs_dir)
                    if rel_to_target == '.':
                        book_title = default_book_name
                    else:
                        # 使用子目录名作为书名
                        book_title = os.path.basename(root)
                    
                    # 计算相对于 BASE_DIR 的路径，如果是外部目录，则返回绝对路径（去除开头斜杠以适配前端路由）
                    try:
                        relative = os.path.relpath(root, BASE_DIR)
                        if not relative.startswith('..'):
                            rel_root = '' if relative == '.' else relative
                        else:
                            rel_root = root.lstrip('/')
                    except Exception:
                        rel_root = root.lstrip('/')
                        
                    results.append({
                        'book_title': book_title,
                        'dir': rel_root,
                        'files': book_files
                    })
                    
        # 按书籍名称进行排序
        results.sort(key=lambda x: x['book_title'])
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"扫描文件夹失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# 关闭服务器的API
@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    try:
        def terminate():
            time.sleep(0.5)
            logger.info("服务器正在关闭...")
            os._exit(0)
            
        threading.Thread(target=terminate).start()
        return jsonify({'success': True, 'message': '服务器正在关闭...'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 获取文章内容的API
@app.route('/api/article/<path:filename>', methods=['GET'])
@rate_limit_decorator
@cache_decorator(expiry=300)  # 较长时间缓存，文章内容不会变化
def get_article_content(filename):
    try:
        # 完整文件路径——优先判断是否为 macOS 的绝对路径（Flask 匹配时会去掉开头的斜杠，导致 `/Users/...` 变成 `Users/...`）
        first_segment = filename.split('/')[0] if '/' in filename else filename
        mac_root_dirs = {'Users', 'Applications', 'System', 'Library', 'Volumes', 'private', 'tmp', 'var', 'usr', 'opt', 'etc', 'bin', 'sbin'}
        
        if first_segment in mac_root_dirs or os.path.exists('/' + filename):
            file_path = '/' + filename  # 恢复绝对路径的前导斜杠
        elif os.path.isabs(filename):
            file_path = filename
        else:
            file_path = os.path.join(BASE_DIR, filename)  # 基于 BASE_DIR 而不是 os.getcwd() 以确保打包后仍然正确
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        file_type = str(ext)[1:].lower()  # type: ignore[index]  # 去掉点号，转为小写
        
        # 解析文件名，获取当前目录
        file_dir = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # 获取当前目录下的所有文章文件（排除隐藏文件和非文章文件）
        article_extensions = {'.txt', '.md', '.html', '.htm'}
        if os.path.exists(file_dir):
            all_files = [
                f for f in os.listdir(file_dir)
                if os.path.isfile(os.path.join(file_dir, f))
                and not f.startswith('.')
                and os.path.splitext(f)[1].lower() in article_extensions
            ]
        else:
            all_files = []
        
        # 对文件列表进行排序，采用完全一致的通用排序规则
        sorted_files = sorted(all_files, key=get_chapter_number)
        
        # 获取当前文件的索引
        current_index = sorted_files.index(file_name) if file_name in sorted_files else -1
        
        # 计算上一章和下一章
        prev_article = None
        next_article = None
        
        if current_index > 0:
            prev_article = os.path.join(file_dir, sorted_files[current_index - 1])
        
        if current_index < len(sorted_files) - 1:
            next_article = os.path.join(file_dir, sorted_files[current_index + 1])
        
        # 返回文章内容和导航信息
        return jsonify({
            'success': True,
            'filename': file_name,
            'content': content,
            'file_type': file_type,
            'prev_article': prev_article,
            'next_article': next_article,
            'chapter_list': sorted_files,
            'current_index': current_index
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'读取文件失败: {str(e)}'
        }), 500

def start_global_hotkey_listener():
    """
    启动系统级全局快捷键监听器，按下 Ctrl+Shift+Alt+Q 或 Cmd+Shift+Alt+Q 即可关闭服务器
    """
    try:
        from pynput import keyboard
        
        def on_shutdown():
            logger.info("系统级全局快捷键被触发，正在关闭 Flask 服务器...")
            time.sleep(0.2)
            os._exit(0)
            
        hotkey_map = {
            '<ctrl>+<shift>+<alt>+q': on_shutdown,
            '<cmd>+<shift>+<alt>+q': on_shutdown
        }
        
        listener = keyboard.GlobalHotKeys(hotkey_map)
        listener.daemon = True
        listener.start()
        logger.info("系统级全局快捷键监听已启动。热键：Ctrl+Shift+Alt+Q 或 Cmd+Shift+Alt+Q")
    except Exception as e:
        logger.warning(f"无法启动全局快捷键监听器（可能需要 macOS 辅助功能/Accessibility 权限）：{e}")

if __name__ == '__main__':
    import os
    
    # 启动系统级全局快捷键监听器
    start_global_hotkey_listener()
    
    port = int(os.environ.get('PORT', 5001))
    
    # 直接运行 Flask 服务器
    app.run(debug=False, host='0.0.0.0', port=port, use_reloader=False)
