#!/usr/bin/env bash
# Run a command inside the workspace build container, from a component directory.
#
#   linux-tools/incontainer.sh blue 'cmake --preset x64-linux-debug-container && cmake --build .cmake-build-x64-linux-debug-container -j16'
#   linux-tools/incontainer.sh blue/.cmake-build-x64-linux-debug-container 'ctest -j8 --output-on-failure'
#
# The container looks like a desktop session to the tests:
# - --userns=keep-id runs as the host user, so build outputs stay owned by us
# - label=disable: SELinux otherwise denies the bind mounts on Fedora
# - $HOME is a writable tmpfs (keep-id alone leaves it root-owned); the workspace and the vcpkg binary
#   cache are bind-mounted inside it at their host paths, so absolute paths in build trees stay valid
# - /etc/machine-id comes from the host (the image ships an empty one)
# - CARBON_GPU=1 passes the host GPU (/dev/dri) through for Vulkan on RADV; without it only lavapipe is available
# - CARBON_DISPLAY=1 lets windows open on the host desktop: only the Wayland socket goes into a private runtime
#   directory, plus the X11 socket and XWayland's auth file for SDL's x11 driver (SDL_VIDEO_DRIVER=x11)
set -euo pipefail
WS=/home/keeper/Workspace/CARBON_Engine
IMAGE=${CARBON_BUILD_IMAGE:-carbon-linux-gcc-buildenv:local-plus}
dir=$1; shift
gpu=()
if [ "${CARBON_GPU:-0}" = 1 ]; then gpu=(--device /dev/dri --group-add keep-groups); fi
display=()
if [ "${CARBON_DISPLAY:-0}" = 1 ]; then
    if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -S "${XDG_RUNTIME_DIR:-}/$WAYLAND_DISPLAY" ]; then
        display+=(--mount type=tmpfs,destination=/tmp/xdg,chown=true,tmpfs-mode=0700
                  -v "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY:/tmp/xdg/$WAYLAND_DISPLAY"
                  -e XDG_RUNTIME_DIR=/tmp/xdg -e WAYLAND_DISPLAY="$WAYLAND_DISPLAY")
    fi
    if [ -n "${DISPLAY:-}" ] && [ -d /tmp/.X11-unix ]; then
        display+=(-v /tmp/.X11-unix:/tmp/.X11-unix:ro -e DISPLAY="$DISPLAY")
        if [ -n "${XAUTHORITY:-}" ] && [ -f "$XAUTHORITY" ]; then
            display+=(-v "$XAUTHORITY:/tmp/xauthority:ro" -e XAUTHORITY=/tmp/xauthority)
        fi
    fi
fi
exec podman run --rm --userns=keep-id --security-opt label=disable "${gpu[@]}" "${display[@]}" \
    -e HOME=/home/keeper \
    --mount type=tmpfs,destination=/home/keeper,chown=true \
    -v /etc/machine-id:/etc/machine-id:ro \
    -v "$WS:$WS" \
    -v /home/keeper/.cache/vcpkg:/home/keeper/.cache/vcpkg \
    -w "$WS/$dir" "$IMAGE" \
    bash -c "$*"
