#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import threading
import time
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
import subprocess

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 任务状态存储
tasks = {}

# 历史记录文件
HISTORY_FILE = 'data/history.json'

# 确保data目录存在
os.makedirs('data', exist_ok=True)

# 初始化历史记录文件
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f)

# 加载历史记录
def load_history():
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

# 保存历史记录
def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

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
        
        # 构建命令
        # 直接使用用户输入的章节数量作为 -n 参数
        # article_crawler.py 现在将 -n 参数直接解释为总章节数（包括当前章节）
        command = f'python3 article_crawler.py "{url}" -f {format} -o "{output_dir}" -n {next_chapters} -p {prev_chapters}'
        tasks[task_id]['command'] = command
        
        # 执行命令
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        # 获取输出文件列表
        output_files = []
        if os.path.exists(output_dir):
            output_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
        
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
        tasks[task_id]['return_code'] = result.returncode
        tasks[task_id]['stdout'] = result.stdout
        tasks[task_id]['stderr'] = result.stderr
        tasks[task_id]['output_files'] = sorted_output_files
        tasks[task_id]['file_count'] = len(sorted_output_files)
        
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
            'file_count': len(output_files),
            'output_files': output_files
        }
        add_history(history_record)
        
    except Exception as e:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['end_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tasks[task_id]['error'] = str(e)
        
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
    return render_template('index.html')

# 提交爬取任务
@app.route('/api/crawl', methods=['POST'])
def crawl():
    data = request.json
    url = data.get('url')
    format = data.get('format', 'txt')
    output_dir = data.get('output_dir', './output')
    next_chapters = data.get('next_chapters', 0)
    prev_chapters = data.get('prev_chapters', 0)
    
    if not url:
        return jsonify({'error': 'URL不能为空'}), 400
    
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
    
    return jsonify({'task_id': task_id})

# 获取任务状态
@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(tasks[task_id])

# 获取历史记录
@app.route('/api/history', methods=['GET'])
def get_history():
    history = load_history()
    return jsonify(history)

# 下载文件
@app.route('/download/<path:filename>')
def download_file(filename):
    # 获取文件所在目录
    directory = os.path.dirname(filename)
    file_name = os.path.basename(filename)
    return send_from_directory(directory, file_name, as_attachment=True)

# 查看文章内容（API）
@app.route('/view/<path:filename>')
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

# 文章展示页面
@app.route('/article/<path:filename>')
def article_view(filename):
    try:
        # 完整文件路径
        file_path = os.path.join(os.getcwd(), filename)
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 获取文件扩展名
        _, ext = os.path.splitext(filename)
        file_type = ext[1:].lower()  # 去掉点号，转为小写
        
        # 解析文件名，获取当前目录
        file_dir = os.path.dirname(filename)
        file_name = os.path.basename(filename)
        
        # 获取当前目录下的所有文件
        if os.path.exists(file_dir):
            all_files = [f for f in os.listdir(file_dir) if os.path.isfile(os.path.join(file_dir, f))]
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
        
        # 渲染文章展示页面
        return render_template('article.html', 
                            filename=file_name,
                            content=content,
                            file_type=file_type,
                            prev_article=prev_article,
                            next_article=next_article)
    except Exception as e:
        return render_template('article.html', 
                            filename=os.path.basename(filename),
                            content=None,
                            file_type='txt',
                            prev_article=None,
                            next_article=None)

# 历史记录页面
@app.route('/history')
def history():
    return render_template('history.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
