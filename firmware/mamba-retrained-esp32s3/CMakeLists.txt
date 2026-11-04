cmake_minimum_required(VERSION 3.16.0)
# Repo has no commits yet; skip ESP-IDF's git-describe step which hard-fails without a HEAD.
set(PROJECT_VER "1.0.0")
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(mamba-retrained-esp32s3)
