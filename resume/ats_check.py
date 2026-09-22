"""Score resume PDFs the way ATS checkers do.

Usage:  python3 ats_check.py [file.pdf ...]   (defaults to every *_Resume_*.pdf here)
Needs:  pip install pymupdf

This is an independent approximation, not the scoring of any commercial
tool (Enhancv, Jobscan, ...). It reads only what a parser can extract from the
PDF, then scores six categories (100 points total):

  Parseability 20 | Contact info 10 | Sections 15 | Keywords 30 |
  Quantified impact 15 | Bullet quality 10

Keywords are compared against a typical job description for an Active
Directory / Microsoft Entra ID administrator. Real ATS match against each
specific job posting, so tailor the Summary and Skills for each application.
"""

import glob
import os
import re
import sys

import pymupdf

# Keywords that commonly appear in AD / Entra ID / IAM administrator postings.
# Each entry: display name -> regex alternatives (case-insensitive).
JD_KEYWORDS = {
    "Active Directory": r"active directory",
    "Microsoft Entra ID": r"entra id",
    "Azure AD": r"azure ad|azure active directory",
    "Domain Controllers": r"domain controller",
    "Group Policy / GPO": r"group policy|\bgpo",
    "AD Replication": r"replication",
    "AD Sites and Services": r"sites and services",
    "DNS": r"\bdns\b",
    "DHCP": r"\bdhcp\b",
    "LDAP": r"\bldap\b",
    "Kerberos": r"kerberos",
    "Entra Connect / AD Connect": r"entra connect|ad connect",
    "Hybrid Identity": r"hybrid identity",
    "Single Sign-On (SSO)": r"\bsso\b|single sign-on",
    "SAML": r"\bsaml\b",
    "MFA": r"\bmfa\b|multi-factor",
    "Conditional Access": r"conditional access",
    "RBAC": r"\brbac\b|role-based access",
    "IAM": r"\biam\b|identity and access management",
    "Least Privilege": r"least[- ]privilege",
    "Service Accounts": r"service account",
    "Organizational Units (OUs)": r"\bous?\b|organizational unit",
    "Audit / Sign-in Logs": r"audit",
    "PowerShell": r"powershell",
    "Windows Server": r"windows server",
    "Exchange Online": r"exchange online",
    "Microsoft 365": r"microsoft 365|office 365|\bm365\b",
    "ServiceNow": r"servicenow",
    "SailPoint": r"sailpoint",
    "Splunk": r"splunk",
    "Incident Management": r"incident",
    "Change Management": r"change management|change activities",
    "Troubleshooting": r"troubleshoot",
    "Disaster Recovery": r"disaster recovery|\bdr\b",
    # Common in postings but only add these if they are true for you:
    "Privileged Access (PIM/PAM)": r"\bpim\b|\bpam\b|privileged",
    "ITIL": r"\bitil\b",
    "Microsoft Intune": r"intune",
    "Identity Governance": r"identity governance|access review",
}

SECTIONS = {
    "Summary": r"^(professional )?summary$|^profile$",
    "Skills": r"^(technical |core )?skills",
    "Experience": r"^(professional |work )?experience$",
    "Education": r"^education$",
    "Certifications": r"^certifications?$",
}

STANDARD_FONTS = ("Helvetica", "Arial", "Times", "Calibri", "Georgia", "Garamond", "Cambria", "Liberation")


def experience_bullets(lines):
    """Join wrapped lines into whole bullets inside the Experience section."""
    out, inside, cur = [], False, None
    for ln in lines:
        s = ln.strip()
        if re.match(SECTIONS["Experience"], s, re.I):
            inside = True
            continue
        if inside and s.isupper() and len(s) > 3:
            break
        if not inside:
            continue
        if s.startswith("•"):
            if cur:
                out.append(cur)
            cur = s.lstrip("• ").strip()
        elif cur is not None and s and not s.startswith("Client:"):
            cur += " " + s
        else:
            if cur:
                out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return out


def score(path):
    doc = pymupdf.open(path)
    text = "\n".join(p.get_text() for p in doc)
    lines = [l for l in text.split("\n") if l.strip()]
    low = text.lower()
    report, total = [], 0.0

    # 1. Parseability (20)
    fonts = {f[3] for p in doc for f in p.get_fonts()}
    images = sum(len(p.get_images()) for p in doc)
    checks = [
        ("opens without repair", not doc.is_repaired),
        ("text layer present", len(text) > 500),
        ("standard fonts only", all(any(s in f for s in STANDARD_FONTS) for f in fonts)),
        ("no images or graphics text", images == 0),
        ("1-2 pages", len(doc) <= 2),
    ]
    pts = 4 * sum(ok for _, ok in checks)
    total += pts
    report.append(("Parseability", pts, 20, [n for n, ok in checks if not ok]))

    # 2. Contact information (10)
    checks = [
        ("email", re.search(r"[\w.+-]+@[\w-]+\.\w+", text)),
        ("phone", re.search(r"\+?\d[\d \-]{8,}\d", text)),
        ("LinkedIn", "linkedin.com/in/" in low),
        ("location", re.search(r"\b(india|chennai|bengaluru|hyderabad|pune)\b", low)),
    ]
    pts = 2.5 * sum(bool(ok) for _, ok in checks)
    total += pts
    report.append(("Contact info", pts, 10, [n for n, ok in checks if not ok]))

    # 3. Standard sections + dates (15)
    heads = [l.strip() for l in lines]
    missing = [n for n, rx in SECTIONS.items() if not any(re.match(rx, h, re.I) for h in heads)]
    has_dates = bool(re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]* \d{4}", low))
    pts = 2.5 * (len(SECTIONS) - len(missing)) + (2.5 if has_dates else 0)
    total += pts
    report.append(("Sections & dates", pts, 15, missing + ([] if has_dates else ["job dates"])))

    # 4. Keywords (30)
    found = [k for k, rx in JD_KEYWORDS.items() if re.search(rx, low)]
    miss = [k for k in JD_KEYWORDS if k not in found]
    pts = 30 * len(found) / len(JD_KEYWORDS)
    total += pts
    report.append(("Keywords", pts, 30, miss))

    # 5. Quantified impact (15): full marks when half the bullets carry a number
    bullets = experience_bullets(lines)
    quant = [b for b in bullets if re.search(r"\d", b)]
    ratio = len(quant) / max(len(bullets), 1)
    pts = 15 * min(1.0, ratio / 0.5)
    total += pts
    report.append(("Quantified impact", pts, 15,
                   [f"{len(quant)} of {len(bullets)} experience bullets contain a number"]))

    # 6. Bullet quality (10): varied opening verbs, sensible length
    firsts = [b.split()[0].lower() for b in bullets if b.split()]
    variety = len(set(firsts)) / max(len(firsts), 1)
    lengths = [len(b.split()) for b in bullets]
    good_len = sum(6 <= n <= 28 for n in lengths) / max(len(lengths), 1)
    pts = 5 * variety + 5 * good_len
    repeats = sorted({w for w in firsts if firsts.count(w) > 1})
    total += pts
    report.append(("Bullet quality", pts, 10,
                   [f"repeated opening verbs: {', '.join(repeats)}"] if repeats else []))

    return total, report, len(doc)


def main(paths):
    for path in paths:
        total, report, pages = score(path)
        print(f"\n{os.path.basename(path)}  ({pages} page{'s' if pages > 1 else ''})")
        print(f"  ATS SCORE: {total:.0f} / 100")
        for name, pts, out_of, notes in report:
            note = f"  -> {'; '.join(notes)}" if notes else ""
            print(f"  {name:<18} {pts:5.1f} / {out_of}{note}")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    main(sys.argv[1:] or sorted(glob.glob(os.path.join(here, "*_Resume_*.pdf"))))
