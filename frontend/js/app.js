// 后端API基础URL，部署时需要根据实际情况修改
const API_BASE_URL = '/api';

// 表单提交事件处理
document.addEventListener('DOMContentLoaded', function() {
    const crawlForm = document.getElementById('crawl-form');
    if (crawlForm) {
        crawlForm.addEventListener('submit', handleCrawlSubmit);
    }
});

// 处理爬取表单提交
function handleCrawlSubmit(e) {
    e.preventDefault();
    
    // 获取表单数据
    const formData = {
        url: document.getElementById('url').value,
        format: document.getElementById('format').value,
        output_dir: './output', // 固定输出目录，由后端管理
        next_chapters: parseInt(document.getElementById('next_chapters').value),
        prev_chapters: parseInt(document.getElementById('prev_chapters').value)
    };
    
    // 显示进度条和状态消息
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');
    const resultContainer = document.getElementById('result-container');
    
    progressBar.style.display = 'block';
    statusMessage.className = 'alert alert-info status-message';
    statusMessage.textContent = '正在提交爬取任务...';
    statusMessage.style.display = 'block';
    resultContainer.style.display = 'none';
    
    // 发送请求
    fetch(`${API_BASE_URL}/crawl`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            statusMessage.className = 'alert alert-danger status-message';
            statusMessage.textContent = `错误: ${data.error}`;
            progressBar.style.display = 'none';
            return;
        }
        
        const taskId = data.task_id;
        statusMessage.textContent = `爬取任务已开始，任务ID: ${taskId}`;
        
        // 轮询任务状态
        pollTaskStatus(taskId);
    })
    .catch(error => {
        statusMessage.className = 'alert alert-danger status-message';
        statusMessage.textContent = `请求失败: ${error.message}`;
        progressBar.style.display = 'none';
    });
}

// 轮询任务状态
function pollTaskStatus(taskId) {
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');
    const resultContainer = document.getElementById('result-container');
    const resultContent = document.getElementById('result-content');
    
    fetch(`${API_BASE_URL}/task/${taskId}`)
    .then(response => response.json())
    .then(task => {
        if (task.error) {
            statusMessage.className = 'alert alert-danger status-message';
            statusMessage.textContent = `错误: ${task.error}`;
            progressBar.style.display = 'none';
            return;
        }
        
        // 更新状态消息
        let statusText = '';
        let statusClass = '';
        
        switch (task.status) {
            case 'pending':
                statusText = '任务等待中...';
                statusClass = 'alert-info';
                break;
            case 'running':
                statusText = '爬取进行中...';
                statusClass = 'alert-primary';
                break;
            case 'completed':
                statusText = '爬取完成！';
                statusClass = 'alert-success';
                
                // 显示结果
                let resultHtml = `
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">任务详情</h5>
                            <p class="card-text"><strong>任务ID:</strong> ${task.id}</p>
                            <p class="card-text"><strong>URL:</strong> ${task.url}</p>
                            <p class="card-text"><strong>输出格式:</strong> ${task.format}</p>
                            <p class="card-text"><strong>向后爬取:</strong> ${task.next_chapters} 章</p>
                            <p class="card-text"><strong>向前爬取:</strong> ${task.prev_chapters} 章</p>
                            <p class="card-text"><strong>输出目录:</strong> ${task.output_dir}</p>
                            <p class="card-text"><strong>开始时间:</strong> ${task.start_time}</p>
                            <p class="card-text"><strong>结束时间:</strong> ${task.end_time}</p>
                            <p class="card-text"><strong>生成文件数:</strong> ${task.file_count} 个</p>
                            
                            ${task.output_files && task.output_files.length > 0 ? `
                                <h6 class="mt-4">生成文件列表:</h6>
                                <ul class="list-group">
                                    ${task.output_files.map(file => `
                                        <li class="list-group-item d-flex justify-content-between align-items-center">
                                            ${file}
                                            <div class="btn-group">
                                                <a href="/download/${task.output_dir}/${file}" class="btn btn-sm btn-outline-primary">下载</a>
                                                <button class="btn btn-sm btn-outline-info" onclick="viewArticle('${task.output_dir}/${file}')">查看</button>
                                            </div>
                                        </li>
                                    `).join('')}
                                </ul>
                            ` : ''}
                            
                            ${task.stdout ? `<div class="mt-3"><h6>标准输出:</h6><pre class="bg-light p-3 rounded">${task.stdout}</pre></div>` : ''}
                        </div>
                    </div>
                `;
                
                resultContent.innerHTML = resultHtml;
                resultContainer.style.display = 'block';
                progressBar.style.display = 'none';
                return;
            case 'failed':
                statusText = '爬取失败！';
                statusClass = 'alert-danger';
                
                // 显示错误信息
                let errorHtml = `
                    <div class="card">
                        <div class="card-body">
                            <h5 class="card-title">任务详情</h5>
                            <p class="card-text"><strong>任务ID:</strong> ${task.id}</p>
                            <p class="card-text"><strong>URL:</strong> ${task.url}</p>
                            <p class="card-text"><strong>输出格式:</strong> ${task.format}</p>
                            <p class="card-text"><strong>向后爬取:</strong> ${task.next_chapters} 章</p>
                            <p class="card-text"><strong>向前爬取:</strong> ${task.prev_chapters} 章</p>
                            <p class="card-text"><strong>错误信息:</strong> ${task.error}</p>
                        </div>
                    </div>
                `;
                
                resultContent.innerHTML = errorHtml;
                resultContainer.style.display = 'block';
                progressBar.style.display = 'none';
                return;
        }
        
        statusMessage.className = `alert ${statusClass} status-message`;
        statusMessage.textContent = statusText;
        
        // 继续轮询
        setTimeout(() => pollTaskStatus(taskId), 1000);
    })
    .catch(error => {
        statusMessage.className = 'alert alert-danger status-message';
        statusMessage.textContent = `获取任务状态失败: ${error.message}`;
        progressBar.style.display = 'none';
    });
}

// 查看文章内容
function viewArticle(filename) {
    // 直接跳转到文章展示页面
    window.location.href = `/article/${filename}`;
}

// 文章展示页面的导航功能
function setupArticleNavigation() {
    const prevBtn = document.getElementById('prevArticle');
    const nextBtn = document.getElementById('nextArticle');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            const prevUrl = this.getAttribute('data-url');
            if (prevUrl) {
                window.location.href = `/article/${prevUrl}`;
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', function() {
            const nextUrl = this.getAttribute('data-url');
            if (nextUrl) {
                window.location.href = `/article/${nextUrl}`;
            }
        });
    }
}

// 历史记录页面功能
function loadHistory() {
    const historyContainer = document.getElementById('history-container');
    if (!historyContainer) return;
    
    fetch(`${API_BASE_URL}/history`)
    .then(response => response.json())
    .then(history => {
        if (history.length === 0) {
            historyContainer.innerHTML = '<div class="alert alert-info" role="alert">暂无历史记录</div>';
            return;
        }
        
        let historyHtml = '';
        history.forEach(item => {
            let statusClass = '';
            let statusText = '';
            
            switch (item.status) {
                case 'completed':
                    statusClass = 'status-completed';
                    statusText = '已完成';
                    break;
                case 'failed':
                    statusClass = 'status-failed';
                    statusText = '失败';
                    break;
                case 'running':
                    statusClass = 'status-running';
                    statusText = '运行中';
                    break;
                case 'pending':
                    statusClass = 'status-pending';
                    statusText = '等待中';
                    break;
            }
            
            historyHtml += `
                <div class="history-item">
                    <div class="history-item-header">
                        <div class="d-flex justify-content-between align-items-center">
                            <h5 class="history-item-title">${item.url}</h5>
                            <span class="history-item-status ${statusClass}">${statusText}</span>
                        </div>
                    </div>
                    <div class="history-item-body">
                        <div class="row">
                            <div class="col-md-3">
                                <strong>任务ID:</strong> ${item.id}
                            </div>
                            <div class="col-md-3">
                                <strong>输出格式:</strong> ${item.format}
                            </div>
                            <div class="col-md-3">
                                <strong>生成文件数:</strong> ${item.file_count} 个
                            </div>
                            <div class="col-md-3">
                                <strong>开始时间:</strong> ${item.start_time}
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-md-3">
                                <strong>向后爬取:</strong> ${item.next_chapters} 章
                            </div>
                            <div class="col-md-3">
                                <strong>向前爬取:</strong> ${item.prev_chapters} 章
                            </div>
                            <div class="col-md-6">
                                <strong>输出目录:</strong> ${item.output_dir}
                            </div>
                        </div>
                        ${item.end_time ? `<div class="mt-2"><strong>结束时间:</strong> ${item.end_time}</div>` : ''}
                        ${item.output_files && item.output_files.length > 0 ? `
                            <div class="mt-3">
                                <strong>生成文件:</strong>
                                <ul class="list-unstyled mt-1">
                                    ${item.output_files.slice(0, 5).map(file => `
                                        <li class="d-flex justify-content-between align-items-center">
                                            <span>${file}</span>
                                            <a href="/download/${item.output_dir}/${file}" class="btn btn-sm btn-outline-primary">下载</a>
                                        </li>
                                    `).join('')}
                                    ${item.output_files.length > 5 ? `<li class="text-muted mt-1">... 共 ${item.output_files.length} 个文件</li>` : ''}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                    <div class="history-item-footer">
                        <div class="text-muted">${item.created_at}</div>
                    </div>
                </div>
            `;
        });
        
        historyContainer.innerHTML = historyHtml;
    })
    .catch(error => {
        historyContainer.innerHTML = `<div class="alert alert-danger" role="alert">加载历史记录失败: ${error.message}</div>`;
    });
}

// 根据页面ID执行相应的初始化函数
document.addEventListener('DOMContentLoaded', function() {
    const currentPage = document.body.getAttribute('data-page');
    
    switch (currentPage) {
        case 'article':
            setupArticleNavigation();
            break;
        case 'history':
            loadHistory();
            break;
        default:
            // 首页不需要额外初始化
            break;
    }
});