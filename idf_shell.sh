#!/bin/bash
# Source file nay de kich hoat moi truong ESP-IDF cho du an edge-ai
# Cach dung: source idf_shell.sh && idf.py build
unset MSYSTEM MSYSTEM_CARCH MSYSTEM_CHOST MSYSTEM_PREFIX MSYSTEM_MOUNTPOINT
export IDF_PATH="C:/Espressif/frameworks/esp-idf-v5.5.4"
export IDF_PYTHON_ENV_PATH="C:/Espressif/python_env/idf5.5_py3.11_env"
export IDF_TOOLS_PATH="C:/Espressif"
export PATH="/c/Espressif/python_env/idf5.5_py3.11_env/Scripts:/c/Espressif/tools/xtensa-esp-elf/esp-14.2.0_20260121/xtensa-esp-elf/bin:/c/Espressif/tools/cmake/3.30.2/bin:/c/Espressif/tools/ninja/1.12.1:/c/Espressif/tools/ccache/4.12.1/ccache-4.12.1-windows-x86_64:/c/Espressif/tools/dfu-util/0.11/dfu-util-0.11-win64:/c/Espressif/tools/idf-git/2.44.0/cmd:/c/Espressif/tools/idf-python/3.11.2:$PATH"
cd "$(dirname "${BASH_SOURCE[0]}")"
echo "ESP-IDF v5.5.4 da kich hoat - du an edge-ai"
