cmake_minimum_required(VERSION 3.16.0)
# Khong dung git-describe cua ESP-IDF (build_info.h do scripts/gen_build_info.py sinh ra).
set(PROJECT_VER "1.0.0")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(energy-logger-xiao)
