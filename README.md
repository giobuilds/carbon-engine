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
| `blueexposure` | carbon-blueexposure | ported, 1184/1184 |
| `exefile` | carbon-exefile (Python host executable) | ported, builds (no tests); Crashpad off |
| `pdm` | carbon-pdm (platform detection) | ported, 4/4 |
| `pdm-proto-wrapper` | carbon-pdmprotowrapper | ported, 4/4 |
| `blue` | carbon-blue (engine kernel) | ported, 389/389 |
| `destiny` | carbon-destiny (space physics) | ported, 73/73 C++ + 458/458 Python |
| `parser` | carbon-parser | ported, 52/52 |
| `imageio` | carbon-imageio | ported, 331/331 |
| `mesh` | carbon-mesh | ported, cmftest 28/28 |
| `trinity` | carbon-trinity (renderer) | stub backend builds; `linux-tools/trinity_smoke.sh` imports it in exefile, creates objects, a device and the headless window |
| `linux-overlay-ports/` | vcpkg overlay ports for the forks, greenlet over HTTPS, and openssl 1.1.1k with `openssl.pc` (curl needs it on Linux) | |
| `docs/` | `vulkan-backend-plan.md`: phased plan for a Vulkan backend (SDL3 windowing, DXC→SPIR-V shaders) | |
| `linux-tools/` | `incontainer.sh` (run anything in the build container), `Containerfile.plus` (build image), `setup_component.sh`, `add_linux_presets.py`, container preset template | |

## Building

Build inside the container: upstream's `carbonengine/linux-containers` gcc image tagged
`carbon-linux-gcc-buildenv:local`, extended by `linux-tools/Containerfile.plus` into `:local-plus`.
`linux-tools/incontainer.sh` runs a command in it with the right mounts and a desktop-like environment:

```
podman build -t carbon-linux-gcc-buildenv:local linux-containers/build/gcc
podman build -t carbon-linux-gcc-buildenv:local-plus -f linux-tools/Containerfile.plus linux-tools
cp linux-tools/CMakeUserPresets.linux.json <component>/CMakeUserPresets.json
linux-tools/incontainer.sh <component> \
  'cmake --preset x64-linux-debug-container && cmake --build .cmake-build-x64-linux-debug-container -j16'
linux-tools/incontainer.sh <component>/.cmake-build-x64-linux-debug-container 'ctest -j8 --output-on-failure'
```

The user preset adds `VCPKG_OVERLAY_PORTS=${sourceDir}/../linux-overlay-ports`, which is how
a component finds the Linux-enabled ports of the layers below it.
