@echo off
python %~f0\..\sut-json-load.py %1 2>&1 | findstr /c:"Expecting property name" /c:"Expecting object" >NUL 2>&1
