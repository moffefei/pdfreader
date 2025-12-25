# Paper Whisperer - 论文深度解读 Agent

让 AI 替你读完顶级论文，并翻译解读，生成论文介绍的公众号文章，还能生成小红书流行的笔记图片。

## 功能特性

- 📄 PDF 论文解析：自动提取文本、图片和元数据
- 🤖 AI 深度解读：使用多模态大模型理解论文内容
- 🌐 多语言翻译：支持中英文翻译
- 📝 公众号文章生成：生成 Markdown 格式的科普文章
- 📸 小红书笔记生成：生成精美的笔记图片

## 技术架构

- **PDF 处理**: pdfplumber, pypdfium2, pdf2image
- **LLM 调用**: OpenAI 兼容接口（302.ai）、Qwen API
- **Web 框架**: FastAPI
- **图片生成**: HTML+CSS 渲染为图片

## 安装

1. 克隆项目
```bash
git clone <repository-url>
cd pdfreader
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 安装 playwright（用于图片生成）
```bash
playwright install chromium
```

4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API 密钥
```

## 使用方法

### 启动 Web 服务

方式一：使用启动脚本
```bash
python run.py
```

方式二：直接使用 uvicorn
```bash
uvicorn paper_whisperer.app:app --reload
```

访问 http://localhost:8000 使用 Web 界面。

### API 接口

- `GET /` - 前端页面
- `POST /upload` - 上传 PDF 文件
- `POST /analyze` - 分析论文
- `GET /status/{task_id}` - 查询处理状态
- `GET /result/{task_id}` - 获取处理结果
- `GET /download/article/{task_id}` - 下载公众号文章
- `GET /download/note/{task_id}` - 下载小红书笔记
- `GET /download/image/{task_id}` - 下载小红书笔记图片

## 配置说明

在 `.env` 文件中配置：

- `OPENAI_API_KEY`: OpenAI API 密钥（用于 302.ai）
- `QWEN_API_KEY`: Qwen API 密钥
- `DEFAULT_MODEL`: 默认使用的模型
- `DEFAULT_VISION_MODEL`: 多模态模型

## 项目结构

```
paper_whisperer/
├── __init__.py
├── config.py              # 配置管理
├── pdf_processor.py       # PDF 处理
├── llm_client.py          # LLM 客户端
├── paper_analyzer.py      # 论文分析
├── content_generator.py   # 内容生成
├── image_generator.py     # 图片生成
├── app.py                 # FastAPI Web 应用
└── templates/             # HTML 模板
    └── xiaohongshu.html   # 小红书笔记模板
```

## 许可证

MIT License

