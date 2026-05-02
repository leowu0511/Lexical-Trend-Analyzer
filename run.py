"""
話題雷達（Topic Radar）啟動腳本
切換到 code/ 目錄後執行 main.py，確保 import 路徑正確
"""
import os
import sys
import subprocess

if __name__ == "__main__":
    code_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "code")
    os.chdir(code_dir)
    try:
        process = subprocess.run([sys.executable, "main.py"])
        sys.exit(process.returncode)
    except KeyboardInterrupt:
        # 使用者按 Ctrl+C → 靜默退出，不印 traceback
        sys.exit(0)
