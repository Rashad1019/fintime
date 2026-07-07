@echo off
cd /d "%~dp0"
echo Starting Fincent... close this window or press Ctrl+C to stop.
uv run streamlit run app.py
pause
