@echo off
python %1 2>&1 | find "sum: 55" >NUL 2>&1
