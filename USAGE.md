# Paper Whisperer 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装 Playwright（用于图片生成）

```bash
playwright install chromium
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.302.ai/v1

QWEN_API_KEY=your_qwen_api_key_here
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 4. 启动服务

```bash
python run.py
```

访问 http://localhost:8000

## 使用流程

1. **上传 PDF 文件**
   - 点击上传区域或拖拽 PDF 文件
   - 系统会自动检查文件大小和页数

2. **开始分析**
   - 点击"开始分析"按钮
   - 系统会显示处理进度

3. **下载结果**
   - 处理完成后，可以下载：
     - 公众号文章（Markdown 格式）
     - 小红书笔记（Markdown 格式）
     - 小红书笔记图片（PNG 格式）

## API 使用示例

### 上传文件

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@paper.pdf"
```

响应：
```json
{
  "task_id": "uuid-here",
  "filename": "paper.pdf",
  "file_size": 1234567,
  "num_pages": 10
}
```

### 开始分析

```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "uuid-here",
    "translate": true,
    "target_lang": "zh",
    "generate_article": true,
    "generate_note": true,
    "generate_image": true
  }'
```

### 查询状态

```bash
curl "http://localhost:8000/status/uuid-here"
```

### 下载结果

```bash
# 下载公众号文章
curl "http://localhost:8000/download/article/uuid-here" -o article.md

# 下载小红书笔记
curl "http://localhost:8000/download/note/uuid-here" -o note.md

# 下载小红书图片
curl "http://localhost:8000/download/image/uuid-here" -o note.png
```

## 编程使用示例

### 直接使用模块

```python
from paper_whisperer.pdf_processor import PDFProcessor
from paper_whisperer.paper_analyzer import PaperAnalyzer
from paper_whisperer.content_generator import ContentGenerator
from paper_whisperer.image_generator import ImageGenerator

# 分析论文
analyzer = PaperAnalyzer(llm_provider="openai")
result = analyzer.analyze_paper("paper.pdf", translate=True)

# 生成公众号文章
content_gen = ContentGenerator()
article = content_gen.generate_wechat_article(result)

# 生成小红书笔记
note = content_gen.generate_xiaohongshu_note(result)

# 生成小红书图片
image_gen = ImageGenerator()
image_gen.generate_xiaohongshu_image(result, "output.png")
```

## 注意事项

1. **API 密钥**：确保正确配置 API 密钥，否则无法调用 LLM 服务
2. **文件大小**：默认最大支持 100MB 的 PDF 文件
3. **页数限制**：默认最大支持 100 页
4. **处理时间**：根据论文页数和复杂度，处理时间可能较长
5. **图片生成**：需要安装 Playwright 或使用 html2image

## 故障排除

### 问题：无法生成图片

**解决方案**：
1. 确保已安装 Playwright：`playwright install chromium`
2. 或者检查 html2image 是否正确安装

### 问题：API 调用失败

**解决方案**：
1. 检查 API 密钥是否正确配置
2. 检查网络连接
3. 查看错误日志

### 问题：PDF 解析失败

**解决方案**：
1. 确保 PDF 文件未损坏
2. 尝试使用其他 PDF 文件
3. 检查 PDF 是否加密（需要密码）

