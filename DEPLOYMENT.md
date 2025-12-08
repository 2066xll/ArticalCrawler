# Cloudflare Pages部署说明

## 注意事项

文章爬取工具是一个基于Python Flask的后端应用，而Cloudflare Pages主要用于静态网站托管。直接部署Flask应用到Cloudflare Pages是不支持的，因为Cloudflare Pages不支持Python后端。

## 解决方案

对于Flask应用，我们建议部署到支持Python的平台，如：

1. Vercel
2. Heroku
3. PythonAnywhere
4. AWS Elastic Beanstalk
5. Google App Engine
6. Azure App Service

## 静态网站部署（仅前端）

如果您只想部署前端部分，可以按照以下步骤操作：

1. 创建一个静态网站目录

```bash
mkdir static-site
cp -r templates/* static-site/
cp -r static/* static-site/
```

2. 修改静态网站的HTML文件，将所有API请求替换为静态内容

3. 将静态网站目录推送到Github

4. 登录Cloudflare控制台

5. 选择Pages > Create a project

6. 连接Github仓库

7. 配置构建命令和输出目录

8. 点击Deploy site

## 使用Cloudflare Workers作为后端

您也可以使用Cloudflare Workers作为后端，与静态前端结合：

1. 将前端部署到Cloudflare Pages

2. 为后端API创建Cloudflare Workers

3. 修改前端的API请求，指向Cloudflare Workers端点

## 部署到支持Python的平台

### Vercel部署

1. 将项目推送到Github

2. 登录Vercel控制台

3. 点击New Project

4. 连接Github仓库

5. 选择Python作为运行时

6. 配置环境变量

7. 点击Deploy

### Heroku部署

1. 创建Heroku账号

2. 安装Heroku CLI

3. 登录Heroku

```bash
heroku login
```

4. 创建Heroku应用

```bash
heroku create <app-name>
```

5. 推送代码到Heroku

```bash
git push heroku main
```

6. 打开应用

```bash
heroku open
```

## 结论

文章爬取工具是一个基于Python Flask的后端应用，不适合直接部署到Cloudflare Pages。我们建议将其部署到支持Python的平台，如Vercel、Heroku或PythonAnywhere。

如果您有任何问题，请随时联系我们。
