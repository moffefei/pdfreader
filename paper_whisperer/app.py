"""
FastAPI Web 应用
提供文件上传、处理接口、进度查询、结果下载
"""
import os
import uuid
import asyncio
from typing import Optional
from pathlib import Path
import aiofiles
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from paper_whisperer.config import settings
from paper_whisperer.pdf_processor import PDFProcessor
from paper_whisperer.paper_analyzer import PaperAnalyzer
from paper_whisperer.content_generator import ContentGenerator
from paper_whisperer.image_generator import ImageGenerator


# 创建 FastAPI 应用
app = FastAPI(title="Paper Whisperer", description="论文深度解读 Agent")

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建必要的目录
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.TEMP_DIR, exist_ok=True)

# 静态文件服务
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 任务状态存储（生产环境应使用 Redis 或数据库）
tasks = {}


# 数据模型
class TaskStatus(BaseModel):
    """任务状态模型"""
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float  # 0-100
    message: str
    result: Optional[dict] = None


class AnalysisRequest(BaseModel):
    """分析请求模型"""
    task_id: str
    translate: bool = True
    target_lang: str = "zh"
    generate_article: bool = True
    generate_note: bool = True
    generate_image: bool = True


# 工具函数
def generate_task_id() -> str:
    """生成任务 ID"""
    return str(uuid.uuid4())


async def save_upload_file(file: UploadFile, file_path: str):
    """保存上传的文件"""
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)


async def process_paper_task(
    task_id: str,
    pdf_path: str,
    translate: bool = True,
    target_lang: str = "zh",
    generate_article: bool = True,
    generate_note: bool = True,
    generate_image: bool = True
):
    """
    处理论文任务（后台任务）
    
    Args:
        task_id: 任务 ID
        pdf_path: PDF 文件路径
        translate: 是否翻译
        target_lang: 目标语言
        generate_article: 是否生成公众号文章
        generate_note: 是否生成小红书笔记
        generate_image: 是否生成图片
    """
    try:
        # 更新任务状态
        tasks[task_id] = {
            "status": "processing",
            "progress": 0,
            "message": "开始处理论文...",
            "result": None
        }
        
        # 初始化处理器
        analyzer = PaperAnalyzer()
        content_generator = ContentGenerator()
        image_generator = ImageGenerator()
        
        # 分析论文
        tasks[task_id]["progress"] = 10
        tasks[task_id]["message"] = "正在分析论文..."
        
        output_dir = os.path.join(settings.TEMP_DIR, task_id)
        analysis_result = analyzer.analyze_paper(
            pdf_path=pdf_path,
            output_dir=output_dir,
            translate=translate,
            target_lang=target_lang
        )
        
        tasks[task_id]["progress"] = 60
        tasks[task_id]["message"] = "正在生成内容..."
        
        result = {
            "analysis": analysis_result,
            "article": None,
            "note": None,
            "image_path": None
        }
        
        # 生成公众号文章
        if generate_article:
            article = content_generator.generate_wechat_article(analysis_result)
            result["article"] = article
            
            # 保存文章
            article_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_article.md")
            async with aiofiles.open(article_path, 'w', encoding='utf-8') as f:
                await f.write(article)
            result["article_path"] = article_path
        
        tasks[task_id]["progress"] = 80
        tasks[task_id]["message"] = "正在生成小红书笔记..."
        
        # 生成小红书笔记
        if generate_note:
            note = content_generator.generate_xiaohongshu_note(analysis_result)
            result["note"] = note
            
            # 保存笔记
            note_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_note.md")
            async with aiofiles.open(note_path, 'w', encoding='utf-8') as f:
                await f.write(note)
            result["note_path"] = note_path
        
        # 生成小红书图片
        if generate_image:
            image_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_note.png")
            image_generator.generate_xiaohongshu_image(
                analysis_result=analysis_result,
                output_path=image_path
            )
            result["image_path"] = image_path
        
        tasks[task_id]["progress"] = 100
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["message"] = "处理完成"
        tasks[task_id]["result"] = result
        
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["message"] = f"处理失败: {str(e)}"
        tasks[task_id]["result"] = None


# API 路由
@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        from fastapi.responses import HTMLResponse
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return {
        "name": "Paper Whisperer",
        "version": "1.0.0",
        "description": "论文深度解读 Agent"
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传 PDF 文件
    
    Returns:
        任务 ID
    """
    # 检查文件类型
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持 PDF 文件")
    
    # 检查文件大小
    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件过大")
    
    # 生成任务 ID
    task_id = generate_task_id()
    
    # 保存文件
    file_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}.pdf")
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    # 检查页数
    processor = PDFProcessor()
    num_pages = processor.get_page_count(file_path)
    if num_pages > settings.MAX_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"页数过多（{num_pages}页），最大支持{settings.MAX_PAGES}页"
        )
    
    # 初始化任务状态
    tasks[task_id] = {
        "status": "pending",
        "progress": 0,
        "message": "文件上传成功，等待处理",
        "result": None
    }
    
    return {
        "task_id": task_id,
        "filename": file.filename,
        "file_size": len(content),
        "num_pages": num_pages
    }


@app.post("/analyze")
async def analyze_paper(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks
):
    """
    分析论文
    
    Args:
        request: 分析请求
        background_tasks: 后台任务
        
    Returns:
        任务状态
    """
    task_id = request.task_id
    
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查文件是否存在
    pdf_path = os.path.join(settings.UPLOAD_DIR, f"{task_id}.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF 文件不存在")
    
    # 添加后台任务
    background_tasks.add_task(
        process_paper_task,
        task_id=task_id,
        pdf_path=pdf_path,
        translate=request.translate,
        target_lang=request.target_lang,
        generate_article=request.generate_article,
        generate_note=request.generate_note,
        generate_image=request.generate_image
    )
    
    return {
        "task_id": task_id,
        "message": "分析任务已启动"
    }


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务状态
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = tasks[task_id]
    return TaskStatus(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info["progress"],
        message=task_info["message"],
        result=task_info.get("result")
    )


@app.get("/result/{task_id}")
async def get_task_result(task_id: str):
    """
    获取任务结果
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务结果
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task_info = tasks[task_id]
    
    if task_info["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    return task_info["result"]


@app.get("/download/article/{task_id}")
async def download_article(task_id: str):
    """
    下载公众号文章
    
    Args:
        task_id: 任务 ID
        
    Returns:
        文件响应
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    article_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_article.md")
    if not os.path.exists(article_path):
        raise HTTPException(status_code=404, detail="文章文件不存在")
    
    return FileResponse(
        article_path,
        filename=f"article_{task_id}.md",
        media_type="text/markdown"
    )


@app.get("/download/note/{task_id}")
async def download_note(task_id: str):
    """
    下载小红书笔记
    
    Args:
        task_id: 任务 ID
        
    Returns:
        文件响应
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    note_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_note.md")
    if not os.path.exists(note_path):
        raise HTTPException(status_code=404, detail="笔记文件不存在")
    
    return FileResponse(
        note_path,
        filename=f"note_{task_id}.md",
        media_type="text/markdown"
    )


@app.get("/download/image/{task_id}")
async def download_image(task_id: str):
    """
    下载小红书笔记图片
    
    Args:
        task_id: 任务 ID
        
    Returns:
        文件响应
    """
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    image_path = os.path.join(settings.OUTPUT_DIR, f"{task_id}_note.png")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="图片文件不存在")
    
    return FileResponse(
        image_path,
        filename=f"note_{task_id}.png",
        media_type="image/png"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

