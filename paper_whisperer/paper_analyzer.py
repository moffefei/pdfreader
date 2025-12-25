"""
论文分析模块
使用多模态模型逐页分析，提取关键信息并翻译
"""
import os
import json
from typing import Dict, List, Optional
from paper_whisperer.pdf_processor import PDFProcessor
from paper_whisperer.llm_client import LLMClientFactory, LLMClient
from paper_whisperer.config import settings


class PaperAnalyzer:
    """论文分析器"""
    
    def __init__(self, llm_provider: str = "openai"):
        """
        初始化论文分析器
        
        Args:
            llm_provider: LLM 提供商，"openai" 或 "qwen"
        """
        self.pdf_processor = PDFProcessor()
        self.llm_client = LLMClientFactory.create_client(provider=llm_provider)
        self.chunk_size = settings.CHUNK_SIZE
    
    def analyze_paper(
        self,
        pdf_path: str,
        output_dir: Optional[str] = None,
        translate: bool = True,
        target_lang: str = "zh"
    ) -> Dict:
        """
        分析整篇论文
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录（用于保存临时图片）
            translate: 是否翻译
            target_lang: 目标语言
            
        Returns:
            分析结果字典
        """
        # 创建临时目录
        if output_dir is None:
            output_dir = os.path.join(settings.TEMP_DIR, os.path.basename(pdf_path).replace(".pdf", ""))
        os.makedirs(output_dir, exist_ok=True)
        
        # 提取元数据
        metadata = self.pdf_processor.extract_metadata(pdf_path)
        num_pages = metadata.get("num_pages", 0)
        
        if num_pages == 0:
            raise ValueError("无法读取 PDF 文件或文件为空")
        
        # 转换页面为图片
        print(f"正在转换 PDF 页面为图片...")
        image_paths = self.pdf_processor.convert_to_images(pdf_path, output_dir)
        
        # 提取文本
        print(f"正在提取文本内容...")
        text_dict = self.pdf_processor.extract_text(pdf_path)
        
        # 逐页分析
        print(f"正在分析论文内容（共 {num_pages} 页）...")
        page_analyses = []
        
        for page_num in range(1, num_pages + 1):
            print(f"分析第 {page_num}/{num_pages} 页...")
            
            page_text = text_dict.get(page_num, "")
            page_image_path = None
            
            # 查找对应的图片
            for img_path in image_paths:
                if f"page_{page_num}.png" in img_path:
                    page_image_path = img_path
                    break
            
            # 分析页面
            analysis = self._analyze_page(page_num, page_text, page_image_path)
            page_analyses.append(analysis)
        
        # 提取关键信息
        print("正在提取关键信息...")
        key_info = self._extract_key_info(text_dict, page_analyses)
        
        # 翻译（如果需要）
        if translate:
            print("正在翻译内容...")
            key_info = self._translate_key_info(key_info, target_lang)
        
        # 生成摘要
        print("正在生成论文摘要...")
        summary = self._generate_summary(key_info, page_analyses)
        
        result = {
            "metadata": metadata,
            "key_info": key_info,
            "summary": summary,
            "page_analyses": page_analyses,
            "num_pages": num_pages
        }
        
        return result
    
    def _analyze_page(
        self,
        page_num: int,
        page_text: str,
        page_image_path: Optional[str]
    ) -> Dict:
        """
        分析单个页面
        
        Args:
            page_num: 页码
            page_text: 页面文本
            page_image_path: 页面图片路径
            
        Returns:
            页面分析结果
        """
        prompt = f"""请分析这页论文内容（第 {page_num} 页），提取以下信息：
1. 主要内容概述（2-3句话）
2. 关键概念和技术术语
3. 重要数据、图表或结果
4. 与其他部分的关联

请用中文回答，语言要专业但易懂。如果这一页主要是图表，请描述图表的内容和含义。"""
        
        try:
            analysis_text = self.llm_client.analyze_page(
                page_text=page_text,
                page_image_path=page_image_path,
                prompt=prompt
            )
        except Exception as e:
            analysis_text = f"分析第 {page_num} 页时出错: {str(e)}"
        
        return {
            "page_num": page_num,
            "text": page_text[:500] + "..." if len(page_text) > 500 else page_text,  # 截断文本
            "analysis": analysis_text
        }
    
    def _extract_key_info(
        self,
        text_dict: Dict[int, str],
        page_analyses: List[Dict]
    ) -> Dict:
        """
        提取关键信息
        
        Args:
            text_dict: 页面文本字典
            page_analyses: 页面分析结果列表
            
        Returns:
            关键信息字典
        """
        # 合并所有页面文本
        full_text = "\n\n".join([
            f"--- 第 {page_num} 页 ---\n{text}"
            for page_num, text in sorted(text_dict.items())
        ])
        
        # 提取前几页（通常是摘要、介绍等）
        first_pages_text = "\n\n".join([
            text_dict.get(i, "")
            for i in range(1, min(4, len(text_dict) + 1))
        ])
        
        prompt = f"""请从以下论文内容中提取关键信息，以 JSON 格式返回：

{{
    "title": "论文标题",
    "authors": ["作者1", "作者2"],
    "abstract": "摘要内容",
    "keywords": ["关键词1", "关键词2"],
    "main_contributions": ["贡献1", "贡献2"],
    "methodology": "研究方法概述",
    "main_results": "主要结果",
    "conclusions": "结论"
}}

论文前几页内容：
{first_pages_text[:3000]}

请只返回 JSON，不要其他文字。"""
        
        try:
            response = self.llm_client.chat_completion([
                {"role": "user", "content": prompt}
            ], temperature=0.3)
            
            # 尝试解析 JSON
            # 移除可能的 markdown 代码块标记
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            key_info = json.loads(response)
        except Exception as e:
            # 如果解析失败，使用默认结构
            print(f"解析关键信息失败: {e}")
            key_info = {
                "title": "",
                "authors": [],
                "abstract": "",
                "keywords": [],
                "main_contributions": [],
                "methodology": "",
                "main_results": "",
                "conclusions": ""
            }
        
        return key_info
    
    def _translate_key_info(self, key_info: Dict, target_lang: str) -> Dict:
        """
        翻译关键信息
        
        Args:
            key_info: 关键信息字典
            target_lang: 目标语言
            
        Returns:
            翻译后的关键信息字典
        """
        translated = {}
        
        for key, value in key_info.items():
            if isinstance(value, str) and value:
                try:
                    translated[key] = self.llm_client.translate_text(value, target_lang)
                except Exception as e:
                    print(f"翻译 {key} 时出错: {e}")
                    translated[key] = value
            elif isinstance(value, list):
                translated[key] = []
                for item in value:
                    if isinstance(item, str) and item:
                        try:
                            translated[key].append(
                                self.llm_client.translate_text(item, target_lang)
                            )
                        except Exception as e:
                            print(f"翻译列表项时出错: {e}")
                            translated[key].append(item)
                    else:
                        translated[key].append(item)
            else:
                translated[key] = value
        
        return translated
    
    def _generate_summary(self, key_info: Dict, page_analyses: List[Dict]) -> str:
        """
        生成论文摘要
        
        Args:
            key_info: 关键信息
            page_analyses: 页面分析结果
            
        Returns:
            摘要文本
        """
        # 合并所有页面分析
        analyses_text = "\n\n".join([
            f"第 {pa['page_num']} 页: {pa['analysis']}"
            for pa in page_analyses[:10]  # 只取前10页的分析
        ])
        
        prompt = f"""基于以下信息，生成一篇论文的深度解读摘要（500-800字）：

关键信息：
标题: {key_info.get('title', '')}
摘要: {key_info.get('abstract', '')}
主要贡献: {', '.join(key_info.get('main_contributions', []))}
研究方法: {key_info.get('methodology', '')}
主要结果: {key_info.get('main_results', '')}

页面分析：
{analyses_text[:2000]}

请用中文撰写，语言要专业但通俗易懂，适合科普文章。"""
        
        try:
            summary = self.llm_client.chat_completion([
                {"role": "user", "content": prompt}
            ], temperature=0.7, max_tokens=2000)
        except Exception as e:
            summary = f"生成摘要时出错: {str(e)}"
        
        return summary
    
    def save_analysis_result(self, result: Dict, output_path: str):
        """
        保存分析结果到 JSON 文件
        
        Args:
            result: 分析结果字典
            output_path: 输出文件路径
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

