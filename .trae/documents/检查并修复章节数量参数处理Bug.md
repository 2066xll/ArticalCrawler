# 检查并修复章节数量参数处理Bug

## 问题分析

通过分析代码和测试结果，发现以下关键Bug：

### 1. **app.py中的语法错误和冗余变量**
- Line 57存在语法错误：注释未正确分隔，导致代码与注释合并
- 定义了两个冗余变量：`crawler_next_chapters` 和 `adjusted_next_chapters`，只使用了后者

### 2. **章节数量参数转换逻辑错误**
- **核心问题**：当用户在Web界面输入3章时，app.py会将其转换为 `-n 2` 传递给 article_crawler.py
- 但 article_crawler.py 现在直接使用 `-n` 参数作为总章节数（包括当前章节）
- 这导致实际爬取的章节数比用户期望少1章

### 3. **参数解释不一致**
- Web界面的"爬取章节数量"表示总章节数
- article_crawler.py 现在也将 `-n` 参数解释为总章节数
- 但 app.py 仍在执行旧的转换逻辑，导致不匹配

## 修复方案

### 1. 修复app.py中的语法错误和冗余变量
- 将合并的代码和注释分开
- 移除未使用的 `crawler_next_chapters` 变量

### 2. 修正章节数量参数转换逻辑
- 移除 app.py 中不必要的参数转换
- 直接将用户输入的章节数作为 `-n` 参数传递给 article_crawler.py

### 3. 确保参数一致性
- 保持Web界面、app.py和article_crawler.py之间的参数解释一致
- 所有地方都将"章节数量"解释为总章节数（包括当前章节）

## 修复步骤

1. **修改app.py中的run_crawler函数**
   - 修复语法错误
   - 移除冗余变量
   - 修正参数转换逻辑

2. **测试修复效果**
   - 使用Web界面输入3章，验证是否爬取3章
   - 直接运行article_crawler.py测试参数
   - 检查历史记录和生成的文件数量

## 预期效果

- 用户在Web界面输入3章时，实际爬取3章
- 直接运行 `article_crawler.py -n 3` 时，爬取3章
- 代码逻辑清晰，无语法错误和冗余变量

## 修复后的代码片段

```python
# app.py中的run_crawler函数
# 构建命令
# 用户输入的next_chapters表示要爬取的总章节数，包括当前章节
# article_crawler.py的-n参数现在也表示总章节数，所以直接传递
command = f'python3 article_crawler.py "{url}" -f {format} -o "{output_dir}" -n {next_chapters}'
tasks[task_id]['command'] = command
```