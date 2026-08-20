"""ROTA-T020 CHECKPOINT A -- printable schedule PDF prototype renderer.

Pipeline/prototype script only, scoped by tasks/ROTA-T020/brief.md
Section 4/16. Produces two static demonstration PDFs on controlled
fictional data:

    schedule_12h.pdf  -- Site running the base 12h regime
    schedule_24h.pdf  -- Site running the base 24h regime

This script imports nothing from ``rota.*``, opens no database, and is
not wired into any production code path. It exists solely to give the
owner two real, openable, printable PDFs to accept or reject before
ROTA-T020 Checkpoint B (real Rota-data integration) may start.

Run:
    pip install -r requirements.txt
    python render_samples.py
"""
from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT_DIR = Path(__file__).parent
PAGE_W, PAGE_H = landscape(A3)
MARGIN = 24.0

# Built-in Helvetica has no Polish diacritics (a Windows-1252 base font
# cannot render "a with ogonek", "l with stroke", etc.). Embed a real
# Unicode TTF instead -- Arial ships with Windows and covers Polish.
# Prototype-only choice (brief.md Section 4): not a production font pick.
_FONT_DIR = Path(r"C:\Windows\Fonts")
pdfmetrics.registerFont(TTFont("Sample-Regular", str(_FONT_DIR / "arial.ttf")))
pdfmetrics.registerFont(TTFont("Sample-Bold", str(_FONT_DIR / "arialbd.ttf")))
pdfmetrics.registerFont(TTFont("Sample-Italic", str(_FONT_DIR / "ariali.ttf")))
FONT = "Sample-Regular"
FONT_BOLD = "Sample-Bold"
FONT_ITALIC = "Sample-Italic"

# ---------------------------------------------------------------------------
# Section 9 -- owner-frozen legend. Exact, non-normalized values: the same
# slot number does NOT carry the same hour value across letters (D4=2h but
# N4=24h). ``None`` marks a genuinely empty ("rezerwa") slot.
# ---------------------------------------------------------------------------
BASE_LEGEND: dict[str, "int | None"] = {
    "D1": 12, "D2": 4, "D3": 24, "D4": 2, "D5": 24,
    "N1": 12, "N2": 16, "N3": 24, "N4": 24, "N5": 24,
    "U1": 12, "U2": 16, "U3": None, "U4": None, "U5": None,
    "C1": 12, "C2": 16, "C3": None, "C4": None, "C5": None,
}
LETTER_LABELS = {"D": "D — dniówka", "N": "N — nocka", "U": "U — urlop", "C": "C — chorobowe"}


def family(code: str) -> str:
    if code == "24":
        return "h24"
    if code == "–":
        return "off"
    return {"D": "d", "N": "n", "U": "u", "C": "c"}.get(code[0], "off")


# Grayscale-only fills/borders -- meaning never depends on hue, so the
# printout stays legible after a straight monochrome photocopy.
FILL = {
    "d": HexColor("#dcdcdc"),
    "n": HexColor("#a6a6a6"),
    "h24": HexColor("#595959"),
    "u": white,
    "c": white,
    "off": None,
}
TEXT = {
    "d": black, "n": black, "h24": white, "u": black, "c": black, "off": HexColor("#8a8a8a"),
}


@dataclass
class Employee:
    name: str
    plan: list[str]
    wyk: list[str]


def month_dates(year: int, month: int) -> list[dt.date]:
    n = calendar.monthrange(year, month)[1]
    return [dt.date(year, month, d) for d in range(1, n + 1)]


def leave_span(days: list[dt.date], *, search_from: int, business_days_needed: int) -> tuple[list[int], list[int]]:
    """A leave period is a continuous CALENDAR span (weekends included, per
    owner correction 2026-08-20: "urlop 40h to 5 dni roboczych ... od
    srody do wtorku wyszarzasz pola jako urlopowe"), not a set of isolated
    business-day cells. Returns (full_span_indices, symbol_bearing_indices)
    -- every index in the span must be shaded as "on leave"; only the
    business days actually needed to reach the owed hour total (the first
    three here) carry a printed hour symbol, the rest of the span (the
    weekend plus any leftover business days) is shaded but blank.
    """
    start = next(i for i in range(search_from, len(days)) if days[i].weekday() == 2)  # Wednesday
    business: list[int] = []
    i = start
    while len(business) < business_days_needed and i < len(days):
        if days[i].weekday() < 5:
            business.append(i)
        i += 1
    span = list(range(start, business[-1] + 1))
    return span, business[:3]


def build_roster_12h(days: list[dt.date]) -> list[Employee]:
    """10 fictional employees, paired so each pair mirrors the other --
    a direct, easy-to-see demonstration of double-primary staffing
    (brief.md Section 5's "co najmniej jeden dzien z podwojna obsada)."""
    n = len(days)
    cycle = ["D1", "N1", "–", "–"]
    roster: list[Employee] = []
    for i in range(10):
        pair_phase = i // 2
        plan = [cycle[(d + pair_phase) % len(cycle)] for d in range(n)]
        wyk = list(plan)
        roster.append(Employee(f"Pracownik {i + 1:02d}", plan, wyk))

    # Section 10 -- literal, binding 40h leave example (D1/D1/N2 -> U1/U1/U2).
    # 40h at 8h/qualifying-workday (T018) is 5 BUSINESS days, but the
    # employee is unavailable for the whole continuous calendar span
    # including any weekend inside it (owner correction 2026-08-20). The
    # printed hour symbols only need to occupy as many cells as are
    # required to reach the total (3 here); every other day in the span
    # -- weekend or business day -- is shaded as "on leave" but blank.
    leave_emp = roster[4]
    # search_from=15 lands the span on a week where this employee's base
    # cycle already has a rest day immediately before and after the leave
    # -- a Wednesday start where the preceding Tuesday is "N1" would print
    # a night shift directly followed by a day-shift-valued leave symbol,
    # i.e. look like a zero-rest violation that never actually happened
    # (owner-caught bug, 2026-08-20: "Pracownik 5 ma bledy typu dniowka po
    # nocce").
    span, symbol_days = leave_span(days, search_from=15, business_days_needed=5)
    assert leave_emp.plan[span[0] - 1] == "–", "leave must start right after a natural rest day"
    assert leave_emp.plan[span[-1] + 1] == "–", "leave must end right before a natural rest day"
    codes_plan = ["D1", "D1", "N2"]
    codes_wyk = ["U1", "U1", "U2"]
    assert sum(BASE_LEGEND[c] for c in codes_plan) == 40
    assert sum(BASE_LEGEND[c] for c in codes_wyk) == 40
    for i in span:
        if i in symbol_days:
            k = symbol_days.index(i)
            leave_emp.plan[i] = codes_plan[k]
            leave_emp.wyk[i] = codes_wyk[k]
        else:
            leave_emp.plan[i] = "U~"
            leave_emp.wyk[i] = "U~"

    # One-day sick (chorobowe) example.
    sick_emp = roster[6]
    sick_emp.plan[14] = "D1"
    sick_emp.wyk[14] = "C1"

    # Mid-month correction: the printed PLAN/WYK already show only the
    # final, correct state -- no trace of who was originally assigned
    # (brief.md Section 5/12 "bez prezentowania winnego wczesniejszego
    # pracownika"). Nothing to render differently; documented in README.
    correction_emp = roster[8]
    correction_emp.plan[20] = "D1"
    correction_emp.wyk[20] = "D1"

    return roster


def build_roster_24h(days: list[dt.date]) -> tuple[list[Employee], dict[str, "int | None"]]:
    n = len(days)
    cycle = ["24", "–", "–"]
    roster: list[Employee] = []
    for i in range(10):
        pair_phase = i // 2
        plan = [cycle[(d + pair_phase) % len(cycle)] for d in range(n)]
        wyk = list(plan)
        roster.append(Employee(f"Pracownik {i + 1:02d}", plan, wyk))

    # Section 9 -- demo-configured reserve slots (U3/C3 bound to 24h) so
    # the owner can evaluate how a coordinator-assigned reserve value
    # would render. Explicitly labelled DEMO in the legend, not a new
    # default.
    legend = dict(BASE_LEGEND)
    legend["U3"] = 24
    legend["C3"] = 24

    sick_emp = roster[3]
    sick_emp.plan[10] = "24"
    sick_emp.wyk[10] = "C3"

    leave_emp = roster[5]
    leave_emp.plan[16] = "24"
    leave_emp.wyk[16] = "U3"

    correction_emp = roster[7]
    correction_emp.plan[22] = "24"
    correction_emp.wyk[22] = "24"

    return roster, legend


def hours_row(row: list[str], legend: dict[str, "int | None"]) -> int:
    values = dict(legend)
    values["–"] = 0
    values["24"] = 24
    return sum(values.get(c) or 0 for c in row)


def absence_hours(row: list[str], legend: dict[str, "int | None"], letter: str) -> int:
    values = dict(legend)
    values["–"] = 0
    values["24"] = 24
    return sum(values.get(c) or 0 for c in row if c.startswith(letter))


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_header(c: canvas.Canvas, *, site_id: str, date_from: dt.date, date_to: dt.date, revision: str, y: float) -> float:
    c.setFont(FONT_BOLD, 20)
    c.drawString(MARGIN, y, "ELNATH ROTA — wydruk grafiku (CHECKPOINT A, PROTOTYP)")
    y -= 24
    c.setFont(FONT, 13)
    c.drawString(MARGIN, y, f"Firma: ELNATH DEMO      Obiekt: {site_id}      Okres: Sierpień 2026 — DEMO")
    y -= 17
    c.drawString(MARGIN, y, f"Zakres dat: {date_from.isoformat()} — {date_to.isoformat()}")
    y -= 17
    c.drawString(MARGIN, y, f"Schedule provenance: DEMO-SV-LINEAGE-{site_id}-0001      {revision}")
    y -= 17
    c.setFont(FONT, 10.5)
    c.setFillColor(HexColor("#555555"))
    c.drawString(MARGIN, y, f"Wygenerowano: {dt.datetime.now().isoformat(timespec='seconds')}  —  dane wyłącznie demonstracyjne, nie z bazy Roty")
    c.setFillColor(black)
    return y - 18


def draw_table(c: canvas.Canvas, *, days: list[dt.date], roster: list[Employee], legend: dict[str, "int | None"], top_y: float) -> float:
    # Owner correction 2026-08-20: readability for older/low-vision users
    # comes first, and the schedule grid itself (not the legend) is what
    # gets read every day -- so the grid gets the generous dimensions and
    # the largest type on the page; nothing below was picked to save
    # space, this A3 sheet has plenty to spare.
    name_w = 130.0
    sum_w = 48.0
    n_days = len(days)
    day_w = (PAGE_W - 2 * MARGIN - name_w - 4 * sum_w) / n_days

    dow_labels = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Ni"]
    header_h1, header_h2 = 19.0, 23.0
    row_h = 22.0

    x0 = MARGIN
    y = top_y

    # header row 1: day-of-week
    c.setFont(FONT, 11.5)
    x = x0 + name_w
    for d in days:
        weekend = d.weekday() >= 5
        if weekend:
            c.setFillColor(HexColor("#e2e2e2"))
            c.rect(x, y - header_h1 - header_h2, day_w, header_h1 + header_h2, stroke=0, fill=1)
            c.setFillColor(black)
        c.drawCentredString(x + day_w / 2, y - header_h1 + 5, dow_labels[d.weekday()])
        x += day_w
    y -= header_h1

    # header row 2: day-of-month + summary column labels
    c.setFont(FONT_BOLD, 13.5)
    x = x0 + name_w
    for d in days:
        c.drawCentredString(x + day_w / 2, y - header_h2 + 6, str(d.day))
        x += day_w
    c.setFont(FONT_BOLD, 10.5)
    for label in ("Plan g.", "Wyk. g.", "Urlop g.", "L4 g."):
        c.drawCentredString(x + sum_w / 2, y - header_h2 + 6, label)
        x += sum_w
    y -= header_h2

    c.setLineWidth(0.75)
    c.line(x0, y, x0 + name_w + n_days * day_w + 4 * sum_w, y)

    for emp in roster:
        plan_h = hours_row(emp.plan, legend)
        wyk_h = hours_row(emp.wyk, legend)
        urlop_h = absence_hours(emp.wyk, legend, "U")
        l4_h = absence_hours(emp.wyk, legend, "C")

        for sub_label, row, extra in (
            ("PLAN", emp.plan, [f"{plan_h}", "", "", ""]),
            ("WYK", emp.wyk, ["", f"{wyk_h}", f"{urlop_h}", f"{l4_h}"]),
        ):
            x = x0
            c.setFont(FONT, 10.5)
            label_text = emp.name if sub_label == "PLAN" else ""
            c.drawString(x + 4, y - row_h + 6, label_text)
            c.setFont(FONT_ITALIC, 8.5)
            c.setFillColor(HexColor("#777777"))
            c.drawRightString(x + name_w - 4, y - row_h + 6, sub_label)
            c.setFillColor(black)
            x += name_w

            for d, code in zip(days, row):
                fam = family(code)
                # Every day gets a visible cell grid line, like an Excel
                # sheet -- an unfilled "off" cell with no border at all is
                # indistinguishable from a blank/unfilled mistake, which is
                # exactly what confused the owner reading the 24h sample
                # (owner correction 2026-08-20: "ciezko zobaczyc te wolne
                # dni ... u ciebie to sie zlewa").
                c.setLineWidth(0.4)
                c.setStrokeColor(HexColor("#c8c8c8"))
                c.rect(x, y - row_h, day_w, row_h, stroke=1, fill=0)
                fill = FILL[fam]
                if fill is not None:
                    c.setFillColor(fill)
                    c.rect(x + 1.5, y - row_h + 1.5, day_w - 3, row_h - 3, stroke=0, fill=1)
                if fam == "u":
                    c.setLineWidth(1.1)
                    c.setStrokeColor(black)
                    c.rect(x + 1.5, y - row_h + 1.5, day_w - 3, row_h - 3, stroke=1, fill=0)
                elif fam == "c":
                    c.setLineWidth(1.1)
                    c.setDash(2, 1.5)
                    c.setStrokeColor(black)
                    c.rect(x + 1.5, y - row_h + 1.5, day_w - 3, row_h - 3, stroke=1, fill=0)
                    c.setDash()
                c.setFillColor(TEXT[fam])
                c.setFont(FONT_BOLD if fam != "off" else FONT, 11)
                label = "" if code == "–" or code.endswith("~") else code
                c.drawCentredString(x + day_w / 2, y - row_h + 6, label)
                c.setFillColor(black)
                x += day_w

            for val in extra:
                c.setFont(FONT, 10.5)
                c.drawCentredString(x + sum_w / 2, y - row_h + 6, val)
                x += sum_w
            y -= row_h

        # Owner correction 2026-08-20: "wiersze miedzy pracownikami musza
        # miec grubsze linie, bo wzrok nie wie ktorej linii ma pilnowac" --
        # a light 0.5pt rule was the same weight as the ordinary cell grid,
        # so the eye couldn't tell "next employee" from "next day". This is
        # now clearly the heaviest horizontal rule on the page.
        c.setStrokeColor(black)
        c.setLineWidth(1.6)
        c.line(x0, y, x0 + name_w + n_days * day_w + 4 * sum_w, y)

    return y


def draw_legend(c: canvas.Canvas, *, legend: dict[str, "int | None"], demo_slots: set[str], show_24_code: bool, y: float) -> float:
    # Owner correction 2026-08-20 (round 2): four thin vertical columns
    # left most of each one empty -- "nie musza byc pionowe slupki, mozna
    # je rozlozyc na dwa, masz miejsce." Two wide columns (D+N, U+C) use
    # the freed width for a visibly larger legend font instead.
    c.setFont(FONT_BOLD, 13)
    c.drawString(MARGIN, y, "Legenda — tabela wartości godzinowych (wartości właściciela, nie normalizowane)")
    y -= 19

    col_w = (PAGE_W - 2 * MARGIN) / 2
    sub_w = col_w / 2
    letters = ("D", "N", "U", "C")

    def cell_x(j: int) -> float:
        return MARGIN + (j // 2) * col_w + (j % 2) * sub_w

    c.setFont(FONT_BOLD, 12)
    for j, letter in enumerate(letters):
        c.drawString(cell_x(j), y, LETTER_LABELS[letter])
    y -= 16

    c.setFont(FONT, 12)
    for slot in "12345":
        for j, letter in enumerate(letters):
            code = f"{letter}{slot}"
            value = legend[code]
            if value is None:
                text = f"{code} = — (rezerwa)"
            elif code in demo_slots:
                text = f"{code} = {value}h (konfiguracja demo)"
            else:
                text = f"{code} = {value}h"
            c.drawString(cell_x(j), y, text)
        y -= 16

    if show_24_code:
        c.setFont(FONT, 12)
        c.drawString(MARGIN, y, "24 = pełny okres 24h w dniu rozpoczęcia (konwencja demo)")
        y -= 16

    y -= 6
    c.setFont(FONT_ITALIC, 9.5)
    c.drawString(
        MARGIN, y,
        "Rezerwa = zdefiniowany slot bez przypisanej wartości, nie usunięty kod. "
        "Numer NIE oznacza wspólnej wartości dla wszystkich liter (np. D4=2h, N4=24h).",
    )
    y -= 14
    c.drawString(
        MARGIN, y,
        "Wyszarzone pole urlopu bez symbolu = dzień w ciągłym okresie nieobecności "
        "(np. weekend w środku urlopu), który nie wymaga osobnej wartości godzinowej.",
    )
    y -= 14
    c.drawString(
        MARGIN, y,
        "Druk czarno-biały: D/N/24 rozróżnia gęstość wypełnienia (jasne → ciemne), "
        "urlop (U) ma ciągłą obwódkę, chorobowe (C) przerywaną — czytelne bez koloru.",
    )
    return y - 15


def draw_footer(c: canvas.Canvas, y: float) -> None:
    c.setFont(FONT_ITALIC, 9.5)
    c.setFillColor(HexColor("#777777"))
    c.drawString(
        MARGIN, y,
        "PROTOTYP CHECKPOINT A — dane demonstracyjne, brak importu do Roty, nie jest źródłem danych. "
        "PLAN = obowiązująca aktualna obsada, WYK = realizacja/nieobecność; nie prezentuje historii "
        "wcześniej zastąpionego pracownika.",
    )
    c.setFillColor(black)


def render_sample(*, site_id: str, days: list[dt.date], roster: list[Employee], legend: dict[str, "int | None"], demo_slots: set[str], show_24_code: bool, revision: str, out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=landscape(A3))
    y = PAGE_H - MARGIN
    y = draw_header(c, site_id=site_id, date_from=days[0], date_to=days[-1], revision=revision, y=y)
    y -= 6
    y = draw_table(c, days=days, roster=roster, legend=legend, top_y=y)
    y -= 10
    y = draw_legend(c, legend=legend, demo_slots=demo_slots, show_24_code=show_24_code, y=y)
    draw_footer(c, y - 4)
    c.showPage()
    c.save()


def main() -> None:
    days = month_dates(2026, 8)

    roster_12h = build_roster_12h(days)
    render_sample(
        site_id="SITE-DEMO-12H", days=days, roster=roster_12h, legend=BASE_LEGEND, demo_slots=set(), show_24_code=False,
        revision="Revision: DEMO-REV-12H-2026-08-20-A", out_path=OUT_DIR / "schedule_12h.pdf",
    )

    roster_24h, legend_24h = build_roster_24h(days)
    render_sample(
        site_id="SITE-DEMO-24H", days=days, roster=roster_24h, legend=legend_24h, demo_slots={"U3", "C3"}, show_24_code=True,
        revision="Revision: DEMO-REV-24H-2026-08-20-A", out_path=OUT_DIR / "schedule_24h.pdf",
    )

    print(f"Wrote {OUT_DIR / 'schedule_12h.pdf'}")
    print(f"Wrote {OUT_DIR / 'schedule_24h.pdf'}")


if __name__ == "__main__":
    main()
