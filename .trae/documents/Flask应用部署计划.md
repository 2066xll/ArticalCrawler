# Flask应用部署计划

## 当前状态分析

1. **项目类型**：基于Python Flask的后端应用
2. **主要功能**：文章爬取、多章节导航、文章预览
3. **技术栈**：Python Flask、BeautifulSoup4、Bootstrap 5
4. **部署限制**：Cloudflare Pages不支持Python后端，不适合直接部署

## 部署方案

### 推荐方案：部署到Vercel

Vercel是一个支持Python后端的平台，部署流程简单，适合快速部署Flask应用。

### 部署步骤

#### 1. 准备项目

- 确保项目已经推送到Github
- 确保项目包含`requirements.txt`文件
- 确保项目包含`app.py`作为主入口文件

#### 2. 配置Vercel部署

- 创建`vercel.json`配置文件，指定构建和运行时配置
- 确保Flask应用使用正确的端口
- 配置环境变量

#### 3. 部署到Vercel

- 连接Github仓库到Vercel
- 配置部署设置
- 触发部署

## 实现细节

### 1. 创建vercel.json配置文件

```json
{
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app.py"
    }
  ]
}
```

### 2. 配置Flask应用端口

确保Flask应用使用Vercel提供的端口：

```python
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=os.environ.get('PORT', 5000))
```

### 3. 部署到Vercel

1. 登录Vercel控制台
2. 点击New Project
3. 连接Github仓库
4. 选择Python作为运行时
5. 配置环境变量
6. 点击Deploy

## 预期效果

- 项目成功部署到Vercel
- 可以通过Vercel提供的域名访问应用
- 应用可以正常运行
- 文章爬取和预览功能正常工作

## 备选方案

### 方案2：部署到Heroku

1. 安装Heroku CLI
2. 登录Heroku
3. 创建Heroku应用
4. 推送代码到Heroku
5. 配置环境变量

### 方案3：部署到PythonAnywhere

1. 创建PythonAnywhere账号
2. 上传项目文件
3. 创建Web应用
4. 配置WSGI文件
5. 启动Web应用

## 部署验证

部署完成后，通过以下方式验证：

1. 访问应用域名，检查首页是否正常显示
2. 测试文章爬取功能
3. 测试文章预览功能
4. 测试上一章和下一章导航功能

## 注意事项

- 确保所有依赖都在requirements.txt中列出
- 确保应用使用正确的端口
- 确保应用在生产环境中关闭debug模式
- 确保应用使用正确的环境变量

## 后续维护

- 定期更新依赖
- 定期检查应用日志
- 定期备份数据
- 监控应用性能

## 部署时间估计

- 准备项目：10分钟
- 配置Vercel：5分钟
- 部署到Vercel：5分钟
- 验证部署：5分钟

总计：25分钟
