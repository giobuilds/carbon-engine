# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this directory is

This is not a single repository. It is a workspace holding independent git clones of every public repo in
`github.com/carbonengine` (Fenris Creations' open-sourced Carbon engine, the EVE Online engine). The six
below are the spine; the rest are listed further down.
Each subdirectory has its own `.git`, `main` branch, `CMakeLists.txt`, `CMakePresets.json`, `vcpkg.json`
and CI config. There is no top-level build. Always `cd` into the component you are changing, and run
git commands from inside it.

Dependency order of the spine (each depends on the ones before it, via vcpkg packages named `carbon-<name>`):

| Dir         | vcpkg name         | CMake target(s)              | What it is |
|-------------|--------------------|------------------------------|------------|
| `core`      | `carbon-core`      | `CcpCore` (shared lib)       | Cross-platform OS abstractions: memory tracking, threads, mutex, logging, callstack, telemetry (Tracy). Everything else links it. |
| `scheduler` | `carbon-scheduler` | `Scheduler` -> `_scheduler` Python ext | Tasklets and channels on top of greenlet, mimicking Stackless Python semantics. |
| `io`        | `carbon-io`        | `_socket`/`_ssl`/`_select` -> `_carbonsocket`, `_carbonssl`, `carbonselect` | CPython's socket/ssl/select modules patched so blocking calls yield to the scheduler (via libuv). |
| `blue`      | `carbon-blue`      | `Blue` -> `blue` (`.pyd`)    | The engine kernel: embedded Python interpreter, game loop (`blue.os.Pump()`), resource manager, persistence (Black/Yaml/Dict readers and writers). |
| `destiny`   | `carbon-destiny`   | `destiny` -> `_destiny` module, `destinyStatic` | Space physics/world simulation: `Ballpark`, `Ball`, collision, partitioning. |
| `trinity`   | `carbon-trinity`   | subprojects `trinityal`, `trinity`, `shadercompiler` | Renderer. `trinityal` is the graphics abstraction layer (dx11/dx12/metal backends); `trinity` is the scene graph, particles, curves, EVE space objects; `shadercompiler` is an HLSL parser (re2c + lemon). |

Several `carbon-*` dependencies are **not** in this workspace but are public repos in the same GitHub
organization (37 repos total, all public, listed in `carbonengine/documentation/components.md`):
`blueexposure` (the `EXPOSURE_BEGIN`/`MAP_ATTRIBUTE` reflection macros), `math`, `pdm-proto-wrapper`,
`exefile` (the Python host executable used to run tests), `imageio`, `mesh`, `parser`, `trinityaudioapi`,
plus `audio`, `fsd`, `geo2`, `resources`, `localization` and others. The vcpkg ports for all of them live in the
public `carbonengine/vcpkg-registry`. To read one of their headers, fetch it with `gh api` or clone the repo
into this workspace next to the others.

CCP Games rebranded to Fenris Creations in May 2026; older files still say CCP ehf. and both names are correct.

## Building and testing

**Supported platforms are Windows (MSVC) and macOS.** The presets in these six repos are conditioned on
`hostSystemName` being Windows or Darwin, and several `CMakeLists.txt` files `FATAL_ERROR` on other
platforms. Linux support is in progress upstream: `vcpkg-registry` gained `x64-linux-*` and `arm64-linux-*`
triplets and toolchains on 2026-09-10, and `carbon-engine/linux-containers` provides Ubuntu gcc/clang build
containers, but no component repo has a Linux preset yet and the `carbon-core`/`carbon-scheduler` ports still
declare Windows and macOS only. This workspace is on Fedora Linux, so nothing here configures or builds as-is.
Verify changes by reading code carefully; do not claim a build or test run succeeded.

The vcpkg submodules (`vendor/github.com/microsoft/vcpkg` and `vendor/github.com/carbonengine/vcpkg-registry`)
are checked out only in the components ported so far (core, scheduler, io). Any other build needs:

```
git submodule update --init --recursive
```

Standard workflow on a supported host, run from inside one component:

```
cmake --list-presets
cmake --preset x64-windows-v145-debug          # or arm64-osx-debug, x64-windows-release, ...
cmake --build .cmake-build-x64-windows-v145-debug --config Debug
cd .cmake-build-x64-windows-v145-debug && ctest -C Debug --output-on-failure
ctest -C Debug -R <TestName>                   # single test
```

Preset naming is `<arch>-<os>[-v145]-<flavor>`. The build directory is always
`.cmake-build-<preset-name>` next to the source. Trinity's presets drop the `v145` segment but still use
the v145 (VS 2022 14.5x) toolchain; older Windows presets in other components use the v141 toolchain.
Trinity on Windows also needs `-A x64 -T <toolset>` on the configure line and the generated `.slnx`
opened directly. Its README still shows `-T v141`, but the presets now select `x64-windows-145-*` triplets
(commit "Switch to using v145 as the default compiler"), so match `-T` to the triplet's toolset.

### Linux build (local port, in progress)

`core` has been ported and passes its full test suite on Linux (193/193, GCC 15 in the container and
natively on Fedora). The working pattern, which the other components should copy:

- `x64-linux-{debug,internal,release,trinitydev}` presets in `CMakePresets.json`, chainloading
  `vendor/github.com/carbonengine/vcpkg-registry/toolchains/x64-linux-carbon.cmake`.
- The vcpkg-registry submodule and the `baseline` in `vcpkg-configuration.json` moved to `f0325d62` or later.
- Build inside the Podman image `carbon-linux-gcc-buildenv:local-plus`: upstream's `linux-containers` gcc image
  (tagged `:local`) plus `linux-tools/Containerfile.plus` (libtool and friends, which Fedora's native vcpkg path also
  lacks, plus `fr_FR`/`en_US` locales, fonts and gdb for blue's tests). Always run it through
  `linux-tools/incontainer.sh <dir> '<command>'`, which adds keep-id, `label=disable`, a writable tmpfs `$HOME`,
  the host's `/etc/machine-id` and the workspace/vcpkg-cache mounts at their host paths:

```
linux-tools/incontainer.sh <component> \
  'cmake --preset x64-linux-debug-container && cmake --build .cmake-build-x64-linux-debug-container -j16'
linux-tools/incontainer.sh <component>/.cmake-build-x64-linux-debug-container 'ctest -j8 --output-on-failure'
```

- `CARBON_GPU=1 linux-tools/incontainer.sh …` passes the host GPU (`/dev/dri`, RADV) into the container; without it
  Vulkan sees only lavapipe. Trinity's Vulkan skeleton builds with `BUILD_VULKAN=ON` (set in trinity's container
  user preset); `linux-tools/trinity_smoke.sh vulkan` loads it.
- Run core's `ctest` serially. The telemetry tests bind a Tracy port and fail under `-j`.
- `scheduler` (247/247), `io` (936/937, one skipped by design), `math` (90/90), `blueexposure` (154/154),
  `exefile` (builds; no tests), `pdm` (4/4), `pdm-proto-wrapper` (4/4), `blue` (389/389), `destiny` (73/73 C++, 458/458
  Python), `parser` (52/52), `imageio` (331/331), `mesh` (28/28) and `trinity` (stub backend; no test target,
  `linux-tools/trinity_smoke.sh` is the end-to-end check) are also ported. `trinityaudioapi` is header-only and
  needs only an HTTPS overlay port. Blue's Python tests run through exefile and need the environment `incontainer.sh` provides (writable
  `$HOME`, machine-id, fonts, `fr_FR` locale). Ported components live on
  a `linux-port` branch in each repo; overlay ports must be added for each so the next layer can consume it.
- **Overlay ports** in `linux-overlay-ports/` (workspace root, not a git repo) replace registry ports that
  exclude Linux or fetch over SSH: `carbon-core` builds from the local core commit named in its portfile
  (update the `REF` whenever core's branch moves), `greenlet` uses HTTPS and adds Linux install/config
  branches, `openssl` is the pinned 1.1.1k port plus an installed `openssl.pc` (curl only uses OpenSSL on Linux
  and asks pkg-config for it). Container presets pass the directory as `VCPKG_OVERLAY_PORTS`.
- The vendored `vcpkg-registry` submodules point at the local `vcpkg-registry` clone's `linux-port` branch,
  which fixes an upstream bug: the Linux `*-triplet.cmake` files include the carbon toolchain by bare name.
- `linux-tools/setup_component.sh <dir>` does the whole component setup (branch, submodules, baseline, presets,
  container user preset); `fix_include_casing.py` fixes `CCPLog.h`-style include casing against core's headers.
- LP64 gotcha: on Linux `long` is `int64_t` and `unsigned long`/`size_t` are `uint64_t`. Code that adds extra
  `long`/`size_t` overloads for macOS (`#else` after `#ifdef _MSC_VER`) must become `#elif defined(__APPLE__)`.
- DirectXMath's portable `sal.h` (pulled in by carbon-math) defines Microsoft's legacy lowercase SAL macros
  (`__valid`, `__success`, ...) that libstdc++ uses as identifiers; carbon-math's `Requirements.h` `#undef`s them
  via `SalLegacyUndef.h` under libstdc++. Symptom: errors deep in `bits/parse_numbers.h` or other std headers.
- `carbon-exefile-interpreter` (how destiny and later components run Python tests through exefile) has an overlay
  port adding the Linux branch and the lower-case flavor postfix (`exefile_debug`).
- The Vulkan backend plan (decisions, phases, done criteria) is `docs/vulkan-backend-plan.md`; update it as phases land.
- Trinity's shader compiler builds on Linux (`BUILD_SHADER_COMPILER=ON`); `ShaderCompiler /define PLATFORM 14 in.fx out`
  (absolute paths) compiles an effect to SPIR-V via `EffectCompilerVulkan`. Its tests need `spirv-tools` (in the image).
- Trinity on Linux builds only the stub platform (`TrinityAL_stub`, `_trinity_stub<flavor>.so`) with a headless
  `Tr2MainWindow_Linux.cpp`; there is no GPU backend or display-server (X11/Wayland) code yet. Importing it needs the
  same PYTHONPATH layout as blue's tests plus `bin` and `bin/python` (scheduler), and `import blue_debug` before
  `import blue` in debug builds (see `linux-tools/trinity_smoke.sh`).
- The Linux toolchains in the registry fork mirror the macOS warning exclusions (`-Wno-reorder`, unused
  variables/functions, unknown pragmas, missing braces) and silence GCC-only `-Wall` extras (sign-compare,
  class-memaccess, cast-user-defined, unused-but-set-variable); trinity builds with warnings as errors.
- This machine's btrfs `/home` has had all space allocated to data chunks; metadata then runs out ("No space left on
  device" with 100+ GB free). Container presets pass `--clean-after-build` to vcpkg to keep file counts down; the
  fix is `sudo btrfs balance start -dusage=20 /home`.
- Expect include-casing errors (`CCPLog.h` vs `CcpLog.h`) in components not yet touched by upstream's
  "case-sensitive systems" PRs; match core's on-disk names.

### Build flavors

`cmake/CcpBuildConfigurations.cmake` replaces CMake's default configurations with exactly four:
`Debug`, `TrinityDev`, `Internal`, `Release`. `Internal` is Release plus asserts; `TrinityDev` is Internal
with optimizations off for renderer work. Non-Release targets get a `_debug`/`_internal`/`_trinitydev`
filename postfix and `CCP_BUILD_FLAVOR` compile define; `CCP_ASSERT_ENABLED` is on for everything except
Release. Tests receive the flavor as `BUILDFLAVOR=<lowercase config>` in their environment.

### Test layout

- **C++ tests** are GoogleTest executables registered with `gtest_discover_tests(... DISCOVERY_MODE PRE_TEST)`.
  Discovery is deliberately deferred to test time because POST_BUILD steps copy runtime DLLs next to the
  executable. Targets: `CcpCoreTest`, `SchedulerCapiTest`, `SocketCppUnitTests`, `BlueCppUnitTests`,
  `DestinyTest`, plus `trinityal/tests`.
- **Python tests** are discovered at *configure* time by a `discover.py` that stubs the not-yet-built C
  extension into `sys.modules`, then each test id becomes one ctest entry. `scheduler` and `io` run them with
  the plain `python -m unittest`; `blue` and `destiny` must run them through the external `exefile`
  interpreter (`exefile /inherit /buildflavor=<flavor> /py -m ...`) because it hosts the embedded `blue` runtime.
  Test packages: `scheduler/tests/python/scheduler/tests`, `io/tests/python/carboniotests`,
  `blue/tests/python/bluetests`, `destiny/python/destiny/test`.
- `BUILD_TESTING` defaults to ON and only applies when the component is the top-level project.

### Options that change what gets built

- `INSTALL_TO_MONOLITH=ON` switches every component from the vcpkg install layout to the Perforce
  "monolith" layout (`bin/<platform>/<arch>/<toolset>/`) and generates a `<Name>Config.cmake` for it. CI uses it;
  local dev normally does not.
- `BUILD_DOCUMENTATION` defaults ON only when `TEAMCITY_VERSION` is set; it drives Doxygen + Sphinx via
  `cmake/CcpDocsGenerator.cmake`.
- `core`: `WITH_TELEMETRY` (Tracy) and `WITH_MEMORY_TRACKING`, both ON. `CcpTelemetry.cpp` is compiled with
  `NDEBUG` on purpose to match Tracy's struct layout; do not remove that.
- `blue`: `PY27_COMPATIBILITY_MODE` (legacy, OFF).
- `trinity`: `BUILD_DX11`, `BUILD_DX12`, `BUILD_METAL`, `BUILD_SHADER_COMPILER`, `WITH_GRANNY`, all OFF, each
  of which appends a vcpkg manifest feature. A plain configure produces no renderer backend. `BUILD_FOR_PYTHON_2`
  is a legacy in-Perforce mode that needs `CCP_EVE_PERFORCE_BRANCH_PATH`; ignore it for new work.

## Code conventions that are not obvious from one file

- **`Foo_Blue.cpp` files** hold the Python/reflection exposure for `Foo`: an `ExposeToBlue()` method using
  `EXPOSURE_BEGIN`/`EXPOSURE_END`, `MAP_INTERFACE`, `MAP_ATTRIBUTE`, `MAP_PROPERTY`, `MAP_METHOD_AND_WRAP`, with
  flags like `Be::READWRITE | Be::NOTIFY | Be::PERSIST`. Adding a field that Python or persistence must see means
  editing both `Foo.cpp/.h` and `Foo_Blue.cpp`. Every exposed class also needs one `BLUE_DEFINE(Foo)` /
  `BLUE_DEFINE_INTERFACE(IFoo)`: destiny collects these in `destiny/src/destiny.cpp`; blue and trinity put them
  in the class's own `_Blue.cpp` or in `blue/src/blue.cpp` / `trinity/trinity/trinity.cpp`.
- **Python module init symbols carry the build flavor**: `PyInit_blue_debug`, `PyInit_trinity_internal`, etc.,
  built with `CCP_CONCATENATE(PyInit_<name>, CCP_BUILD_FLAVOR)`. That is why the `.pyd`/`.so` filenames carry the
  same postfix and why Python tests need `BUILDFLAVOR` set to import the right one.
- **Naming prefixes**: `Ccp*` = core, `Blue*`/`IBlue*` = blue, `Tr2*`/`ITr2*`/`Tri*` = trinity, `*AL` = trinityal
  abstraction-layer types, `Eve*` = EVE-specific objects inside trinity/destiny.
- **Every source file uses a precompiled `StdAfx.h`** (`stdafx.h` in destiny/trinity) as its first include.
- **`cmake/` is a vendored copy** of the same helper set in each component (`CcpBuildConfigurations`,
  `CcpTargetConfigurations`, `CcpPackageConfigHelpers`, `CcpDocsGenerator`, `PyTestDiscoverTests`). The copies have
  drifted; fix the copy in the component you are working on, do not assume they are identical.
- `io/src` is patched CPython 3.12 source. `io/patches/README.md` maps each file back to cpython and asks that
  you regenerate the corresponding `.patch` whenever you change one of those files. `socketmodule.cpp` was
  converted from C to C++, so upstream diffs do not apply cleanly.
- `scheduler/README.md`: when changing the Python or C API surface, update docstrings and the C++ doc blocks,
  since Sphinx/Doxygen output is generated from them.
- Formatting is `.clang-format` per component (4-space indent, tabs for continuation, pointer-left,
  `ColumnLimit` 120, except trinity uses 0). Trinity enforces this on PRs with `cpp-linter` and has a
  `.clang-tidy` config with `CCP_ASSERT` registered as an assert macro.

## CI

Each component carries a `.teamcity/` Kotlin DSL project (Windows and macOS matrices across the four flavors,
plus a "Publish to Perforce" deployment). The CI recipe is exactly: `cmake --preset <p> -DINSTALL_TO_MONOLITH=ON`,
`cmake --build --config <flavor>`, `ctest -C <flavor> --output-on-failure`, `cmake --install`. GitHub Actions
are minimal (trinity: clang-format check; io: dependabot for vcpkg).

## Contributing

All six use the standard GitHub PR model against `main`. `core`, `scheduler`, `blue`, `destiny`, `trinity` are MIT;
`io` is PSF-2.0 because it derives from CPython. Copyright headers are `// Copyright © <year> CCP ehf.`
