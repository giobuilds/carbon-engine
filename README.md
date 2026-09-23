# carbon-engine (Linux port superproject)

Workspace that ports [Fenris Creations' Carbon engine](https://github.com/carbonengine)
to Linux, one component at a time. Each ported component is a submodule pointing at the
`linux-port` branch of a fork under `giobuilds`; unported components are plain clones
that this repo ignores.

| Path | What | Status |
|---|---|---|
| `vcpkg-registry` | fork of the CCP registry with Linux toolchain fixes | needed by everything |
| `core` | carbon-core | ported, 193/193 tests |
| `scheduler` | carbon-scheduler | ported, 247/247 |
| `io` | carbon-io | ported, 937/937 |
| `math` | carbon-math | ported, 90/90 |
| `blueexposure` | carbon-blueexposure | in progress |
| `linux-overlay-ports/` | vcpkg overlay ports for the forks (and greenlet over HTTPS) | |
| `linux-tools/` | `setup_component.sh`, `add_linux_presets.py`, container preset template | |

## Building

Build inside the container from `carbonengine/linux-containers` (gcc image) plus `libtool`;
see `CLAUDE.md` for the exact `podman run` line and the Fedora host caveats. Inside a
component:

```
cp ../linux-tools/CMakeUserPresets.linux.json CMakeUserPresets.json
cmake --preset x64-linux-debug-container
cmake --build .cmake-build-x64-linux-debug-container -j16
(cd .cmake-build-x64-linux-debug-container && ctest -C Debug)
```

The user preset adds `VCPKG_OVERLAY_PORTS=${sourceDir}/../linux-overlay-ports`, which is how
a component finds the Linux-enabled ports of the layers below it.
