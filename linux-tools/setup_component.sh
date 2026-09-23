#!/usr/bin/env bash
# Prepare a Carbon component checkout for the Linux port:
#   branch linux-port, vcpkg submodules (registry at the fixed commit), baseline bump,
#   vcpkg bootstrap, shared downloads dir, Linux presets, container user preset.
set -euo pipefail
comp=$1
WS=/home/keeper/Workspace/CARBON_Engine
REGISTRY_FIX=7268e6d65def7609bcd99f25d287b04a2a08f881
REGISTRY_BASELINE=f0325d62b39d94fcd91216ba8eb6786ce2c00364
cd "$WS/$comp"
git rev-parse --verify -q linux-port >/dev/null || git checkout -q -b linux-port
git checkout -q linux-port
git submodule update --init --depth 1 vendor/github.com/microsoft/vcpkg >/dev/null 2>&1
git submodule update --init vendor/github.com/carbonengine/vcpkg-registry >/dev/null 2>&1
git -C vendor/github.com/carbonengine/vcpkg-registry fetch -q "$WS/vcpkg-registry" linux-port
git -C vendor/github.com/carbonengine/vcpkg-registry checkout -q $REGISTRY_FIX
sed -i 's#url = https://github.com/carbonengine/vcpkg-registry#url = https://github.com/giobuilds/vcpkg-registry#' .gitmodules
python3 - "$REGISTRY_BASELINE" <<'PY'
import json,sys
p='vcpkg-configuration.json'; d=json.load(open(p))
for r in d['registries']:
    if 'carbonengine/vcpkg-registry' in r['repository']:
        r['baseline']=sys.argv[1]
        r['repository']='https://github.com/carbonengine/vcpkg-registry.git'  # SSH URLs cannot be fetched inside the build container
json.dump(d,open(p,'w'),indent=2); open(p,'a').write('\n')
PY
V=vendor/github.com/microsoft/vcpkg
(cd $V && ./bootstrap-vcpkg.sh -disableMetrics >/dev/null 2>&1)
if [ ! -L $V/downloads ]; then rm -rf $V/downloads; ln -s "$WS/core/vendor/github.com/microsoft/vcpkg/downloads" $V/downloads; fi
python3 "$WS/linux-tools/add_linux_presets.py" CMakePresets.json
cp "$WS/linux-tools/CMakeUserPresets.linux.json" CMakeUserPresets.json
git submodule status
cmake --list-presets
