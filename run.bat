@echo off
cd /d %~dp0
python -m uvicorn server.app:app --host 0.0.0.0 --port 8765 --reload
