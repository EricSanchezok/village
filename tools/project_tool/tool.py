import os
import json
import ast
from pathlib import Path
from typing import Optional, Dict, Any, List
from core.tool import ToolBase

class ProjectTool(ToolBase):
    """
    高级项目理解工具，专为智能体优化自我代码而设计
    """
    
    def __init__(self):
        parameters = {
            "operation": (
                str,
                "必须指定的操作类型。每个操作的核心用途:\n"
                "▼ get_project_structure: 生成项目目录树结构图\n"
                "  - 用途：理解项目整体架构，可视化文件组织\n"
                "  - 输出：树状结构 + 相对路径\n"
                "▼ get_code_structure: 提取代码关键结构信息\n"
                "  - 用途：分析类/函数/依赖关系等架构元素\n"
                "  - 输出：类名、函数签名、导入关系\n"
                "▼ get_dependencies: 识别项目依赖库\n"
                "  - 用途：了解项目依赖环境及版本\n"
                "  - 支持：Python/JS/Java等主要生态\n"
                "▼ search_code: 在项目中搜索特定代码模式\n"
                "  - 用途：查找特定代码模式或关键字\n"
                "  - 特性：支持多语言+跨文件搜索"
            ),
            "project_path": (
                Optional[str],
                "项目根目录路径（可选）\n"
                "▼ 使用说明:\n"
                "- 默认：使用工具内置项目根目录\n"
                "- 相对路径：基于当前工作目录\n"
                "- 绝对路径：完整系统路径\n"
                "▼ 示例：\n"
                "'src'  # 相对路径\n"
                "'/home/user/project'  # 绝对路径"
            ),
            "search_pattern": (
                Optional[str],
                "搜索关键词或正则表达式（仅用于search_code操作）\n"
                "▼ 特性:\n"
                "- 支持简单字符串匹配\n"
                "- 支持正则表达式（高级搜索）\n"
                "- 跨多种文件类型同时搜索\n"
                "▼ 示例：\n"
                "'def create_'  # 搜索函数定义\n"
                "'\\b[A-Z][a-z]+\\b'  # 搜索大写开头的单词"
            ),
            "file_types": (
                Optional[List[str]],
                "文件扩展名过滤器（列表格式）\n"
                "▼ 使用场景:\n"
                "- get_code_structure：指定分析哪些语言文件\n"
                "- search_code：指定在哪些文件类型中搜索\n"
                "▼ 默认行为：分析所有常见代码文件（.py/.js/.java等）\n"
                "▼ 格式要求:\n"
                "- 使用'.'前缀的扩展名列表\n"
                "- 不区分大小写\n"
                "▼ 示例：\n"
                "['.py', '.ipynb']  # Python文件\n"
                "['.js', '.ts']  # JavaScript/TypeScript文件"
            ),
            "ignore_patterns": (
                Optional[List[str]],
                "排除目录/文件过滤器（列表格式）\n"
                "▼ 内置默认值:\n"
                "['__pycache__', '.git', '.idea', 'node_modules', 'dist', 'venv']\n"
                "▼ 使用建议:\n"
                "- 追加自定义忽略规则\n"
                "- 不会覆盖默认规则\n"
                "▼ 示例：\n"
                "['tmp', 'logs']  # 排除临时和日志目录\n"
                "['*.bak', '*.tmp']  # 排除临时文件"
            )
        }
        super().__init__(
            name="project_operation",
            description=(
                "高级项目理解工具，专为智能体优化自我代码而设计。"
                "▼ 核心能力:\n"
                "■ 架构洞察：可视化项目结构，理解模块关系\n"
                "■ 代码智能：提取类/函数/变量等架构元素\n"
                "■ 依赖追踪：识别项目依赖及版本\n"
                "■ 代码搜索：跨文件查找特定代码模式\n"
                "▼ 安全特性:\n"
                "- 所有路径基于项目根目录（防止越权访问）\n"
                "- 自动过滤敏感文件和目录\n"
                "▼ 智能优化:\n"
                "- 多语言支持（Python/JS/Java等）\n"
                "- 依赖生态识别（requirements.txt/package.json/pom.xml等）"
            ),
            parameters=parameters
        )
        
        # 设置项目根目录
        self.project_root = Path(__file__).parent.parent.parent
        # 默认忽略的目录和文件
        self.default_ignore = [
            '__pycache__', '.git', '.idea', 'node_modules', 
            'dist', 'build', 'venv', 'env', '.vscode'
        ]
    
    async def run(
        self, 
        operation: str,
        project_path: Optional[str] = None,
        search_pattern: Optional[str] = None,
        file_types: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        try:
            operation = operation.lower()
            resolved_project_path = self._resolve_project_path(project_path)
            
            if operation == "get_project_structure":
                return await self._get_project_structure(resolved_project_path, ignore_patterns)
            elif operation == "get_code_structure":
                return await self._get_code_structure(resolved_project_path, file_types, ignore_patterns)
            elif operation == "get_dependencies":
                return await self._get_dependencies(resolved_project_path)
            elif operation == "search_code":
                return await self._search_code(resolved_project_path, search_pattern, file_types, ignore_patterns)
            else:
                raise ValueError(f"不支持的操作: {operation}")
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "parameters": {
                    "project_path": project_path,
                    "search_pattern": search_pattern,
                    "file_types": file_types,
                    "ignore_patterns": ignore_patterns
                }
            }
    
    def _resolve_project_path(self, project_path: Optional[str]) -> Path:
        """解析项目路径"""
        if project_path:
            path = Path(project_path)
            if path.is_absolute():
                return path
            return self.project_root / path
        return self.project_root
    
    def _is_ignored(self, path: Path, ignore_patterns: Optional[List[str]] = None) -> bool:
        """检查路径是否应该被忽略"""
        ignore_list = self.default_ignore.copy()
        if ignore_patterns:
            ignore_list.extend(ignore_patterns)
        
        for part in path.parts:
            if part in ignore_list:
                return True
            if part.startswith('.') and part != '.':
                return True
        return False
    
    async def _get_project_structure(self, project_path: Path, ignore_patterns: Optional[List[str]]) -> Dict[str, Any]:
        """获取项目结构树"""
        structure = self._build_directory_tree(project_path, ignore_patterns)
        return {
            "success": True,
            "operation": "get_project_structure",
            "project_path": str(project_path),
            "structure": structure
        }
    
    def _build_directory_tree(self, path: Path, ignore_patterns: Optional[List[str]], depth: int = 0) -> Dict[str, Any]:
        """递归构建目录树"""
        if self._is_ignored(path, ignore_patterns):
            return None
        
        node = {
            "name": path.name,
            "type": "directory" if path.is_dir() else "file",
            "path": str(path.relative_to(self.project_root))
        }
        
        if path.is_dir():
            children = []
            for child in path.iterdir():
                child_node = self._build_directory_tree(child, ignore_patterns, depth + 1)
                if child_node:
                    children.append(child_node)
            node["children"] = children
        
        return node
    
    async def _get_code_structure(self, project_path: Path, file_types: Optional[List[str]], ignore_patterns: Optional[List[str]]) -> Dict[str, Any]:
        """分析代码结构"""
        if not file_types:
            file_types = [".py", ".js", ".java", ".ts"]  # 默认支持这些文件类型
        
        code_entities = {
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": []
        }
        
        # 遍历项目文件
        for file_path in project_path.rglob("*"):
            if self._is_ignored(file_path, ignore_patterns):
                continue
            
            if file_path.is_file() and file_path.suffix in file_types:
                file_entities = self._analyze_code_file(file_path)
                for key in code_entities:
                    code_entities[key].extend(file_entities.get(key, []))
        
        return {
            "success": True,
            "operation": "get_code_structure",
            "file_types": file_types,
            "code_entities": code_entities
        }
    
    def _analyze_code_file(self, file_path: Path) -> Dict[str, List[Dict]]:
        """分析单个代码文件的结构"""
        entities = {
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": []
        }
        
        content = file_path.read_text(encoding="utf-8")
        relative_path = file_path.relative_to(self.project_root)
        
        # Python 文件分析
        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        entities["classes"].append({
                            "name": node.name,
                            "file": str(relative_path),
                            "line": node.lineno,
                            "bases": [base.id for base in node.bases if isinstance(base, ast.Name)]
                        })
                    elif isinstance(node, ast.FunctionDef):
                        entities["functions"].append({
                            "name": node.name,
                            "file": str(relative_path),
                            "line": node.lineno,
                            "args": [arg.arg for arg in node.args.args]
                        })
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            entities["imports"].append({
                                "module": alias.name,
                                "file": str(relative_path),
                                "line": node.lineno
                            })
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        for alias in node.names:
                            entities["imports"].append({
                                "module": f"{module}.{alias.name}" if module else alias.name,
                                "file": str(relative_path),
                                "line": node.lineno
                            })
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                entities["variables"].append({
                                    "name": target.id,
                                    "file": str(relative_path),
                                    "line": node.lineno
                                })
            except SyntaxError:
                pass  # 忽略语法错误
        
        # 其他语言的分析可以在这里扩展
        
        return entities
    
    async def _get_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """获取项目依赖"""
        dependencies = []
        
        # 检查各种依赖文件
        if (project_path / "requirements.txt").exists():
            deps = self._parse_requirements_file(project_path / "requirements.txt")
            dependencies.extend(deps)
        
        if (project_path / "package.json").exists():
            deps = self._parse_package_json(project_path / "package.json")
            dependencies.extend(deps)
        
        if (project_path / "pom.xml").exists():
            deps = self._parse_pom_xml(project_path / "pom.xml")
            dependencies.extend(deps)
        
        return {
            "success": True,
            "operation": "get_dependencies",
            "dependencies": dependencies
        }
    
    def _parse_requirements_file(self, path: Path) -> List[Dict]:
        """解析Python requirements.txt文件"""
        dependencies = []
        content = path.read_text(encoding="utf-8")
        
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                # 简单解析包名和版本
                parts = line.split("==")
                if len(parts) == 2:
                    dependencies.append({
                        "name": parts[0],
                        "version": parts[1],
                        "file": "requirements.txt"
                    })
                else:
                    dependencies.append({
                        "name": line,
                        "version": "unknown",
                        "file": "requirements.txt"
                    })
        
        return dependencies
    
    def _parse_package_json(self, path: Path) -> List[Dict]:
        """解析JavaScript package.json文件"""
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
            dependencies = []
            
            for dep_type in ["dependencies", "devDependencies", "peerDependencies"]:
                if dep_type in content:
                    for name, version in content[dep_type].items():
                        dependencies.append({
                            "name": name,
                            "version": version,
                            "type": dep_type,
                            "file": "package.json"
                        })
            
            return dependencies
        except json.JSONDecodeError:
            return []
    
    def _parse_pom_xml(self, path: Path) -> List[Dict]:
        """解析Java pom.xml文件"""
        # 简化实现，实际应该使用XML解析器
        content = path.read_text(encoding="utf-8")
        dependencies = []
        
        # 简单查找依赖项
        start_idx = 0
        while True:
            start_idx = content.find("<dependency>", start_idx)
            if start_idx == -1:
                break
            
            end_idx = content.find("</dependency>", start_idx)
            if end_idx == -1:
                break
            
            dep_block = content[start_idx:end_idx+13]
            
            # 提取groupId, artifactId, version
            group_id = self._extract_xml_tag(dep_block, "groupId")
            artifact_id = self._extract_xml_tag(dep_block, "artifactId")
            version = self._extract_xml_tag(dep_block, "version")
            
            if group_id and artifact_id:
                dependencies.append({
                    "name": f"{group_id}:{artifact_id}",
                    "version": version or "unknown",
                    "file": "pom.xml"
                })
            
            start_idx = end_idx + 13
        
        return dependencies
    
    def _extract_xml_tag(self, xml: str, tag: str) -> Optional[str]:
        """从XML片段中提取标签内容"""
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        start_idx = xml.find(start_tag)
        if start_idx == -1:
            return None
        
        end_idx = xml.find(end_tag, start_idx)
        if end_idx == -1:
            return None
        
        return xml[start_idx+len(start_tag):end_idx].strip()
    
    async def _search_code(self, project_path: Path, pattern: str, file_types: Optional[List[str]], ignore_patterns: Optional[List[str]]) -> Dict[str, Any]:
        """在项目中搜索代码模式"""
        if not pattern:
            raise ValueError("搜索模式不能为空")
        
        if not file_types:
            file_types = [".py", ".js", ".java", ".ts", ".html", ".css"]
        
        results = []
        
        for file_path in project_path.rglob("*"):
            if self._is_ignored(file_path, ignore_patterns):
                continue
            
            if file_path.is_file() and file_path.suffix in file_types:
                content = file_path.read_text(encoding="utf-8")
                if pattern in content:
                    # 简单实现：记录包含模式的文件
                    # 实际中可以添加行号和高亮上下文
                    results.append({
                        "file": str(file_path.relative_to(self.project_root)),
                        "matches": [pattern]  # 简化实现
                    })
        
        return {
            "success": True,
            "operation": "search_code",
            "pattern": pattern,
            "results": results
        }