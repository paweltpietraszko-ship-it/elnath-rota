"""ROTA-T065-PRINT-GAP CHECKPOINT A -- isolated visual prototype.

Brief section 14: a real, synthetic-data PDF for OWNER visual sign-off,
built OUTSIDE the production export path. This script never imports or
mutates rota/application/schedule_export.py's write paths and never
touches a database -- it only reuses that module's pure, read-only
presentation helpers (font resolution, page geometry constants) so the
prototype looks like a real page instead of a made-up one.

Run: python tasks/ROTA-T065-PRINT-GAP/prototype/generate_sample.py
Output: tasks/ROTA-T065-PRINT-GAP/prototype/sample_ordinary.pdf
"""
from __future__ import annotations

import calendar
import sys
from dataclasses import dataclass
from datetime import date, datetime
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
LEGEND_H = 70.0
WEEKEND_BG = HexColor("#e2e2e2")
DOW = ["Pn", "Wt", "Śr", "Cz", "Pt", "So", "Ni"]
YEAR, MONTH = 2026, 9


@dataclass(frozen=True)
class WorkPiece:
    start_hour: int
    end_hour: int  # > 24 means it crosses into the next day (e.g. 22..30 == 22:00-06:00+1)
    role_letter: str  # "K" (Kierownik), "S" (Sprzedawca/załoga), or "" (no required_role)


@dataclass(frozen=True)
class EmployeeSchedule:
    display_name: str
    # date -> list[WorkPiece] (work) OR a single absence/off string ("Urlop", "L4")
    days: dict[int, "list[WorkPiece] | str"]


def month_days() -> list[date]:
    n = calendar.monthrange(YEAR, MONTH)[1]
    return [date(YEAR, MONTH, d) for d in range(1, n + 1)]


def _piece_label(p: WorkPiece) -> str:
    start = f"{p.start_hour:02d}"
    end_hour = p.end_hour % 24
    end = f"{end_hour:02d}"
    crosses = p.end_hour > 24
    label = f"{start}-{end}" + ("(+1)" if crosses else "")
    if p.role_letter:
        label += f" {p.role_letter}"
    return label


def cell_lines(value) -> list[str]:
    """One line per work piece -- stacked vertically instead of joined with
    "/" on one line, which overflowed a full month's narrow day columns for
    any multi-piece or midnight-crossing cell (CHECKPOINT A finding)."""
    if isinstance(value, str):
        return [value]
    if not value:
        return ["–"]  # BLANK, same convention as OCHRONA print
    return [_piece_label(p) for p in value]


def cell_hours(value) -> int:
    if not value or isinstance(value, str):
        return 0  # absences shown as plain words here -- CHECKPOINT A also freezes whether/how these count in the summary column
    total = 0
    for p in value:
        total += p.end_hour - p.start_hour
    return total


# --- Synthetic roster -------------------------------------------------
# Names are invented -- brief section 14: "Nie używać realnych nazwisk."

def build_roster() -> list[EmployeeSchedule]:
    roster: list[EmployeeSchedule] = []

    # Hero #1 -- Anna Wilk: KIEROWNIK, demonstrates almost every scenario
    # from brief section 14 on her own: mixed roles across days (1),
    # role + no-role assignment (2), two non-overlapping shifts one day (3),
    # a midnight-crossing shift (4), urlop (5), L4 (6), a plain day off (7).
    anna_days: dict[int, object] = {
        1: [WorkPiece(5, 12, "K")],
        2: [WorkPiece(10, 18, "S")],
        3: [WorkPiece(6, 10, "K"), WorkPiece(16, 20, "K")],
        4: [WorkPiece(22, 30, "K")],  # 22:00-06:00(+1)
        5: [WorkPiece(9, 17, "")],  # PRIMARY assignment, no required_role
        8: "Urlop",
        9: "Urlop",
        12: "L4",
        13: "L4",
        14: "L4",
        # 6, 7, 10, 11, 15+ intentionally left as plain days off (no work, no absence)
    }
    for d in range(15, 31):
        if d % 6 not in (0, 1):
            anna_days.setdefault(d, [WorkPiece(5, 13, "K")])
    roster.append(EmployeeSchedule("Anna Wilk", anna_days))

    # Hero #2 -- Marek Duda: SPRZEDAWCA_ZALOGA, plain realistic weekly rhythm
    marek_days: dict[int, object] = {}
    for d, day in enumerate(month_days(), start=1):
        if day.weekday() == 6:  # Sunday off
            continue
        marek_days[d] = [WorkPiece(10, 18, "S")]
    marek_days[10] = "Urlop"
    marek_days[11] = "Urlop"
    roster.append(EmployeeSchedule("Marek Duda", marek_days))

    # Filler employees -- realistic simple patterns, enough headcount x 30
    # days to force a page break at the accepted A3 row-height floor
    # (brief section 14 point 8).
    filler_names = [
        "Ola Zielińska", "Tomasz Baran", "Ewa Sikora", "Kuba Wróbel",
        "Zofia Kowal", "Rafał Mazur", "Julia Pawlak", "Adam Górski",
        "Nina Kaczmarek", "Bartek Wysocki", "Maja Sokołowska", "Igor Jabłoński",
        "Karol Witek", "Lena Adamska", "Filip Urban", "Wiktoria Sadowska",
        "Damian Krupa", "Alicja Kubiak", "Szymon Wilczek", "Natalia Ostrowska",
        "Michał Zając", "Weronika Kubik",
    ]
    for i, name in enumerate(filler_names):
        days: dict[int, object] = {}
        role = "K" if i % 5 == 0 else "S"
        start = 6 + (i % 3) * 4
        for day in month_days():
            d = day.day
            if day.weekday() in (5, 6):
                continue
            days[d] = [WorkPiece(start, start + 8, role)]
        roster.append(EmployeeSchedule(name, days))

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
    c.setFont(regular, 7)
    c.drawString(x + 2, y - row_h + row_h / 2 - 3, emp.display_name)
    x += NAME_W
    total = 0
    for day in days:
        value = emp.days.get(day.day)
        lines = cell_lines(value)
        total += cell_hours(value)
        c.setStrokeColor(HexColor("#c8c8c8"))
        c.setLineWidth(0.4)
        c.rect(x, y - row_h, day_w, row_h, stroke=1, fill=0)
        is_absence = isinstance(value, str)
        if is_absence:
            c.setStrokeColor(black)
            c.setDash(2, 1.5)
            c.rect(x + 1, y - row_h + 1, day_w - 2, row_h - 2, stroke=1, fill=0)
            c.setDash()
        fs = 6.5
        while fs > 4.5 and max(pdfmetrics.stringWidth(t, bold, fs) for t in lines) > day_w - 3:
            fs -= 0.5
        line_h = fs + 1.5
        top = y - row_h / 2 + (len(lines) - 1) * line_h / 2
        c.setFont(bold, fs)
        for i, line in enumerate(lines):
            c.drawCentredString(x + day_w / 2, top - i * line_h - fs * 0.35, line)
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
                "Godziny = rzeczywisty przedział pracy tego dnia (np. 5-12). Litera po godzinach = rola: K = Kierownik, S = Sprzedawca/załoga. Brak litery = brak wymaganej roli.",
                "Kilka niezależnych zmian jednego dnia rozdzielone znakiem “/”, w kolejności chronologicznej.",
                "Zmiana przechodząca przez północ: godzina końcowa z dopiskiem (+1) oznacza następną dobę (np. 22-06(+1)).",
                "Obramowanie przerywane + słowo = nieobecność (Urlop, L4). “–” = zwykły dzień bez pracy, bez nieobecności.",
                "“Godz.” = suma godzin rzeczywistej pracy w miesiącu (bez godzin absencji — do potwierdzenia w CHECKPOINT A).",
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
