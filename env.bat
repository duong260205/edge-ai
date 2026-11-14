@echo off
rem Kich hoat moi truong ESP-IDF cho du an edge-ai
call C:\Espressif\python_env\idf5.5_py3.11_env\Scripts\activate.bat
set IDF_PATH=C:\Espressif\frameworks\esp-idf-v5.5.4
set PATH=C:\Espressif\tools\xtensa-esp-elf\esp-14.2.0_20260121\xtensa-esp-elf\bin;C:\Espressif\tools\cmake\3.30.2\bin;C:\Espressif\tools\ninja\1.12.1\bin;C:\Espressif\tools\idf-exe\1.0.3;C:\Espressif\tools\ccache\4.12.1\ccache-4.12.1-windows-x86_64;C:\Espressif\tools\dfu-util\0.11\dfu-util-0.11-win64;C:\Espressif\tools\idf-git\2.44.0\cmd;%PATH%
cd /d %~dp0
echo ============================================
echo  ESP-IDF v5.5.4 - du an edge-ai da san sang
echo  Lenh build: idf.py build
echo  Lenh flash: idf.py -p COM3 flash
echo  Lenh xem log: idf.py -p COM3 monitor
echo ============================================
cmd /k
