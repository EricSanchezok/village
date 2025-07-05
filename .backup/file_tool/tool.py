import os
import json
import shutil
import zipfile
import aiofiles
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Union, List, Tuple
from core import ToolBase
from filelock import FileLock

class FileTool(ToolBase):
    """
    文件操作工具，支持全面的文件系统操作
    """
    
    def __init__(self):
        parameters = {
            "operation": (
                str,
                "必须指定的操作类型。可用操作: \n"
                "- read_file: 读取文件内容\n"
                "- write_file: 覆盖写入文件\n"
                "- append_file: 追加文件内容\n"
                "- delete_file: 删除文件或目录\n"
                "- list_directory: 列出目录内容\n"
                "- create_directory: 创建新目录\n"
                "- file_exists: 检查文件/目录是否存在\n"
                "- get_file_info: 获取文件元数据\n"
                "- move_file: 移动/重命名文件或目录\n"
                "- copy_file: 复制文件或目录\n"
                "- set_permissions: 设置文件权限\n"
                "- search_files: 搜索匹配文件\n"
                "- compress: 创建压缩文件\n"
                "- extract: 解压文件"
            ),
            "file_path": (
                Optional[str],
                "文件系统路径。可以是绝对路径或相对于项目根目录的相对路径。"
                "用于文件操作(read/write/delete等)和部分目录操作。"
            ),
            "directory_path": (
                Optional[str],
                "目录路径。优先于file_path用于目录操作(list/create等)。"
                "可以是绝对路径或相对于项目根目录的相对路径。"
            ),
            "content": (
                Optional[str],
                "要写入或追加的文件内容。仅用于write_file和append_file操作。"
            ),
            "new_file_path": (
                Optional[str],
                "目标路径。用于move_file(移动目标)和copy_file(复制目标)操作。"
            ),
            "encoding": (
                Optional[str],
                "文件编码格式，默认为'utf-8'。"
                "仅用于文本文件操作(read/write/append)。"
            ),
            "recursive": (
                Optional[bool],
                "递归操作标志，默认为False。"
                "用于: \n"
                "- list_directory: 递归列出子目录\n"
                "- delete_file: 递归删除非空目录\n"
                "- search_files: 递归搜索子目录"
            ),
            "permissions": (
                Optional[int],
                "文件权限(八进制格式)，例如0o755表示rwxr-xr-x。"
                "仅用于set_permissions操作。"
            ),
            "pattern": (
                Optional[str],
                "文件匹配模式，支持通配符(*)和正则表达式。"
                "仅用于search_files操作。"
            ),
            "archive_path": (
                Optional[str],
                "压缩文件路径。"
                "用于: \n"
                "- compress: 压缩输出路径\n"
                "- extract: 解压输入路径"
            ),
            "target_dir": (
                Optional[str],
                "解压目标目录。仅用于extract操作。"
            )
        }
        super().__init__(
            name="file_operation",
            description=(
                "全面的文件系统操作工具，支持文件和目录的创建、读取、修改、删除、搜索、压缩和解压。"
                "关键能力包括:\n"
                "1. 原子文件写入 - 确保写入操作不会导致文件损坏\n"
                "2. 递归操作 - 支持目录的递归处理\n"
                "3. 路径安全 - 所有操作限制在项目目录内\n"
                "4. 异步处理 - 高效处理大文件操作\n"
                "\n"
                "使用指南:\n"
                "- 使用相对路径时基于项目根目录: PROJECT_ROOT\n"
                "- 文件操作自动处理并发冲突\n"
                "- 压缩/解压支持ZIP格式\n"
                "- 权限设置使用UNIX风格八进制格式"
            ),
            parameters=parameters
        )
        
        # 设置项目根目录
        self.project_root = Path(__file__).parent.parent.parent
    
    async def run(
        self, 
        operation: str,
        file_path: Optional[str] = None,
        content: Optional[str] = None,
        directory_path: Optional[str] = None,
        encoding: str = "utf-8",
        recursive: bool = False,
        new_file_path: Optional[str] = None,
        permissions: Optional[int] = None,
        pattern: Optional[str] = None,
        archive_path: Optional[str] = None,
        target_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            operation = operation.lower()
            
            if operation == "read_file":
                return await self._read_file(file_path, encoding)
            elif operation == "write_file":
                return await self._write_file(file_path, content, encoding)
            elif operation == "append_file":
                return await self._append_file(file_path, content, encoding)
            elif operation == "delete_file":
                return await self._delete_file(file_path, recursive)
            elif operation == "list_directory":
                return await self._list_directory(directory_path or file_path, recursive)
            elif operation == "create_directory":
                return await self._create_directory(directory_path or file_path)
            elif operation == "file_exists":
                return await self._file_exists(file_path)
            elif operation == "get_file_info":
                return await self._get_file_info(file_path)
            elif operation == "move_file":
                return await self._move_file(file_path, new_file_path)
            elif operation == "copy_file":
                return await self._copy_file(file_path, new_file_path)
            elif operation == "set_permissions":
                return await self._set_permissions(file_path, permissions)
            elif operation == "search_files":
                return await self._search_files(directory_path or file_path, pattern, recursive)
            elif operation == "compress":
                return await self._compress(file_path or directory_path, archive_path)
            elif operation == "extract":
                return await self._extract(archive_path, target_dir)
            else:
                raise ValueError(f"不支持的操作: {operation}")
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "parameters": {
                    "file_path": file_path,
                    "content": content[:100] + "..." if content and len(content) > 100 else content,
                    "directory_path": directory_path,
                    "encoding": encoding,
                    "recursive": recursive,
                    "new_file_path": new_file_path,
                    "permissions": permissions,
                    "pattern": pattern,
                    "archive_path": archive_path,
                    "target_dir": target_dir
                }
            }
    
    def _resolve_path(self, path: str) -> Path:
        """解析路径，支持相对路径和绝对路径，并确保路径安全"""
        if not path:
            raise ValueError("路径不能为空")
        
        path_obj = Path(path)
        if path_obj.is_absolute():
            resolved = path_obj
        else:
            resolved = self.project_root / path
        
        # 解析符号链接和'.', '..'
        resolved = resolved.resolve()
        
        # 确保路径在项目范围内
        if self.project_root.resolve() not in resolved.parents and resolved != self.project_root.resolve():
            raise PermissionError(f"访问超出项目目录范围: {resolved}")
        
        return resolved
    
    async def _read_file(self, file_path: Optional[str], encoding: str) -> Dict[str, Any]:
        """读取文件内容（支持大文件）"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        if not resolved_path.is_file():
            raise ValueError(f"路径不是文件: {resolved_path}")
        
        # 使用aiofiles异步读取文件
        async with aiofiles.open(resolved_path, 'r', encoding=encoding) as f:
            content = await f.read()
        
        return {
            "success": True,
            "operation": "read_file",
            "file_path": str(resolved_path),
            "content": content,
            "file_size": resolved_path.stat().st_size,
            "encoding": encoding
        }
    
    async def _write_file(self, file_path: Optional[str], content: Optional[str], encoding: str) -> Dict[str, Any]:
        """原子写入文件内容（覆盖）"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        if content is None:
            raise ValueError("文件内容不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        # 确保父目录存在
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建临时文件路径
        temp_path = resolved_path.with_suffix(resolved_path.suffix + ".tmp")
        
        # 使用文件锁确保原子操作
        lock_path = resolved_path.with_suffix('.lock')
        with FileLock(lock_path):
            # 写入临时文件
            async with aiofiles.open(temp_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            # 原子替换
            temp_path.replace(resolved_path)
        
        return {
            "success": True,
            "operation": "write_file",
            "file_path": str(resolved_path),
            "content_length": len(content),
            "encoding": encoding,
            "message": f"文件已安全写入: {resolved_path}"
        }
    
    async def _append_file(self, file_path: Optional[str], content: Optional[str], encoding: str) -> Dict[str, Any]:
        """追加文件内容"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        if content is None:
            raise ValueError("追加内容不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        # 确保父目录存在
        resolved_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用文件锁确保安全
        lock_path = resolved_path.with_suffix('.lock')
        with FileLock(lock_path):
            async with aiofiles.open(resolved_path, 'a', encoding=encoding) as f:
                await f.write(content)
        
        return {
            "success": True,
            "operation": "append_file",
            "file_path": str(resolved_path),
            "appended_length": len(content),
            "encoding": encoding,
            "message": f"内容已安全追加到文件: {resolved_path}"
        }
    
    async def _delete_file(self, file_path: Optional[str], recursive: bool = False) -> Dict[str, Any]:
        """删除文件或目录"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"路径不存在: {resolved_path}")
        
        if resolved_path.is_file():
            resolved_path.unlink()
            return {
                "success": True,
                "operation": "delete_file",
                "file_path": str(resolved_path),
                "message": f"文件已删除: {resolved_path}"
            }
        elif resolved_path.is_dir():
            if recursive:
                # 递归删除非空目录
                shutil.rmtree(resolved_path)
                return {
                    "success": True,
                    "operation": "delete_file",
                    "file_path": str(resolved_path),
                    "message": f"目录及内容已递归删除: {resolved_path}"
                }
            else:
                if any(resolved_path.iterdir()):
                    raise OSError(f"目录非空: {resolved_path}。使用 recursive=True 强制删除")
                resolved_path.rmdir()
                return {
                    "success": True,
                    "operation": "delete_file",
                    "file_path": str(resolved_path),
                    "message": f"空目录已删除: {resolved_path}"
                }
        else:
            raise ValueError(f"无法删除路径: {resolved_path}")
    
    async def _list_directory(self, directory_path: Optional[str], recursive: bool) -> Dict[str, Any]:
        """列出目录内容"""
        if not directory_path:
            raise ValueError("目录路径不能为空")
        
        resolved_path = self._resolve_path(directory_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"目录不存在: {resolved_path}")
        
        if not resolved_path.is_dir():
            raise ValueError(f"路径不是目录: {resolved_path}")
        
        items = []
        
        if recursive:
            for item in resolved_path.rglob("*"):
                # 跳过隐藏文件和目录
                if item.name.startswith('.'):
                    continue
                    
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "relative_path": str(item.relative_to(resolved_path)),
                    "type": "file" if item.is_file() else "directory",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified_time": item.stat().st_mtime
                })
        else:
            for item in resolved_path.iterdir():
                # 跳过隐藏文件和目录
                if item.name.startswith('.'):
                    continue
                    
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "file" if item.is_file() else "directory",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified_time": item.stat().st_mtime
                })
        
        return {
            "success": True,
            "operation": "list_directory",
            "directory_path": str(resolved_path),
            "recursive": recursive,
            "items": items,
            "total_count": len(items)
        }
    
    async def _create_directory(self, directory_path: Optional[str]) -> Dict[str, Any]:
        """创建目录"""
        if not directory_path:
            raise ValueError("目录路径不能为空")
        
        resolved_path = self._resolve_path(directory_path)
        
        resolved_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "success": True,
            "operation": "create_directory",
            "directory_path": str(resolved_path),
            "message": f"目录已创建: {resolved_path}"
        }
    
    async def _file_exists(self, file_path: Optional[str]) -> Dict[str, Any]:
        """检查文件是否存在"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        return {
            "success": True,
            "operation": "file_exists",
            "file_path": str(resolved_path),
            "exists": resolved_path.exists(),
            "is_file": resolved_path.is_file() if resolved_path.exists() else None,
            "is_directory": resolved_path.is_dir() if resolved_path.exists() else None
        }
    
    async def _get_file_info(self, file_path: Optional[str]) -> Dict[str, Any]:
        """获取文件信息"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        stat = resolved_path.stat()
        
        return {
            "success": True,
            "operation": "get_file_info",
            "file_path": str(resolved_path),
            "name": resolved_path.name,
            "size": stat.st_size,
            "is_file": resolved_path.is_file(),
            "is_directory": resolved_path.is_dir(),
            "created_time": stat.st_ctime,
            "modified_time": stat.st_mtime,
            "accessed_time": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:]
        }
    
    async def _move_file(self, source_path: Optional[str], target_path: Optional[str]) -> Dict[str, Any]:
        """移动或重命名文件/目录"""
        if not source_path or not target_path:
            raise ValueError("源路径和目标路径不能为空")
        
        source = self._resolve_path(source_path)
        target = self._resolve_path(target_path)
        
        if not source.exists():
            raise FileNotFoundError(f"源路径不存在: {source}")
        
        # 使用文件锁确保安全
        lock_path = source.with_suffix('.lock')
        with FileLock(lock_path):
            shutil.move(source, target)
        
        return {
            "success": True,
            "operation": "move_file",
            "source_path": str(source),
            "target_path": str(target),
            "message": f"已移动: {source} -> {target}"
        }
    
    async def _copy_file(self, source_path: Optional[str], target_path: Optional[str]) -> Dict[str, Any]:
        """复制文件/目录"""
        if not source_path or not target_path:
            raise ValueError("源路径和目标路径不能为空")
        
        source = self._resolve_path(source_path)
        target = self._resolve_path(target_path)
        
        if not source.exists():
            raise FileNotFoundError(f"源路径不存在: {source}")
        
        # 使用文件锁确保安全
        lock_path = source.with_suffix('.lock')
        with FileLock(lock_path):
            if source.is_file():
                shutil.copy2(source, target)
            elif source.is_dir():
                shutil.copytree(source, target)
            else:
                raise ValueError(f"无法复制路径: {source}")
        
        return {
            "success": True,
            "operation": "copy_file",
            "source_path": str(source),
            "target_path": str(target),
            "message": f"已复制: {source} -> {target}"
        }
    
    async def _set_permissions(self, file_path: Optional[str], permissions: Optional[int]) -> Dict[str, Any]:
        """设置文件权限"""
        if not file_path:
            raise ValueError("文件路径不能为空")
        if permissions is None:
            raise ValueError("权限不能为空")
        
        resolved_path = self._resolve_path(file_path)
        
        if not resolved_path.exists():
            raise FileNotFoundError(f"路径不存在: {resolved_path}")
        
        # 使用文件锁确保安全
        lock_path = resolved_path.with_suffix('.lock')
        with FileLock(lock_path):
            resolved_path.chmod(permissions)
        
        return {
            "success": True,
            "operation": "set_permissions",
            "file_path": str(resolved_path),
            "permissions": oct(permissions),
            "message": f"权限已设置为: {oct(permissions)}"
        }
    
    async def _search_files(self, directory_path: Optional[str], pattern: Optional[str], recursive: bool) -> Dict[str, Any]:
        """搜索匹配模式的文件"""
        if not directory_path:
            raise ValueError("目录路径不能为空")
        if not pattern:
            raise ValueError("搜索模式不能为空")
        
        resolved_dir = self._resolve_path(directory_path)
        
        if not resolved_dir.exists():
            raise FileNotFoundError(f"目录不存在: {resolved_dir}")
        
        if not resolved_dir.is_dir():
            raise ValueError(f"路径不是目录: {resolved_dir}")
        
        results = []
        
        if recursive:
            search_iter = resolved_dir.rglob(pattern)
        else:
            search_iter = resolved_dir.glob(pattern)
        
        for path in search_iter:
            if path.is_file() and not path.name.startswith('.'):
                results.append({
                    "path": str(path),
                    "relative_path": str(path.relative_to(resolved_dir)),
                    "size": path.stat().st_size,
                    "modified_time": path.stat().st_mtime
                })
        
        return {
            "success": True,
            "operation": "search_files",
            "directory_path": str(resolved_dir),
            "pattern": pattern,
            "recursive": recursive,
            "results": results,
            "count": len(results)
        }
    
    async def _compress(self, source_path: Optional[str], archive_path: Optional[str]) -> Dict[str, Any]:
        """压缩文件或目录"""
        if not source_path or not archive_path:
            raise ValueError("源路径和压缩文件路径不能为空")
        
        source = self._resolve_path(source_path)
        archive = self._resolve_path(archive_path)
        
        if not source.exists():
            raise FileNotFoundError(f"源路径不存在: {source}")
        
        # 确保压缩文件父目录存在
        archive.parent.mkdir(parents=True, exist_ok=True)
        
        # 使用文件锁确保安全
        lock_path = source.with_suffix('.lock')
        with FileLock(lock_path):
            if source.is_file():
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(source, arcname=source.name)
            elif source.is_dir():
                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file in source.rglob('*'):
                        if file.is_file() and not file.name.startswith('.'):
                            arcname = file.relative_to(source)
                            zipf.write(file, arcname=arcname)
            else:
                raise ValueError(f"无法压缩路径: {source}")
        
        return {
            "success": True,
            "operation": "compress",
            "source_path": str(source),
            "archive_path": str(archive),
            "message": f"已创建压缩文件: {archive}"
        }
    
    async def _extract(self, archive_path: Optional[str], target_dir: Optional[str]) -> Dict[str, Any]:
        """解压文件"""
        if not archive_path or not target_dir:
            raise ValueError("压缩文件路径和目标目录不能为空")
        
        archive = self._resolve_path(archive_path)
        target = self._resolve_path(target_dir)
        
        if not archive.exists():
            raise FileNotFoundError(f"压缩文件不存在: {archive}")
        
        if not archive.is_file():
            raise ValueError(f"路径不是文件: {archive}")
        
        # 确保目标目录存在
        target.mkdir(parents=True, exist_ok=True)
        
        # 使用文件锁确保安全
        lock_path = archive.with_suffix('.lock')
        with FileLock(lock_path):
            with zipfile.ZipFile(archive, 'r') as zipf:
                zipf.extractall(target)
        
        return {
            "success": True,
            "operation": "extract",
            "archive_path": str(archive),
            "target_dir": str(target),
            "message": f"已解压到: {target}"
        }