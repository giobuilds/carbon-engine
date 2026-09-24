# Vulkan backend for trinity on Linux: plan

Status: planning, 2026-09-24. Trinity currently builds on Linux with the stub backend only
(`giobuilds/trinity` `linux-port`, `linux-tools/trinity_smoke.sh`).

## Decisions

| Question | Decision | Why |
|---|---|---|
| What must it render? | Your own games and effects, validated first with the TrinityAL test shaders | EVE's effect sources (`res:/graphics/effect/**.fx`) are not in any public repo; only paths to them are. Running shipped EVE shaders would need CCP's sources or a DXBC→SPIR-V translator, and is out of scope. |
| Windowing | SDL3 as a platform layer only (our own Vulkan, no SDL renderer) | Only option with IME composition, rect cursor confinement, HiDPI cursors, monitors/pixel density on both X11 and Wayland; also fixes blue's clipboard and message-box stubs. In the vendored vcpkg (3.4.4, x11/wayland/ibus features), zlib licence. |
| Vulkan version | 1.3 core (dynamic rendering, synchronization2, descriptor indexing, timeline semaphores) | Dev machine: RX 6600 on RADV (Mesa 26.2), Vulkan 1.4. lavapipe (llvmpipe) is installed for GPU-less tests in the container. |
| Template backend | DX12 for structure, Metal for render passes and parallel encoding | See "Backend contract". |
| Shader compilation | Offline in `trinity/shadercompiler`, HLSL front end reused, DXC `-spirv` back end | Same effect container and metadata as DX/Metal, so the runtime loader does not change. |

## Background (from the codebase)

### Backend contract (`trinity/trinityal`)
- Platform selection is compile-time: `TRINITY_PLATFORM` plus a SYMBOL/SUFFIX/NAME block in
  `include/TrinityALForward.h`; generic headers pull the backend class through `TRINITY_AL_PLATFORM_INCLUDE`.
- Pimpl classes (backend implements `TrinityALImpl::X`, usually over `Tr2DeviceResourceAL<X>`): Buffer,
  ConstantBuffer, Texture, SamplerState, Shader, ShaderProgram, VertexLayout, ResourceSet, Fence, GpuTimer,
  OcclusionQuery, PipelineStatsQuery, SwapChain, and the four Rt* raytracing classes (optional,
  `TRINITY_PLATFORM_SUPPORTS_RAY_TRACING`).
- Whole class in the backend: `Tr2CapsAL` (+ all `TRINITY_PLATFORM_SUPPORTS_*` macros), `Tr2RenderContextAL`
  (+ `Tr2BindlessResourcesAL`), `Tr2PrimaryRenderContextAL`, `Tr2VideoAdapterInfo`, upscaling technique list.
- The render context API is duck-typed per backend; `stub/Tr2RenderContextStub.h` is the minimal list the engine
  calls (frame, state, draws, targets, debug markers, frame numbers, upscaling hooks).
- Sizes: DX12 19.5k lines, Metal 14.8k, stub 2.9k. Estimate for Vulkan: 12–15k with raytracing, 9–10k without.
- Binding input comes entirely from `Tr2ShaderSignatureAL` (pipeline inputs, `Tr2ShaderRegisterAL` with D3D
  register type/index/space/arrayCount, static samplers, thread-group size). DX12 builds its root signature from
  it in `dx12/Tr2ShaderProgramALDx12.cpp:222-282`.
- DX12 execution model to mirror: one direct queue, per-back-buffer fences and allocators, `Present()` waits on
  the next buffer's fence, `ReleaseLater` buckets per back buffer, batched barriers with `m_defaultState` and
  per-resource-set in/out transitions, 2 MB constant pages with a bump allocator, hashed PSO cache
  (`util/PsoDescription.h`).

### Shaders (`trinity/shadercompiler`, `trinity/trinity/Shader`)
- Runtime path: `Tr2Effect::ConvertEffectPath` maps `…/effect/x.fx` to `…/effect.<TRINITY_PLATFORM_NAME>/x.sm_{hi,lo,depth}`;
  `Tr2EffectRes` → `Tr2EffectDescription::Read` → `Tr2EffectStateManager::RegisterShader` → `Tr2ShaderAL::Create`.
- The container (`EffectData.h`) is identical on all platforms; only the bytecode blob differs (DXBC/DXIL, metallib).
- `ShaderCompiler.cpp` parses HLSL (re2c/lemon), permutes, and per platform either re-emits HLSL for fxc/dxc or
  translates to MSL (`EffectCompilerMetal`, which also derives reflection from its AST).
- HLSL features in use that matter for SPIR-V: register spaces and unbounded arrays, D3D cbuffer packing, column-major
  matrices (fxc `PACK_MATRIX_COLUMN_MAJOR`), separate textures/samplers, structured/byte-address/append buffers,
  `SamplerComparisonState`, `Texture2DMS`, `SV_Depth`/`SV_StencilRef`/`SV_SampleIndex`, DXR libraries. No wave
  intrinsics, no real `half` use.
- Metal uses the D3D clip space unchanged; Vulkan's Y axis is flipped.

### Window and presentation (`trinity/trinity/UI`)
- Platform files implement the `Tr2MainWindow` OS hooks; shared `SetState` drives `CreateOSWindow`,
  `PopulatePresentParameters`, `gTriDev->ChangeDevice(adapter, GetOutputWindow(), &pp)`.
- Python callbacks: `onMouseMove/Down/Up/Wheel` (back-buffer pixel coordinates, wheel in 120-per-notch units),
  `onKeyDown/Up(vk, flags)` with Win32 VK codes (`Scancodes.cpp` `SCANCODES`, exported as `triui`),
  `onChar`, `onFocusChange`, `onClose` (veto), and on macOS the IME pair `onSetMarkedTextIME_MacOS` /
  `onInsertTextIME_MacOS`.
- macOS drains its event queue in `Tr2MainWindow::OnTick` (registered with `BeOS->RegisterForTicks`); Linux follows that.
- Windows fullscreen is borderless (`USE_BORDERLESS_WINDOW`), which is also the only option on Wayland.

## Phases

Each phase ends in a pushed, tested state on the `linux-port` branches.

### Phase 0: Foundations
- `TRINITY_VULKAN` platform id, `TRINITY_PLATFORM_NAME "vulkan"`, `TrinityAL_vulkan` and `trinity_vulkan` targets on
  Linux; a `vulkan` vcpkg feature (vulkan-headers, volk, vulkan-memory-allocator, sdl3; spirv-reflect for the
  shader compiler).
- `TrinityALTest_vulkan` target and a Linux `RenderWindow`/window fixture for `trinityal/tests`; runs on RADV and on
  lavapipe (`VK_ICD_FILENAMES=…/lvp_icd.x86_64.json`) inside the container.
- Audit of the ~150 files outside `trinityal` that test `TRINITY_PLATFORM == TRINITY_DIRECTX12/METAL` or call
  `*Dx12(`/`GetMetalContext` (~312 call sites): classify each as "needs a Vulkan branch", "DX-only feature",
  or "fine". Output: a checklist in this document.

Done when: the empty backend compiles and links, the test target runs (tests skip), the audit list exists.

### Phase 1: Shader toolchain
- Build `shadercompiler` on Linux (CMake Linux branch, `shader-compiler` vcpkg feature for Linux with
  directx-dxc, re2c, lemon; guard the `_WIN32`/`CComPtr` parts of `EffectCompilerDX11` and the include handler).
- `PLATFORM_VULKAN` in `Platforms.h`; `EffectCompilerVulkan : EffectCompilerBase` reusing the DX11 AST passes
  (`PatchCBuffers`, texture-function conversion, `MergeSamplers`, `CreateGlobalsCB`/`AssignRegisters` with spaces,
  `OutputHLSL`), then DXC with `-spirv -fspv-target-env=vulkan1.3 -fvk-use-dx-layout -Zpc` and explicit binding
  shifts (or `[[vk::binding]]` emitted by `OutputHLSL`).
- Binding convention: descriptor set = register space; binding = per-type offset + register index. Constant
  buffers become uniform buffers; static samplers become immutable samplers.
- Reflection: a SPIRV-Reflect adapter beside `ReflectionDx11`/`FunctionDx12` in `DxReflection.h`, filling the same
  `StageInput`/`RegisterInputDescription`, so `Tr2EffectDescription::Read` is unchanged.
- `build.py`/`paths.py` learn the `vulkan` platform; output lands in `effect.vulkan/`.
- Compile `trinityal/tests/Shaders.DX12/*` to SPIR-V through the test CMake loop.

Done when: the test shaders and a sample `.fx` compile to `effect.vulkan/*.sm_hi` on Linux, and spirv-val passes.

### Phase 2: Core backend (offscreen)
- Instance/device (volk, debug utils, validation layers in Debug), VMA, one graphics+compute queue, per-frame
  command pools and fences, deferred release keyed by frame.
- Buffers, constant buffers (frame-local bump allocator), textures and subresources, samplers, upload/readback.
- Image layouts and synchronization2 barriers, modelled on DX12's default state + resource-set transitions.
- `Tr2ShaderProgramAL` builds a `VkPipelineLayout` from the signature; `Tr2ResourceSetAL` becomes one descriptor
  set per resource set; constants via dynamic uniform buffers.
- Pipeline cache keyed like `PSODescription` (render states, vertex layout, attachment formats), plus `VkPipelineCache`
  persisted to disk; D3D render-state enums translated in one place.
- Dynamic rendering driven by `RenderPassHint` (Metal's model), compute dispatch, UAVs, occlusion/timestamp queries.
- Caps: raytracing, parallel contexts, bindless textures, variable refresh and upscalers reported unsupported.

Done when: TrinityAL Buffer, ConstantBuffer, Texture, TextureSubresource, RenderTarget and Compute tests pass on RADV
and lavapipe with validation layers clean.

### Phase 3: Window and presentation (SDL3)
- `Tr2MainWindow_Linux.cpp` on SDL3: `SDL_WINDOW_VULKAN | SDL_WINDOW_HIGH_PIXEL_DENSITY`, events drained in
  `OnTick`/`ProcessMessages`, `Tr2WindowHandle` = `SDL_Window*`.
- Input: `SDL_Scancode` → Win32 VK table (like macOS `s_keyCodes`), layout-aware names, repeat flag, focus, close
  veto, mouse in back-buffer pixels (scaled like macOS), wheel in 120 units, `SDL_SetWindowMouseRect` for
  `ClipCursor`, color cursors in `Tr2MouseCursor`, window icon.
- Modes: windowed, fixed window, borderless fullscreen; resize and minimise with `SetThrottling`.
- Swapchain: surface from SDL, FIFO for `PRESENT_INTERVAL_ONE`, MAILBOX/IMMEDIATE otherwise, recreate on
  `OUT_OF_DATE`/`SUBOPTIMAL`, SDR B8G8R8A8 + sRGB views.
- `Tr2VideoAdapterInfo`: adapters from Vulkan, monitors and modes from SDL displays.
- Blue: clipboard and message box through SDL3 (decide between linking SDL in blue and a provider hook set by trinity).

Done when: a Python script opens a window, clears and presents at vsync, receives keyboard/mouse/focus/close events,
and survives resize, minimise and fullscreen toggles on X11 and Wayland.

### Phase 4: Engine integration
- Work through the phase 0 audit: Vulkan branches where the engine calls backend-specific paths.
- FSR1 upscaling shaders as SPIR-V (`Fsr1Vk.h`), branch in `src/upscaling/Tr2Fsr1Upscaling.cpp`.
- Render a scene (`EveSpaceScene` or a minimal scene) with your own compiled effects.
- Rendering tests with reference screenshots generated on RADV.

Done when: a scene renders in a window through the engine's normal render path, and the Rendering test group passes
with screenshot comparison.

### Later (optional)
- Parallel contexts via secondary command buffers (`TRINITY_PLATFORM_SUPPORTS_PARALLEL_CONTEXTS`, Metal's model).
- Bindless heap views via descriptor indexing.
- Raytracing via `VK_KHR_ray_tracing_pipeline` (DXR libraries from dxc `lib_6_3` to SPIR-V).
- FSR3 (has a Vulkan backend), variable refresh rate, HDR swapchains, IME composition callbacks for Linux.

## Risks and open questions
- **fxc → DXC**: DXC is stricter (implicit truncation, legacy `sampler`, uniform parameters); existing HLSL may
  need fixes in the front end or the sources.
- **Y flip**: negative viewport height vs `-fvk-invert-y`; both interact with `SV_Position`/`VPOS` and with sampling
  render targets.
- **Platform checks outside TrinityAL** can silently skip Vulkan; the phase 0 audit exists to catch them.
- **Descriptor model**: per-draw sets vs push descriptors vs descriptor buffers; start with per-resource-set sets and
  dynamic uniform buffers, measure later.
- **AppendStructuredBuffer counters** need separate buffers in Vulkan (Metal reports `BUFFER_COUNTERS 0`; do the same first).
- **Test coverage**: most Rendering tests only check `S_OK`; phase 4 adds reference images.
- **Upstream**: Fenris has an internal Linux effort (PR #31 closed 2026-09-23); keep the Vulkan work additive and
  platform-guarded so it can be rebased onto theirs.
