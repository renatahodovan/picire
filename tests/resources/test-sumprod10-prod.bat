@echo off
python %1 2>&1 | find "prod: 3628800" >NUL 2>&1
