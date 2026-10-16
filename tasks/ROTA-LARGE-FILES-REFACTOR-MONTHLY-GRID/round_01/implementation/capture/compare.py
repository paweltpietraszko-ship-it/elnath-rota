"""Diff two capture runs (default: base vs after). Grid DOM dumps must be
identical; screenshots compared byte-for-byte (sha256), then -- only if
bytes differ -- pixel-wise via Playwright-independent PNG decode (zlib)."""
import hashlib, json, struct, sys, zlib
from pathlib import Path

HERE = Path(__file__).parent
a_label, b_label = (sys.argv[1:3] + ["base", "after"])[:2] if len(sys.argv) > 1 else ("base", "after")
A, B = HERE / a_label, HERE / b_label

def png_pixels(p: Path):
    data = p.read_bytes(); pos = 8; idat = b""; w = h = 0
    while pos < len(data):
        n, typ = struct.unpack(">I4s", data[pos:pos + 8]); chunk = data[pos + 8:pos + 8 + n]; pos += 12 + n
        if typ == b"IHDR": w, h = struct.unpack(">II", chunk[:8])
        elif typ == b"IDAT": idat += chunk
    return w, h, zlib.decompress(idat)  # raw filtered scanlines: equal iff same encoder input

ca, cb = json.loads((A / "capture.json").read_text()), json.loads((B / "capture.json").read_text())
problems = []
for key in sorted(set(ca["steps"]) | set(cb["steps"])):
    va, vb = ca["steps"].get(key), cb["steps"].get(key)
    if isinstance(va, dict) and "grids" in va:
        va = {k: v for k, v in va.items() if k != "content_text_head"}
        vb = {k: v for k, v in (vb or {}).items() if k != "content_text_head"}
    print(f"{key:28s} {'IDENTICAL' if va == vb else 'DIFFERENT'}")
    if va != vb: problems.append(key)
print(f"{'writes':28s} {a_label}={ca['writes']} {b_label}={cb['writes']}")
if ca["writes"] or cb["writes"]: problems.append("writes")
shots = sorted({p.name for p in A.glob('*.png')} | {p.name for p in B.glob('*.png')})
for name in shots:
    pa, pb = A / name, B / name
    if not (pa.exists() and pb.exists()):
        print(f"{name:40s} MISSING"); problems.append(name); continue
    ha, hb = hashlib.sha256(pa.read_bytes()).hexdigest(), hashlib.sha256(pb.read_bytes()).hexdigest()
    verdict = "BYTE-IDENTICAL" if ha == hb else ("PIXEL-IDENTICAL" if png_pixels(pa) == png_pixels(pb) else "PIXEL-DIFFERENT")
    print(f"{name:40s} {verdict} sha256={ha[:12]}")
    if verdict == "PIXEL-DIFFERENT": problems.append(name)
print("RESULT:", "NO DIFFERENCES" if not problems else f"DIFFERENCES: {problems}")
sys.exit(1 if problems else 0)
