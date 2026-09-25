#!/usr/bin/env bash
# Runs linux-tools/trinity_window_demo.py (the Vulkan main window) in the build container on the host desktop
# (CARBON_DISPLAY=1, CARBON_GPU=1). SDL_VIDEO_DRIVER=x11 tries XWayland; DEMO_SECONDS limits the run.
set -euo pipefail
WS=/home/keeper/Workspace/CARBON_Engine
T=$WS/trinity/.cmake-build-x64-linux-debug-container
V=$T/vcpkg_installed/x64-linux-debug
EXEFILE=$WS/blue/.cmake-build-x64-linux-debug-container/vcpkg_installed/x64-linux-debug/tools/carbon-exefile/exefile_debug
S=$V/lib/python3.12
export CARBON_GPU=${CARBON_GPU:-1} CARBON_DISPLAY=${CARBON_DISPLAY:-1}
exec "$WS/linux-tools/incontainer.sh" linux-tools "PYTHONUNBUFFERED=1 LD_LIBRARY_PATH=$V/lib \
DEMO_SECONDS=${DEMO_SECONDS:-0} ${DEMO_CLIPBOARD:+DEMO_CLIPBOARD=1} ${SDL_VIDEO_DRIVER:+SDL_VIDEO_DRIVER=$SDL_VIDEO_DRIVER} ${CARBON_VULKAN_DEVICE:+CARBON_VULKAN_DEVICE=$CARBON_VULKAN_DEVICE} \
PYTHONPATH=$WS/linux-tools:$T/trinity/Linux/x64/GNU:$V/lib:$V/bin:$V/bin/python:$WS/blue/python:$S/lib-dynload:$S \
BUILDFLAVOR=debug $EXEFILE /inherit /buildflavor=debug /py -m trinity_window_demo"
