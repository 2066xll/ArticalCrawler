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

## 部署到Cloudflare Pages

1. 将项目推送到Github

2. 登录Cloudflare控制台

3. 选择Pages > Create a project

4. 连接Github仓库

5. 配置构建命令和输出目录

6. 点击Deploy site

## 项目结构

```
article-crawler/
├── app.py                   # Flask应用主文件
├── article_crawler.py        # 文章爬取脚本
├── requirements.txt          # 依赖列表
├── .gitignore               # Git忽略文件
├── data/                    # 数据文件目录
├── templates/               # HTML模板目录
│   ├── index.html          # 首页模板
│   ├── article.html        # 文章展示模板
│   └── history.html        # 历史记录模板
└── static/                 # 静态文件目录
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
