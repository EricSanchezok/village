import asyncio
import os
import platform
from pathlib import Path
from typing import Optional, Dict, Any
from core.tool import ToolBase 

# --- 第 1 部分：环境检测函数 ---
# 你提供的环境检测函数，我们将直接使用它
def get_shell_from_env():
    """
    通过检查环境变量来尝试确定当前的 shell 环境。
    """
    # PowerShell 的一个典型特征是 PSModulePath 环境变量
    if 'PSModulePath' in os.environ:
        return "PowerShell"
    
    # os.name 在 Windows 上是 'nt'，在类 Unix 系统上是 'posix'
    if os.name == 'posix':
        # BASH 变量是 Bash shell 的一个强有力指标
        if 'BASH' in os.environ:
            return "Bash"
        
        # SHELL 变量是另一个常用指标
        shell_path = os.environ.get('SHELL', '')
        if 'bash' in shell_path:
            return "Bash"
        elif 'zsh' in shell_path:
            # 我们可以将 Zsh 也视为一种 Bash 兼容的 shell
            return "Bash" # 或者返回 "Zsh" 进行更精细的控制
        else:
            return os.path.basename(shell_path) or "Unknown POSIX Shell"
    
    elif os.name == 'nt':
        if 'COMSPEC' in os.environ and 'cmd.exe' in os.environ['COMSPEC']:
            return "CMD"

    return "Unknown"


class BashTool(ToolBase):
    """
    一个用于在安全的、受限的环境中执行 Bash 命令的工具。
    """
    # ... (你的 BashTool 完整代码) ...
    def __init__(self, timeout: int = 60):
        parameters = {
            "command": (str, "要执行的单行 Bash 命令。注意：不支持复杂的、交互式的或需要特权的命令。"),
            "working_directory": (Optional[str], "命令执行的工作目录。必须是相对于项目根目录的相对路径。如果未提供，则默认为项目根目录。"),
            "timeout": (Optional[int], f"命令执行的超时时间（秒）。如果未提供，则使用默认值 {timeout} 秒。")
        }
        super().__init__(
            name="execute_bash",
            description="在受限的沙箱环境中异步执行单行 Bash 命令。适用于 Linux, macOS, 和 Windows Subsystem for Linux (WSL)。",
            parameters=parameters
        )
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.default_timeout = timeout

    def _resolve_working_directory(self, path: Optional[str]) -> Path:
        if not path: return self.project_root
        path_obj = Path(path)
        if path_obj.is_absolute(): raise PermissionError("工作目录不允许使用绝对路径。请提供相对于项目根目录的路径。")
        resolved = (self.project_root / path_obj).resolve()
        if self.project_root not in resolved.parents and resolved != self.project_root:
            raise PermissionError(f"工作目录访问超出项目范围: {resolved}")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    async def run(self, command: str, working_directory: Optional[str] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        if not command: return {"success": False, "error": "命令不能为空。", "command": command, "return_code": -1}
        effective_timeout = timeout if timeout is not None else self.default_timeout
        try:
            cwd = self._resolve_working_directory(working_directory)
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=effective_timeout)
            stdout = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr = stderr_bytes.decode('utf-8', errors='replace').strip()
            return {"success": process.returncode == 0, "command": command, "working_directory": str(cwd), "return_code": process.returncode, "stdout": stdout, "stderr": stderr}
        except asyncio.TimeoutError:
            return {"success": False, "error": f"命令执行超时（超过 {effective_timeout} 秒）。", "command": command, "return_code": -1}
        except PermissionError as e:
            return {"success": False, "error": str(e), "command": command}
        except Exception as e:
            return {"success": False, "error": f"执行命令时发生未知错误: {str(e)}", "command": command, "return_code": -1}

class PowerShellTool(ToolBase):
    """
    一个用于在 Windows 环境下，在安全的、受限的环境中执行 PowerShell 命令的工具。
    """
    def __init__(self, timeout: int = 60):
        parameters = {
            "command": (str, "要执行的单行 PowerShell 命令。注意：不支持复杂的、交互式的或需要特权的命令。"),
            "working_directory": (Optional[str], "命令执行的工作目录。必须是相对于项目根目录的相对路径。如果未提供，则默认为项目根目录。"),
            "timeout": (Optional[int], f"命令执行的超时时间（秒）。如果未提供，则使用默认值 {timeout} 秒。")
        }
        super().__init__(
            name="execute_powershell",
            description="在受限的沙箱环境中异步执行单行 PowerShell 命令 (仅限 Windows)。",
            parameters=parameters
        )
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.default_timeout = timeout

    def _resolve_working_directory(self, path: Optional[str]) -> Path:
        if not path: return self.project_root
        path_obj = Path(path)
        if path_obj.is_absolute(): raise PermissionError("工作目录不允许使用绝对路径。请提供相对于项目根目录的路径。")
        resolved = (self.project_root / path_obj).resolve()
        if self.project_root not in resolved.parents and resolved != self.project_root:
            raise PermissionError(f"工作目录访问超出项目范围: {resolved}")
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved
    
    async def run(self, command: str, working_directory: Optional[str] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        if platform.system() != "Windows": return {"success": False, "error": "此工具只能在 Windows 操作系统上运行。", "command": command}
        if not command: return {"success": False, "error": "命令不能为空。", "command": command, "return_code": -1}
        effective_timeout = timeout if timeout is not None else self.default_timeout
        try:
            cwd = self._resolve_working_directory(working_directory)
            process = await asyncio.create_subprocess_exec('powershell', '-NoProfile', '-Command', command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, cwd=cwd)
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=effective_timeout)
            stdout = stdout_bytes.decode('utf-8', errors='replace').strip()
            stderr = stderr_bytes.decode('utf-8', errors='replace').strip()
            return {"success": process.returncode == 0, "command": command, "working_directory": str(cwd), "return_code": process.returncode, "stdout": stdout, "stderr": stderr}
        except asyncio.TimeoutError:
            return {"success": False, "error": f"命令执行超时（超过 {effective_timeout} 秒）。", "command": command, "return_code": -1}
        except FileNotFoundError:
            return {"success": False, "error": "执行失败：'powershell' 命令未找到。请确保 PowerShell 已安装并在系统的 PATH 中。", "command": command}
        except PermissionError as e:
            return {"success": False, "error": str(e), "command": command}
        except Exception as e:
            return {"success": False, "error": f"执行命令时发生未知错误: {str(e)}", "command": command, "return_code": -1}

class ShellTool(ToolBase):
    """
    一个智能的、跨平台的 Shell 执行工具。
    它会自动检测当前环境，并选择使用 Bash 或 PowerShell 来执行命令。
    """
    def __init__(self, timeout: int = 60):
        self.shell_type = get_shell_from_env()
        self._delegate: ToolBase = None 

        if self.shell_type == "Bash":
            self._delegate = BashTool(timeout=timeout)
        elif self.shell_type == "PowerShell":
            self._delegate = PowerShellTool(timeout=timeout)
        else:
            raise RuntimeError(f"不支持的 Shell 环境: '{self.shell_type}'. ShellTool 只能在 Bash 或 PowerShell 中工作。")

        unified_parameters = {
            "command": (
                str, 
                "要执行的单行 shell 命令。"
            ),
            "working_directory": (
                Optional[str],
                "命令执行的工作目录（相对于项目根目录的路径）。如果为 null，则使用项目根目录。"
            ),
            "timeout": (
                Optional[int],
                f"命令执行的超时时间（秒）。如果为 null，则默认为 {timeout} 秒。"
            )
        }

        super().__init__(
            name="execute_shell_command",
            description=(
                "在安全的沙箱环境中执行 shell 命令。"
                "此工具会自动为当前操作系统选择合适的 shell (例如：为 Windows 选择 PowerShell，为 Linux/macOS 选择 Bash)。"
                "主要用于执行非交互式的、自动化的任务，如文件操作、运行脚本或检查系统状态。"
            ),
            parameters=unified_parameters
        )

    async def run(
        self,
        command: str,
        working_directory: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        异步执行一个 Shell 命令。
        这个方法会将调用直接转发给内部持有的具体工具实例 (BashTool 或 PowerShellTool)。
        """
        # 直接调用代理实例的 run 方法
        return await self._delegate.run(
            command=command,
            working_directory=working_directory,
            timeout=timeout
        )


async def main():
    print(f"--- 智能 Shell 工具测试 ---")
    try:
        # 无论在什么系统，都只需要实例化 ShellTool
        shell_tool = ShellTool()
        
        print(f"检测到当前 Shell 类型为: {shell_tool.shell_type}")
        print(f"将要使用的内部工具为: {shell_tool._delegate.__class__.__name__}")
        print(f"工具暴露的名称为: {shell_tool.name}")
        
        # 准备一个跨平台都能理解的简单命令
        # 在 PowerShell 中是 'Get-Location', 在 Bash 中是 'pwd'
        command_to_run = "Get-Location" if shell_tool.shell_type == "PowerShell" else "pwd"
        
        print(f"\n执行命令: '{command_to_run}'")
        
        result = await shell_tool.run(command=command_to_run)
        
        print("\n--- 执行结果 ---")
        if result.get("success"):
            print(f"✅ 命令成功执行")
            print(f"   退出码: {result.get('return_code')}")
            print(f"   标准输出 (stdout):\n---\n{result.get('stdout')}\n---")
        else:
            print(f"❌ 命令执行失败")
            print(f"   错误信息: {result.get('error')}")

    except RuntimeError as e:
        print(f"\n初始化 ShellTool 失败: {e}")
    except Exception as e:
        print(f"\n发生未知错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())