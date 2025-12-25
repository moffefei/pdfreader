"""
LLM 客户端模块
支持 OpenAI 兼容接口（302.ai）和 Qwen 接口
"""
import base64
import os
from typing import List, Dict, Optional, Union
from openai import OpenAI
import dashscope
from dashscope import MultiModalConversation
from paper_whisperer.config import settings


class LLMClient:
    """统一的 LLM 客户端，支持多个 API 接口"""
    
    def __init__(self, provider: str = "openai"):
        """
        初始化 LLM 客户端
        
        Args:
            provider: 提供商，"openai" 或 "qwen"
        """
        self.provider = provider
        
        if provider == "openai":
            self.client = OpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL
            )
            self.model = settings.DEFAULT_VISION_MODEL
        elif provider == "qwen":
            dashscope.api_key = settings.QWEN_API_KEY
            self.model = settings.QWEN_MODEL
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    def encode_image(self, image_path: str) -> str:
        """
        将图片编码为 base64
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            base64 编码的图片字符串
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def chat_completion(
        self,
        messages: List[Dict],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        文本对话完成
        
        Args:
            messages: 消息列表
            model: 模型名称，None 使用默认模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            模型回复内容
        """
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        elif self.provider == "qwen":
            response = dashscope.Generation.call(
                model=model or self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Qwen API 错误: {response.message}")
    
    def vision_completion(
        self,
        messages: List[Dict],
        image_paths: List[str],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        多模态对话完成（支持图片）
        
        Args:
            messages: 消息列表
            image_paths: 图片文件路径列表
            model: 模型名称，None 使用默认模型
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            模型回复内容
        """
        if self.provider == "openai":
            # OpenAI 兼容接口格式
            formatted_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    formatted_msg = {"role": msg.get("role", "user"), "content": []}
                    
                    # 处理文本内容
                    text_content = None
                    if "text" in msg:
                        text_content = msg["text"]
                    elif "content" in msg:
                        if isinstance(msg["content"], str):
                            text_content = msg["content"]
                    
                    if text_content:
                        formatted_msg["content"].append({
                            "type": "text",
                            "text": text_content
                        })
                    
                    # 添加图片
                    for img_path in image_paths:
                        if os.path.exists(img_path):
                            base64_image = self.encode_image(img_path)
                            formatted_msg["content"].append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            })
                    
                    formatted_messages.append(formatted_msg)
                else:
                    formatted_messages.append(msg)
            
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=formatted_messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        
        elif self.provider == "qwen":
            # Qwen 多模态接口格式
            contents = []
            
            # 添加文本内容
            for msg in messages:
                if isinstance(msg, dict):
                    if "text" in msg:
                        contents.append({"text": msg["text"]})
                    elif "content" in msg:
                        if isinstance(msg["content"], str):
                            contents.append({"text": msg["content"]})
            
            # 添加图片
            for img_path in image_paths:
                with open(img_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    contents.append({
                        "image": f"data:image/png;base64,{image_data}"
                    })
            
            response = MultiModalConversation.call(
                model=model or self.model,
                messages=[{
                    "role": "user",
                    "content": contents
                }],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Qwen API 错误: {response.message}")
    
    def analyze_page(
        self,
        page_text: str,
        page_image_path: Optional[str] = None,
        prompt: Optional[str] = None
    ) -> str:
        """
        分析 PDF 页面
        
        Args:
            page_text: 页面文本内容
            page_image_path: 页面图片路径（可选）
            prompt: 自定义提示词
            
        Returns:
            分析结果
        """
        default_prompt = """请分析这页论文内容，提取以下信息：
1. 主要内容概述
2. 关键概念和技术
3. 重要数据和结果
4. 与其他部分的关联

请用中文回答，语言要专业但易懂。"""
        
        full_prompt = f"{prompt or default_prompt}\n\n页面文本内容：\n{page_text}"
        
        messages = [{
            "role": "user",
            "content": full_prompt
        }]
        
        if page_image_path and os.path.exists(page_image_path):
            return self.vision_completion(messages, [page_image_path])
        else:
            return self.chat_completion(messages)
    
    def translate_text(
        self,
        text: str,
        target_lang: str = "zh",
        source_lang: Optional[str] = None
    ) -> str:
        """
        翻译文本
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言，"zh" 中文，"en" 英文
            source_lang: 源语言，None 表示自动检测
            
        Returns:
            翻译后的文本
        """
        lang_map = {"zh": "中文", "en": "英文"}
        target = lang_map.get(target_lang, "中文")
        source = lang_map.get(source_lang, "原文") if source_lang else "原文"
        
        prompt = f"请将以下文本翻译成{target}，保持专业术语的准确性，语言流畅自然：\n\n{text}"
        
        messages = [{
            "role": "user",
            "content": prompt
        }]
        
        return self.chat_completion(messages, temperature=0.3)


class LLMClientFactory:
    """LLM 客户端工厂"""
    
    @staticmethod
    def create_client(provider: str = "openai") -> LLMClient:
        """
        创建 LLM 客户端
        
        Args:
            provider: 提供商，"openai" 或 "qwen"
            
        Returns:
            LLMClient 实例
        """
        return LLMClient(provider=provider)
    
    @staticmethod
    def get_default_client() -> LLMClient:
        """获取默认客户端（OpenAI 兼容接口）"""
        return LLMClient(provider="openai")

