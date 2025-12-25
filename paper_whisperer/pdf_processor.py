"""
PDF 处理模块
基于 skills/pdf 目录的能力，提取文本、图片和元数据
"""
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader


class PDFProcessor:
    """PDF 处理器"""
    
    def __init__(self, max_dim: int = 1000):
        """
        初始化 PDF 处理器
        
        Args:
            max_dim: 图片最大尺寸（像素）
        """
        self.max_dim = max_dim
    
    def extract_metadata(self, pdf_path: str) -> Dict:
        """
        提取 PDF 元数据
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            包含元数据的字典
        """
        try:
            reader = PdfReader(pdf_path)
            metadata = reader.metadata or {}
            
            return {
                "title": metadata.get("/Title", ""),
                "author": metadata.get("/Author", ""),
                "subject": metadata.get("/Subject", ""),
                "creator": metadata.get("/Creator", ""),
                "producer": metadata.get("/Producer", ""),
                "creation_date": str(metadata.get("/CreationDate", "")),
                "modification_date": str(metadata.get("/ModDate", "")),
                "num_pages": len(reader.pages),
            }
        except Exception as e:
            return {
                "title": "",
                "author": "",
                "subject": "",
                "creator": "",
                "producer": "",
                "creation_date": "",
                "modification_date": "",
                "num_pages": 0,
                "error": str(e)
            }
    
    def extract_text(self, pdf_path: str, pages: Optional[List[int]] = None) -> Dict[int, str]:
        """
        提取 PDF 文本内容
        
        Args:
            pdf_path: PDF 文件路径
            pages: 要提取的页码列表（从1开始），None 表示提取所有页
            
        Returns:
            字典，键为页码（从1开始），值为文本内容
        """
        text_dict = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_extract = pages if pages else list(range(1, total_pages + 1))
                
                for page_num in pages_to_extract:
                    if 1 <= page_num <= total_pages:
                        page = pdf.pages[page_num - 1]
                        text = page.extract_text() or ""
                        text_dict[page_num] = text
        except Exception as e:
            print(f"提取文本时出错: {e}")
        
        return text_dict
    
    def extract_tables(self, pdf_path: str, pages: Optional[List[int]] = None) -> Dict[int, List]:
        """
        提取 PDF 中的表格
        
        Args:
            pdf_path: PDF 文件路径
            pages: 要提取的页码列表（从1开始），None 表示提取所有页
            
        Returns:
            字典，键为页码（从1开始），值为表格列表
        """
        tables_dict = {}
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                pages_to_extract = pages if pages else list(range(1, total_pages + 1))
                
                for page_num in pages_to_extract:
                    if 1 <= page_num <= total_pages:
                        page = pdf.pages[page_num - 1]
                        tables = page.extract_tables() or []
                        tables_dict[page_num] = tables
        except Exception as e:
            print(f"提取表格时出错: {e}")
        
        return tables_dict
    
    def convert_to_images(
        self, 
        pdf_path: str, 
        output_dir: str, 
        pages: Optional[List[int]] = None,
        use_pypdfium: bool = True
    ) -> List[str]:
        """
        将 PDF 页面转换为图片
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
            pages: 要转换的页码列表（从1开始），None 表示转换所有页
            use_pypdfium: 是否使用 pypdfium2（更快），否则使用 pdf2image
            
        Returns:
            生成的图片文件路径列表
        """
        os.makedirs(output_dir, exist_ok=True)
        image_paths = []
        
        try:
            if use_pypdfium:
                # 使用 pypdfium2（更快）
                pdf = pdfium.PdfDocument(pdf_path)
                total_pages = len(pdf)
                pages_to_convert = pages if pages else list(range(1, total_pages + 1))
                
                for page_num in pages_to_convert:
                    if 1 <= page_num <= total_pages:
                        page = pdf[page_num - 1]
                        bitmap = page.render(scale=2.0)
                        img = bitmap.to_pil()
                        
                        # 缩放图片
                        img = self._resize_image(img)
                        
                        image_path = os.path.join(output_dir, f"page_{page_num}.png")
                        img.save(image_path, "PNG")
                        image_paths.append(image_path)
                
                pdf.close()
            else:
                # 使用 pdf2image（兼容性更好）
                images = convert_from_path(pdf_path, dpi=200)
                total_pages = len(images)
                pages_to_convert = pages if pages else list(range(1, total_pages + 1))
                
                for page_num in pages_to_convert:
                    if 1 <= page_num <= total_pages:
                        img = images[page_num - 1]
                        
                        # 缩放图片
                        img = self._resize_image(img)
                        
                        image_path = os.path.join(output_dir, f"page_{page_num}.png")
                        img.save(image_path, "PNG")
                        image_paths.append(image_path)
        
        except Exception as e:
            print(f"转换图片时出错: {e}")
        
        return image_paths
    
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """
        缩放图片，保持宽高比
        
        Args:
            img: PIL Image 对象
            
        Returns:
            缩放后的图片
        """
        width, height = img.size
        if width > self.max_dim or height > self.max_dim:
            scale_factor = min(self.max_dim / width, self.max_dim / height)
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return img
    
    def get_page_count(self, pdf_path: str) -> int:
        """
        获取 PDF 页数
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            页数
        """
        try:
            reader = PdfReader(pdf_path)
            return len(reader.pages)
        except Exception:
            return 0
    
    def extract_full_text(self, pdf_path: str) -> str:
        """
        提取完整文本（所有页）
        
        Args:
            pdf_path: PDF 文件路径
            
        Returns:
            完整文本内容
        """
        text_dict = self.extract_text(pdf_path)
        full_text = ""
        
        for page_num in sorted(text_dict.keys()):
            full_text += f"\n--- 第 {page_num} 页 ---\n"
            full_text += text_dict[page_num]
            full_text += "\n"
        
        return full_text.strip()

