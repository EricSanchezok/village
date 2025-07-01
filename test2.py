from playwright.__main__ import get_driver_env

# 打印浏览器实际路径
chromium_path = get_driver_env()
print("Chromium路径:", chromium_path)