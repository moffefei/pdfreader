"""
配置管理模块
"""
import os
from typing import Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # API 配置
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.302.ai/v1"
    
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    
    # 模型配置
    DEFAULT_MODEL: str = "gpt-4o"  # 默认使用 OpenAI 兼容接口
    DEFAULT_VISION_MODEL: str = "gpt-4o"  # 多模态模型
    QWEN_MODEL: str = "qwen-vl-max"  # Qwen 多模态模型
    
    # 文件路径配置
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    TEMP_DIR: str = "temp"
    
    # 处理配置
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    MAX_PAGES: int = 100  # 最大页数
    CHUNK_SIZE: int = 5  # 每次处理的页数
    
    # 图片生成配置
    XIAOHONGSHU_WIDTH: int = 1080
    XIAOHONGSHU_HEIGHT: int = 1920
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()

