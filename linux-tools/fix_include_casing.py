#!/usr/bin/env python3
"""Rewrite #include names whose casing differs from the real header in a set of
include directories (case-insensitive filesystems hide these; Linux does not).
Usage: fix_include_casing.py <include-dir>... -- <source-dir>..."""
import pathlib, re, sys
sep = sys.argv.index('--')
real = {}
for d in sys.argv[1:sep]:
    for p in pathlib.Path(d).rglob('*.h'): real.setdefault(p.name.lower(), p.name)
fixed = 0
for d in sys.argv[sep+1:]:
    for path in pathlib.Path(d).rglob('*'):
        if path.suffix not in ('.h', '.cpp', '.mm', '.c', '.inl') or 'vendor' in path.parts or any(p.startswith('.cmake-build') for p in path.parts): continue
        s = path.read_text(errors='replace')
        def sub(m):
            global fixed
            r = real.get(m.group(2).lower())
            if r and r != m.group(2):
                fixed += 1; print(f'{path}: {m.group(2)} -> {r}')
                return m.group(1) + r + m.group(3)
            return m.group(0)
        t = re.sub(r'(#include\s*[<"])([A-Za-z0-9_.]+\.h)([>"])', sub, s)
        if t != s: path.write_text(t)
print('fixed', fixed)
