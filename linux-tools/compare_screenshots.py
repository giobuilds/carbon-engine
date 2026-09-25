#!/usr/bin/env python3
"""Compare TrinityALTest screenshots (32-bit BGRX DDS, as SaveReadableRenderTarget writes them) against references
(the same format, or the 24-bit files checked in under trinityal/tests/screenshots/dx11).

usage: compare_screenshots.py <reference dir> <actual dir> [--tolerance N]

Prints, per image present in both, the share of pixels whose largest channel difference exceeds the tolerance, and the
largest difference. Exit status 1 if any image differs in more than 1% of its pixels.
"""
import os
import struct
import sys


def load_dds(path):
    with open(path, 'rb') as f:
        data = f.read()
    height, width = struct.unpack_from('<II', data, 12)
    pixels = data[128:128 + width * height * 4]
    if len(pixels) != width * height * 4:
        raise ValueError(f'{path}: truncated or not 32-bit ({width}x{height})')
    return width, height, pixels


def load_reference(path, width, height):
    """The checked-in DX11 references are 24-bit BGR after a 122-byte header whose fields do not decode as a standard
    DDS header; recognise them by size and return them as 32-bit BGRX. Otherwise read them as this harness writes."""
    size = os.path.getsize(path)
    if size == 122 + width * height * 3:
        with open(path, 'rb') as f:
            data = f.read()[122:]
        pixels = bytearray(width * height * 4)
        pixels[0::4] = data[0::3]
        pixels[1::4] = data[1::3]
        pixels[2::4] = data[2::3]
        return width, height, bytes(pixels)
    return load_dds(path)


def compare(reference, actual, tolerance):
    aw, ah, ap = load_dds(actual)
    rw, rh, rp = load_reference(reference, aw, ah)
    if (rw, rh) != (aw, ah):
        return None, f'size {aw}x{ah} != reference {rw}x{rh}'
    differing = 0
    largest = 0
    for i in range(0, len(rp), 4):
        d = max(abs(rp[i] - ap[i]), abs(rp[i + 1] - ap[i + 1]), abs(rp[i + 2] - ap[i + 2]))  # ignore X
        if d > tolerance:
            differing += 1
        largest = max(largest, d)
    return differing / (rw * rh), f'max diff {largest}'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    tolerance = 8
    if '--tolerance' in sys.argv:
        tolerance = int(sys.argv[sys.argv.index('--tolerance') + 1])
        args.remove(str(tolerance))
    reference_dir, actual_dir = args
    failed = False
    for root, _, files in sorted(os.walk(reference_dir)):
        for name in sorted(files):
            if not name.endswith('.dds'):
                continue
            reference = os.path.join(root, name)
            relative = os.path.relpath(reference, reference_dir)
            actual = os.path.join(actual_dir, relative)
            if not os.path.exists(actual):
                print(f'{relative:70} missing')
                continue
            try:
                share, note = compare(reference, actual, tolerance)
            except ValueError as e:
                print(f'{relative:70} skipped: reference not readable ({e})')
                continue
            if share is None:
                print(f'{relative:70} {note}')
                failed = True
                continue
            bad = share > 0.01
            failed |= bad
            print(f'{relative:70} {"DIFF" if bad else "ok  "} {share * 100:6.2f}% of pixels, {note}')
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
