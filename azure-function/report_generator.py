"""
report_generator.py
Generates the Daily Incident Report HTML and Excel from live Zoho ticket data.
"""
from __future__ import annotations

import io
import re
from datetime import date, datetime, timezone, timedelta

from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# ── IST offset ────────────────────────────────────────────────────────────────
IST = timedelta(hours=5, minutes=30)


# ── Band / display-name classification ───────────────────────────────────────
ACCOUNT_BAND: dict[str, str] = {
    "neurealm": "Platinum",
    "otsuka":   "Gold",
    "otsuka-us": "Gold",
    "kyndryl":  "Gold",
    "tatacommunications": "Gold",
    "tata communications": "Gold",
    "au.logicalis": "Gold",
    "logicalis": "Gold",
    "synopsys":  "Gold",
    "synoptek":  "Gold",
    "getronics": "Silver",
    "cloud-kinetics": "Silver",
    "cloud kinetics": "Silver",
}

DISPLAY_NAMES: dict[str, str] = {
    "neurealm":        "Neurealm",
    "otsuka":          "Otsuka",
    "otsuka-us":       "Otsuka",
    "kyndryl":         "Kyndryl",
    "tatacommunications": "Tata Communications",
    "tata communications": "Tata Communications",
    "au.logicalis":    "Logicalis",
    "logicalis":       "Logicalis",
    "synopsys":        "Synopsys",
    "synoptek":        "Synoptek",
    "getronics":       "Getronics",
    "cloud-kinetics":  "Cloud Kinetics",
    "cloud kinetics":  "Cloud Kinetics",
    "sonata-software": "Sonata",
    "sonata software": "Sonata",
    "ltts":            "LTTS",
    "gevernova":       "GE Vernova",
    "ge vernova":      "GE Vernova",
    "core42":          "Core42",
    "blackstone":      "Blackstone",
}

BLACKSTONE_KEYWORDS = ["blackstone"]


def _norm(s: str) -> str:
    return s.strip().lower() if s else ""


def get_band(account_name: str) -> str:
    key = _norm(account_name)
    if key == "neurealm":
        return "Platinum"
    for k, band in ACCOUNT_BAND.items():
        if k in key or key in k:
            return band
    return "Bronze"


def get_display(account_name: str) -> str:
    key = _norm(account_name)
    for k, disp in DISPLAY_NAMES.items():
        if k == key:
            return disp
        if k in key:
            return disp
    if any(kw in key for kw in BLACKSTONE_KEYWORDS):
        return "Blackstone"
    return account_name or "Unknown"


# ── Zoho ticket → internal tuple ─────────────────────────────────────────────
def parse_ticket(raw: dict, today: date) -> dict:
    """
    Returns a normalized ticket dict with keys:
      num, subject, priority, account_raw, band, display, ado,
      created_date, last_updated, contact, assignee, status, reason, age, bucket
    """
    num = raw.get("ticketNumber", "")
    subject = raw.get("subject", "")
    priority = raw.get("priority") or "P3"
    status = raw.get("status", "")

    # Account name
    account_raw = ""
    if raw.get("account"):
        account_raw = raw["account"].get("accountName") or raw["account"].get("name") or ""
    if not account_raw:
        account_raw = raw.get("accountName", "")

    # ADO — stored in custom field; field names vary, try common keys
    ado = ""
    cf = raw.get("cf") or {}
    for key in ("cf_ado_number", "cf_ado", "cf_adoNumber", "cf_ado_link", "cf_azure_devops"):
        if cf.get(key):
            ado = str(cf[key]).strip()
            break
    # Also try top-level
    if not ado:
        for key in ("adoNumber", "ado_number", "ado"):
            if raw.get(key):
                ado = str(raw[key]).strip()
                break

    # Dates — Zoho returns ISO strings with timezone
    def _parse_dt(s: str | None) -> date | None:
        if not s:
            return None
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return (dt + IST).date()
        except Exception:
            return None

    created_date = _parse_dt(raw.get("createdTime")) or today
    last_updated_date = _parse_dt(raw.get("modifiedTime")) or today

    def _fmt_date(d: date) -> str:
        months = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        return f"{months[d.month-1]} {d.day:02d}"

    # Contact / assignee
    contact = ""
    if raw.get("contact"):
        c = raw["contact"]
        contact = c.get("firstName", "") + " " + c.get("lastName", "")
        contact = contact.strip()
    if not contact:
        contact = raw.get("contactName") or raw.get("requesterName") or ""

    assignee = ""
    if raw.get("assignee"):
        a = raw["assignee"]
        assignee = a.get("firstName", "") + " " + a.get("lastName", "")
        assignee = assignee.strip()
    if not assignee:
        assignee = raw.get("assigneeName") or ""

    # Reason (last comment / resolution notes) — not in basic list, empty by default
    reason = raw.get("resolution") or raw.get("reasonForOnHold") or ""

    age_days = (today - created_date).days
    bkt = _bucket(age_days)

    band = get_band(account_raw)
    # Blackstone override
    if any(kw in _norm(account_raw) for kw in BLACKSTONE_KEYWORDS) or \
       any(kw in _norm(subject) for kw in BLACKSTONE_KEYWORDS):
        band = "Blackstone-Bronze"

    display = get_display(account_raw)

    return {
        "num": str(num),
        "subject": subject,
        "priority": priority if priority.startswith("P") else f"P{priority}",
        "account_raw": account_raw,
        "band": band,
        "display": display,
        "ado": ado,
        "created_date": created_date,
        "created_str": created_date.isoformat(),
        "last_updated": _fmt_date(last_updated_date),
        "contact": contact,
        "assignee": assignee,
        "status": status,
        "reason": reason,
        "age": age_days,
        "bucket": bkt,
        "team": "L2" if ado else "L1",
    }


def _bucket(a: int) -> str:
    if a <= 7:   return "0-7d"
    if a <= 14:  return "8-14d"
    if a <= 30:  return "15-30d"
    return "30d+"


# ── Style helpers ─────────────────────────────────────────────────────────────
def _f(hex6: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex6)


def _font(hex6: str, bold=False, sz=10) -> Font:
    return Font(color=hex6, bold=bold, size=sz)


AL_CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
AL_LEFT   = Alignment(horizontal="left",   vertical="center", wrap_text=True)

AGE_STYLES    = {"0-7d":  ("F0FDF4","14532D"), "8-14d": ("FEFCE8","713F12"),
                 "15-30d":("FEF3C7","B45309"),  "30d+":  ("FEE2E2","B91C1C")}
PRI_STYLES    = {"P2": ("FFF7ED","C2410C"), "P3": ("F1F5F9","475569")}
STATUS_STYLES = {"Open":("DBEAFE","1D4ED8"), "In Progress":("DCFCE7","15803D"),
                 "On Hold":("FEF9C3","B45309"),
                 "Awaiting Resolution Confirmation":("EDE9FE","6D28D9")}
BAND_STYLES   = {"Platinum":("CBD5E1","1E293B"), "Gold":("FEF9C3","92400E"),
                 "Silver":("DBEAFE","1E4976"),   "Bronze":("FFF7ED","9A3412"),
                 "Blackstone-Bronze":("FFF7ED","9A3412")}
BAND_BADGE    = {"Platinum":"Platinum","Gold":"Gold","Silver":"Silver",
                 "Bronze":"Bronze","Blackstone-Bronze":"Bronze"}

ROW_BG = {
    ("On Hold","30d+"):      "FFF0F0",
    ("On Hold","15-30d"):    "FFFBF0",
    ("On Hold","8-14d"):     "FFFBF0",
    ("In Progress","8-14d"): "FEFFF0",
}


def _row_bg(status: str, bkt: str) -> str:
    return ROW_BG.get((status, bkt), "FFFFFF")


# ── Excel helpers ─────────────────────────────────────────────────────────────
W14 = [10, 18, 10, 40, 8, 26, 8, 10, 6, 10, 16, 36, 16, 12]
W13 = [10, 18, 10, 44, 8, 26, 8, 10, 6, 10, 16, 16, 12]
H14 = ["Ticket #","Customer","Band","Subject","Priority","Status","Age","Bucket",
       "Team","ADO #","Raised By","Reason","Last Updated","Created"]
H13 = ["Ticket #","Customer","Band","Subject","Priority","Status","Age","Bucket",
       "Team","ADO #","Raised By","Last Updated","Created"]


def _set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


def _write_header(ws, row_num: int, headers: list[str], fill_hex: str):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row_num, i, h)
        c.fill = _f(fill_hex)
        c.font = Font(color="FFFFFF", bold=True, size=10)
        c.alignment = AL_CENTER
    ws.row_dimensions[row_num].height = 25


def _write_row(ws, row_num: int, t: dict, with_reason: bool = True):
    bkt = t["bucket"]
    status = t["status"]
    rbg = _row_bg(status, bkt)
    band = t["band"]
    af, afont = AGE_STYLES[bkt]
    pf, pfont = PRI_STYLES.get(t["priority"], ("F1F5F9","475569"))
    sf, sfont = STATUS_STYLES.get(status, ("FFFFFF","000000"))
    bf, bfont = BAND_STYLES.get(band, ("FFF7ED","9A3412"))
    badge_label = BAND_BADGE.get(band, "Bronze")

    cells: list[tuple] = [
        (f"#{t['num']}",    rbg,      "2563EB", True),   # A Ticket #
        (t["display"],      rbg,      "0F172A", False),  # B Customer
        (badge_label,       bf,       bfont,    True),   # C Band
        (t["subject"],      rbg,      "0F172A", False),  # D Subject
        (t["priority"],     pf,       pfont,    True),   # E Priority
        (status,            sf,       sfont,    True),   # F Status
        (f"{t['age']}d",    af,       afont,    True),   # G Age
        (bkt,               af,       afont,    False),  # H Bucket
        (t["team"],         "EDE9FE" if t["team"]=="L2" else "F1F5F9",
                            "6D28D9" if t["team"]=="L2" else "64748B",
                            t["team"]=="L2"),             # I Team
        (t["ado"],          "F5F3FF" if t["ado"] else "FFFFFF",
                            "6D28D9", bool(t["ado"])),   # J ADO #
        (t["contact"],      "F8FAFC", "334155", False),  # K Raised By
    ]

    if with_reason:
        cells.append((t["reason"],       "FFFBEB", "92400E", False))  # L Reason
        cells.append((t["last_updated"], rbg,      "0F172A", False))  # M Last Updated
        cells.append((_created_disp(t["created_date"]), rbg, "0F172A", False))  # N Created
    else:
        cells.append((t["last_updated"], rbg,      "0F172A", False))  # L Last Updated
        cells.append((_created_disp(t["created_date"]), rbg, "0F172A", False))  # M Created

    for col_idx, (val, fill_hex, font_hex, bold) in enumerate(cells, 1):
        c = ws.cell(row_num, col_idx, val)
        c.fill = _f(fill_hex)
        c.font = Font(color=font_hex, bold=bold, size=9)
        c.alignment = AL_LEFT
    ws.row_dimensions[row_num].height = 30


def _created_disp(d: date) -> str:
    months = ["Jan","Feb","Mar","Apr","May","Jun",
              "Jul","Aug","Sep","Oct","Nov","Dec"]
    return f"{months[d.month-1]} {d.day:02d}"


# ── Public API ────────────────────────────────────────────────────────────────
def generate_excel(tickets: list[dict], today: date) -> bytes:
    """Return Excel workbook bytes from normalized ticket dicts."""
    mo = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]
    title_date = f"{mo[today.month-1]} {today.day}, {today.year}"

    wb = Workbook()

    # -- Summary sheet
    ws1 = wb.active
    ws1.title = "Summary"
    ws1.column_dimensions["A"].width = 32
    ws1.column_dimensions["B"].width = 10
    ws1.column_dimensions["C"].width = 12

    ws1["A1"] = f"Daily Incident Report — {title_date}"
    ws1["A1"].font = Font(color="0F172A", bold=True, size=12)
    ws1["A2"] = f"Period: {title_date} · 18:00 IST"
    ws1["A2"].font = Font(color="64748B", size=10)
    ws1.row_dimensions[1].height = 22
    ws1.row_dimensions[2].height = 18
    ws1.row_dimensions[3].height = 8

    _write_header(ws1, 4, ["Status","Count","% of Total"], "1E293B")

    by_status: dict[str, list] = {}
    for t in tickets:
        by_status.setdefault(t["status"], []).append(t)

    total = len(tickets)
    open_ = by_status.get("Open", [])
    ip    = by_status.get("In Progress", [])
    oh    = by_status.get("On Hold", [])
    arc   = by_status.get("Awaiting Resolution Confirmation", [])

    for i, (s, lst) in enumerate([
        ("Open", open_), ("In Progress", ip),
        ("On Hold", oh), ("Awaiting Resolution Confirmation", arc),
        ("Total", tickets)
    ], 5):
        n = len(lst)
        ws1[f"A{i}"] = s
        ws1[f"B{i}"] = n
        ws1[f"C{i}"] = f"{n/total*100:.1f}%" if s != "Total" else "100%"
        ws1.row_dimensions[i].height = 22
        if s != "Total":
            sf, sfont = STATUS_STYLES.get(s, ("FFFFFF","000000"))
            for col in ["A","B","C"]:
                c = ws1[f"{col}{i}"]
                c.fill = _f(sf)
                c.font = Font(color=sfont, bold=True, size=10)
        else:
            for col in ["A","B","C"]:
                ws1[f"{col}{i}"].font = Font(bold=True, size=10)

    # -- All Tickets
    ws2 = wb.create_sheet("All Tickets")
    _set_widths(ws2, W14)
    _write_header(ws2, 1, H14, "1E293B")
    for r, t in enumerate(tickets, 2):
        _write_row(ws2, r, t, with_reason=True)

    # -- Platinum Gold Silver
    ws3 = wb.create_sheet("Platinum Gold Silver")
    _set_widths(ws3, W14)
    _write_header(ws3, 1, H14, "334155")
    r = 2
    for t in tickets:
        if t["band"] in ("Platinum","Gold","Silver"):
            _write_row(ws3, r, t, with_reason=True); r += 1

    # -- New
    ws4 = wb.create_sheet("New")
    _set_widths(ws4, W13)
    _write_header(ws4, 1, H13, "1D4ED8")
    for r, t in enumerate(open_, 2):
        _write_row(ws4, r, t, with_reason=False)

    # -- In Progress
    ws5 = wb.create_sheet("In Progress")
    _set_widths(ws5, W13)
    _write_header(ws5, 1, H13, "15803D")
    for r, t in enumerate(ip, 2):
        _write_row(ws5, r, t, with_reason=False)

    # -- On Hold
    ws6 = wb.create_sheet("On Hold")
    _set_widths(ws6, W14)
    _write_header(ws6, 1, H14, "B45309")
    for r, t in enumerate(oh, 2):
        _write_row(ws6, r, t, with_reason=True)

    # -- Awaiting Resolution
    ws7 = wb.create_sheet("Awaiting Resolution")
    _set_widths(ws7, W14)
    _write_header(ws7, 1, H14, "6D28D9")
    for r, t in enumerate(arc, 2):
        _write_row(ws7, r, t, with_reason=True)

    # -- L2 Tickets
    ws8 = wb.create_sheet("L2 Tickets")
    _set_widths(ws8, W13)
    _write_header(ws8, 1, H13, "6D28D9")
    r = 2
    for t in tickets:
        if t["ado"]:
            _write_row(ws8, r, t, with_reason=False); r += 1

    # -- Aging View
    ws9 = wb.create_sheet("Aging View")
    _set_widths(ws9, W14)
    r = 1
    for bkt in ["30d+","15-30d","8-14d","0-7d"]:
        _write_header(ws9, r, H14, "475569"); r += 1
        for t in tickets:
            if t["bucket"] == bkt:
                _write_row(ws9, r, t, with_reason=True); r += 1

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def generate_html(tickets: list[dict], today: date) -> str:
    """Return full HTML report string."""
    mo_long  = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]
    mo_short = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]
    title_date = f"{mo_long[today.month-1]} {today.day}, {today.year}"

    by_status: dict[str, list] = {}
    for t in tickets:
        by_status.setdefault(t["status"], []).append(t)

    open_ = by_status.get("Open", [])
    ip    = by_status.get("In Progress", [])
    oh    = by_status.get("On Hold", [])
    arc   = by_status.get("Awaiting Resolution Confirmation", [])

    n_new  = len(open_)
    n_ip   = len(ip)
    n_oh   = len(oh)
    n_arc  = len(arc)

    # L2 count: only Platinum/Gold/Silver with ADO
    n_l2 = sum(1 for t in tickets
               if t["ado"] and t["band"] in ("Platinum","Gold","Silver"))

    # Aging counts
    ag = {"30d+":0,"15-30d":0,"8-14d":0,"0-7d":0}
    for t in tickets:
        ag[t["bucket"]] += 1

    # Band counts (visible in report)
    n_plat  = sum(1 for t in tickets if t["band"] == "Platinum")
    n_gold  = sum(1 for t in tickets if t["band"] == "Gold")
    n_silver= sum(1 for t in tickets if t["band"] == "Silver")

    # Group visible tickets by band/account for HTML sections
    # Order: Platinum accounts, then Gold accounts, then Silver accounts, then Blackstone (Bronze named)
    def _group_by_account(ticket_list: list[dict]) -> dict[str, list]:
        groups: dict[str, list] = {}
        for t in ticket_list:
            groups.setdefault(t["display"], []).append(t)
        return groups

    plat_tickets      = [t for t in tickets if t["band"] == "Platinum"]
    gold_tickets      = [t for t in tickets if t["band"] == "Gold"]
    silver_tickets    = [t for t in tickets if t["band"] == "Silver"]
    blackstone_tickets= [t for t in tickets if t["band"] == "Blackstone-Bronze"]

    # CSS
    css = """
    body{font-family:'Segoe UI',Arial,sans-serif;background:#F8FAFC;margin:0;padding:20px;color:#0F172A}
    .container{max-width:1200px;margin:0 auto;background:#fff;border-radius:12px;box-shadow:0 4px 24px rgba(0,0,0,.08);overflow:hidden}
    .header{background:linear-gradient(135deg,#1E293B 0%,#334155 100%);padding:28px 36px;color:#fff}
    .header h1{margin:0;font-size:22px;font-weight:700;letter-spacing:-.3px}
    .header p{margin:6px 0 0;font-size:13px;opacity:.7}
    .summary-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:20px 28px;background:#F8FAFC;border-bottom:1px solid #E2E8F0}
    .card{background:#fff;border-radius:8px;padding:14px 16px;border:1px solid #E2E8F0;text-align:center}
    .card .label{font-size:11px;color:#64748B;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
    .card .value{font-size:26px;font-weight:700;color:#0F172A}
    .card.blue{border-top:3px solid #3B82F6}.card.green{border-top:3px solid #22C55E}
    .card.yellow{border-top:3px solid #EAB308}.card.purple{border-top:3px solid #A855F7}
    .card.l2{border-top:3px solid #6D28D9}
    .age-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;padding:0 28px 16px;background:#F8FAFC;border-bottom:1px solid #E2E8F0}
    .age-card{border-radius:8px;padding:12px 16px;text-align:center}
    .age-card .label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
    .age-card .value{font-size:22px;font-weight:700}
    .age-red{background:#FEE2E2;color:#B91C1C}.age-orange{background:#FEF3C7;color:#B45309}
    .age-yellow{background:#FEFCE8;color:#713F12}.age-green{background:#F0FDF4;color:#14532D}
    .band-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:0 28px 20px;background:#F8FAFC;border-bottom:1px solid #E2E8F0}
    .band-card{border-radius:8px;padding:12px 16px;text-align:center}
    .band-card .label{font-size:11px;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
    .band-card .value{font-size:22px;font-weight:700}
    .plat{background:#CBD5E1;color:#1E293B}.gold{background:#FEF9C3;color:#92400E}.silver{background:#DBEAFE;color:#1E4976}
    .section{padding:20px 28px;border-bottom:1px solid #F1F5F9}
    .section-header{display:flex;align-items:center;gap:10px;margin-bottom:14px}
    .section-title{font-size:15px;font-weight:700;color:#1E293B}
    .badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:700}
    .badge-plat{background:#CBD5E1;color:#1E293B}.badge-gold{background:#FEF9C3;color:#92400E}
    .badge-silver{background:#DBEAFE;color:#1E4976}.badge-bronze{background:#FFF7ED;color:#9A3412}
    table{width:100%;border-collapse:collapse;font-size:12px}
    th{background:#1E293B;color:#fff;padding:8px 10px;text-align:left;font-size:11px;font-weight:600}
    td{padding:7px 10px;border-bottom:1px solid #F1F5F9;vertical-align:top}
    .ticket-id{color:#2563EB;font-weight:700;white-space:nowrap}
    .pri-p2{background:#FFF7ED;color:#C2410C;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700}
    .pri-p3{background:#F1F5F9;color:#475569;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:700}
    .stat-open{background:#DBEAFE;color:#1D4ED8;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}
    .stat-ip{background:#DCFCE7;color:#15803D;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}
    .stat-oh{background:#FEF9C3;color:#B45309;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}
    .stat-arc{background:#EDE9FE;color:#6D28D9;padding:2px 7px;border-radius:4px;font-size:10px;font-weight:600}
    .age-0{background:#F0FDF4;color:#14532D;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .age-1{background:#FEFCE8;color:#713F12;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .age-2{background:#FEF3C7;color:#B45309;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .age-3{background:#FEE2E2;color:#B91C1C;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .ado{background:#F5F3FF;color:#6D28D9;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .team-l2{background:#EDE9FE;color:#6D28D9;padding:2px 6px;border-radius:4px;font-size:10px;font-weight:700}
    .team-l1{background:#F1F5F9;color:#64748B;padding:2px 6px;border-radius:4px;font-size:10px}
    .reason{font-size:11px;color:#78350F;max-width:280px}
    .footer{padding:16px 28px;background:#F8FAFC;text-align:center;font-size:11px;color:#94A3B8}
    """

    def _age_cls(bkt: str) -> str:
        return {"0-7d":"age-0","8-14d":"age-1","15-30d":"age-2","30d+":"age-3"}[bkt]

    def _stat_cls(status: str) -> str:
        return {"Open":"stat-open","In Progress":"stat-ip",
                "On Hold":"stat-oh","Awaiting Resolution Confirmation":"stat-arc"}.get(status,"")

    def _stat_label(status: str) -> str:
        return "ARC" if status == "Awaiting Resolution Confirmation" else status

    def _pri_cls(pri: str) -> str:
        return "pri-p2" if pri == "P2" else "pri-p3"

    def _badge_cls(band: str) -> str:
        return {"Platinum":"badge-plat","Gold":"badge-gold",
                "Silver":"badge-silver"}.get(band,"badge-bronze")

    def _ticket_rows(ticket_list: list[dict], show_reason: bool = True) -> str:
        rows = []
        for t in ticket_list:
            reason_cell = f'<td class="reason">{t["reason"] or "—"}</td>' if show_reason else ""
            rows.append(f"""
            <tr>
              <td class="ticket-id">#{t["num"]}</td>
              <td>{t["display"]}</td>
              <td><span class="{_age_cls(t["bucket"])}">{t["age"]}d</span></td>
              <td><span class="{_pri_cls(t["priority"])}">{t["priority"]}</span></td>
              <td><span class="{_stat_cls(t["status"])}">{_stat_label(t["status"])}</span></td>
              <td style="max-width:300px;font-size:11px">{t["subject"]}</td>
              <td><span class="{"ado" if t["ado"] else "team-l1"}">{t["ado"] or "—"}</span></td>
              <td><span class="{"team-l2" if t["team"]=="L2" else "team-l1"}">{t["team"]}</span></td>
              <td style="font-size:11px;color:#64748B">{t["contact"]}</td>
              <td style="font-size:11px;color:#334155">{t["assignee"]}</td>
              {reason_cell}
              <td style="font-size:10px;color:#94A3B8;white-space:nowrap">{t["last_updated"]}</td>
            </tr>""")
        return "\n".join(rows)

    def _table_header(show_reason: bool = True) -> str:
        reason_th = "<th>Reason / Last Update</th>" if show_reason else ""
        return f"""
        <table>
          <thead>
            <tr>
              <th>Ticket #</th><th>Customer</th><th>Age</th><th>Pri</th>
              <th>Status</th><th>Subject</th><th>ADO #</th><th>Team</th>
              <th>Raised By</th><th>Assignee</th>{reason_th}<th>Modified</th>
            </tr>
          </thead>
          <tbody>"""

    def _account_section(account_name: str, band: str, ticket_list: list[dict],
                         show_reason: bool = True) -> str:
        badge = BAND_BADGE.get(band, "Bronze")
        bc = _badge_cls(band)
        rows = _ticket_rows(ticket_list, show_reason)
        return f"""
        <div class="section">
          <div class="section-header">
            <span class="section-title">{account_name}</span>
            <span class="badge {bc}">{badge}</span>
            <span style="font-size:12px;color:#64748B">({len(ticket_list)} ticket{"s" if len(ticket_list)!=1 else ""})</span>
          </div>
          {_table_header(show_reason)}
          {rows}
          </tbody></table>
        </div>"""

    # Build sections
    sections = []

    # Platinum
    for acct, lst in _group_by_account(plat_tickets).items():
        sections.append(_account_section(acct, "Platinum", lst, show_reason=True))

    # Gold
    for acct, lst in _group_by_account(gold_tickets).items():
        sections.append(_account_section(acct, "Gold", lst, show_reason=True))

    # Silver
    for acct, lst in _group_by_account(silver_tickets).items():
        sections.append(_account_section(acct, "Silver", lst, show_reason=True))

    # Blackstone (Bronze named account)
    if blackstone_tickets:
        sections.append(_account_section("Blackstone", "Blackstone-Bronze", blackstone_tickets, show_reason=False))

    sections_html = "\n".join(sections)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Daily Incident Report — {title_date}</title>
<style>{css}</style>
</head>
<body>
<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>Daily Incident Report</h1>
    <p>{title_date} &nbsp;·&nbsp; CoreStack Support Team</p>
  </div>

  <!-- Status summary cards -->
  <div class="summary-grid">
    <div class="card blue"><div class="label">New</div><div class="value">{n_new}</div></div>
    <div class="card green"><div class="label">In Progress</div><div class="value">{n_ip}</div></div>
    <div class="card yellow"><div class="label">On Hold</div><div class="value">{n_oh}</div></div>
    <div class="card purple"><div class="label">Awaiting Confirmation</div><div class="value">{n_arc}</div></div>
    <div class="card l2"><div class="label">With L2 (PGS)</div><div class="value">{n_l2}</div></div>
  </div>

  <!-- Aging cards -->
  <div class="age-grid">
    <div class="age-card age-red"><div class="label">30d+</div><div class="value">{ag["30d+"]}</div></div>
    <div class="age-card age-orange"><div class="label">15-30d</div><div class="value">{ag["15-30d"]}</div></div>
    <div class="age-card age-yellow"><div class="label">8-14d</div><div class="value">{ag["8-14d"]}</div></div>
    <div class="age-card age-green"><div class="label">0-7d</div><div class="value">{ag["0-7d"]}</div></div>
  </div>

  <!-- Band cards -->
  <div class="band-grid">
    <div class="band-card plat"><div class="label">Platinum</div><div class="value">{n_plat}</div></div>
    <div class="band-card gold"><div class="label">Gold</div><div class="value">{n_gold}</div></div>
    <div class="band-card silver"><div class="label">Silver</div><div class="value">{n_silver}</div></div>
  </div>

  <!-- Account sections -->
  {sections_html}

  <div class="footer">
    Generated automatically by CoreStack Support Bot &nbsp;·&nbsp; {title_date} 18:00 IST
  </div>
</div>
</body>
</html>"""

    return html
