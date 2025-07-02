import os

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
            return "Zsh"
        else:
            # 返回 SHELL 变量的值，如果它存在
            return os.path.basename(shell_path) or "Unknown POSIX Shell"
    
    elif os.name == 'nt':
        # 在 Windows 上，如果不是 PowerShell，那很可能就是 cmd.exe
        # COMSPEC 环境变量通常指向 cmd.exe
        if 'COMSPEC' in os.environ and 'cmd.exe' in os.environ['COMSPEC']:
            return "CMD"

    return "Unknown"

if __name__ == "__main__":
    current_shell = get_shell_from_env()
    print(f"检测到当前 Shell (通过环境变量): {current_shell}")