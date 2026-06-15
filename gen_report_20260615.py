from datetime import date
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

TODAY = date(2026, 6, 15)

IP = [
    ("211192","FinOps Email Notification Issue (Clone)","P3","tatacommunications","tcl","125029","2026-05-19","Jun 09","Sunilkumar S","PremKumar B","In Progress",""),
    ("217515","FW: Cost Mismatch in recommendation","P3","CoreStack","kyndryl","","2026-06-04","Jun 12","Nagalakshmi N","Ganga Reddy","In Progress",""),
    ("219541","Trustech - Finops not triggered","P2","CoreStack_CS","internal","","2026-06-09","Jun 12","Krishna Kumar VJ","Ganga Reddy","In Progress",""),
    ("216808","Difference Between CoreStack Recommendation and Azure Calculation","P3","Kyndryl","kyndryl","132316","2026-06-02","Jun 12","Randhir Kumar","PremKumar B","In Progress",""),
    ("216750","FW: Production Environment IFoundry5X","P3","tatacommunications","tcl","132646","2026-06-02","Jun 12","Sunilkumar S","PremKumar B","In Progress",""),
    ("220105","Merged cells in cost recommendation Report","P3","CoreStack","kyndryl","133816","2026-06-10","Jun 12","Nagalakshmi N","PremKumar B","In Progress",""),
    ("205888","Need assistance to update creds for EA account for Trinity College","P2","au.logicalis","logicallis","132186","2026-05-05","Jun 12","Kamran Wahid","PremKumar B","In Progress",""),
    ("220546","ODP/Blackstone - Bus Patrol","P3","Corestack","internal","","2026-06-11","Jun 12","Jayven Couch","Nithin Ram","In Progress",""),
    ("220875","Dashboard slowness","P2","Synopsys","synopsys","133875","2026-06-12","Jun 14","Ranjitha Thota","Ganga Reddy","In Progress",""),
    ("221821","GE Reports not working","P3","gevernova","GE Vernova","133952","2026-06-14","Jun 14","VijayKumar P","Avinash Naidu","In Progress",""),
    ("221940","Re: Corestack Project Addition","P3","ltts","LTTS","","2026-06-15","Jun 15","Kaustubh M","Avinash Naidu","In Progress",""),
    ("222003","SHI Locuz - Need Assistance in Compliance Execution","P3","CoreStack","internal","","2026-06-15","Jun 15","Nagalakshmi N","Deepesh H","In Progress",""),
    ("220999","Request for Investigation – OCI Cost Processing","P3","core42","internal","133976","2026-06-12","Jun 15","Muthu D","PremKumar B","In Progress",""),
    ("222040","Billing Amount Difference between GCP and Core Stock","P3","ltts","internal","","2026-06-15","Jun 15","Kaustubh M","Deepesh H","In Progress",""),
    ("206833","Mar26 usage for Mitsui Chemicals","P3","Synoptek","synoptek","129985","2026-05-07","Jun 15","Stacey Zborowski","Nithin Ram","In Progress",""),
]
OH = [
    ("209005","Getting wrong recommended SKU in cost recommendation report","P2","neurealm","internal","130297","2026-05-13","Jun 14","Swapnilyadav I","PremKumar B","On Hold","The reported invalid recommendation issue has been fixed. Reviewed all the remaining right sizing system recommendations and they appear to be valid. However the customer recently has raised a concern that all the recommendations provided by CS are invalid. So we have given the context and informed Nagalakshmi to reply in this ticket. Hence we are keeping it on hold."),
    ("211893","Re: Core stock Finops Dashboard cost differ","P2","neurealm","","","2026-05-21","Jun 11","Parthasarathy K","Avinash Naidu","On Hold","Customer needs to raise the support case with Azure. This is an issue from Azure side."),
    ("211895","Re: Core stock Finops Dashboard cost differ for GCP","P3","neurealm","internal","131068","2026-05-21","Jun 15","Parthasarathy K","Nithin Ram","On Hold","Steps provided customer has to implement the changes."),
    ("211954","AWS Accounts transfer from INH to ISO Tenant","P3","otsuka-us","Otsuka","","2026-05-21","Jun 15","Rajkumar Uppu","Aadhithya S","On Hold","Awaiting confirmation from Ashok to proceed with backfilling of the cost data for these 3 accounts."),
    ("215451","Re: Corestack Project Addition","P3","ltts","LTTS","","2026-05-29","Jun 14","Kaustubh M","Avinash Naidu","On Hold","Waiting for the customer to provide the availability so that we can get into a call to discuss this further."),
    ("217785","RDS Snapshot Not Created on May 31","P3","cloud-kinetics","cloudkinetics","132850","2026-06-05","Jun 11","Service Assurance","Gnanadesigan A","On Hold","We have stated that we do not have sufficient logs to troubleshoot further and the customer is checking internally."),
    ("217961","Sonata - CSP accounts not showing up","P3","CoreStack_CS","Sonata","132668","2026-06-05","Jun 15","Deovrat Soman","PremKumar B","On Hold","The initial reported issue has been resolved, however while loading the dashboard we are encountering errors. Engineering team suspects the issue is due to missing currency."),
    ("217989","ODP - ALiando - CoreTrust - National Tree - Cost Processing","P3","CoreStack","internal","","2026-06-05","Jun 12","Anaranya Bagchi","Ganga Reddy","On Hold","Anaranya has sent a mail to the customer to allow the API permission from CSP Partner."),
    ("217990","Cloud.corestack.io is slow across all pages","P3","CoreStack","internal","","2026-06-05","Jun 15","Satyabrat","Ganga Reddy","On Hold","We are awaiting response from Pendo team."),
    ("219147","RE: RE:[CASE] CUR Backfill","P3","sonata-software","Sonata","","2026-06-08","Jun 13","Raghavan P","Nithin Ram","On Hold","Flow currently being tested and 1 account works as expected. Will proceed with the remaining."),
    ("219360","cloud.corestack.io","P3","CoreStack","internal","","2026-06-08","Jun 09","Satyabrat","Nithin Ram","On Hold","NA"),
]
ARC = [
    ("214686","No cost data for TreeRing (AEMCS)","P3","Corestack","internal","","2026-05-27","Jun 14","Jayven Couch","Logesh S","Awaiting Resolution Confirmation","Waiting for the ticket owner to confirm."),
    ("216586","Unable to onboard Snowflake in CS4CS","P3","CoreStack","internal","","2026-06-01","Jun 12","Anaranya Bagchi","Ganga Reddy","Awaiting Resolution Confirmation","Waiting for Anaranya's availability for call."),
    ("217606","Login Issue with CoreStack Tool","P3","otsuka-us","Otsuka","","2026-06-04","Jun 15","Rajkumar Uppu","Ganga Reddy","Awaiting Resolution Confirmation","Customer pinged in teams and asked to hold for 1 day."),
    ("219361","Filtrona Finops Dashboard Unallocated Resource Groups","P3","Getronics","Getronics","","2026-06-08","Jun 11","Shashank N","Nithin Ram","Awaiting Resolution Confirmation","NA"),
    ("219377","ODP Corporation MCA Billing Account cost processing errors","P3","Corestack","internal","","2026-06-08","Jun 09","Jayven Couch","Nithin Ram","Awaiting Resolution Confirmation","Awaiting credential refresh to validate the cost process."),
    ("219658","US Prod - Dashboard Not Loading","P3","CoreStack_CS","internal","","2026-06-09","Jun 10","Ashok Kumar E","Nithin Ram","Awaiting Resolution Confirmation","NA"),
    ("219989","Re: Corestack","P3","CoreStack_CS","Sonata","","2026-06-10","Jun 14","Deovrat Soman","PremKumar B","Awaiting Resolution Confirmation","Unable to reproduce the issue, informed the same to the customer and we are awaiting their response."),
    ("220165","Trustedtech - HMH - cost for April","P3","CoreStack_CS","internal","","2026-06-10","Jun 10","Krishna Kumar VJ","Nithin Ram","Awaiting Resolution Confirmation","N/A"),
    ("220416","Sonata - Tata Tele CSP processing issue","P2","CoreStack_CS","Sonata","133815","2026-06-11","Jun 15","Deovrat Soman","PremKumar B","Awaiting Resolution Confirmation","Cost has been processed and we are now awaiting customer's confirmation."),
    ("220456","US SaaS - Kyndryl Lifelabs - 2 subscriptions are not available","P3","CoreStack","kyndryl","","2026-06-11","Jun 15","Nagalakshmi N","Avinash Naidu","Awaiting Resolution Confirmation","NA"),
    ("221054","US SaaS - Kyndryl - Default dashboards not visible","P3","CoreStack","internal","","2026-06-12","Jun 12","Nagalakshmi N","Nithin Ram","Awaiting Resolution Confirmation","NA"),
]
OPEN = [
    ("219258","Firing: High Priority MSProd App Server Memory Utilisation above 90%","P3","Corestack","internal","","2026-06-08","Jun 08","Notify SRE Ops","—","Open",""),
    ("219898","Deployment Status Confirmation Required","P3","cloud-kinetics","cloudkinetics","","2026-06-10","Jun 10","Service Assurance","PremKumar B","Open",""),
    ("220491","FW: Resources Cost - Beside Tagged and untagged - LifeLabs","P3","CoreStack","kyndryl","133656","2026-06-11","Jun 12","Nagalakshmi N","Avinash Naidu","Open",""),
]
ALL_TICKETS = OPEN + IP + OH + ARC

BAND_MAP_ACCT = {"neurealm":"Platinum","otsuka-us":"Gold","Kyndryl":"Gold","tatacommunications":"Gold",
                 "au.logicalis":"Gold","Synopsys":"Gold","Synoptek":"Gold","Getronics":"Silver","cloud-kinetics":"Silver"}
CUST_GOLD = {"kyndryl","Otsuka","synopsys","synoptek","tcl","logicallis"}
CUST_SILVER = {"Getronics","cloudkinetics"}

def get_band(acct, cust):
    k = acct.lower()
    if k == "neurealm": return "Platinum"
    if acct in BAND_MAP_ACCT: return BAND_MAP_ACCT[acct]
    if cust in CUST_GOLD: return "Gold"
    if cust in CUST_SILVER: return "Silver"
    return "Bronze"

def get_disp(acct, cust):
    m = {"neurealm":"Neurealm","otsuka-us":"Otsuka","Kyndryl":"Kyndryl",
         "tatacommunications":"Tata Communications","au.logicalis":"Logicalis",
         "Synopsys":"Synopsys","Synoptek":"Synoptek","Getronics":"Getronics",
         "cloud-kinetics":"Cloud Kinetics","sonata-software":"Sonata","ltts":"LTTS",
         "gevernova":"GE Vernova","core42":"Core42"}
    if acct in m: return m[acct]
    cm = {"kyndryl":"Kyndryl","Otsuka":"Otsuka","synopsys":"Synopsys","synoptek":"Synoptek",
          "tcl":"Tata Communications","logicallis":"Logicalis","Getronics":"Getronics",
          "cloudkinetics":"Cloud Kinetics","Sonata":"Sonata","LTTS":"LTTS",
          "GE Vernova":"GE Vernova","internal":"CoreStack (Internal)"}
    return cm.get(cust, acct)

def age(d): return (TODAY - date.fromisoformat(d)).days
def bucket(a):
    if a<=7: return "0-7d"
    if a<=14: return "8-14d"
    if a<=30: return "15-30d"
    return "30d+"

def created_disp(d):
    mo = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    dt = date.fromisoformat(d)
    return f"{mo[dt.month-1]} {dt.day:02d}"

# ── Fills & Fonts ──────────────────────────────────────────────────────────────
def f(hex6): return PatternFill("solid", fgColor=hex6)
def font(hex6, bold=False, sz=10): return Font(color=hex6, bold=bold, size=sz)

ROW_BG = {
    ("On Hold","30d+"):   "FFF0F0",
    ("On Hold","15-30d"): "FFFBF0",
    ("On Hold","8-14d"):  "FFFBF0",
    ("In Progress","8-14d"): "FEFFF0",
}
def row_bg(status, bkt): return ROW_BG.get((status, bkt), "FFFFFF")

AGE_STYLES = {"0-7d":("F0FDF4","14532D"), "8-14d":("FEFCE8","713F12"),
              "15-30d":("FEF3C7","B45309"), "30d+":("FEE2E2","B91C1C")}
PRI_STYLES = {"P2":("FFF7ED","C2410C"), "P3":("F1F5F9","475569")}
STATUS_STYLES = {"Open":("DBEAFE","1D4ED8"),"In Progress":("DCFCE7","15803D"),
                 "On Hold":("FEF9C3","B45309"),"Awaiting Resolution Confirmation":("EDE9FE","6D28D9")}
BAND_STYLES = {"Platinum":("CBD5E1","1E293B"),"Gold":("FEF9C3","92400E"),
               "Silver":("DBEAFE","1E4976"),"Bronze":("FFF7ED","9A3412")}
TEAM_STYLES = {"L2":("EDE9FE","6D28D9"), "L1":("F1F5F9","64748B")}

al_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
al_left   = Alignment(horizontal="left",   vertical="center", wrap_text=True)

def write_header(ws, row, headers, fill_hex):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row, i, h)
        c.fill = f(fill_hex); c.font = Font(color="FFFFFF", bold=True, size=10)
        c.alignment = al_center
    ws.row_dimensions[row].height = 25

def write_row(ws, row_num, t, with_reason=True, with_created=True):
    num, subj, pri, acct, cust, ado, created, mod, contact, assignee, status, reason = t
    a = age(created); bkt = bucket(a)
    band = get_band(acct, cust); disp = get_disp(acct, cust)
    team = "L2" if ado else "L1"
    rbg = row_bg(status, bkt)

    # Build cell list: (value, fill_hex, font_hex, bold)
    cells = []
    # A: Ticket #
    cells.append((f"#{num}", rbg, "2563EB", True))
    # B: Customer
    cells.append((disp, rbg, "0F172A", False))
    # C: Band
    bf, bfont = BAND_STYLES[band]
    cells.append((band, bf, bfont, True))
    # D: Subject
    cells.append((subj, rbg, "0F172A", False))
    # E: Priority
    pf, pfont = PRI_STYLES.get(pri, ("F1F5F9","475569"))
    cells.append((pri, pf, pfont, True))
    # F: Status
    sf, sfont = STATUS_STYLES.get(status, ("FFFFFF","000000"))
    cells.append((status if status != "Awaiting Resolution Confirmation" else "Awaiting Resolution Confirmation", sf, sfont, True))
    # G: Age value
    af, afont = AGE_STYLES[bkt]
    cells.append((f"{a}d", af, afont, True))
    # H: Bucket
    cells.append((bkt, af, afont, False))
    # I: Team
    tf, tfont = TEAM_STYLES[team]
    cells.append((team, tf, tfont, team=="L2"))
    # J: ADO #
    if ado:
        cells.append((ado, "F5F3FF", "6D28D9", True))
    else:
        cells.append(("", "FFFFFF", "000000", False))
    # K: Raised By
    cells.append((contact, "F8FAFC", "334155", False))
    # L: Reason (14-col) or Last Updated (13-col)
    if with_reason:
        cells.append((reason, "FFFBEB", "92400E", False))
        # M: Last Updated
        cells.append((mod, rbg, "0F172A", False))
    else:
        cells.append((mod, rbg, "0F172A", False))
    # N: Created (14-col only) or M for 13-col
    if with_created:
        cells.append((created_disp(created), rbg, "0F172A", False))

    for col_idx, (val, fill_hex, font_hex, bold) in enumerate(cells, 1):
        c = ws.cell(row_num, col_idx, val)
        c.fill = f(fill_hex); c.font = Font(color=font_hex, bold=bold, size=9)
        c.alignment = al_left
    ws.row_dimensions[row_num].height = 30

def set_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

W14 = [10,18,10,40,8,26,8,10,6,10,16,36,16,12]
W13 = [10,18,10,44,8,26,8,10,6,10,16,16,12]
H14 = ["Ticket #","Customer","Band","Subject","Priority","Status","Age","Bucket","Team","ADO #","Raised By","Reason","Last Updated","Created"]
H13 = ["Ticket #","Customer","Band","Subject","Priority","Status","Age","Bucket","Team","ADO #","Raised By","Last Updated","Created"]

wb = Workbook()

# ── Sheet 1: Summary ──────────────────────────────────────────────────────────
ws1 = wb.active; ws1.title = "Summary"
ws1.column_dimensions["A"].width = 32
ws1.column_dimensions["B"].width = 10
ws1.column_dimensions["C"].width = 12
# Title rows
ws1["A1"] = "Daily Incident Report — June 15, 2026"
ws1["A1"].font = Font(color="0F172A", bold=True, size=12)
ws1["A2"] = "Period: June 15, 2026 · 19:30 IST"
ws1["A2"].font = Font(color="64748B", size=10)
ws1.row_dimensions[1].height = 22; ws1.row_dimensions[2].height = 18
# Blank row
ws1.row_dimensions[3].height = 8
# Header row 4
write_header(ws1, 4, ["Status","Count","% of Total"], "1E293B")
total = len(ALL_TICKETS)
n_open=len(OPEN); n_ip=len(IP); n_oh=len(OH); n_arc=len(ARC)
for i,(s,n) in enumerate([("Open",n_open),("In Progress",n_ip),("On Hold",n_oh),
                            ("Awaiting Resolution Confirmation",n_arc),("Total",total)],5):
    ws1[f"A{i}"]=s; ws1[f"B{i}"]=n
    ws1[f"C{i}"] = f"{n/total*100:.1f}%" if s!="Total" else "100%"
    ws1.row_dimensions[i].height = 22
    if s!="Total":
        sf,sfont = STATUS_STYLES.get(s,("FFFFFF","000000"))
        for col in ["A","B","C"]:
            c=ws1[f"{col}{i}"]; c.fill=f(sf); c.font=Font(color=sfont,bold=True,size=10)
    else:
        for col in ["A","B","C"]: ws1[f"{col}{i}"].font=Font(bold=True,size=10)

# ── Sheet 2: All Tickets ──────────────────────────────────────────────────────
ws2 = wb.create_sheet("All Tickets"); set_widths(ws2,W14)
write_header(ws2,1,H14,"1E293B")
for r,t in enumerate(ALL_TICKETS,2): write_row(ws2,r,t,with_reason=True)

# ── Sheet 3: Platinum Gold Silver ─────────────────────────────────────────────
ws3 = wb.create_sheet("Platinum Gold Silver"); set_widths(ws3,W14)
write_header(ws3,1,H14,"334155")
r=2
for t in ALL_TICKETS:
    if get_band(t[3],t[4]) in ("Platinum","Gold","Silver"):
        write_row(ws3,r,t,with_reason=True); r+=1

# ── Sheet 4: New ──────────────────────────────────────────────────────────────
ws4 = wb.create_sheet("New"); set_widths(ws4,W13)
write_header(ws4,1,H13,"1D4ED8")
for r,t in enumerate(OPEN,2): write_row(ws4,r,t,with_reason=False)

# ── Sheet 5: In Progress ──────────────────────────────────────────────────────
ws5 = wb.create_sheet("In Progress"); set_widths(ws5,W13)
write_header(ws5,1,H13,"15803D")
for r,t in enumerate(IP,2): write_row(ws5,r,t,with_reason=False)

# ── Sheet 6: On Hold ──────────────────────────────────────────────────────────
ws6 = wb.create_sheet("On Hold"); set_widths(ws6,W14)
write_header(ws6,1,H14,"B45309")
for r,t in enumerate(OH,2): write_row(ws6,r,t,with_reason=True)

# ── Sheet 7: Awaiting Resolution ──────────────────────────────────────────────
ws7 = wb.create_sheet("Awaiting Resolution"); set_widths(ws7,W14)
write_header(ws7,1,H14,"6D28D9")
for r,t in enumerate(ARC,2): write_row(ws7,r,t,with_reason=True)

# ── Sheet 8: L2 Tickets ───────────────────────────────────────────────────────
ws8 = wb.create_sheet("L2 Tickets"); set_widths(ws8,W13)
write_header(ws8,1,H13,"6D28D9")
r=2
for t in ALL_TICKETS:
    if t[5]: write_row(ws8,r,t,with_reason=False); r+=1

# ── Sheet 9: Aging View ───────────────────────────────────────────────────────
ws9 = wb.create_sheet("Aging View"); set_widths(ws9,W14)
BUCKET_HEADER_COLORS = {"30d+":"DC2626","15-30d":"D97706","8-14d":"CA8A04","0-7d":"16A34A"}
r=1
for bkt in ["30d+","15-30d","8-14d","0-7d"]:
    write_header(ws9,r,H14,"475569"); r+=1
    for t in ALL_TICKETS:
        a=age(t[6])
        if bucket(a)==bkt:
            write_row(ws9,r,t,with_reason=True); r+=1

wb.save("/home/user/GD/CS_Daily_Incident_Report_20260615.xlsx")
print("Excel done ✓")

# ── Fix HTML: L2 count ────────────────────────────────────────────────────────
with open("/home/user/GD/CS_Daily_Incident_Report_20260615.html","r") as fh:
    html = fh.read()

# Count visible L2 (Platinum+Gold+Silver with ADO)
visible_l2 = sum(1 for t in ALL_TICKETS
                 if t[5] and get_band(t[3],t[4]) in ("Platinum","Gold","Silver"))
print(f"Visible L2 count: {visible_l2}")

import re
# Replace the L2 count in the "With L2 (PGS)" summary card
html = re.sub(
    r'(With L2 \(PGS\).*?font-size:26px[^>]+>)\d+',
    lambda m: m.group(1) + str(visible_l2),
    html, flags=re.DOTALL
)
with open("/home/user/GD/CS_Daily_Incident_Report_20260615.html","w") as fh:
    fh.write(html)
print("HTML L2 count fixed ✓")
