#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import threading
import time
import uuid
import re
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, make_response  # type: ignore[import]
import subprocess

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

# PyInstaller 打包支持：检测运行环境
if getattr(sys, 'frozen', False):
    # 打包后：资源在 sys._MEIPASS 临时目录中
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    # 开发环境：资源在脚本所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
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
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
app.static_folder = FRONTEND_DIR
app.static_url_path = '/static'

# 任务状态存储
tasks = {}

# 历史记录文件
HISTORY_FILE = 'data/history.json'
# 任务状态文件
TASKS_FILE = 'data/tasks.json'

# 确保data目录存在
os.makedirs('data', exist_ok=True)

# 初始化历史记录文件
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

# 初始化任务状态文件
if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)

# 加载历史记录
def load_history():
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 保存历史记录
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# 加载任务状态
def load_tasks():
    global tasks
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        tasks = json.load(f)

# 保存任务状态
def save_tasks():
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

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
        # 更新任务状态
        tasks[task_id]['status'] = 'running'
        tasks[task_id]['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 保存任务状态
        save_tasks()
        
        import io
        
        # 构建模拟的命令行参数
        crawler_args = [
            'article_crawler.py',
            url,
            '-f', str(format),
            '-o', str(output_dir),
            '-n', str(next_chapters),
            '-p', str(prev_chapters)
        ]
        command = ' '.join(crawler_args)
        tasks[task_id]['command'] = command
        save_tasks()
        
        # 直接调用爬虫模块（兼容打包和开发模式）
        import article_crawler
        
        # 保存原始 sys.argv 和 stdout/stderr
        original_argv = sys.argv
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        return_code = 0
        try:
            # 用爬虫参数替换 sys.argv
            sys.argv = crawler_args
            
            # 重定向 stdout/stderr 到捕获缓冲区
            import logging
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # 重新配置 logging 以写入 stderr 捕获缓冲区
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                stream=stderr_capture
            )
            
            article_crawler.main()
        except SystemExit as e:
            return_code = e.code if e.code is not None else 0
        except Exception as e:
            return_code = 1
            stderr_capture.write(str(e))
        finally:
            # 恢复原始 sys.argv 和 stdout/stderr
            sys.argv = original_argv
            sys.stdout = old_stdout  # type: ignore[possibly-undefined]
            sys.stderr = old_stderr  # type: ignore[possibly-undefined]
            
            # 恢复 logging 配置
            for handler in logging.root.handlers[:]:
                logging.root.removeHandler(handler)
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
        
        captured_stdout = stdout_capture.getvalue()
        captured_stderr = stderr_capture.getvalue()
        
        # 获取输出文件列表（只包含文章文件，排除隐藏文件和系统文件）
        output_files = []
        article_extensions = {'.txt', '.md', '.html', '.htm'}
        if os.path.exists(output_dir):
            output_files = [
                f for f in os.listdir(output_dir)
                if os.path.isfile(os.path.join(output_dir, f))
                and not f.startswith('.')
                and os.path.splitext(f)[1].lower() in article_extensions
            ]
        
        # 对文件列表按照章节号排序
        def sort_files_by_chapter(files):
            def get_chapter_number(filename):
                # 匹配章节号，支持多种格式
                match = re.search(r'第(\d+)章', filename)
                if match:
                    return int(match.group(1))
                # 如果没有找到章节号，返回0
                return 0
            
            # 按照章节号排序
            return sorted(files, key=get_chapter_number)
        
        sorted_output_files = sort_files_by_chapter(output_files)
        
        # 更新任务结果
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['return_code'] = return_code
        # 限制stdout和stderr的长度，防止JSON序列化问题
        tasks[task_id]['stdout'] = captured_stdout[:1000] if captured_stdout else ''
        tasks[task_id]['stderr'] = captured_stderr[:1000] if captured_stderr else ''
        tasks[task_id]['output_files'] = sorted_output_files
        tasks[task_id]['file_count'] = len(sorted_output_files)
        # 保存任务状态
        save_tasks()
        
        # 添加到历史记录
        history_record = {
            'id': task_id,
            'url': url,
            'format': format,
            'output_dir': output_dir,
            'next_chapters': next_chapters,
            'prev_chapters': prev_chapters,
            'status': 'completed',
            'start_time': tasks[task_id]['start_time'],
            'end_time': tasks[task_id]['end_time'],
            'file_count': len(sorted_output_files),
            'output_files': sorted_output_files
        }
        add_history(history_record)
        
    except Exception as e:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['error'] = str(e)
        # 保存任务状态
        save_tasks()
        
        # 添加到历史记录
        history_record = {
            'id': task_id,
            'url': url,
            'format': format,
            'output_dir': output_dir,
            'next_chapters': next_chapters,
            'prev_chapters': prev_chapters,
            'status': 'failed',
            'start_time': tasks[task_id]['start_time'],
            'end_time': tasks[task_id]['end_time'],
            'error': str(e)
        }
        add_history(history_record)

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
@cache_decorator(expiry=5)  # 5秒缓存
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
        # 完整文件路径
        file_path = os.path.join(os.getcwd(), filename)
        
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

# 获取文章内容的API
@app.route('/api/article/<path:filename>', methods=['GET'])
@rate_limit_decorator
@cache_decorator(expiry=300)  # 较长时间缓存，文章内容不会变化
def get_article_content(filename):
    try:
        # 完整文件路径
        file_path = os.path.join(os.getcwd(), filename)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        file_type = str(ext)[1:].lower()  # type: ignore[index]  # 去掉点号，转为小写
        
        # 解析文件名，获取当前目录
        file_dir = os.path.dirname(filename)
        file_name = os.path.basename(filename)
        
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
        
        # 对文件列表按照章节号排序
        def sort_files_by_chapter(files):
            def get_chapter_number(file_name):
                # 匹配章节号，支持多种格式
                match = re.search(r'第(\d+)章', file_name)
                if match:
                    return int(match.group(1))
                # 如果没有找到章节号，返回0
                return 0
            
            # 按照章节号排序
            return sorted(files, key=get_chapter_number)
        
        sorted_files = sort_files_by_chapter(all_files)
        
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

if __name__ == '__main__':
    import os
    app.run(debug=False, host='0.0.0.0', port=os.environ.get('PORT', 5001))
