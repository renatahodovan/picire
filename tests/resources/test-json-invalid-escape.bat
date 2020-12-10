@echo off
python %~f0\..\sut-json-load.py %1 2>&1 | find "Error: Invalid \escape:" >NUL 2>&1
