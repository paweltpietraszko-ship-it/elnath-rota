"""Mechanical move proof: for each of the six moved declarations, extract
its full text (leading comment block + declaration through its closing
brace) from the base file and from the new module, and compare. The only
allowed difference is the `export ` keyword on ScheduleGrid/daysInMonth.
Usage: python manifest.py <base_sha>"""
import re, subprocess, sys

BASE = sys.argv[1]
OLD = subprocess.run(["git", "show", f"{BASE}:frontend/src/screens/MonthlyPlanning.tsx"], capture_output=True, text=True, check=True).stdout.split("\n")
NEW = open("frontend/src/screens/monthly-planning/ScheduleGrid.tsx", encoding="utf-8").read().split("\n")
PARENT = open("frontend/src/screens/MonthlyPlanning.tsx", encoding="utf-8").read().split("\n")
SYMBOLS = ["daysInMonth", "hourOf", "cellLabel", "assignmentHours", "totalHours", "ScheduleGrid"]

def block(lines, name):
    start = next(i for i, l in enumerate(lines) if re.match(rf"^(export )?function {name}\b", l))
    first = start
    while first > 0 and lines[first - 1].startswith("//"):
        first -= 1
    end = next(i for i in range(start, len(lines)) if lines[i] == "}")
    return first + 1, end + 1, lines[first:end + 1]

ok = True
print(f"BASE {BASE} frontend/src/screens/MonthlyPlanning.tsx  ->  frontend/src/screens/monthly-planning/ScheduleGrid.tsx")
for name in SYMBOLS:
    o1, o2, ob = block(OLD, name)
    n1, n2, nb = block(NEW, name)
    nb_cmp = [re.sub(rf"^export (function {name}\b)", r"\1", l) for l in nb]
    same = ob == nb_cmp
    exported = nb[[i for i, l in enumerate(nb) if "function " + name in l][0]].startswith("export ")
    ok &= same
    print(f"{name:16s} old L{o1}-{o2} ({len(ob)} lines)  new L{n1}-{n2} ({len(nb)} lines)  exported={exported}  body={'IDENTICAL' if same else 'DIFFERENT'}")
    still = [i + 1 for i, l in enumerate(PARENT) if re.match(rf"^(export )?function {name}\b", l)]
    if still:
        ok = False; print(f"   !! still declared in parent at {still}")
order_old = [block(OLD, n)[0] for n in SYMBOLS]
order_new = [block(NEW, n)[0] for n in SYMBOLS]
print("relative order preserved:", order_old == sorted(order_old) and order_new == sorted(order_new))
ok &= order_new == sorted(order_new)
print("RESULT:", "ALL SIX IDENTICAL (only `export` added on ScheduleGrid, daysInMonth)" if ok else "MISMATCH")
sys.exit(0 if ok else 1)
