#!/usr/bin/env bash
# Smoke-test the trinity stub build: import it next to blue inside exefile, create scene objects, a device and the
# headless main window, and set a window state. Trinity has no Linux test target yet; this is the end-to-end check.
# Usage: linux-tools/trinity_smoke.sh   (after building trinity's x64-linux-debug-container preset)
set -euo pipefail
WS=/home/keeper/Workspace/CARBON_Engine
T=$WS/trinity/.cmake-build-x64-linux-debug-container
V=$T/vcpkg_installed/x64-linux-debug
EXEFILE=$WS/blue/.cmake-build-x64-linux-debug-container/vcpkg_installed/x64-linux-debug/tools/carbon-exefile/exefile_debug
S=$V/lib/python3.12
# blue_debug/_carbonsocket live in lib, _scheduler and the scheduler package in bin and bin/python, bluepycore in
# blue/python: the same layout blue's own Python tests put on PYTHONPATH.
exec "$WS/linux-tools/incontainer.sh" linux-tools "PYTHONUNBUFFERED=1 LD_LIBRARY_PATH=$V/lib \
PYTHONPATH=$WS/linux-tools:$T/trinity/Linux/x64/GNU:$V/lib:$V/bin:$V/bin/python:$WS/blue/python:$S/lib-dynload:$S \
BUILDFLAVOR=debug $EXEFILE /inherit /buildflavor=debug /py -m trinity_smoke"
