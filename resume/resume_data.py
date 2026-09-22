"""Single source of truth for Athi Shree V's resume content.

Both the PDF (via HTML) and the DOCX are generated from this file, so the
two formats always carry identical, ATS-parsable text.
"""

NAME = "ATHI SHREE V"
TITLE = "Active Directory & Microsoft Entra ID (Azure AD) Administrator | Identity & Access Management (IAM)"
CONTACT = [
    "+91 63795 44624",
    "vathishree@gmail.com",
    "linkedin.com/in/athisree-venkat-845660190",
]

SUMMARY = (
    "Active Directory and Microsoft Entra ID (Azure AD) Administrator with 3.8 years of experience in "
    "enterprise Identity and Access Management (IAM) for global banking and life-sciences clients. "
    "L2/L3 expertise in AD DS, Domain Controllers, AD replication, Group Policy (GPO), DNS, DHCP and LDAP, "
    "plus hybrid identity with Microsoft Entra Connect, SAML SSO, MFA, Conditional Access and RBAC. "
    "SC-300 certified; uses PowerShell and disciplined incident and change management to keep access secure."
)

SKILLS = [
    ("Identity & Directory Services",
     "Active Directory (AD DS), Microsoft Entra ID (Azure AD), Domain Controllers, AD Sites and Services, "
     "AD Replication, LDAP, Organizational Units (OUs), Security & Distribution Groups, Service Accounts, "
     "Delegation, ACLs, SPN / Kerberos"),
    ("Access Management & Security",
     "Identity and Access Management (IAM), Multi-Factor Authentication (MFA), Conditional Access, "
     "SAML, Single Sign-On (SSO), Role-Based Access Control (RBAC), Enterprise Applications, "
     "Group-Based Licensing, Sign-in & Audit Logs, Least Privilege"),
    ("Hybrid Identity & Cloud",
     "Microsoft Entra Connect (Azure AD Connect), Hybrid Identity, Microsoft 365, Exchange Online, "
     "Microsoft Azure"),
    ("Windows Server Infrastructure",
     "DNS (Zones, Records, Conditional Forwarders, Zone Transfers), DHCP (Scopes, Reservations, Failover), "
     "Group Policy (GPO), File Share & NTFS Permissions"),
    ("Automation & IT Operations",
     "PowerShell Scripting, Incident Management, Change Management, Patching, Disaster Recovery (DR), "
     "Root Cause Analysis, L2/L3 Troubleshooting"),
]

EMPLOYER = "Cognizant Technology Solutions"
EMPLOYER_ROLE = "Associate"
EMPLOYER_DATES = "Dec 2022 – Present"

PROJECTS = [
    {
        "client": "Synchrony Bank",
        "role": "L3 Active Directory Administrator",
        "dates": "Current Project",
        "bullets": [
            "Deliver L3 Active Directory administration and advanced troubleshooting, managing Domain Controller "
            "health, AD replication, authentication and core AD DS services across the enterprise.",
            "Administer Group Policy (GPO): troubleshoot, validate and optimize policy application and "
            "security settings across the domain.",
            "Maintain AD Sites and Services, subnets and replication topology to ensure reliable domain "
            "connectivity and authentication across locations.",
            "Troubleshoot LDAP authentication, AD security permissions (ACLs), delegation, service accounts "
            "and SPN / Kerberos-related access issues.",
            "Support Microsoft Entra ID (Azure AD) enterprise application access, Conditional Access policies "
            "and RBAC role assignments.",
            "Handle incident and change activities end to end for security-focused access requests, "
            "coordinating validation, implementation and closure.",
        ],
    },
    {
        "client": "Gilead Sciences",
        "role": "L2 Active Directory Administrator",
        "dates": "Previous Project",
        "bullets": [
            "Provisioned and managed AD user and service accounts, security and distribution groups, OUs and "
            "delegated access in line with security policies and least-privilege principles.",
            "Administered Domain Controllers, DNS integration and AD replication; investigated and resolved "
            "authentication and replication issues.",
            "Created, maintained and troubleshot Group Policy Objects (GPOs) to enforce security standards.",
            "Managed Microsoft Entra ID users and groups; implemented MFA, Conditional Access and group-based "
            "license provisioning.",
            "Configured SAML Single Sign-On (SSO) and Microsoft Entra Connect for hybrid identity; reviewed "
            "audit and sign-in logs to secure access.",
            "Administered DNS and DHCP (records, conditional forwarders, zone transfers, scopes, reservations, "
            "failover), file share and RBAC permissions, and Exchange Online mailboxes and mail flow.",
        ],
    },
]

ACHIEVEMENTS = [
    "Recognized as a top ticket-closure contributor in the core IT support team and received the "
    "Women Rising Star special mention for ticket resolution and team collaboration.",
    "Collaborated with automation teams to streamline recurring service requests and improve operational "
    "efficiency.",
    "Trained and mentored new IT support hires on technical procedures and support workflows.",
]

EDUCATION = [
    ("B.E., Computer Science and Engineering",
     "Sri Venkateswara College of Engineering", "2018 – 2022", "CGPA: 9.23 / 10"),
    ("Higher Secondary (HSLC)",
     "Holy Cross Anglo Indian Higher Secondary School", "2016 – 2018", "Score: 86%"),
]

CERTIFICATIONS = [
    "Microsoft Certified: Identity and Access Administrator Associate (SC-300)",
    "Microsoft Certified: Azure Data Fundamentals (DP-900)",
]
