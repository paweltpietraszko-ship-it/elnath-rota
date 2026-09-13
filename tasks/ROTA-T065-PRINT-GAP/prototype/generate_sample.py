"""ROTA-T065-PRINT-GAP CHECKPOINT A -- isolated visual prototype.

Brief section 14: a real, synthetic-data PDF for OWNER visual sign-off,
built OUTSIDE the production export path. This script never imports or
mutates rota/application/schedule_export.py's write paths and never
touches a database -- it only reuses that module's pure, read-only
presentation helpers (font resolution, page geometry constants) so the
prototype looks like a real page instead of a made-up one.

Round 2 (2026-09-13, OWNER_ACCEPTED): role is printed once next to the
employee's name (their real position -- doesn't change day to day, even
when they cover a shift normally staffed by another role), not repeated
per shift. Day cells show only hours. Role is echoed as a fill tint on
the cell for quick scanning, but the fill is not the only signal --
absences use border style (solid = Urlop, dashed = L4), matching
OCHRONA's existing convention. Page background is always white (this
simulates printed paper, not a themed screen).

Run: python tasks/ROTA-T065-PRINT-GAP/prototype/generate_sample.py
Output: tasks/ROTA-T065-PRINT-GAP/prototype/sample_ordinary.pdf
"""
from __future__ import annotations

import calendar
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from rota.application.schedule_export import _resolve_unicode_font  # noqa: E402 -- read-only reuse, see module docstring

MARGIN = 24.0
NAME_W = 170.0
SUM_W = 56.0
HEADER_H = 90.0
FOOTER_H = 20.0
LEGEND_H = 78.0
WEEKEND_BG = HexColor("#e6e0ce")
_FILL = {"kier": HexColor("#e4e4e1"), "sprz": HexColor("#b9b9b4"), "uczen": HexColor("#8f8f89")}
_TEXT_ON_FILL = {"kier": black, "sprz": black, "uczen": white}
DOW = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Ni"]
YEAR, MONTH = 2026, 9


@dataclass(frozen=True)
class WorkPiece:
    start_hour: int
    end_hour: int  # > 24 means it crosses into the next day (e.g. 22..30 == 22:00-06:00+1)


@dataclass(frozen=True)
class EmployeeSchedule:
    display_name: str
    roles: tuple[str, ...]  # real position(s), printed once at the name -- never per shift
    fill_key: str  # which _FILL tint echoes this person's role on their work cells
    # date -> list[WorkPiece] (work) OR a single absence/off string ("Urlop", "L4")
    days: dict[int, "list[WorkPiece] | str"] = field(default_factory=dict)


def month_days() -> list[date]:
    n = calendar.monthrange(YEAR, MONTH)[1]
    return [date(YEAR, MONTH, d) for d in range(1, n + 1)]


def _piece_label(p: WorkPiece) -> str:
    start = str(p.start_hour)
    end_hour = p.end_hour % 24
    crosses = p.end_hour > 24
    return f"{start}–{end_hour}" + ("(+1)" if crosses else "")


def cell_lines(value) -> list[str]:
    """One line per work piece -- stacked vertically instead of joined with
    "/" on one line, which overflowed a full month's narrow day columns for
    any multi-piece or midnight-crossing cell (CHECKPOINT A round 1 finding)."""
    if isinstance(value, str):
        return [value]
    if not value:
        return ["–"]  # BLANK, same convention as OCHRONA print
    return [_piece_label(p) for p in value]


def cell_hours(value) -> int:
    if not value or isinstance(value, str):
        return 0  # absences shown as plain words -- not counted in the "Godz." column (OWNER to reconfirm at CHECKPOINT B)
    return sum(p.end_hour - p.start_hour for p in value)


# --- Synthetic roster -------------------------------------------------
# Names are invented -- brief section 14: "Nie używać realnych nazwisk."

def build_roster() -> list[EmployeeSchedule]:
    roster: list[EmployeeSchedule] = []

    # Hero #1 -- Anna Wilk: KIEROWNIK, demonstrates most scenarios from
    # brief section 14 on her own: two non-overlapping shifts one day,
    # a midnight-crossing shift, covering an additional shift (still
    # printed as Kierownik, never relabeled), urlop, L4, a plain day off.
    anna_days: dict[int, object] = {
        1: [WorkPiece(5, 12)],
        2: [WorkPiece(6, 10), WorkPiece(16, 20)],
        3: [WorkPiece(22, 30)],  # 22:00-06:00(+1)
        4: [WorkPiece(9, 17)],  # covering an additional shift, still Kierownik
        8: "Urlop",
        9: "Urlop",
        12: "L4",
        13: "L4",
        14: "L4",
        # 5-7, 10-11, 15+ intentionally left as plain days off (no work, no absence)
    }
    for d in range(15, 31):
        if d % 6 not in (0, 1):
            anna_days.setdefault(d, [WorkPiece(5, 13)])
    roster.append(EmployeeSchedule("Anna Wilk", ("Kierownik",), "kier", anna_days))

    # Hero #2 -- Marek Duda: SPRZEDAWCA_ZALOGA, plain realistic weekly rhythm
    marek_days: dict[int, object] = {}
    for day in month_days():
        if day.weekday() == 6:  # Sunday off
            continue
        marek_days[day.day] = [WorkPiece(10, 18)]
    marek_days[10] = "Urlop"
    marek_days[11] = "Urlop"
    roster.append(EmployeeSchedule("Marek Duda", ("Sprzedawca / załoga",), "sprz", marek_days))

    # Third role example -- demonstrates the print holding up once the
    # role list is no longer just the two hardcoded values (see BOARD.md
    # ROTA-T065-CONFIGURABLE-ROLES). "Uczeń" is a placeholder label for
    # this visual demo only, not a production EmployeeRole value.
    bartek_days: dict[int, object] = {}
    for day in month_days():
        if day.weekday() in (5, 6):
            continue
        bartek_days[day.day] = [WorkPiece(9, 13)]
    roster.append(EmployeeSchedule("Bartek Wysocki", ("Uczeń",), "uczen", bartek_days))

    # Filler employees -- realistic simple patterns, enough headcount x 30
    # days to force a page break at the accepted A3 row-height floor
    # (brief section 14 point 8).
    filler_specs = [
        ("Ola Zielińska", "Kierownik", "kier", 6),
        ("Tomasz Baran", "Sprzedawca / załoga", "sprz", 10),
        ("Ewa Sikora", "Sprzedawca / załoga", "sprz", 14),
        ("Kuba Wróbel", "Sprzedawca / załoga", "sprz", 6),
        ("Zofia Kowal", "Sprzedawca / załoga", "sprz", 10),
        ("Rafał Mazur", "Kierownik", "kier", 14),
        ("Julia Pawlak", "Sprzedawca / załoga", "sprz", 6),
        ("Adam Górski", "Sprzedawca / załoga", "sprz", 10),
        ("Nina Kaczmarek", "Sprzedawca / załoga", "sprz", 14),
        ("Bartek Wysocki (Sprzedaż)", "Sprzedawca / załoga", "sprz", 6),
        ("Maja Sokołowska", "Kierownik", "kier", 10),
        ("Igor Jabłoński", "Sprzedawca / załoga", "sprz", 14),
        ("Karol Witek", "Sprzedawca / załoga", "sprz", 6),
        ("Lena Adamska", "Sprzedawca / załoga", "sprz", 10),
        ("Filip Urban", "Sprzedawca / załoga", "sprz", 14),
        ("Wiktoria Sadowska", "Kierownik", "kier", 6),
        ("Damian Krupa", "Sprzedawca / załoga", "sprz", 10),
        ("Alicja Kubiak", "Sprzedawca / załoga", "sprz", 14),
        ("Szymon Wilczek", "Sprzedawca / załoga", "sprz", 6),
        ("Natalia Ostrowska", "Sprzedawca / załoga", "sprz", 10),
        ("Michał Zając", "Kierownik", "kier", 14),
        ("Weronika Kubik", "Sprzedawca / załoga", "sprz", 6),
    ]
    for name, role, fill_key, start in filler_specs:
        days: dict[int, object] = {}
        for day in month_days():
            if day.weekday() in (5, 6):
                continue
            days[day.day] = [WorkPiece(start, start + 8)]
        roster.append(EmployeeSchedule(name, (role,), fill_key, days))

    return roster


def draw_day_headers(c, day_w, days, bold, y) -> float:
    x = MARGIN + NAME_W
    for d in days:
        if d.weekday() >= 5:
            c.setFillColor(WEEKEND_BG)
            c.rect(x, y - 30, day_w, 30, stroke=0, fill=1)
            c.setFillColor(black)
        c.setFont(bold, 6.5)
        c.drawCentredString(x + day_w / 2, y - 10, DOW[d.weekday()])
        c.setFont(bold, 8)
        c.drawCentredString(x + day_w / 2, y - 24, str(d.day))
        x += day_w
    c.setFont(bold, 6.5)
    c.drawCentredString(x + SUM_W / 2, y - 18, "Godz.")
    return y - 32


def draw_row(c, y, row_h, day_w, emp: EmployeeSchedule, days, regular, bold) -> None:
    x = MARGIN
    c.setFont(regular, 7.5)
    c.drawString(x + 2, y - row_h / 2 + 4, emp.display_name)
    c.setFont(regular, 6)
    c.setFillColor(HexColor("#5c6156"))
    c.drawString(x + 2, y - row_h / 2 - 6, " / ".join(emp.roles))
    c.setFillColor(black)
    x += NAME_W
    total = 0
    fill = _FILL.get(emp.fill_key)
    text_color = _TEXT_ON_FILL.get(emp.fill_key, black)
    for day in days:
        value = emp.days.get(day.day)
        lines = cell_lines(value)
        total += cell_hours(value)
        is_absence = isinstance(value, str)
        is_off = value is None
        c.setStrokeColor(HexColor("#c8c8c8"))
        c.setLineWidth(0.4)
        c.rect(x, y - row_h, day_w, row_h, stroke=1, fill=0)
        if not is_absence and not is_off and fill is not None:
            c.setFillColor(fill)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=0, fill=1)
        if is_absence:
            c.setStrokeColor(black)
            if value == "Urlop":
                c.setLineWidth(1.4)
            else:  # L4
                c.setDash(2, 1.5)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setDash()
            c.setLineWidth(0.4)
        fs = 6.5
        while fs > 4.5 and max(pdfmetrics.stringWidth(t, bold, fs) for t in lines) > day_w - 3:
            fs -= 0.5
        line_h = fs + 1.5
        top = y - row_h / 2 + (len(lines) - 1) * line_h / 2
        c.setFillColor(black if (is_absence or is_off or fill is None) else text_color)
        c.setFont(bold, fs)
        for i, line in enumerate(lines):
            c.drawCentredString(x + day_w / 2, top - i * line_h - fs * 0.35, line)
        c.setFillColor(black)
        x += day_w
    c.setFont(regular, 7)
    c.drawCentredString(x + SUM_W / 2, y - row_h / 2 - 3, str(total))


def render(path: Path) -> None:
    regular, bold, italic = _resolve_unicode_font()
    days = month_days()
    roster = build_roster()
    page_w, page_h = landscape(A3)
    day_w = (page_w - 2 * MARGIN - NAME_W - SUM_W) / len(days)
    row_h = 30.0
    available = page_h - 2 * MARGIN - HEADER_H - LEGEND_H - FOOTER_H
    rows_per_page = max(1, int(available // row_h))
    pages = [roster[i : i + rows_per_page] for i in range(0, len(roster), rows_per_page)]

    c = canvas.Canvas(str(path), pagesize=landscape(A3))
    c.setFillColor(white)
    c.rect(0, 0, page_w, page_h, stroke=0, fill=1)  # explicit white page -- never inherits a themed background
    c.setFillColor(black)
    for page_num, page_rows in enumerate(pages, start=1):
        y = page_h - MARGIN
        c.setFont(bold, 16)
        c.drawString(MARGIN, y, "NORDSHOP III sp. z o.o. — Obiekt standardowy NORDSHOP III")
        y -= 18
        c.setFont(regular, 9.5)
        c.drawString(MARGIN, y, f"Okres: wrzesień 2026   Zakres dat: {days[0].isoformat()} — {days[-1].isoformat()}")
        y -= 12
        c.drawString(MARGIN, y, "Kod weryfikacyjny grafiku: PROTOTYP-CHECKPOINT-A (dane syntetyczne)")
        y -= 16
        y = draw_day_headers(c, day_w, days, bold, y)
        for emp in page_rows:
            draw_row(c, y, row_h, day_w, emp, days, regular, bold)
            y -= row_h
        if page_num == len(pages):
            legend_y = y - 14
            c.setFont(bold, 9)
            c.drawString(MARGIN, legend_y, "Legenda")
            legend_y -= 12
            c.setFont(regular, 8)
            for line in (
                "Rola pracownika (rzeczywiste stanowisko) jest wypisana raz pod nazwiskiem, nie przy każdej zmianie — nawet gdy ktoś pokrywa dodatkową zmianę, zostaje swoją rolą.",
                "Komórki dni pokazują wyłącznie rzeczywiste godziny (np. 5–12); odcień wypełnienia komórki to podpowiedź tej samej roli.",
                "Kilka niezależnych zmian jednego dnia — osobne linie w tej samej komórce, w kolejności chronologicznej.",
                "Zmiana przechodząca przez północ: godzina końcowa z dopiskiem (+1) oznacza następną dobę (np. 22–06(+1)).",
                "Nieobecność: pogrubiona pełna ramka = Urlop, przerywana ramka = L4, bez wypełnienia. “–” = zwykły dzień bez pracy.",
                "“Godz.” = suma godzin rzeczywistej pracy w miesiącu (bez godzin absencji).",
            ):
                c.drawString(MARGIN, legend_y, line)
                legend_y -= 11
        c.setFont(regular, 7.5)
        c.drawCentredString(page_w / 2, MARGIN / 2, f"Strona {page_num} z {len(pages)}  —  PROTOTYP CHECKPOINT A, nie dokument produkcyjny")
        c.showPage()
    c.save()


if __name__ == "__main__":
    out = Path(__file__).resolve().parent / "sample_ordinary.pdf"
    render(out)
    print(f"Written: {out}")
