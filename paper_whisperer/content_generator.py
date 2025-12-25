"""
内容生成模块
生成公众号文章（Markdown）和小红书笔记内容
"""
from typing import Dict
from paper_whisperer.llm_client import LLMClientFactory


class ContentGenerator:
    """内容生成器"""
    
    def __init__(self, llm_provider: str = "openai"):
        """
        初始化内容生成器
        
        Args:
            llm_provider: LLM 提供商
        """
        self.llm_client = LLMClientFactory.create_client(provider=llm_provider)
    
    def generate_wechat_article(self, analysis_result: Dict) -> str:
        """
        生成公众号文章（Markdown 格式）
        
        Args:
            analysis_result: 论文分析结果
            
        Returns:
            Markdown 格式的文章内容
        """
        key_info = analysis_result.get("key_info", {})
        summary = analysis_result.get("summary", "")
        metadata = analysis_result.get("metadata", {})
        
        prompt = f"""基于以下论文分析结果，生成一篇适合公众号发布的科普文章（Markdown 格式）。

要求：
1. 标题要吸引人，能引起读者兴趣
2. 开头要有引人入胜的引言
3. 内容要通俗易懂，避免过于专业的术语
4. 适当使用小标题分段
5. 突出论文的创新点和应用价值
6. 结尾要有总结和思考

论文信息：
标题: {key_info.get('title', metadata.get('title', ''))}
作者: {', '.join(key_info.get('authors', []))}
摘要: {key_info.get('abstract', '')}
主要贡献: {', '.join(key_info.get('main_contributions', []))}
研究方法: {key_info.get('methodology', '')}
主要结果: {key_info.get('main_results', '')}

深度解读摘要：
{summary}

请生成完整的 Markdown 文章，包含标题、引言、正文、总结等部分。"""
        
        try:
            article = self.llm_client.chat_completion([
                {"role": "user", "content": prompt}
            ], temperature=0.8, max_tokens=3000)
        except Exception as e:
            article = f"生成文章时出错: {str(e)}"
        
        return article
    
    def generate_xiaohongshu_note(self, analysis_result: Dict) -> str:
        """
        生成小红书笔记内容（Markdown 格式）
        
        Args:
            analysis_result: 论文分析结果
            
        Returns:
            Markdown 格式的小红书笔记内容
        """
        key_info = analysis_result.get("key_info", {})
        summary = analysis_result.get("summary", "")
        
        prompt = f"""基于以下论文分析结果，生成一篇适合小红书发布的笔记内容（Markdown 格式）。

要求：
1. 标题要吸引眼球，可以使用 emoji 装饰
2. 开头要有吸引人的 hook（钩子）
3. 使用要点列表，每个要点前加 emoji
4. 语言要轻松活泼，但保持专业性
5. 适当使用 emoji 增加趣味性
6. 内容要简洁，控制在 500-800 字
7. 结尾要有互动引导（如"你觉得呢？"）

论文信息：
标题: {key_info.get('title', '')}
主要贡献: {', '.join(key_info.get('main_contributions', []))}
主要结果: {key_info.get('main_results', '')}

深度解读摘要：
{summary}

请生成完整的 Markdown 笔记，格式要符合小红书风格，使用适当的 emoji。"""
        
        try:
            note = self.llm_client.chat_completion([
                {"role": "user", "content": prompt}
            ], temperature=0.9, max_tokens=2000)
        except Exception as e:
            note = f"生成笔记时出错: {str(e)}"
        
        return note
    
    def generate_xiaohongshu_note_structured(self, analysis_result: Dict) -> Dict:
        """
        生成结构化的小红书笔记内容
        
        Args:
            analysis_result: 论文分析结果
            
        Returns:
            包含标题、要点列表等结构化内容的字典
        """
        key_info = analysis_result.get("key_info", {})
        summary = analysis_result.get("summary", "")
        
        prompt = f"""基于以下论文分析结果，生成小红书笔记的结构化内容，以 JSON 格式返回：

{{
    "title": "吸引人的标题（可含emoji）",
    "hook": "开头吸引人的一句话",
    "key_points": [
        "要点1（可含emoji）",
        "要点2（可含emoji）",
        ...
    ],
    "highlight": "核心亮点（1-2句话）",
    "conclusion": "总结和互动引导"
}}

论文信息：
标题: {key_info.get('title', '')}
主要贡献: {', '.join(key_info.get('main_contributions', []))}
主要结果: {key_info.get('main_results', '')}

深度解读摘要：
{summary}

请只返回 JSON，不要其他文字。"""
        
        try:
            response = self.llm_client.chat_completion([
                {"role": "user", "content": prompt}
            ], temperature=0.9, max_tokens=1500)
            
            # 解析 JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            import json
            structured_note = json.loads(response)
        except Exception as e:
            print(f"生成结构化笔记失败: {e}")
            structured_note = {
                "title": f"📚 {key_info.get('title', '论文解读')}",
                "hook": "今天来聊聊这篇有趣的论文！",
                "key_points": [
                    f"✨ 主要贡献: {', '.join(key_info.get('main_contributions', []))}",
                    f"🔬 研究方法: {key_info.get('methodology', '')[:100]}",
                    f"📊 主要结果: {key_info.get('main_results', '')[:100]}"
                ],
                "highlight": summary[:200] if summary else "这是一篇值得关注的论文",
                "conclusion": "你觉得这个研究怎么样？欢迎在评论区讨论！"
            }
        
        return structured_note

