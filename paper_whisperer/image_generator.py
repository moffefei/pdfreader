"""
图片生成模块
HTML+CSS 模板渲染为小红书风格笔记图片
"""
import os
import base64
from typing import Dict, Optional
from jinja2 import Template
from html2image import Html2Image
from paper_whisperer.config import settings
from paper_whisperer.content_generator import ContentGenerator


class ImageGenerator:
    """图片生成器"""
    
    def __init__(self):
        """初始化图片生成器"""
        self.hti = Html2Image()
        self.width = settings.XIAOHONGSHU_WIDTH
        self.height = settings.XIAOHONGSHU_HEIGHT
        self.content_generator = ContentGenerator()
    
    def load_template(self) -> str:
        """
        加载 HTML 模板
        
        Returns:
            模板内容
        """
        template_path = os.path.join(
            os.path.dirname(__file__),
            "templates",
            "xiaohongshu.html"
        )
        
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def generate_xiaohongshu_image(
        self,
        analysis_result: Dict,
        output_path: str,
        structured_note: Optional[Dict] = None
    ) -> str:
        """
        生成小红书风格笔记图片
        
        Args:
            analysis_result: 论文分析结果
            output_path: 输出图片路径
            structured_note: 结构化笔记内容（可选，如果不提供则自动生成）
            
        Returns:
            生成的图片文件路径
        """
        # 如果没有提供结构化笔记，则生成
        if structured_note is None:
            structured_note = self.content_generator.generate_xiaohongshu_note_structured(
                analysis_result
            )
        
        # 加载模板
        template_content = self.load_template()
        template = Template(template_content)
        
        # 渲染 HTML
        html_content = template.render(
            title=structured_note.get("title", "📚 论文解读"),
            hook=structured_note.get("hook", ""),
            key_points=structured_note.get("key_points", []),
            highlight=structured_note.get("highlight", ""),
            conclusion=structured_note.get("conclusion", "")
        )
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 生成图片
        try:
            # 使用 html2image 生成图片
            # html2image 需要保存到当前目录，然后再移动
            temp_filename = os.path.basename(output_path)
            self.hti.screenshot(
                html_str=html_content,
                save_as=temp_filename,
                size=(self.width, self.height)
            )
            
            # 移动文件到目标位置
            temp_path = temp_filename
            if os.path.exists(temp_path) and temp_path != output_path:
                import shutil
                shutil.move(temp_path, output_path)
            
            return output_path
        except Exception as e:
            print(f"使用 html2image 生成图片时出错: {e}")
            # 如果 html2image 失败，尝试使用 playwright
            try:
                return self._generate_with_playwright(html_content, output_path)
            except Exception as e2:
                print(f"使用 Playwright 生成图片时也出错: {e2}")
                raise Exception(f"图片生成失败: {e}, {e2}")
    
    def _generate_with_playwright(
        self,
        html_content: str,
        output_path: str
    ) -> str:
        """
        使用 Playwright 生成图片（备用方案）
        
        Args:
            html_content: HTML 内容
            output_path: 输出路径
            
        Returns:
            生成的图片文件路径
        """
        try:
            from playwright.sync_api import sync_playwright
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(
                    viewport={"width": self.width, "height": self.height}
                )
                
                # 将 HTML 内容写入页面
                page.set_content(html_content)
                
                # 截图
                page.screenshot(path=output_path, full_page=True)
                
                browser.close()
            
            return output_path
        except Exception as e:
            print(f"使用 Playwright 生成图片时出错: {e}")
            raise
    
    def generate_custom_image(
        self,
        title: str,
        content: Dict,
        output_path: str,
        template_path: Optional[str] = None
    ) -> str:
        """
        生成自定义图片
        
        Args:
            title: 标题
            content: 内容字典
            output_path: 输出路径
            template_path: 自定义模板路径（可选）
            
        Returns:
            生成的图片文件路径
        """
        if template_path and os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
        else:
            template_content = self.load_template()
        
        template = Template(template_content)
        html_content = template.render(title=title, **content)
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            temp_filename = os.path.basename(output_path)
            self.hti.screenshot(
                html_str=html_content,
                save_as=temp_filename,
                size=(self.width, self.height)
            )
            
            temp_path = temp_filename
            if os.path.exists(temp_path) and temp_path != output_path:
                import shutil
                shutil.move(temp_path, output_path)
            
            return output_path
        except Exception as e:
            print(f"生成自定义图片时出错: {e}")
            try:
                return self._generate_with_playwright(html_content, output_path)
            except Exception as e2:
                print(f"使用 Playwright 生成图片时也出错: {e2}")
                raise Exception(f"图片生成失败: {e}, {e2}")

