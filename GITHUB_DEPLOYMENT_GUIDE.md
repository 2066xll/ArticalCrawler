# GitHub部署指南

## 1. 准备工作

### 步骤1：创建GitHub账号

如果您还没有GitHub账号，请先创建一个：

1. 访问 [GitHub官网](https://github.com/)
2. 点击"Sign up"
3. 按照提示完成注册

### 步骤2：安装Git

确保您的计算机上已经安装了Git：

```bash
git --version
```

如果没有安装，请访问 [Git官网](https://git-scm.com/) 下载并安装。

## 2. 创建GitHub仓库

### 步骤1：登录GitHub

1. 访问 [GitHub登录页面](https://github.com/login)
2. 使用您的GitHub账号登录

### 步骤2：创建仓库

1. 登录后，点击右上角的"+"按钮，选择"New repository"
2. 填写仓库信息：
   - Repository name: `article-crawler`
   - Description: 文章爬取工具
   - Visibility: Public
3. 点击"Create repository"

## 3. 将本地项目推送到GitHub

### 步骤1：初始化Git仓库（如果尚未初始化）

如果您的本地项目还没有初始化Git仓库，请运行：

```bash
git init
git add .
git commit -m "Initial commit"
```

### 步骤2：添加远程仓库

在GitHub仓库页面，复制仓库URL，然后运行：

```bash
git remote add origin <repository-url>
```

### 步骤3：推送到GitHub

运行以下命令将本地项目推送到GitHub：

```bash
git push -u origin main
```

## 4. 使用GitHub Pages部署（静态内容）

GitHub Pages只支持静态网站部署。由于您的项目是基于Python Flask的后端应用，直接部署到GitHub Pages可能会有一些限制。但是，您可以考虑以下选项：

### 选项1：仅部署前端

1. 将前端文件提取到一个单独的目录
2. 推送到GitHub
3. 在仓库设置中启用GitHub Pages

### 选项2：使用GitHub Actions + 静态生成

1. 使用GitHub Actions构建静态网站
2. 将构建后的静态文件推送到GitHub Pages分支

### 选项3：使用GitHub Pages + Cloudflare Workers

1. 将前端部署到GitHub Pages
2. 使用Cloudflare Workers处理API请求

## 5. 后续步骤

### 1. 访问GitHub仓库

在浏览器中访问您的GitHub仓库，确认代码已经成功推送。

### 2. 部署到其他平台

如果您需要部署完整的后端应用，建议考虑使用Vercel、Heroku、PythonAnywhere等支持Python的平台。

### 3. 更新项目

每当您对本地项目进行更改后，运行以下命令将更改推送到GitHub：

```bash
git add .
git commit -m "Update description"
git push
```

## 6. 常见问题

### 问题1：推送失败，提示权限问题

解决方案：确保您的GitHub账号有权限推送到该仓库。

### 问题2：推送失败，提示分支不存在

解决方案：尝试使用以下命令创建分支并推送：

```bash
git push -u origin HEAD:main
```

### 问题3：GitHub Pages不显示我的内容

解决方案：确保您的仓库中有静态HTML文件，并且已经在设置中启用了GitHub Pages。

## 7. 进一步阅读

- [GitHub Pages官方文档](https://docs.github.com/en/pages)
- [Git官方文档](https://git-scm.com/doc)
- [Vercel部署指南](https://vercel.com/docs/concepts/deployments/overview)

## 8. 联系支持

如果您在部署过程中遇到任何问题，可以：

1. 查看GitHub官方文档
2. 搜索GitHub社区
3. 联系GitHub支持

祝您部署顺利！
