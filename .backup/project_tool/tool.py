import os
import json
import ast
from pathlib import Path
from typing import Optional, Dict, Any, List
from core import ToolBase 

class ProjectTool(ToolBase):
    """
    用于分析和理解本项目代码的工具。
    """
    def __init__(self):
        parameters = {
            "operation": (
                str,
                "指定要执行的操作。可用选项: "
                "'get_project_structure', "
                "'get_code_structure', "
                "'get_dependencies', "
                "'search_code'."
            ),
            "project_path": (
                Optional[str],
                "项目根目录的路径。如果为 null，则使用默认的项目根目录。"
            ),
            "search_pattern": (
                Optional[str],
                "用于 'search_code' 操作的搜索关键词或正则表达式。"
            ),
            "file_types": (
                Optional[List[str]],
                "要包含的文件扩展名列表 (例如: ['.py', '.js'])。适用于 'get_code_structure' 和 'search_code' 操作。"
            ),
            "ignore_patterns": (
                Optional[List[str]],
                "要忽略的目录或文件模式列表。此列表会附加到默认的忽略规则之后 (例如: '.git', 'node_modules')。"
            )
        }
        
        super().__init__(
            name="project_operation",
            description=(
                "提供对本项目源代码的静态分析功能。此工具可以：\n"
                "1. `get_project_structure`: 生成项目的文件和目录结构树。\n"
                "2. `get_code_structure`: 从源代码中提取关键实体，如类、函数和导入。\n"
                "3. `get_dependencies`: 从常见的依赖文件 (如 requirements.txt, package.json) 中解析项目依赖。\n"
                "4. `search_code`: 在指定的代码文件中搜索文本或正则表达式模式。"
            ),
            parameters=parameters
        )

        self.project_root = Path(__file__).parent.parent.parent
        self.default_ignore = [
            '__pycache__', '.git', '.idea', 'node_modules', 
            'dist', 'build', 'venv', '.vscode'
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
            return {}
        
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
    
    async def _search_code(self, project_path: Path, pattern: Optional[str], file_types: Optional[List[str]], ignore_patterns: Optional[List[str]]) -> Dict[str, Any]:
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