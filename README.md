# 文章爬取工具

一个基于Python Flask的文章爬取工具，支持多章节爬取、文章预览和章节导航功能。

## 功能特性

- 支持多章节爬取
- 支持上一章和下一章导航
- 支持文章预览
- 支持多种输出格式（TXT、Markdown）
- 支持向前和向后爬取
- 支持文件列表排序
- 支持文章内容的优雅展示
- 支持Cloudflare Pages部署

## 技术栈

- Python Flask
- BeautifulSoup4
- Bootstrap 5
- Cloudflare Pages

## 安装和使用

### 本地安装

1. 克隆项目到本地

```bash
git clone <repository-url>
cd article-crawler
```

2. 创建虚拟环境并激活

```bash
python -m venv .venv
source .venv/bin/activate
```

3. 安装依赖

```bash
pip install -r requirements.txt
```

4. 运行应用

```bash
python app.py
```

5. 在浏览器中访问 `http://127.0.0.1:5001`

### 命令行使用

```bash
python article_crawler.py "<url>" -f <format> -o <output_dir> -n <chapters> -p <prev_chapters>
```

- `<url>`: 要爬取的文章链接
- `<format>`: 输出格式（txt或md）
- `<output_dir>`: 输出目录
- `<chapters>`: 向后爬取的章节数
- `<prev_chapters>`: 向前爬取的章节数

## 部署方案

### 选项1：完整Flask应用部署（推荐）

**支持平台**：Vercel、Render、Railway、AWS EC2等

#### 部署到Vercel

1. 将项目推送到GitHub仓库

2. 登录Vercel控制台，点击"Add New Project"

3. 选择你的GitHub仓库

4. 配置项目：
   - Framework Preset: `Other`
   - Build Command: `pip install -r requirements.txt`
   - Output Directory: 留空
   - Install Command: `pip install -r requirements.txt`
   - Development Command: `python app.py`

5. 点击"Deploy"

#### 部署到Render

1. 将项目推送到GitHub仓库

2. 登录Render控制台，点击"New Web Service"

3. 选择你的GitHub仓库

4. 配置项目：
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`

5. 点击"Create Web Service"

### 选项2：静态前端+分离后端部署

**前端部署到Cloudflare Pages**

1. 将项目推送到GitHub仓库

2. 登录Cloudflare控制台，选择Pages > Create a project

3. 连接GitHub仓库

4. 配置构建命令和输出目录：
   - Build Command: `echo 'Building static frontend...'`
   - Output Directory: `frontend`

5. 点击"Deploy site"

**后端部署到支持Python的平台**

1. 将后端API部署到Vercel、Render或其他Python支持平台

2. 配置前端API请求指向后端服务URL：
   - 在前端页面点击右上角的"API配置"按钮
   - 输入后端服务的完整URL（例如：`https://your-backend-api.vercel.app/api`）
   - 点击"确定"保存配置

### 选项3：仅静态前端部署（功能受限）

1. 将项目推送到GitHub仓库

2. 登录Cloudflare Pages或GitHub Pages

3. 部署`frontend/`目录下的静态文件

4. 注意：API功能将不可用，仅展示前端界面

## 自动部署配置

项目已配置GitHub Actions自动部署，当推送到main/master分支时：

1. 自动运行构建和测试
2. 自动部署到Vercel（需要配置Secrets）
3. 自动部署到Cloudflare Pages（需要配置Secrets）

## API端点配置

前端提供了API配置功能，方便用户根据部署环境灵活配置API请求地址：

1. 在前端页面点击右上角的"API配置"按钮
2. 输入API基础URL（例如：`/api`或`https://your-backend-api.vercel.app/api`）
3. 点击"确定"保存配置

配置将保存在浏览器本地存储中，刷新页面后仍然有效。

## 项目结构

```
article-crawler/
├── app.py                   # Flask应用主文件
├── article_crawler.py        # 文章爬取脚本
├── requirements.txt          # Python依赖列表
├── _worker.js                # Cloudflare Workers配置
├── wrangler.toml             # Cloudflare Pages配置
├── vercel.json               # Vercel部署配置
├── .gitignore                # Git忽略文件
├── frontend/                 # 静态前端目录
│   ├── index.html           # 首页
│   ├── article.html         # 文章展示页
│   ├── history.html         # 历史记录页
│   ├── stats.html           # 统计分析页
│   ├── css/                 # CSS样式文件
│   └── js/                  # JavaScript文件
├── templates/                # Flask模板目录
│   ├── index.html           # 首页模板
│   ├── article.html         # 文章展示模板
│   └── history.html         # 历史记录模板
├── worker/                   # Cloudflare Workers开发目录
└── .github/workflows/       # GitHub Actions工作流配置
```

## 配置文件

### requirements.txt

列出了项目所需的所有依赖。

### .gitignore

指定了Git忽略的文件和目录。

## 开发说明

1. 文章爬取逻辑在 `article_crawler.py` 中实现
2. Flask应用逻辑在 `app.py` 中实现
3. 前端模板在 `templates/` 目录中
4. 静态文件在 `static/` 目录中

## 许可证

MIT License
