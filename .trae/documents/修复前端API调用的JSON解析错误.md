## 问题分析

错误信息：`Failed to execute 'json' on 'Response': Unexpected end of JSON input`

这是因为前端在调用API时，直接尝试将响应解析为JSON，但没有检查响应是否成功或是否为空。当后端返回空响应或非JSON格式响应时，就会出现这个错误。

## 解决方案

修改前端JavaScript代码，在所有fetch调用中添加响应状态检查和错误处理：

### 1. 修改 `frontend/js/app.js`

* 在 `handleCrawlSubmit` 函数中的fetch调用添加错误处理

* 在 `pollTaskStatus` 函数中的fetch调用添加错误处理

* 在 `loadHistory` 函数中的fetch调用添加错误处理

### 2. 修改 `frontend/article.html`

* 在 `loadArticle` 函数中的fetch调用添加错误处理

### 3. 实现统一的fetch错误处理逻辑

在所有fetch调用中，添加以下检查：

```javascript
fetch(url)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text(); // 先获取文本，再尝试解析JSON
    })
    .then(text => {
        if (!text) {
            throw new Error('空响应');
        }
        return JSON.parse(text); // 显式解析JSON，捕获解析错误
    })
    .then(data => {
        // 处理成功响应
    })
    .catch(error => {
        // 处理错误
    });
```

## 预期效果

* 修复JSON解析错误

* 提供更友好的错误信息

* 增强前端代码的健壮性

* 减少因API响应问题导致的页面崩溃

