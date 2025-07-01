import re
import json
import asyncio
import aiohttp
from urllib.parse import urljoin, quote_plus  # 添加 quote_plus 导入
from typing import Optional, Dict, Any, List
from core.tool import ToolBase

# 尝试导入BeautifulSoup，处理可能的安装问题
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    BeautifulSoup = None  # 防止未定义错误

class WebBrowserTool(ToolBase):
    """
    网页浏览和搜索工具，支持网页内容解析、交互式浏览、信息提取和网络搜索
    """

    def __init__(self):
        # 检查依赖是否已安装
        if not HAS_BS4:
            raise RuntimeError("BeautifulSoup4未安装！请运行: pip install beautifulsoup4 lxml")
        
        # 支持的搜索引擎列表
        self.search_engines = {
            "google": "https://www.google.com/search?q={query}&num={max_results}",
            "bing": "https://www.bing.com/search?q={query}&count={max_results}",
            "duckduckgo": "https://duckduckgo.com/html/?q={query}",
            "baidu": "https://www.baidu.com/s?wd={query}&pn=0&rn={max_results}"
        }
        
        # 默认用户代理
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
        
        parameters = {
            "operation": (
                str,
                "必须指定的操作类型。可用操作:\n"
                "- load_url: 加载指定URL的网页内容\n"
                "- extract_content: 从当前页面或HTML内容中提取结构化信息\n"
                "- search_web: 执行网络搜索并返回结果\n"
                "- interact: 模拟网页交互（如点击链接、填写表单等）"
            ),
            "url": (
                Optional[str],
                "要访问的网页URL。"
            ),
            "html_content": (
                Optional[str],
                "原始的HTML内容（当无法直接访问URL时使用）。"
            ),
            "query": (
                Optional[str],
                "搜索关键词（仅用于search_web操作）。"
            ),
            "search_engine": (
                Optional[str],
                f"使用的搜索引擎（默认：google）。可选项: {list(self.search_engines.keys())}"
            ),
            "max_results": (
                Optional[int],
                "返回的最大结果数（仅用于search_web操作，默认：5）。"
            ),
            "timeout": (
                Optional[int],
                "请求超时时间（秒，默认：20）。"
            ),
            "element_css": (
                Optional[str],
                "要交互或提取的HTML元素CSS选择器（用于interact或extract_content操作）。"
            ),
            "action_type": (
                Optional[str],
                "交互操作类型（用于interact操作）。可选项: ['click', 'form_submit', 'input_text']"
            ),
            "input_value": (
                Optional[str],
                "要输入的表单值（当action_type为input_text时使用）。"
            ),
            "extraction_rules": (
                Optional[dict],
                "内容提取规则（用于extract_content操作）。格式: {\"field_name\": \"css_selector\"}"
            )
        }
        
        super().__init__(
            name="web_browser",
            description=(
                "高级网页浏览工具，支持加载网页、提取信息、网络搜索和交互操作。\n"
                "关键能力:\n"
                "1. 网页内容提取 - 智能解析网页结构，提取文本、链接、表格等结构化数据\n"
                "2. 交互式浏览 - 模拟用户点击、表单提交等行为实现多步导航\n"
                "3. 智能搜索 - 支持多种搜索引擎，自动解析搜索结果\n"
                "4. 内容摘要 - 对大型网页生成内容摘要\n"
                "\n"
                "使用指南:\n"
                "- 加载网页内容使用load_url操作\n"
                "- 从搜索结果或当前页面提取关键信息使用extract_content\n"
                "- 执行新搜索使用search_web操作\n"
                "- 复杂任务使用interact实现多步交互"
            ),
            parameters=parameters
        )
        
        # 当前会话状态
        self.current_url = None
        self.current_html = None
        self.session_history = []
        
        # 创建共享会话
        self.session = aiohttp.ClientSession(
            headers={"User-Agent": self.user_agent},
            timeout=aiohttp.ClientTimeout(total=20)
        )

    async def run(
        self,
        operation: str,
        url: Optional[str] = None,
        html_content: Optional[str] = None,
        query: Optional[str] = None,
        search_engine: str = "google",
        max_results: int = 5,
        timeout: int = 20,
        element_css: Optional[str] = None,
        action_type: Optional[str] = None,
        input_value: Optional[str] = None,
        extraction_rules: Optional[dict] = None
    ) -> Dict[str, Any]:
        try:
            # 检查依赖
            if not HAS_BS4:
                raise ImportError(
                    "BeautifulSoup4未安装，无法解析HTML内容。"
                    "请运行: pip install beautifulsoup4 lxml"
                )
                
            operation = operation.lower()
            timeout = timeout or 20
            
            if operation == "load_url":
                return await self._load_webpage(url, timeout)
                
            elif operation == "extract_content":
                return await self._extract_content(url, html_content, extraction_rules, element_css)
                
            elif operation == "search_web":
                return await self._search_web(query, search_engine, max_results, timeout)
                
            elif operation == "interact":
                return await self._interact_with_element(
                    url, html_content, element_css, action_type, input_value, timeout
                )
                
            else:
                raise ValueError(f"不支持的操作: {operation}")
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "parameters": {
                    "url": url,
                    "query": query,
                    "search_engine": search_engine,
                    "max_results": max_results,
                    "timeout": timeout,
                    "element_css": element_css,
                    "action_type": action_type,
                    "input_value": input_value,
                    "extraction_rules": extraction_rules
                }
            }
    
    async def _load_webpage(self, url: str, timeout: int) -> Dict[str, Any]:
        """加载网页内容并解析为结构化数据"""
        if not url:
            raise ValueError("URL不能为空")
            
        # 如果提供相对URL，使用当前页面作为基础
        if not url.startswith(("http://", "https://")) and self.current_url:
            url = urljoin(self.current_url, url)
            
        async with self.session.get(url, timeout=timeout) as response:
            response.raise_for_status()
            html_content = await response.text()
            self.current_url = url
            self.current_html = html_content
            
            # 更新会话历史
            self.session_history.append({
                "action": "load",
                "url": url,
                "timestamp": asyncio.get_running_loop().time()
            })
            
            # 解析网页内容
            soup = BeautifulSoup(html_content, 'lxml')
            title = soup.title.string if soup.title else "无标题"
            
            # 提取主要内容
            article = soup.find('article') or soup.find('main') or soup
            text_content = self._clean_text(article.get_text(separator=' ', strip=True))
            summary = self._summarize_content(text_content)
            
            # 提取关键元素
            links = self._extract_links(soup)
            headings = self._extract_headings(soup)
            images = self._extract_images(soup)
            forms = self._extract_forms(soup)
            
            return {
                "success": True,
                "operation": "load_url",
                "url": url,
                "title": title,
                "status": response.status,
                "summary": summary,
                "elements": {
                    "links": links,
                    "headings": headings,
                    "images": images,
                    "forms": forms,
                    "content_length": len(text_content),
                    "link_count": len(links),
                    "form_count": len(forms)
                },
                "metadata": {
                    "content_type": response.headers.get('Content-Type', ''),
                    "encoding": response.get_encoding(),
                    "load_time": response.elapsed.total_seconds()
                }
            }
    
    async def _search_web(self, query: str, engine: str, max_results: int, timeout: int) -> Dict[str, Any]:
        """执行网络搜索并解析结果"""
        if not query:
            raise ValueError("搜索查询不能为空")
            
        engine = engine.lower()
        if engine not in self.search_engines:
            raise ValueError(f"不支持的搜索引擎: {engine}")
            
        # 构建搜索URL - 修复这里的问题
        search_url = self.search_engines[engine].format(
            query=quote_plus(query),  # 使用 urllib.parse.quote_plus
            max_results=max_results
        )
        
        # 执行搜索
        async with self.session.get(search_url, timeout=timeout) as response:
            response.raise_for_status()
            html_content = await response.text()
            
            # 解析搜索结果（不同引擎需要不同的解析逻辑）
            if engine == "google":
                results = self._parse_google_results(html_content)
            elif engine == "bing":
                results = self._parse_bing_results(html_content)
            elif engine == "duckduckgo":
                results = self._parse_duckduckgo_results(html_content)
            elif engine == "baidu":
                results = self._parse_baidu_results(html_content)
            else:
                results = []
            
            # 限制结果数量
            results = results[:max_results]
            
            return {
                "success": True,
                "operation": "search_web",
                "query": query,
                "search_engine": engine,
                "search_url": search_url,
                "results": results,
                "result_count": len(results)
            }
    
    # 其他方法保持不变...
    
    async def close(self):
        """关闭会话"""
        await self.session.close()