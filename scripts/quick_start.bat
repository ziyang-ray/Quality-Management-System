@echo off
REM 合规助手快速启动脚本
REM 使用方法：双击运行或在命令行执行

echo ========================================
echo   合规助手快速启动
echo ========================================
echo.

REM 设置 Python 路径
set PYTHON=G:/anaconda/envs/SHRL/python.exe

REM 检查 Python 环境
echo [1/5] 检查 Python 环境...
%PYTHON% --version
if errorlevel 1 (
    echo 错误：找不到 Python 环境
    pause
    exit /b 1
)
echo.

REM 检查依赖
echo [2/5] 检查依赖...
%PYTHON% -c "import pydantic; import langchain; print('依赖检查通过')"
if errorlevel 1 (
    echo 错误：缺少必要依赖
    pause
    exit /b 1
)
echo.

REM 检查数据索引
echo [3/5] 检查数据索引...
if exist "data\compliance_index\chunks.jsonl" (
    echo 索引文件已存在
) else (
    echo 正在构建索引...
    %PYTHON% scripts\build_compliance_index.py
)
echo.

REM 检查知识图谱
echo [4/5] 检查知识图谱...
if exist "data\compliance_graph\nodes.jsonl" (
    echo 知识图谱已存在
) else (
    echo 正在构建知识图谱...
    %PYTHON% scripts\build_initial_knowledge_graph.py
)
echo.

REM 检查环境配置
echo [5/5] 检查环境配置...
if exist ".env" (
    echo 环境配置文件已存在
) else (
    echo 警告：未找到 .env 文件
    echo 请复制 .env.example 为 .env 并配置 API Key
    echo.
    echo 示例：
    echo   copy .env.example .env
    echo   然后编辑 .env 文件，添加你的 API Key
    echo.
    pause
    exit /b 1
)

echo ========================================
echo   环境准备完成！
echo ========================================
echo.
echo 现在你可以运行以下命令：
echo.
echo 1. 预览证据检索（不调用 LLM）：
echo    %PYTHON% scripts\preview_compliance_review.py --request "Please review CAPA" --full
echo.
echo 2. 生成审查报告：
echo    %PYTHON% scripts\run_compliance_review.py --request "Please review CAPA" --output reports\capa_review.md
echo.
echo 3. 测试新功能：
echo    %PYTHON% scripts\test_imports.py
echo.
echo 按任意键退出...
pause >nul
