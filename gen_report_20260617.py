"""
Generate CS Daily Incident Report for 2026-06-17.
Live data fetched from Zoho Desk MCP (Open/IP/OH/ARC).
Pentagon auto-notification tickets (clouddesk@pentagon.co.in) excluded as noise.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "azure-function"))

from datetime import date
from report_generator import generate_html, generate_excel

TODAY = date(2026, 6, 17)

# ---------------------------------------------------------------------------
# Raw ticket data (49 tickets after filtering Pentagon noise)
# ---------------------------------------------------------------------------
TICKETS = [
    # ── OPEN (8) ────────────────────────────────────────────────────────────
    {"num":"217606","subject":"Login Issue with CoreStack Tool",
     "priority":"Normal","account":"Otsuka","band":"Gold","ado":"",
     "created_date":date(2026,6,4),"last_updated":"17 Jun 2026",
     "contact":"Rajkumar U","assignee":"Ganga Reddy","status":"Open","reason":"","team":"L1"},
    {"num":"219258","subject":"Firing: [High Priority] MSProd App Server Memory Utilisation above 90%",
     "priority":"Normal","account":"CoreStack SRE","band":"Bronze","ado":"",
     "created_date":date(2026,6,8),"last_updated":"08 Jun 2026",
     "contact":"SRE Monitor","assignee":"Unassigned","status":"Open","reason":"","team":"L1"},
    {"num":"219898","subject":"Deployment Status Confirmation Required",
     "priority":"Normal","account":"Cloud Kinetics","band":"Silver","ado":"",
     "created_date":date(2026,6,10),"last_updated":"17 Jun 2026",
     "contact":"Cloud Kinetics SA","assignee":"PremKumar B","status":"Open","reason":"","team":"L1"},
    {"num":"220999","subject":"Request for Investigation – OCI Cost Processing and Cost Optimizer Issues",
     "priority":"Normal","account":"Core42","band":"Bronze","ado":"",
     "created_date":date(2026,6,12),"last_updated":"17 Jun 2026",
     "contact":"Muthu D","assignee":"PremKumar B","status":"Open","reason":"","team":"L1"},
    {"num":"222219","subject":"Request for Azure DevOps Cost Details at Resource Level",
     "priority":"Normal","account":"Otsuka","band":"Gold","ado":"",
     "created_date":date(2026,6,15),"last_updated":"16 Jun 2026",
     "contact":"Rajkumar U","assignee":"Nithin Ram","status":"Open","reason":"","team":"L1"},
    {"num":"222287","subject":"Confirmation Request – AI (LLM) Cost Details",
     "priority":"Normal","account":"Otsuka","band":"Gold","ado":"",
     "created_date":date(2026,6,15),"last_updated":"16 Jun 2026",
     "contact":"Rajkumar U","assignee":"Nithin Ram","status":"Open","reason":"","team":"L1"},
    {"num":"223020","subject":"Firing: [Critical] MSProd-graphdb-01 server load average above 2",
     "priority":"Normal","account":"CoreStack SRE","band":"Bronze","ado":"",
     "created_date":date(2026,6,17),"last_updated":"17 Jun 2026",
     "contact":"SRE Monitor","assignee":"Avinash Naidu","status":"Open","reason":"","team":"L1"},
    {"num":"223026","subject":"Resolved: [Critical] MSProd-graphdb-01 server load average above 2",
     "priority":"Normal","account":"CoreStack SRE","band":"Bronze","ado":"",
     "created_date":date(2026,6,17),"last_updated":"17 Jun 2026",
     "contact":"SRE Monitor","assignee":"Avinash Naidu","status":"Open","reason":"","team":"L1"},

    # ── IN PROGRESS (20) ────────────────────────────────────────────────────
    {"num":"222922","subject":"Memory Spike in GEV Dedicated Prod Environment",
     "priority":"Normal","account":"GE Vernova","band":"Bronze","ado":"",
     "created_date":date(2026,6,17),"last_updated":"17 Jun 2026",
     "contact":"Vijaykumar P","assignee":"Avinash Naidu","status":"In Progress","reason":"","team":"L1"},
    {"num":"222173","subject":"PoV Exide: Unable to execute CIS compliance standard",
     "priority":"Normal","account":"Exide","band":"Bronze","ado":"",
     "created_date":date(2026,6,15),"last_updated":"17 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"222571","subject":"Re: CoreStack - FinOps. Call",
     "priority":"High","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,16),"last_updated":"17 Jun 2026",
     "contact":"Deovrat S","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"222547","subject":"Request for Review of Optimization Recommendations (SKU Marked as NA)",
     "priority":"Normal","account":"Otsuka","band":"Gold","ado":"",
     "created_date":date(2026,6,16),"last_updated":"16 Jun 2026",
     "contact":"Rajkumar U","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"222218","subject":"Enable FinOps Governance Summary Report | QapiPlus",
     "priority":"Normal","account":"Aliando","band":"Bronze","ado":"",
     "created_date":date(2026,6,15),"last_updated":"16 Jun 2026",
     "contact":"Ajit T","assignee":"Nithin Ram","status":"In Progress","reason":"","team":"L1"},
    {"num":"222619","subject":"FinOps Governance Summary Report | Month field not able to select",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,16),"last_updated":"16 Jun 2026",
     "contact":"Jayven C","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"219593","subject":"Issue with Budget Report Month Selection and Financial Year Setup",
     "priority":"Normal","account":"Microland","band":"Bronze","ado":"",
     "created_date":date(2026,6,9),"last_updated":"16 Jun 2026",
     "contact":"Senapathi R","assignee":"PremKumar B","status":"In Progress","reason":"","team":"L1"},
    {"num":"222463","subject":"Mismatch in Cost Figures Between Azure Cost Management and CoreStack FinOps",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,16),"last_updated":"16 Jun 2026",
     "contact":"Thadi S","assignee":"Avinash Naidu","status":"In Progress","reason":"","team":"L1"},
    {"num":"222461","subject":"Kyndryl SaaS Okta SSO Configuration",
     "priority":"Normal","account":"Kyndryl","band":"Gold","ado":"",
     "created_date":date(2026,6,16),"last_updated":"16 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Avinash Naidu","status":"In Progress","reason":"","team":"L1"},
    {"num":"222257","subject":"Arcera - Replace PAYG to CSP Onboarding",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,15),"last_updated":"15 Jun 2026",
     "contact":"Krishnakumar VJ","assignee":"Nithin Ram","status":"In Progress","reason":"","team":"L1"},
    {"num":"222040","subject":"Billing Amount Difference between GCP and CoreStack",
     "priority":"Normal","account":"LTTS","band":"Bronze","ado":"",
     "created_date":date(2026,6,15),"last_updated":"15 Jun 2026",
     "contact":"Kaustubh M","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"222003","subject":"SHI Locuz - Need Assistance in Compliance Execution & Scheduling",
     "priority":"Normal","account":"SHI Locuz","band":"Bronze","ado":"",
     "created_date":date(2026,6,15),"last_updated":"15 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Deepesh H","status":"In Progress","reason":"","team":"L1"},
    {"num":"220546","subject":"ODP/Blackstone - Bus Patrol",
     "priority":"Normal","account":"Blackstone","band":"Bronze","ado":"",
     "created_date":date(2026,6,11),"last_updated":"11 Jun 2026",
     "contact":"Jayven C","assignee":"Nithin Ram","status":"In Progress","reason":"","team":"L1"},
    {"num":"220105","subject":"Merged cells in cost recommendation Report",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,10),"last_updated":"10 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"PremKumar B","status":"In Progress","reason":"","team":"L1"},
    {"num":"219541","subject":"Trustech - FinOps not triggered",
     "priority":"High","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,9),"last_updated":"09 Jun 2026",
     "contact":"Krishnakumar VJ","assignee":"Ganga Reddy","status":"In Progress","reason":"","team":"L1"},
    {"num":"216750","subject":"FW: Production Environment | IFoundry5X",
     "priority":"Normal","account":"Tata Communications","band":"Gold","ado":"",
     "created_date":date(2026,6,2),"last_updated":"09 Jun 2026",
     "contact":"Sunilkumar S","assignee":"PremKumar B","status":"In Progress","reason":"","team":"L1"},
    {"num":"216808","subject":"Difference Between CoreStack Recommendation and Azure Calculator Pricing",
     "priority":"Normal","account":"Kyndryl","band":"Gold","ado":"",
     "created_date":date(2026,6,2),"last_updated":"04 Jun 2026",
     "contact":"Randhir K","assignee":"PremKumar B","status":"In Progress","reason":"","team":"L1"},
    {"num":"217515","subject":"FW: Cost Mismatch in recommendation (Kyndryl)",
     "priority":"Normal","account":"Kyndryl","band":"Gold","ado":"",
     "created_date":date(2026,6,4),"last_updated":"04 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Ganga Reddy","status":"In Progress","reason":"","team":"L1"},
    {"num":"211192","subject":"FinOps Email Notification Issue (Clone)",
     "priority":"Normal","account":"Tata Communications","band":"Gold","ado":"",
     "created_date":date(2026,5,19),"last_updated":"19 May 2026",
     "contact":"Sunilkumar S","assignee":"PremKumar B","status":"In Progress","reason":"","team":"L1"},
    {"num":"206833","subject":"Mar26 usage for Mitsui Chemicals",
     "priority":"Normal","account":"Synoptek","band":"Gold","ado":"",
     "created_date":date(2026,5,7),"last_updated":"07 May 2026",
     "contact":"S Zborowski","assignee":"Nithin Ram","status":"In Progress","reason":"","team":"L1"},

    # ── ON HOLD (10) ────────────────────────────────────────────────────────
    {"num":"211893","subject":"Re: Core stock FinOps Dashboard cost differ",
     "priority":"High","account":"Neurealm","band":"Platinum","ado":"",
     "created_date":date(2026,5,21),"last_updated":"15 Jun 2026",
     "contact":"Parthasarathy K","assignee":"Avinash Naidu","status":"On Hold","reason":"","team":"L1"},
    {"num":"211895","subject":"Re: Core stock FinOps Dashboard cost differ for GCP",
     "priority":"Normal","account":"Neurealm","band":"Platinum","ado":"",
     "created_date":date(2026,5,21),"last_updated":"15 Jun 2026",
     "contact":"Parthasarathy K","assignee":"Nithin Ram","status":"On Hold","reason":"","team":"L1"},
    {"num":"220491","subject":"FW: Resources Cost - Beside Tagged and untagged - LifeLabs",
     "priority":"Normal","account":"LifeLabs","band":"Bronze","ado":"",
     "created_date":date(2026,6,11),"last_updated":"15 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Avinash Naidu","status":"On Hold","reason":"","team":"L1"},
    {"num":"219147","subject":"RE: CUR Backfill",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,8),"last_updated":"13 Jun 2026",
     "contact":"Raghavan P","assignee":"Nithin Ram","status":"On Hold","reason":"","team":"L1"},
    {"num":"217990","subject":"cloud.corestack.io is slow across all pages",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,5),"last_updated":"12 Jun 2026",
     "contact":"Satya C","assignee":"Ganga Reddy","status":"On Hold","reason":"","team":"L1"},
    {"num":"205888","subject":"Need assistance to update creds for EA account for Trinity College",
     "priority":"High","account":"Logicalis","band":"Gold","ado":"",
     "created_date":date(2026,5,5),"last_updated":"12 Jun 2026",
     "contact":"Kamran W","assignee":"PremKumar B","status":"On Hold","reason":"","team":"L1"},
    {"num":"217785","subject":"RDS Snapshot Not Created on May 31",
     "priority":"Normal","account":"Cloud Kinetics","band":"Silver","ado":"",
     "created_date":date(2026,6,5),"last_updated":"11 Jun 2026",
     "contact":"Cloud Kinetics SA","assignee":"Gnanadesigan A","status":"On Hold","reason":"","team":"L1"},
    {"num":"217961","subject":"Sonata - CSP accounts not showing up",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,5),"last_updated":"09 Jun 2026",
     "contact":"Deovrat S","assignee":"PremKumar B","status":"On Hold","reason":"","team":"L1"},
    {"num":"219360","subject":"cloud.corestack.io",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,8),"last_updated":"08 Jun 2026",
     "contact":"Satya C","assignee":"Nithin Ram","status":"On Hold","reason":"","team":"L1"},
    {"num":"211954","subject":"AWS Accounts transfer from INH to ISO Tenant",
     "priority":"Normal","account":"Otsuka","band":"Gold","ado":"",
     "created_date":date(2026,5,21),"last_updated":"22 May 2026",
     "contact":"Rajkumar U","assignee":"Aadhithya S","status":"On Hold","reason":"","team":"L1"},

    # ── AWAITING RESOLUTION CONFIRMATION (11) ───────────────────────────────
    {"num":"222615","subject":"Unable to login in Logicalis Cloud Management Portal (CMP)",
     "priority":"Normal","account":"Logicalis","band":"Gold","ado":"",
     "created_date":date(2026,6,16),"last_updated":"17 Jun 2026",
     "contact":"Julio A","assignee":"Ganga Reddy","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"222631","subject":"Taylor Farms - Graphion SBOM workflow - Infra scans getting skipped",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,16),"last_updated":"16 Jun 2026",
     "contact":"A Bagchi","assignee":"Ganga Reddy","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"220875","subject":"Dashboard slowness",
     "priority":"High","account":"Synopsys","band":"Gold","ado":"",
     "created_date":date(2026,6,12),"last_updated":"15 Jun 2026",
     "contact":"Ranjitha T","assignee":"Ganga Reddy","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"221054","subject":"US SaaS - Kyndryl - Default dashboards not visible for tenant/finops_admin",
     "priority":"Normal","account":"Kyndryl","band":"Gold","ado":"",
     "created_date":date(2026,6,12),"last_updated":"12 Jun 2026",
     "contact":"Nagalakshmi N","assignee":"Nithin Ram","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"220416","subject":"Sonata - Tata Tele CSP processing issue",
     "priority":"High","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,11),"last_updated":"12 Jun 2026",
     "contact":"Deovrat S","assignee":"PremKumar B","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"220165","subject":"Trustedtech - HMH - cost for April",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,10),"last_updated":"10 Jun 2026",
     "contact":"Krishnakumar VJ","assignee":"Nithin Ram","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"219989","subject":"Re: Corestack",
     "priority":"Normal","account":"Sonata Software","band":"Bronze","ado":"",
     "created_date":date(2026,6,10),"last_updated":"10 Jun 2026",
     "contact":"Deovrat S","assignee":"PremKumar B","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"219658","subject":"US Prod - Dashboard Not Loading",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,9),"last_updated":"09 Jun 2026",
     "contact":"Ashokkumar E","assignee":"Nithin Ram","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"219377","subject":"ODP Corporation MCA Billing Account cost processing errors",
     "priority":"Normal","account":"Blackstone","band":"Bronze","ado":"",
     "created_date":date(2026,6,8),"last_updated":"08 Jun 2026",
     "contact":"Jayven C","assignee":"Nithin Ram","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"219361","subject":"Filtrona | FinOps Dashboard | Unallocated Resource Groups",
     "priority":"Normal","account":"Getronics","band":"Silver","ado":"",
     "created_date":date(2026,6,8),"last_updated":"08 Jun 2026",
     "contact":"Shashank N","assignee":"Nithin Ram","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
    {"num":"216586","subject":"Unable to onboard Snowflake in CS4CS",
     "priority":"Normal","account":"CoreStack","band":"Bronze","ado":"",
     "created_date":date(2026,6,1),"last_updated":"05 Jun 2026",
     "contact":"A Bagchi","assignee":"Ganga Reddy","status":"Awaiting Resolution Confirmation","reason":"","team":"L1"},
]


def _age(t):
    return (TODAY - t["created_date"]).days

def _bucket(a):
    if a <= 7:  return "0-7d"
    if a <= 14: return "8-14d"
    if a <= 30: return "15-30d"
    return "30d+"

def _row_bg(status, bkt):
    if status == "On Hold" and bkt == "30d+":                  return "#FFF0F0"
    if status == "On Hold" and bkt in ("8-14d","15-30d"):      return "#FFFBF0"
    if status == "In Progress" and bkt == "8-14d":             return "#FEFFF0"
    return "#FFFFFF"


def build_tickets():
    out = []
    for t in TICKETS:
        a = _age(t)
        b = _bucket(a)
        d = dict(t)
        # normalise field names to match report_generator expectations
        if "account" in d and "display" not in d:
            d["display"] = d.pop("account")
        elif "account" in d:
            d.pop("account")
        # convert priority to P-format used by report_generator
        _pri_map = {"Critical": "P1", "High": "P2", "Normal": "P3", "Low": "P4"}
        if not d.get("priority", "").startswith("P"):
            d["priority"] = _pri_map.get(d.get("priority", "Normal"), "P3")
        d["age"]    = a
        d["bucket"] = b
        d["created_str"] = d["created_date"].isoformat()
        out.append(d)
    return out


if __name__ == "__main__":
    tickets = build_tickets()

    html_bytes = generate_html(tickets, TODAY).encode("utf-8")
    xlsx_bytes = generate_excel(tickets, TODAY)

    html_path = f"CS_Daily_Incident_Report_{TODAY.strftime('%Y%m%d')}.html"
    xlsx_path = f"CS_Daily_Incident_Report_{TODAY.strftime('%Y%m%d')}.xlsx"

    with open(html_path, "wb") as f:
        f.write(html_bytes)
    with open(xlsx_path, "wb") as f:
        f.write(xlsx_bytes)

    open_c  = sum(1 for t in tickets if t["status"] == "Open")
    ip_c    = sum(1 for t in tickets if t["status"] == "In Progress")
    oh_c    = sum(1 for t in tickets if t["status"] == "On Hold")
    arc_c   = sum(1 for t in tickets if t["status"] == "Awaiting Resolution Confirmation")
    print(f"Tickets: Open={open_c}  IP={ip_c}  OH={oh_c}  ARC={arc_c}  Total={len(tickets)}")
    print(f"Written: {html_path}, {xlsx_path}")
