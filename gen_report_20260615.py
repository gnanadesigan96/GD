#!/usr/bin/env python3
"""Generate CS_Daily_Incident_Report_20260615.xlsx"""
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

def hex_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color.lstrip("#"))

def write_header_row(ws, headers, fill_hex, font_hex="FFFFFF"):
    ws.append(headers)
    r = ws.max_row
    ws.row_dimensions[r].height = 30
    for c in range(1, len(headers)+1):
        cell = ws.cell(r, c)
        cell.fill = hex_fill(fill_hex)
        cell.font = Font(bold=True, color=font_hex, size=10)
        cell.alignment = Alignment(wrap_text=True, vertical="center")

def write_data_row(ws, data, fill_hex, font_hex="000000"):
    ws.append(list(data))
    r = ws.max_row
    ws.row_dimensions[r].height = 30
    for c in range(1, len(data)+1):
        cell = ws.cell(r, c)
        cell.fill = hex_fill(fill_hex)
        cell.font = Font(color=font_hex, size=10)
        cell.alignment = Alignment(wrap_text=True, vertical="center")

def set_col_widths(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

WIDTHS_13 = [10,45,10,20,10,18,28,10,12,8,12,18,14]
WIDTHS_14 = WIDTHS_13 + [50]
HEADERS_13 = ["Ticket#","Subject","Priority","Account","Band","Assignee","Status","Age(days)","Age Bucket","L1/L2","ADO Link","Raised By","Last Update"]
HEADERS_14 = HEADERS_13 + ["Hold/ARC Reason"]

IN_PROGRESS = [
    [211192,"FinOps Email Notification Issue (Clone)","P3","Tata Communications","Gold","PremKumar B","In Progress",27,"15-30d","L2","125029","Sunilkumar S","Jun 09",""],
    [217515,"FW: Cost Mismatch in recommendation","P3","Kyndryl","Gold","Ganga Reddy","In Progress",11,"8-14d","L1","","Nagalakshmi N","Jun 12",""],
    [219541,"Trustech - Finops not triggered","P2","Internal","Bronze","Ganga Reddy","In Progress",6,"0-7d","L1","","Krishna Kumar VJ","Jun 12",""],
    [216808,"Difference Between CoreStack Recommendation and Azure Calculation","P3","Kyndryl","Gold","PremKumar B","In Progress",13,"8-14d","L2","132316","Randhir Kumar","Jun 12",""],
    [216750,"FW: Production Environment IFoundry5X","P3","Tata Communications","Gold","PremKumar B","In Progress",13,"8-14d","L2","132646","Sunilkumar S","Jun 12",""],
    [220105,"Merged cells in cost recommendation Report","P3","Kyndryl","Gold","PremKumar B","In Progress",5,"0-7d","L2","133816","Nagalakshmi N","Jun 12",""],
    [205888,"Need assistance to update creds for EA account for Trinity College","P2","Logicalis","Gold","PremKumar B","In Progress",41,"30d+","L2","132186","Kamran Wahid","Jun 12",""],
    [220546,"ODP/Blackstone - Bus Patrol","P3","Internal","Bronze","Nithin Ram","In Progress",4,"0-7d","L1","","Jayven Couch","Jun 12",""],
    [220875,"Dashboard slowness","P2","Synopsys","Gold","Ganga Reddy","In Progress",3,"0-7d","L2","133875","Ranjitha Thota","Jun 14",""],
    [221821,"GE Reports not working","P3","GE Vernova","Bronze","Avinash Naidu","In Progress",1,"0-7d","L2","133952","Vijaykumar P","Jun 14",""],
    [221940,"Re: Corestack Project Addition","P3","LTTS","Bronze","Avinash Naidu","In Progress",0,"0-7d","L1","","Kaustubh M","Jun 15",""],
    [222003,"SHI Locuz - Need Assistance in Compliance Execution","P3","Internal","Bronze","Deepesh H","In Progress",0,"0-7d","L1","","Nagalakshmi N","Jun 15",""],
    [220999,"Request for Investigation - OCI Cost Processing","P3","Core42","Bronze","PremKumar B","In Progress",3,"0-7d","L2","133976","Muthu D","Jun 15",""],
    [222040,"Billing Amount Difference between GCP and Core Stock","P3","LTTS","Bronze","Deepesh H","In Progress",0,"0-7d","L1","","Kaustubh M","Jun 15",""],
    [206833,"Mar26 usage for Mitsui Chemicals","P3","Synoptek","Gold","Nithin Ram","In Progress",39,"30d+","L2","129985","Stacey Zborowski","Jun 15",""],
]

ON_HOLD = [
    [209005,"Getting wrong recommended SKU in cost recommendation report","P2","Neurealm","Platinum","PremKumar B","On Hold",33,"30d+","L2","130297","Swapnilyadav Ingale","Jun 14","The reported invalid recommendation issue has been fixed. Reviewed all the remaining right sizing system recommendations and they appear to be valid. However the customer recently has raised a concern that all the recommendations provided by CS are invalid. So we have given the context and informed Nagalakshmi to reply in this ticket. Hence we are keeping it on hold."],
    [211893,"Re: Core stock Finops Dashboard cost differ","P2","Neurealm","Platinum","Avinash Naidu","On Hold",25,"15-30d","L1","","Parthasarathy K","Jun 11","Customer needs to raise the support case with Azure. This is an issue from Azure side."],
    [211895,"Re: Core stock Finops Dashboard cost differ for GCP","P3","Neurealm","Platinum","Nithin Ram","On Hold",25,"15-30d","L2","131068","Parthasarathy K","Jun 15","Steps provided customer has to implement the changes."],
    [211954,"AWS Accounts transfer from INH to ISO Tenant","P3","Otsuka","Gold","Aadhithya Shanmugapriyan","On Hold",25,"15-30d","L1","","Rajkumar Uppu","Jun 15","Awaiting confirmation from Ashok to proceed with backfilling of the cost data for these 3 accounts."],
    [215451,"Re: Corestack Project Addition","P3","LTTS","Bronze","Avinash Naidu","On Hold",17,"15-30d","L1","","Kaustubh M","Jun 14","Waiting for the customer to provide the availability so that we can get into a call to discuss this further."],
    [217785,"RDS Snapshot Not Created on May 31","P3","Cloud Kinetics","Silver","Gnanadesigan A","On Hold",10,"8-14d","L2","132850","Service Assurance","Jun 11","We have stated that we do not have sufficient logs to troubleshoot further and the customer is checking internally."],
    [217961,"Sonata - CSP accounts not showing up","P3","Sonata","Bronze","PremKumar B","On Hold",10,"8-14d","L2","132668","Deovrat Soman","Jun 15","The initial reported issue has been resolved, however while loading the dashboard we are encountering errors. Engineering team suspects the issue is due to missing currency."],
    [217989,"ODP - ALiando - CoreTrust - National Tree - Cost Processing","P3","Internal","Bronze","Ganga Reddy","On Hold",10,"8-14d","L1","","Anaranya Bagchi","Jun 12","Anaranya has sent a mail to the customer to allow the API permission from CSP Partner."],
    [217990,"Cloud.corestack.io is slow across all pages","P3","Internal","Bronze","Ganga Reddy","On Hold",10,"8-14d","L1","","Satyabrat","Jun 15","We are awaiting response from Pendo team."],
    [219147,"RE: RE:[CASE] CUR Backfill","P3","Sonata","Bronze","Nithin Ram","On Hold",7,"0-7d","L1","","Raghavan P","Jun 13","Flow currently being tested and 1 account works as expected. Will proceed with the remaining."],
    [219360,"cloud.corestack.io","P3","Internal","Bronze","Nithin Ram","On Hold",7,"0-7d","L1","","Satyabrat","Jun 09","NA"],
]

ARC = [
    [214686,"No cost data for TreeRing (AEMCS)","P3","Internal","Bronze","logesh S","Awaiting Resolution Confirmation",19,"15-30d","L1","","Jayven Couch","Jun 14","Waiting for the ticket owner to confirm."],
    [216586,"Unable to onboard Snowflake in CS4CS","P3","Internal","Bronze","Ganga Reddy","Awaiting Resolution Confirmation",14,"8-14d","L1","","Anaranya Bagchi","Jun 12","Waiting for Anaranya's availability for call."],
    [217606,"Login Issue with CoreStack Tool","P3","Otsuka","Gold","Ganga Reddy","Awaiting Resolution Confirmation",11,"8-14d","L1","","Rajkumar Uppu","Jun 15","Customer pinged in teams and asked to hold for 1 day."],
    [219361,"Filtrona Finops Dashboard Unallocated Resource Groups","P3","Getronics","Silver","Nithin Ram","Awaiting Resolution Confirmation",7,"0-7d","L1","","Shashank Nayakt","Jun 11","NA"],
    [219377,"ODP Corporation MCA Billing Account cost processing errors","P3","Internal","Bronze","Nithin Ram","Awaiting Resolution Confirmation",7,"0-7d","L1","","Jayven Couch","Jun 09","Awaiting credential refresh to validate the cost process."],
    [219658,"US Prod - Dashboard Not Loading","P3","Internal","Bronze","Nithin Ram","Awaiting Resolution Confirmation",6,"0-7d","L1","","Ashok Kumar Elangovan","Jun 10","NA"],
    [219989,"Re: Corestack","P3","Sonata","Bronze","PremKumar B","Awaiting Resolution Confirmation",5,"0-7d","L1","","Deovrat Soman","Jun 14","Unable to reproduce the issue, informed the same to the customer and we are awaiting their response."],
    [220165,"Trustedtech - HMH - cost for April","P3","Internal","Bronze","Nithin Ram","Awaiting Resolution Confirmation",5,"0-7d","L1","","Krishna Kumar VJ","Jun 10","N/A"],
    [220416,"Sonata - Tata Tele CSP processing issue","P2","Sonata","Bronze","PremKumar B","Awaiting Resolution Confirmation",4,"0-7d","L2","133815","Deovrat Soman","Jun 15","Cost has been processed and we are now awaiting customer's confirmation."],
    [220456,"US SaaS - Kyndryl Lifelabs - 2 subscriptions are not available","P3","Kyndryl","Gold","Avinash Naidu","Awaiting Resolution Confirmation",4,"0-7d","L1","","Nagalakshmi N","Jun 15","NA"],
    [221054,"US SaaS - Kyndryl - Default dashboards not visible","P3","Internal","Bronze","Nithin Ram","Awaiting Resolution Confirmation",3,"0-7d","L1","","Nagalakshmi N","Jun 12","NA"],
]

OPEN = [
    [219258,"Firing: High Priority MSProd App Server Memory Utilisation above 90%","P3","Internal","Bronze","--","Open",7,"0-7d","L1","","Notify SRE Ops","Jun 08",""],
    [219898,"Deployment Status Confirmation Required","P3","Cloud Kinetics","Silver","PremKumar B","Open",5,"0-7d","L1","","Service Assurance","Jun 10",""],
    [220491,"FW: Resources Cost - Beside Tagged and untagged - LifeLabs","P3","Kyndryl","Gold","Avinash Naidu","Open",4,"0-7d","L2","133656","Nagalakshmi N","Jun 12",""],
]

ALL_TICKETS = IN_PROGRESS + ON_HOLD + ARC + OPEN
L2_IDS = {211192,216808,216750,205888,220105,220875,206833,209005,211895,217785,217961,220416,220491}
BAND_FILL = {"Platinum":"CBD5E1","Gold":"FEF9C3","Silver":"DBEAFE","Bronze":"FFF7ED"}
BAND_FONT = {"Platinum":"1E293B","Gold":"92400E","Silver":"1E4976","Bronze":"9A3412"}

# Sheet 1: Summary
ws1 = wb.active
ws1.title = "Summary"
write_header_row(ws1, ["Status","Count","%"], "1E293B")
for row in [("Open",3,"7.5%"),("In Progress",15,"37.5%"),("On Hold",11,"27.5%"),("Awaiting Resolution Confirmation",11,"27.5%"),("Total",40,"100%")]:
    ws1.append(list(row))
    r = ws1.max_row
    ws1.row_dimensions[r].height = 25
    for c in range(1,4):
        ws1.cell(r,c).alignment = Alignment(vertical="center")
set_col_widths(ws1, [35,10,10])

# Sheet 2: All Tickets
ws2 = wb.create_sheet("All Tickets")
write_header_row(ws2, HEADERS_14, "1E293B")
for t in ALL_TICKETS:
    write_data_row(ws2, t, BAND_FILL.get(t[4],"FFFFFF"), BAND_FONT.get(t[4],"000000"))
set_col_widths(ws2, WIDTHS_14)

# Sheet 3: Platinum Gold Silver
ws3 = wb.create_sheet("Platinum Gold Silver")
write_header_row(ws3, HEADERS_14, "334155")
for t in ALL_TICKETS:
    if t[4] in ("Platinum","Gold","Silver"):
        write_data_row(ws3, t, BAND_FILL[t[4]], BAND_FONT[t[4]])
set_col_widths(ws3, WIDTHS_14)

# Sheet 4: New / Open
ws4 = wb.create_sheet("New - Open")
write_header_row(ws4, HEADERS_13, "1D4ED8")
for t in OPEN:
    write_data_row(ws4, t[:13], "DBEAFE", "1D4ED8")
set_col_widths(ws4, WIDTHS_13)

# Sheet 5: In Progress
ws5 = wb.create_sheet("In Progress")
write_header_row(ws5, HEADERS_13, "15803D")
for t in IN_PROGRESS:
    write_data_row(ws5, t[:13], "DCFCE7", "15803D")
set_col_widths(ws5, WIDTHS_13)

# Sheet 6: On Hold
ws6 = wb.create_sheet("On Hold")
write_header_row(ws6, HEADERS_14, "B45309")
for t in ON_HOLD:
    write_data_row(ws6, t, "FEF9C3", "B45309")
set_col_widths(ws6, WIDTHS_14)

# Sheet 7: Awaiting Resolution
ws7 = wb.create_sheet("Awaiting Resolution")
write_header_row(ws7, HEADERS_14, "6D28D9")
for t in ARC:
    write_data_row(ws7, t, "EDE9FE", "6D28D9")
set_col_widths(ws7, WIDTHS_14)

# Sheet 8: L2 Tickets
ws8 = wb.create_sheet("L2 Tickets")
write_header_row(ws8, HEADERS_14, "6D28D9")
for t in ALL_TICKETS:
    if t[0] in L2_IDS:
        write_data_row(ws8, t, "EDE9FE", "6D28D9")
set_col_widths(ws8, WIDTHS_14)

# Sheet 9: Aging View
ws9 = wb.create_sheet("Aging View")
write_header_row(ws9, HEADERS_14, "1E293B")
BUCKET_ORDER = ["30d+","15-30d","8-14d","0-7d"]
BUCKET_FILL_MAP = {"30d+":"FEE2E2","15-30d":"FEF3C7","8-14d":"FEFCE8","0-7d":"F0FDF4"}
BUCKET_FONT_MAP = {"30d+":"B91C1C","15-30d":"B45309","8-14d":"713F12","0-7d":"14532D"}
for bucket in BUCKET_ORDER:
    ws9.append([bucket]+[""]*13)
    r = ws9.max_row
    ws9.row_dimensions[r].height = 22
    for c in range(1,15):
        cell = ws9.cell(r,c)
        cell.fill = hex_fill(BUCKET_FILL_MAP[bucket])
        cell.font = Font(bold=True, color=BUCKET_FONT_MAP[bucket], size=10)
        cell.alignment = Alignment(vertical="center")
    for t in ALL_TICKETS:
        if t[8] == bucket:
            write_data_row(ws9, t, "FFFFFF", "000000")
set_col_widths(ws9, WIDTHS_14)

out = "/home/user/GD/CS_Daily_Incident_Report_20260615.xlsx"
wb.save(out)
print(f"Saved: {out}")
