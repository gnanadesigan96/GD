"""Single source of truth for Athi Shree V's resume content.

Both the PDF and the DOCX are generated from this file, so the two formats
always carry identical, ATS-parsable text.
"""

NAME = "ATHI SHREE V"
TITLE = "Active Directory & Microsoft Entra ID Administrator | Identity & Access Management (IAM)"
CONTACT = [
    "Chennai, India",
    "+91 63795 44624",
    "vathishree@gmail.com",
    "linkedin.com/in/athisree-venkat-845660190",
]

SUMMARY = (
    "Active Directory and Microsoft Entra ID (Azure AD) Administrator with 3.8 years of experience in "
    "enterprise Identity and Access Management (IAM) for global banking and life-sciences clients, supporting "
    "10,000+ users, 50+ Domain Controllers and 50+ AD sites. L2/L3 expertise in AD DS, AD replication, Group Policy (GPO), "
    "DNS, DHCP and LDAP, plus hybrid identity with Microsoft Entra Connect, SAML SSO, MFA, Conditional Access "
    "and RBAC. SC-300 certified; uses PowerShell, ServiceNow and Splunk to deliver secure, well-controlled "
    "incident and change management."
)

SKILLS = [
    ("Identity & Directory",
     "Active Directory (AD DS), Entra ID (Azure AD), Domain Controllers, AD Sites and Services, "
     "AD Replication, LDAP, OUs, Security & Distribution Groups, Service Accounts, Delegation, ACLs, "
     "SPN/Kerberos"),
    ("Access & Security",
     "IAM, Multi-Factor Authentication (MFA), Conditional Access, SAML, Single Sign-On (SSO), RBAC, "
     "Enterprise Applications, Group-Based Licensing, Sign-in & Audit Logs, Least Privilege"),
    ("Hybrid & Cloud",
     "Microsoft Entra Connect (Azure AD Connect), Hybrid Identity, Microsoft 365, Exchange Online, "
     "Azure"),
    ("Windows Infrastructure",
     "Windows Server, DNS (Zones, Records, Conditional Forwarders, Zone Transfers), DHCP (Scopes, Reservations, Failover), "
     "Group Policy (GPO), File Share & NTFS Permissions"),
    ("Tools & Platforms",
     "ServiceNow, Splunk, New Relic, PagerDuty, SailPoint (Identity Governance), Quest Change Auditor, Citrix, "
     "PowerShell"),
    ("IT Operations",
     "Incident & Change Management, Patching, DR, Root Cause Analysis, "
     "L2/L3 Troubleshooting"),
]

JOB_TITLE = "Active Directory Administrator"
EMPLOYER = "Cognizant Technology Solutions"
EMPLOYER_DETAIL = "Associate | Chennai, India"
EMPLOYER_DATES = "Dec 2022 – Present"

PROJECTS = [
    {
        "client": "Synchrony Bank",
        "role": "L3 Active Directory Administrator",
        "dates": "Current Project",
        "bullets": [
            "Deliver L3 Active Directory administration for 10,000+ users, resolving identity and access "
            "escalations.",
            "Manage health, replication and authentication across 50+ Domain Controllers and core AD DS services.",
            "Administer Group Policy, including the Default Domain Controllers Policy: troubleshoot, validate "
            "and optimize security settings.",
            "Maintain AD Sites and Services, subnets and replication topology across 50+ AD sites.",
            "Troubleshoot LDAP authentication, ACLs, delegation, service accounts and SPN / Kerberos access issues.",
            "Support Microsoft Entra ID enterprise application access, Conditional Access policies and RBAC roles.",
            "Handle incident and change activities for security access requests, resolving them within SLA.",
        ],
    },
    {
        "client": "Gilead Sciences",
        "role": "L2 Active Directory Administrator",
        "dates": "Previous Project",
        "bullets": [
            "Provisioned AD user/service accounts, security and distribution groups, OUs and delegated access.",
            "Administered Domain Controllers, DNS integration and AD replication; resolved authentication and "
            "replication issues.",
            "Created, maintained and troubleshot Windows Group Policy Objects (GPOs) to enforce security standards.",
            "Rolled out MFA to 300+ users; managed Entra ID users, groups, Conditional Access and group-based "
            "licensing.",
            "Configured SAML single sign-on for 4 enterprise applications and Entra Connect for hybrid identity.",
            "Ran DNS and DHCP operations (records, forwarders, zone transfers, scopes, reservations, failover).",
            "Controlled file-share and RBAC permissions; supported Exchange Online mailboxes and mail flow.",
        ],
    },
]

CERTIFICATIONS = [
    "Microsoft Certified: Identity and Access Administrator Associate (SC-300)",
    "Microsoft Certified: Azure Data Fundamentals (DP-900)",
]

# (degree, school, dates, grade)
EDUCATION = [
    ("B.E., Computer Science and Engineering",
     "Sri Venkateswara College of Engineering", "2018 – 2022", "CGPA: 9.23 / 10"),
    ("Higher Secondary (HSLC)",
     "Holy Cross Anglo Indian Higher Secondary School", "2016 – 2018", "Score: 86%"),
]

ACHIEVEMENTS = [
    "Top ticket-closure contributor in the core IT support team for fast, effective issue resolution.",
    "Received the Women Rising Star special mention for ticket resolution and team collaboration.",
    "Collaborated with automation teams to streamline recurring service requests and improve efficiency.",
    "Trained and mentored new IT support hires on technical procedures and support workflows.",
]
