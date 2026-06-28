# yuan-wiki-archive

这是一个用于备份代号鸢 BWiki 公开页面文本、HTML 和页面元数据的 Python 项目。

## 项目作用

这个项目会从 BWiki 的 MediaWiki API 中抓取公开页面数据，保存以下内容：

- 搜索结果 JSON
- 每个页面的 HTML 文件
- 每个页面的 JSON 元数据文件
- 纯文本内容
- 页面索引文件

不会下载图片、音频或视频。

## 为什么使用 MediaWiki API，而不是 Selenium

MediaWiki API 更适合这个场景，因为它：

- 结构化明确，便于获取搜索结果和页面内容
- 请求速度更快，适合批量抓取
- 不需要打开浏览器，也更容易自动化
- 更适合保存公开文本和元数据

Selenium 主要适合处理复杂前端交互，但这个任务只需要接口数据，API 更轻量也更稳定。

## 安装依赖

在项目根目录执行：

```bash
pip install -r requirements.txt
```

## 搜索左慈页面

运行下面的命令即可：

```bash
python crawl_search.py
```

默认关键词是“左慈”。如果想换关键词，可以这样做：

```bash
python crawl_search.py "张三"
```

结果会保存到：

- data/search_leftci.json

## 抓取页面

先执行搜索，再抓取页面：

```bash
python crawl_search.py
python crawl_pages.py
```

抓取结果会保存到：

- data/pages_json/：每个页面的 JSON 文件
- data/pages_html/：每个页面的 HTML 文件
- data/index.json：总索引文件

## 估算占用空间

运行：

```bash
python estimate_size.py
```

它会输出 JSON 文件总大小、HTML 文件总大小、页面数量，以及总大小（MB）。

## 注意事项

- 仅用于个人学习和研究用途。
- 不要高频请求 Wiki 服务。
- 不要公开整包转载抓取结果。
- 需要遵守目标站点的使用条款和机器人政策。
