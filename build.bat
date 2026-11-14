@echo off
rem Build helper cho du an edge-ai - tu dong xoa bien MSYSTEM (xung dot Git Bash)
set "MSYSTEM="
set "IDF_PATH=C:\Espressif\frameworks\esp-idf-v5.5.4"
set "IDF_PYTHON_ENV_PATH=C:\Espressif\python_env\idf5.5_py3.11_env"
set "IDF_TOOLS_PATH=C:\Espressif"
set "PATH=C:\Espressif\python_env\idf5.5_py3.11_env\Scripts;C:\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin;C:\Espressif\tools\cmake\3.30.2\bin;C:\Espressif\tools\ninja\1.12.1;C:\Espressif\tools\ccache\4.12.1\ccache-4.12.1-windows-x86_64;C:\Espressif\tools\dfu-util\0.11\dfu-util-0.11-win64;C:\Espressif\tools\idf-git\2.44.0\cmd;C:\Espressif\tools\idf-python\3.11.2;%PATH%"
cd /d "%~dp0"
python "%IDF_PATH%\tools\idf.py" %*
