#!/usr/bin/env python3
"""Insert x64-linux presets into a Carbon component's CMakePresets.json.

Mirrors the Windows/macOS structure: hidden `linux` (host condition) and
`x64-linux` (chainloads the registry's x64-linux-carbon toolchain), then one
concrete preset per build flavor. Also ensures the `common` preset exports
PATH_TO_VCPKG_ROOT, which the registry's *-triplet.cmake files require when a
carbon-* port is built as a dependency. Idempotent.
"""
import json, sys

FLAVORS = ["internal", "release", "debug", "trinitydev"]
TOOLCHAIN = "${sourceDir}/vendor/github.com/carbonengine/vcpkg-registry/toolchains/x64-linux-carbon.cmake"

def main(path):
    d = json.load(open(path))
    presets = d["configurePresets"]
    names = {p["name"] for p in presets}
    if "x64-linux" in names:
        print(f"{path}: already has x64-linux presets"); return
    for p in presets:
        if p["name"] == "common":
            p.setdefault("environment", {}).setdefault("PATH_TO_VCPKG_ROOT", "${sourceDir}/vendor/github.com/microsoft/vcpkg")
    def idx(name): return next(i for i, p in enumerate(presets) if p["name"] == name)
    presets.insert(idx("osx") + 1, {
        "name": "linux", "inherits": "common",
        "condition": {"type": "equals", "lhs": "${hostSystemName}", "rhs": "Linux"},
        "hidden": True})
    anchor = "x64-osx" if "x64-osx" in names else "arm64-osx"
    presets.insert(idx(anchor) + 1, {
        "name": "x64-linux", "inherits": "linux",
        "cacheVariables": {"VCPKG_CHAINLOAD_TOOLCHAIN_FILE": TOOLCHAIN},
        "hidden": True})
    for f in FLAVORS:
        presets.append({
            "name": f"x64-linux-{f}", "inherits": "x64-linux",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": f.capitalize() if f != "trinitydev" else "TrinityDev",
                "VCPKG_TARGET_TRIPLET": f"x64-linux-{f}",
                "VCPKG_HOST_TRIPLET": f"x64-linux-{f}"}})
    json.dump(d, open(path, "w"), indent=2); open(path, "a").write("\n")
    print(f"{path}: added linux presets")

if __name__ == "__main__":
    for p in sys.argv[1:]: main(p)
