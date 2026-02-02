#!/bin/bash
# Fix waifu2x-converter-cpp-cuda-git for CUDA 13+
# CUDA 13 minimum supported arch is sm_75 (Turing)

PKGBUILD="$HOME/.cache/yay/waifu2x-converter-cpp-cuda-git/PKGBUILD"

if [[ ! -f "$PKGBUILD" ]]; then
	echo "PKGBUILD not found. Run 'yay waifu2x-converter-cpp-cuda-git' first to download it."
	exit 1
fi

# Add sed commands to prepare() function to replace sm_52/ptx52 with sm_75/ptx75
if grep -q 's/sm_52/sm_75' "$PKGBUILD"; then
	echo "PKGBUILD already patched."
else
	sed -i '/^prepare() {$/a\
  # Fix for CUDA 13+ which requires sm_75+ (Turing)\
  sed -i "s/sm_52/sm_75/g" waifu2x-converter-cpp/CMakeLists.txt\
  sed -i "s/ptx52/ptx75/g" waifu2x-converter-cpp/CMakeLists.txt\
  sed -i "s/ptx52/ptx75/g" waifu2x-converter-cpp/src/modelHandler_CUDA.cpp' "$PKGBUILD"
	echo "PKGBUILD patched. Now run 'yay waifu2x-converter-cpp-cuda-git' again."
fi
