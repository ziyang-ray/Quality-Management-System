@echo off
REM 合规审查运行脚本

echo Setting up environment...
set PYTHONIOENCODING=utf-8
set ANTHROPIC_BASE_URL=https://token-plan-sgp.xiaomimimo.com/anthropic
set ANTHROPIC_API_KEY=tp-s7egar2qket67uqm1yb7u842lvtp7bmgcjyyticqcojigb1v
set ANTHROPIC_AUTH_TOKEN=tp-s7egar2qket67uqm1yb7u842lvtp7bmgcjyyticqcojigb1v

echo Running compliance review...
G:/anaconda/envs/SHRL/python.exe scripts/run_compliance_review.py --request "请审查CAPA（纠正预防措施）" --output reports/capa_review.md --artifacts-dir runs

echo Done!
pause
