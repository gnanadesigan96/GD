"""Single source of truth for Athi Shree V's resume content.

Both the PDF and the DOCX are generated from this file, so the two formats
always carry identical, ATS-parsable text.
"""

NAME = "ATHI SHREE V"
TITLE = "L3 Active Directory & Microsoft Entra ID Administrator"
CONTACT = [
    "Chennai, India",
    "+91 63795 44624",
    "vathishree@gmail.com",
    "linkedin.com/in/athisree-venkat-845660190",
]

SUMMARY = (
    "Active Directory and Microsoft Entra ID (Azure AD) Administrator with 3.8 years of experience in "
    "Identity and Access Management (IAM) for banking and life-sciences enterprises. Supports 10,000+ users "
    "and 50+ Domain Controllers, specializing in AD replication, Group Policy, DNS, DHCP, hybrid identity, "
    "SSO, MFA and Conditional Access. Microsoft Certified: Identity and Access Administrator (SC-300)."
)

SKILLS = [
    ("Active Directory",
     "AD DS, Domain Controllers, AD Sites and Services, Replication, Group Policy (GPO), LDAP, Kerberos, "
     "OUs, Delegation"),
    ("Microsoft Entra ID",
     "Azure AD, Entra Connect, Hybrid Identity, Conditional Access, MFA, SAML SSO, RBAC, Enterprise Apps"),
    ("Infrastructure",
     "Windows Server, DNS, DHCP, NTFS Permissions, Exchange Online, Microsoft 365"),
    ("Tools & Processes",
     "PowerShell, Incident Management, Change Management, Patching, Disaster Recovery"),
]

JOB_TITLE = "Active Directory Administrator"
EMPLOYER = "Cognizant Technology Solutions"
EMPLOYER_DETAIL = "Associate | Chennai, India"
EMPLOYER_DATES = "Dec 2022 – Present"

PROJECTS = [
    {
        "client": "Synchrony Bank",
        "role": "L3 Active Directory Administrator",
        "dates": "Current",
        "bullets": [
            "Administer Active Directory for 10,000+ user accounts, resolving L3 identity and access escalations.",
            "Monitor health and replication of 50+ Domain Controllers across multiple AD sites.",
            "Optimize Group Policy processing and security baselines for domain-joined users and computers.",
            "Resolve LDAP, Kerberos/SPN, ACL and service-account issues that block application sign-in.",
            "Deliver Entra ID feature requests for enterprise apps, Conditional Access and RBAC, from design "
            "to closure.",
        ],
    },
    {
        "client": "Gilead Sciences",
        "role": "L2 Active Directory Administrator",
        "dates": "Previous",
        "bullets": [
            "Provisioned user and service accounts, groups and OUs using least-privilege delegation.",
            "Maintained Domain Controllers, AD-integrated DNS and replication; diagnosed authentication failures.",
            "Rolled out MFA, Conditional Access and group-based licensing in Microsoft Entra ID.",
            "Configured SAML single sign-on and Entra Connect hybrid synchronization.",
            "Ran DNS and DHCP operations: zones, forwarders, scopes, reservations and failover.",
        ],
    },
]

CERTIFICATIONS = [
    "Microsoft Certified: Identity and Access Administrator Associate (SC-300)",
    "Microsoft Certified: Azure Data Fundamentals (DP-900)",
]

# (degree, school, year, grade)
EDUCATION = [
    ("B.E., Computer Science and Engineering",
     "Sri Venkateswara College of Engineering", "2018 – 2022", "CGPA 9.23/10"),
]

ACHIEVEMENTS = [
    "Rising Star special mention for ticket resolution and team collaboration.",
    "Top ticket-closure contributor in the core IT support team.",
    "Mentored new IT support hires on procedures and support workflows.",
]
