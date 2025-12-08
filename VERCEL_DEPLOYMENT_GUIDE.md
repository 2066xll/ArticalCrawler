# Vercel部署指南

## 1. 创建GitHub仓库

### 步骤1：创建GitHub仓库

1. 登录GitHub账号
2. 点击右上角的"+"按钮，选择"New repository"
3. 填写仓库信息：
   - Repository name: `article-crawler`
   - Description: 文章爬取工具
   - Visibility: Public
4. 点击"Create repository"

### 步骤2：将本地项目推送到GitHub

1. 在GitHub仓库页面，复制仓库URL
2. 在本地项目目录中运行以下命令：

```bash
# 添加远程仓库
git remote add origin <repository-url>

# 推送到GitHub
git push -u origin main
```

## 2. 部署到Vercel

### 步骤1：创建Vercel账号

1. 访问 [Vercel官网](https://vercel.com/)
2. 点击"Sign Up"
3. 使用GitHub账号登录

### 步骤2：创建Vercel项目

1. 登录后，点击"New Project"
2. 在"Import Git Repository"页面，选择你的GitHub仓库 `article-crawler`
3. 点击"Import"

### 步骤3：配置项目

1. 在"Configure Project"页面：
   - Framework Preset: 选择"Other"
   - Build Command: 留空
   - Output Directory: 留空
   - Install Command: `pip install -r requirements.txt`

2. 点击"Deploy"

### 步骤4：等待部署完成

Vercel将自动构建和部署你的项目。部署完成后，你将看到一个成功页面，显示你的应用URL。

## 3. 访问应用

1. 在Vercel项目页面，点击"Visit"按钮
2. 或者直接访问提供的URL，如 `https://article-crawler.vercel.app`

## 4. 配置环境变量（可选）

如果你的应用需要环境变量，可以在Vercel项目设置中配置：

1. 进入Vercel项目页面
2. 点击"Settings"
3. 点击"Environment Variables"
4. 添加所需的环境变量
5. 点击"Save"

## 5. 持续部署

每当你推送到GitHub仓库，Vercel将自动重新部署你的应用。

## 6. 常见问题

### 问题1：部署失败，提示找不到依赖

解决方案：确保 `requirements.txt` 文件包含所有必要的依赖。

### 问题2：应用无法访问

解决方案：检查Vercel项目的部署日志，查看是否有错误信息。

### 问题3：端口问题

解决方案：确保你的应用使用Vercel提供的端口：

```python
if __name__ == '__main__':
    import os
    app.run(debug=False, host='0.0.0.0', port=os.environ.get('PORT', 5000))
```

## 7. 后续维护

- 定期更新依赖
- 定期检查应用日志
- 定期备份数据
- 监控应用性能

## 8. 其他部署选项

如果Vercel不适合你的需求，你可以考虑以下部署选项：

- [Heroku](https://www.heroku.com/)
- [PythonAnywhere](https://www.pythonanywhere.com/)
- [AWS Elastic Beanstalk](https://aws.amazon.com/elasticbeanstalk/)
- [Google App Engine](https://cloud.google.com/appengine)
- [Azure App Service](https://azure.microsoft.com/en-us/services/app-service/)

详细的部署说明请参考 `DEPLOYMENT.md` 文件。
