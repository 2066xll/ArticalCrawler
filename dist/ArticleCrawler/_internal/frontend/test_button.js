// 测试按钮点击事件的脚本
console.log('测试脚本加载成功');

// 直接测试按钮点击
function testButtonClick() {
    console.log('开始测试按钮点击');
    
    // 获取提交按钮
    const submitBtn = document.querySelector('button[type="submit"]');
    console.log('submitBtn:', submitBtn);
    
    if (submitBtn) {
        console.log('提交按钮存在，测试点击事件');
        
        // 模拟点击
        submitBtn.click();
        console.log('模拟点击完成');
        
        // 测试直接触发表单提交
        const form = document.getElementById('crawl-form');
        console.log('form:', form);
        if (form) {
            console.log('表单存在，测试直接触发表单提交');
            form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
            console.log('表单提交事件触发完成');
        }
    }
}

// 测试事件监听器绑定
function testEventListeners() {
    console.log('开始测试事件监听器绑定');
    
    const form = document.getElementById('crawl-form');
    console.log('form:', form);
    
    if (form) {
        console.log('表单存在，检查事件监听器');
        
        // 获取所有事件监听器
        const listeners = getEventListeners(form);
        console.log('表单事件监听器:', listeners);
        
        // 检查submit事件监听器
        if (listeners.submit) {
            console.log('submit事件监听器存在:', listeners.submit);
        } else {
            console.log('submit事件监听器不存在');
        }
    }
    
    const submitBtn = document.querySelector('button[type="submit"]');
    console.log('submitBtn:', submitBtn);
    
    if (submitBtn) {
        console.log('提交按钮存在，检查事件监听器');
        
        // 获取所有事件监听器
        const listeners = getEventListeners(submitBtn);
        console.log('按钮事件监听器:', listeners);
        
        // 检查click事件监听器
        if (listeners.click) {
            console.log('click事件监听器存在:', listeners.click);
        } else {
            console.log('click事件监听器不存在');
        }
    }
}

// 测试ArticleCrawler对象
function testArticleCrawler() {
    console.log('开始测试ArticleCrawler对象');
    console.log('ArticleCrawler:', ArticleCrawler);
    
    if (ArticleCrawler) {
        console.log('ArticleCrawler对象存在');
        console.log('ArticleCrawler.form:', ArticleCrawler.form);
        console.log('ArticleCrawler.form.handleSubmit:', ArticleCrawler.form.handleSubmit);
        
        // 测试直接调用handleSubmit方法
        if (ArticleCrawler.form.handleSubmit) {
            console.log('尝试直接调用handleSubmit方法');
            try {
                // 创建一个模拟的事件对象
                const mockEvent = {
                    preventDefault: function() {
                        console.log('preventDefault called');
                    }
                };
                
                ArticleCrawler.form.handleSubmit(mockEvent);
                console.log('直接调用handleSubmit方法成功');
            } catch (error) {
                console.error('直接调用handleSubmit方法失败:', error);
            }
        }
    }
}

// 运行所有测试
function runAllTests() {
    console.log('====================================');
    console.log('运行所有测试');
    console.log('====================================');
    
    testButtonClick();
    console.log('------------------------------------');
    testEventListeners();
    console.log('------------------------------------');
    testArticleCrawler();
    console.log('====================================');
    console.log('测试完成');
}

// 页面加载完成后运行测试
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', runAllTests);
} else {
    runAllTests();
}
