@echo off
chcp 65001 >nul
echo ========================================
echo   MiniCode - 本地 AI 编程助手 安装程序
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] 安装依赖...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [2/3] 配置 API Key...
if not exist ".env" (
    echo [提示] 请创建 .env 文件并填入你的 API Key
    echo 示例: SILICONFLOW_API_KEY=sk-你的key
    echo 获取地址: https://cloud.siliconflow.cn/account/ak
    copy .env.example .env >nul
) else (
    echo [OK] .env 文件已存在
)

echo [3/3] 创建桌面快捷方式...
python -c "from pathlib import Path; import os; desktop=Path(os.environ['USERPROFILE'])/'Desktop'; print(f'桌面路径: {desktop}')" >nul 2>&1

echo.
echo ========================================
echo   安装完成！
echo ========================================
echo.
echo  使用方法:
echo    终端模式:   python cli\main.py chat
echo    单次执行:   python cli\main.py headless "你的任务"
echo    Web 界面:   streamlit run web\app.py
echo    桌面版:     python desktop_app.py
echo.
pause
