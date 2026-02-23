// 模块化设计的文章爬取工具前端代码

// 全局命名空间
const ArticleCrawler = {
    // API配置模块
    api: {
        baseUrl: localStorage.getItem('apiBaseUrl') || '/api',
        
        setBaseUrl(url) {
            this.baseUrl = url;
            localStorage.setItem('apiBaseUrl', url);
            this.showMessage('API基础URL已更新为: ' + url, 'success');
        },
        
        getBaseUrl() {
            return this.baseUrl;
        },
        
        // 统一的fetch包装函数
        async fetch(endpoint, options = {}) {
            try {
                const url = `${this.baseUrl}${endpoint}`;
                const response = await fetch(url, {
                    headers: {
                        'Content-Type': 'application/json',
                        ...options.headers
                    },
                    ...options
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP错误! 状态码: ${response.status}`);
                }
                
                const text = await response.text();
                if (!text) {
                    throw new Error('空响应，API可能未正确配置');
                }
                
                return JSON.parse(text);
            } catch (error) {
                throw error;
            }
        }
    },
    
    // UI工具模块
    ui: {
        // 显示加载状态
        showLoading(element, text = '加载中...') {
            if (!element) return;
            
            element.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>${text}`;
            element.disabled = true;
        },
        
        // 隐藏加载状态
        hideLoading(element, originalText) {
            if (!element) return;
            
            element.innerHTML = originalText;
            element.disabled = false;
        },
        
        // 显示消息
        showMessage(text, type = 'info') {
            const statusMessage = document.getElementById('status-message');
            if (!statusMessage) return;
            
            statusMessage.className = `alert alert-${type} status-message fade-in`;
            statusMessage.textContent = text;
            statusMessage.style.display = 'block';
        },
        
        // 隐藏消息
        hideMessage() {
            const statusMessage = document.getElementById('status-message');
            if (statusMessage) {
                statusMessage.style.display = 'none';
            }
        },
        
        // 更新进度条
        updateProgress(progressBar, value) {
            if (!progressBar) return;
            
            progressBar.style.display = 'block';
            progressBar.querySelector('.progress-bar').style.width = `${value}%`;
        },
        
        // 隐藏进度条
        hideProgress(progressBar) {
            if (progressBar) {
                progressBar.style.display = 'none';
            }
        }
    },
    
    // 表单处理模块
    form: {
        // 初始化表单事件监听
        init() {
            console.log('开始初始化表单事件监听');
            const crawlForm = document.getElementById('crawl-form');
            console.log('crawlForm元素:', crawlForm);
            if (crawlForm) {
                console.log('绑定submit事件监听器');
                crawlForm.addEventListener('submit', this.handleSubmit.bind(this));
                console.log('submit事件监听器绑定成功');
            } else {
                console.error('crawl-form元素不存在');
            }
            
            // 直接为提交按钮添加点击事件监听器
            const submitBtn = document.querySelector('button[type="submit"]');
            console.log('submitBtn元素:', submitBtn);
            if (submitBtn) {
                console.log('绑定点击事件监听器到提交按钮');
                // 保存this引用
                const self = this;
                submitBtn.addEventListener('click', function(e) {
                    console.log('提交按钮被点击');
                    // 阻止默认行为
                    e.preventDefault();
                    
                    // 直接调用startCrawl方法
                    console.log('直接调用startCrawl方法');
                    self.startCrawl();
                });
                console.log('提交按钮点击事件监听器绑定成功');
            } else {
                console.error('提交按钮不存在');
            }
            
            // 初始化批量URL切换
            this.initBatchUrlSwitch();
            console.log('表单事件监听初始化完成');
        },
        
        // 初始化批量URL切换
        initBatchUrlSwitch() {
            const singleUrlBtn = document.getElementById('singleUrlBtn');
            const batchUrlBtn = document.getElementById('batchUrlBtn');
            const singleUrlSection = document.getElementById('singleUrlSection');
            const batchUrlSection = document.getElementById('batchUrlSection');
            const urlInput = document.getElementById('url');
            const batchUrlsTextarea = document.getElementById('batchUrls');
            
            if (singleUrlBtn && batchUrlBtn && singleUrlSection && batchUrlSection) {
                // 单个URL按钮点击事件
                singleUrlBtn.addEventListener('click', () => {
                    singleUrlBtn.classList.add('active');
                    batchUrlBtn.classList.remove('active');
                    singleUrlSection.style.display = 'block';
                    batchUrlSection.style.display = 'none';
                    urlInput.required = true;
                    batchUrlsTextarea.required = false;
                });
                
                // 批量URL按钮点击事件
                batchUrlBtn.addEventListener('click', () => {
                    singleUrlBtn.classList.remove('active');
                    batchUrlBtn.classList.add('active');
                    singleUrlSection.style.display = 'none';
                    batchUrlSection.style.display = 'block';
                    urlInput.required = false;
                    batchUrlsTextarea.required = true;
                });
            }
        },
        
        // 直接处理爬取操作
        async startCrawl() {
            console.log('开始执行爬取操作');
            
            // 获取表单元素
            const urlInput = document.getElementById('url');
            const batchUrlsTextarea = document.getElementById('batchUrls');
            const formatSelect = document.getElementById('format');
            const nextChaptersInput = document.getElementById('next_chapters');
            const prevChaptersInput = document.getElementById('prev_chapters');
            const submitBtn = document.querySelector('button[type="submit"]');
            const singleUrlBtn = document.getElementById('singleUrlBtn');
            
            console.log('获取表单元素完成:');
            console.log('urlInput:', urlInput);
            console.log('batchUrlsTextarea:', batchUrlsTextarea);
            console.log('formatSelect:', formatSelect);
            console.log('nextChaptersInput:', nextChaptersInput);
            console.log('prevChaptersInput:', prevChaptersInput);
            console.log('submitBtn:', submitBtn);
            console.log('singleUrlBtn:', singleUrlBtn);
            
            // 检查必要的DOM元素是否存在
            if (!submitBtn) {
                console.error('提交按钮不存在');
                ArticleCrawler.ui.showMessage('提交按钮不存在，请刷新页面重试', 'danger');
                return;
            }
            
            // 检查按钮是否已经在处理中，防止重复点击
            if (submitBtn.disabled) {
                console.log('按钮已经在处理中，防止重复点击');
                return;
            }
            console.log('按钮状态检查完成，开始处理表单数据');

            // 检查当前模式
            const isSingleUrlMode = singleUrlBtn && singleUrlBtn.classList.contains('active');
            let urls = [];
            
            // 验证表单数据
            if (isSingleUrlMode) {
                if (!urlInput) {
                    console.error('URL输入框不存在');
                    ArticleCrawler.ui.showMessage('URL输入框不存在，请刷新页面重试', 'danger');
                    return;
                }
                
                if (!urlInput.checkValidity()) {
                    urlInput.reportValidity();
                    return;
                }
                urls = [urlInput.value];
            } else {
                if (!batchUrlsTextarea) {
                    console.error('批量URL输入框不存在');
                    ArticleCrawler.ui.showMessage('批量URL输入框不存在，请刷新页面重试', 'danger');
                    return;
                }
                
                if (!batchUrlsTextarea.value.trim()) {
                    batchUrlsTextarea.setCustomValidity('请输入至少一个URL');
                    batchUrlsTextarea.reportValidity();
                    return;
                }
                
                // 解析批量URL，每行一个
                urls = batchUrlsTextarea.value
                    .split('\n')
                    .map(url => url.trim())
                    .filter(url => url && /^https?:\/\//.test(url));
                
                if (urls.length === 0) {
                    batchUrlsTextarea.setCustomValidity('请输入有效的URL');
                    batchUrlsTextarea.reportValidity();
                    return;
                }
                
                if (urls.length > 10) {
                    batchUrlsTextarea.setCustomValidity('一次最多支持10个URL');
                    batchUrlsTextarea.reportValidity();
                    return;
                }
            }
            
            // 重置自定义验证
            if (batchUrlsTextarea) {
                batchUrlsTextarea.setCustomValidity('');
            }
            
            // 检查其他必要的表单元素
            if (!formatSelect || !nextChaptersInput || !prevChaptersInput) {
                console.error('表单元素不完整');
                ArticleCrawler.ui.showMessage('表单元素不完整，请刷新页面重试', 'danger');
                return;
            }
            
            // 表单数据
            const baseFormData = {
                format: formatSelect.value,
                output_dir: './output', // 固定输出目录，由后端管理
                next_chapters: parseInt(nextChaptersInput.value) || 0,
                prev_chapters: parseInt(prevChaptersInput.value) || 0
            };
            
            // 准备要发送的数据
            const formData = {
                urls: urls,
                ...baseFormData
            };
            
            // 显示进度条和状态消息
            const progressBar = document.getElementById('progress-bar');
            const resultContainer = document.getElementById('result-container');
            
            // 保存原始按钮文本
            const originalBtnText = submitBtn.innerHTML;
            
            // 显示加载状态
            ArticleCrawler.ui.showLoading(submitBtn, '提交中...');
            if (progressBar) {
                ArticleCrawler.ui.updateProgress(progressBar, 10);
            }
            ArticleCrawler.ui.showMessage('正在提交爬取任务...', 'info');
            if (resultContainer) {
                resultContainer.style.display = 'none';
            }
            
            // 发送请求
            console.log('准备发送API请求');
            console.log('请求数据:', formData);
            try {
                const response = await ArticleCrawler.api.fetch('/crawl', {
                    method: 'POST',
                    body: JSON.stringify(formData)
                });
                console.log('API请求成功，响应:', response);
                
                if (!response.success) {
                    console.log('API请求失败:', response.error);
                    ArticleCrawler.ui.showMessage(`错误: ${response.error || '未知错误'}`, 'danger');
                    if (progressBar) {
                        ArticleCrawler.ui.hideProgress(progressBar);
                    }
                    ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                    return;
                }
                
                const taskIds = response.task_ids;
                const isSingleTask = taskIds && taskIds.length === 1;
                
                if (isSingleTask) {
                    const taskId = taskIds[0];
                    ArticleCrawler.ui.showMessage(`爬取任务已开始，任务ID: ${taskId}`, 'info');
                    if (progressBar) {
                        ArticleCrawler.ui.updateProgress(progressBar, 30);
                    }
                    
                    // 轮询任务状态
                    ArticleCrawler.tasks.pollTaskStatus(taskId, progressBar, submitBtn, originalBtnText);
                } else {
                    ArticleCrawler.ui.showMessage(`批量爬取任务已开始，共 ${taskIds ? taskIds.length : 0} 个任务`, 'info');
                    if (progressBar) {
                        ArticleCrawler.ui.updateProgress(progressBar, 30);
                    }
                    
                    // 批量任务处理逻辑
                    setTimeout(() => {
                        ArticleCrawler.ui.showMessage(`所有爬取任务已提交，正在处理中...`, 'info');
                        if (progressBar) {
                            ArticleCrawler.ui.hideProgress(progressBar);
                        }
                        ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                        
                        // 3秒后跳转到历史页面
                        setTimeout(() => {
                            window.location.href = 'history.html';
                        }, 3000);
                    }, 1000);
                }
            } catch (error) {
                console.error('API请求出错:', error);
                ArticleCrawler.ui.showMessage(`请求失败: ${error.message}`, 'danger');
                if (progressBar) {
                    ArticleCrawler.ui.hideProgress(progressBar);
                }
                ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
            }
        },
        
        // 处理表单提交
        async handleSubmit(e) {
            console.log('表单submit事件触发');
            e.preventDefault();
            // 调用startCrawl方法
            this.startCrawl();
        }
    },
    
    // 任务状态管理模块
    tasks: {
        // 轮询任务状态
        async pollTaskStatus(taskId, progressBar, submitBtn, originalBtnText, retryCount = 0) {
            const resultContainer = document.getElementById('result-container');
            const resultContent = document.getElementById('result-content');
            
            try {
                // 获取任务状态
                const response = await ArticleCrawler.api.fetch(`/task/${taskId}`);
                
                if (!response.success) {
                    ArticleCrawler.ui.showMessage(`错误: ${response.error || '未知错误'}`, 'danger');
                    if (progressBar) {
                        ArticleCrawler.ui.hideProgress(progressBar);
                    }
                    if (submitBtn) {
                        ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                    }
                    return;
                }
                
                const task = response.task;
                
                // 更新状态消息
                let statusText = '';
                let statusClass = '';
                let progressValue = 0;
                
                switch (task.status) {
                    case 'pending':
                        statusText = '任务等待中...';
                        statusClass = 'info';
                        progressValue = 20;
                        break;
                    case 'running':
                        statusText = '爬取进行中...';
                        statusClass = 'primary';
                        progressValue = 60;
                        break;
                    case 'completed':
                        statusText = '爬取完成！';
                        statusClass = 'success';
                        progressValue = 100;
                        
                        // 显示结果
                        if (resultContent) {
                            ArticleCrawler.tasks.showTaskResult(resultContent, task);
                        }
                        if (resultContainer) {
                            resultContainer.style.display = 'block';
                        }
                        if (progressBar) {
                            ArticleCrawler.ui.hideProgress(progressBar);
                        }
                        if (submitBtn) {
                            ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                        }
                        return;
                    case 'failed':
                        statusText = '爬取失败！';
                        statusClass = 'danger';
                        progressValue = 100;
                        
                        // 显示错误信息
                        if (resultContent) {
                            ArticleCrawler.tasks.showTaskError(resultContent, task);
                        }
                        if (resultContainer) {
                            resultContainer.style.display = 'block';
                        }
                        if (progressBar) {
                            ArticleCrawler.ui.hideProgress(progressBar);
                        }
                        if (submitBtn) {
                            ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                        }
                        return;
                }
                
                ArticleCrawler.ui.showMessage(statusText, statusClass);
                if (progressBar) {
                    ArticleCrawler.ui.updateProgress(progressBar, progressValue);
                }
                
                // 继续轮询
                setTimeout(() => {
                    this.pollTaskStatus(taskId, progressBar, submitBtn, originalBtnText);
                }, 1000);
            } catch (error) {
                // 重试逻辑
                if (retryCount < 3) {
                    // 显示重试提示
                    ArticleCrawler.ui.showMessage(`获取任务状态失败，${retryCount + 1}/3 秒后重试...`, 'warning');
                    // 1秒后重试
                    setTimeout(() => {
                        this.pollTaskStatus(taskId, progressBar, submitBtn, originalBtnText, retryCount + 1);
                    }, 1000);
                } else {
                    // 重试次数用完，显示错误信息
                    ArticleCrawler.ui.showMessage(`获取任务状态失败: ${error.message}。请刷新页面重试。`, 'danger');
                    if (progressBar) {
                        ArticleCrawler.ui.hideProgress(progressBar);
                    }
                    if (submitBtn) {
                        ArticleCrawler.ui.hideLoading(submitBtn, originalBtnText);
                    }
                }
            }
        },
        
        // 显示任务结果
        showTaskResult(container, task) {
            if (!container) return;
            
            let resultHtml = `
                <div class="card fade-in">
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
                                    <li class="list-group-item d-flex justify-content-between align-items-center fade-in">
                                        ${file}
                                        <div class="btn-group">
                                            <a href="/download/${task.output_dir}/${file}" class="btn btn-sm btn-outline-primary">下载</a>
                                            <button class="btn btn-sm btn-outline-info" onclick="ArticleCrawler.article.view('${task.output_dir}/${file}')">查看</button>
                                        </div>
                                    </li>
                                `).join('')}
                            </ul>
                        ` : ''}
                        
                        ${task.stdout ? `<div class="mt-3"><h6>标准输出:</h6><pre class="bg-light p-3 rounded">${task.stdout}</pre></div>` : ''}
                        ${task.stderr ? `<div class="mt-3"><h6>错误输出:</h6><pre class="bg-light p-3 rounded text-danger">${task.stderr}</pre></div>` : ''}
                    </div>
                </div>
            `;
            
            container.innerHTML = resultHtml;
        },
        
        // 显示任务错误
        showTaskError(container, task) {
            if (!container) return;
            
            let errorHtml = `
                <div class="card fade-in">
                    <div class="card-body">
                        <h5 class="card-title">任务详情</h5>
                        <p class="card-text"><strong>任务ID:</strong> ${task.id}</p>
                        <p class="card-text"><strong>URL:</strong> ${task.url}</p>
                        <p class="card-text"><strong>输出格式:</strong> ${task.format}</p>
                        <p class="card-text"><strong>向后爬取:</strong> ${task.next_chapters} 章</p>
                        <p class="card-text"><strong>向前爬取:</strong> ${task.prev_chapters} 章</p>
                        <p class="card-text text-danger"><strong>错误信息:</strong> ${task.error}</p>
                        ${task.stderr ? `<div class="mt-3"><h6>错误输出:</h6><pre class="bg-light p-3 rounded text-danger">${task.stderr}</pre></div>` : ''}
                    </div>
                </div>
            `;
            
            container.innerHTML = errorHtml;
        },
        
        // 查询任务状态
        query() {
            try {
                const taskIdInput = document.getElementById('taskIdInput');
                const progressBar = document.getElementById('progress-bar');
                const submitBtn = document.querySelector('button[type="submit"]');
                
                // 检查必要的DOM元素是否存在
                if (!taskIdInput) {
                    console.error('任务ID输入框不存在');
                    ArticleCrawler.ui.showMessage('任务ID输入框不存在，请刷新页面重试', 'danger');
                    return;
                }
                
                const taskId = taskIdInput.value.trim();
                
                if (!taskId) {
                    ArticleCrawler.ui.showMessage('请输入任务ID', 'warning');
                    return;
                }
                
                // 显示进度条和状态消息
                if (progressBar) {
                    ArticleCrawler.ui.updateProgress(progressBar, 10);
                }
                ArticleCrawler.ui.showMessage(`正在查询任务 ${taskId} 的状态...`, 'info');
                
                // 调用轮询函数，开始查询任务状态
                if (submitBtn) {
                    ArticleCrawler.tasks.pollTaskStatus(taskId, progressBar, submitBtn, submitBtn.innerHTML);
                } else {
                    ArticleCrawler.tasks.pollTaskStatus(taskId, progressBar, null, '');
                }
            } catch (error) {
                console.error('查询任务状态失败:', error);
                ArticleCrawler.ui.showMessage(`查询任务状态失败: ${error.message}`, 'danger');
            }
        }
    },
    
    // 文章查看模块
    article: {
        // 初始化文章导航
        initNavigation() {
            const prevBtn = document.getElementById('prevArticle');
            const nextBtn = document.getElementById('nextArticle');
            
            if (prevBtn) {
                prevBtn.addEventListener('click', function() {
                    const prevUrl = this.getAttribute('data-url');
                    if (prevUrl) {
                        ArticleCrawler.article.view(prevUrl);
                    }
                });
            }
            
            if (nextBtn) {
                nextBtn.addEventListener('click', function() {
                    const nextUrl = this.getAttribute('data-url');
                    if (nextUrl) {
                        ArticleCrawler.article.view(nextUrl);
                    }
                });
            }
        },
        
        // 查看文章内容
        view(filename) {
            // 直接跳转到文章展示页面
            window.location.href = `/article/${filename}`;
        }
    },
    
    // 历史记录模块
    history: {
        // 加载历史记录
        async load() {
            const historyContainer = document.getElementById('history-container');
            if (!historyContainer) return;
            
            try {
                // 显示加载状态
                historyContainer.innerHTML = '<div class="text-center py-5"><span class="spinner-border spinner-border-lg" role="status" aria-hidden="true"></span><br>加载历史记录...</div>';
                
                // 获取历史记录
                const response = await ArticleCrawler.api.fetch('/history');
                
                if (!response.success) {
                    historyContainer.innerHTML = `<div class="alert alert-danger" role="alert">加载历史记录失败: ${response.error || '未知错误'}</div>`;
                    return;
                }
                
                const history = response.history;
                
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
                        <div class="history-item fade-in">
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
            } catch (error) {
                historyContainer.innerHTML = `<div class="alert alert-danger" role="alert">加载历史记录失败: ${error.message}</div>`;
            }
        }
    },
    
    // API配置界面模块
    config: {
        // 添加API配置按钮
        addConfigButton() {
            const configButton = document.createElement('button');
            configButton.className = 'btn btn-outline-secondary';
            configButton.innerHTML = '<i class="bi bi-gear"></i> API配置';
            configButton.onclick = function() {
                // 显示模态对话框
                ArticleCrawler.config.showConfigModal();
            };
            
            // 添加到适当位置
            const container = document.querySelector('.container');
            if (container) {
                const configDiv = document.createElement('div');
                configDiv.className = 'd-flex justify-content-end mb-3';
                configDiv.appendChild(configButton);
                container.insertBefore(configDiv, container.firstChild);
            }
            
            // 初始化模态对话框事件
            this.initModalEvents();
        },
        
        // 显示配置模态对话框
        showConfigModal() {
            try {
                // 获取当前API URL
                const currentUrl = ArticleCrawler.api.getBaseUrl();
                
                // 设置输入框值
                const apiBaseUrlInput = document.getElementById('apiBaseUrl');
                if (apiBaseUrlInput) {
                    apiBaseUrlInput.value = currentUrl;
                }
                
                // 显示模态对话框
                const apiConfigModal = document.getElementById('apiConfigModal');
                if (apiConfigModal) {
                    const modal = new bootstrap.Modal(apiConfigModal);
                    modal.show();
                    
                    // 聚焦到输入框
                    if (apiBaseUrlInput) {
                        apiBaseUrlInput.focus();
                    }
                }
            } catch (error) {
                console.error('显示配置模态对话框失败:', error);
                ArticleCrawler.ui.showMessage('显示配置界面失败，请刷新页面重试', 'danger');
            }
        },
        
        // 初始化模态对话框事件
        initModalEvents() {
            try {
                const apiConfigForm = document.getElementById('apiConfigForm');
                if (apiConfigForm) {
                    apiConfigForm.addEventListener('submit', (e) => {
                        e.preventDefault();
                        
                        const apiBaseUrl = document.getElementById('apiBaseUrl');
                        if (apiBaseUrl && apiBaseUrl.value.trim() !== '') {
                            // 保存API URL
                            ArticleCrawler.api.setBaseUrl(apiBaseUrl.value.trim());
                            
                            // 关闭模态对话框
                            const apiConfigModal = document.getElementById('apiConfigModal');
                            if (apiConfigModal) {
                                const modal = bootstrap.Modal.getInstance(apiConfigModal);
                                if (modal) {
                                    modal.hide();
                                }
                            }
                        }
                    });
                }
            } catch (error) {
                console.error('初始化模态对话框事件失败:', error);
            }
        }
    },
    
    // 初始化应用
    init() {
        // 添加API配置按钮
        this.config.addConfigButton();
        
        // 初始化表单处理
        this.form.init();
        
        // 根据页面类型进行初始化
        const currentPage = document.body.getAttribute('data-page');
        
        switch (currentPage) {
            case 'article':
                this.article.initNavigation();
                break;
            case 'history':
                this.history.load();
                break;
            default:
                // 首页不需要额外初始化
                break;
        }
    }
};

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', function() {
    ArticleCrawler.init();
});

// 暴露全局函数，兼容现有HTML调用
function queryTaskStatus() {
    ArticleCrawler.tasks.query();
}

function setUrl(baseUrl) {
    document.getElementById('url').value = baseUrl;
}

function refreshPage() {
    window.location.reload();
}