import os
import re
from datetime import datetime

from app.services.skill_extractor import SKILLS, extract_skills

# Global configurable flag for Tech-Only Job Discovery
TECH_ONLY = os.getenv("TECH_ONLY", "true").lower() in ("true", "1", "yes")

# Non-job / boilerplate navigation markers (Excluded - Tier 0)
NON_JOB_PATTERNS = [
    r"skip to main content",
    r"request an accommodation",
    r"interview tips",
    r"faqs?",
    r"transparency faqs?",
    r"learn more about our recruiting",
    r"^careers?$",
    r"^search jobs$",
    r"^explore careers?$",
    r"^privacy policy$",
    r"^terms of use$",
    r"^cookie policy$",
    r"^accessibility$",
    r"\b\d+\s+open\s+jobs\b",
    r"\bview\s+all\s+jobs\b",
    r"\bsee\s+all\s+jobs\b",
    r"\bsearch\s+open\s+jobs\b",
]

NON_JOB_URL_MARKERS = (
    "/forms/create",
    "/hiring-tips/",
    "/hiringfaqs",
    "/transparency",
    "/accessibility",
)

# Explicit non-technical primary roles.
# If these appear as the role title, the job is NOT a primary technical role,
# even if it mentions tech keywords (e.g. 'Inside Sales - Cyber Security', 'Marketing - AI Products', 'HR - Technology').
NON_TECH_ROLE_PATTERNS = [
    r"\b(?:inside\s+sales|outside\s+sales|sales\s+exec(?:utive)?|sales\s+rep(?:resentative)?|sales\s+manager|sales\s+director|telesales|account\s+exec(?:utive)?|business\s+development|presales|pre-sales|sales\s+lead|sales\s+operations|sales)\b",
    r"\b(?:marketing|brand|growth\s+lead|growth\s+manager|seo|content\s+writer|copywriter|social\s+media|public\s+relations|pr\s+specialist|communications\s+specialist)\b",
    r"\b(?:hr|human\s+resources|recruiter|recruiting|talent\s+acquisition|people\s+operations|people\s+partner|sourcer|headhunter|campus\s+recruiter)\b",
    r"\b(?:accountant|accounting|accounts\s+payable|accounts\s+receivable|bookkeeper|payroll|tax|audit|auditor|financial\s+reporting|record\s+to\s+report)\b",
    r"\b(?:legal|counsel|attorney|lawyer|paralegal|compliance\s+officer|contract\s+manager)\b",
    r"\b(?:nurse|doctor|medical|healthcare|receptionist|office\s+assistant|clerk|executive\s+assistant|admin\s+assistant|retail\s+associate|store\s+associate|cashier)\b",
    r"\b(?:custodian|janitor|maintenance\s+worker|driver|warehouse|facilities)\b",
    r"\b(?:trust\s+and\s+safety|policy\s+analyst|claims\s+process\s+consultant)\b",
]

# Genuine technical primary role patterns
GENUINE_TECH_ROLE_PATTERNS = [
    # 1. Software Engineering & Development
    r"\b(?:software\s+(?:engineer(?:ing)?|developer|development|architect|programmer)|sde|sdet)\b",
    r"\b(?:frontend|front-end|front\s+end)\s*(?:engineer|developer|lead|architect)?\b",
    r"\b(?:backend|back-end|back\s+end)\s*(?:engineer|developer|lead|architect)?\b",
    r"\b(?:fullstack|full-stack|full\s+stack)\s*(?:engineer|developer|lead|architect)?\b",
    r"\b(?:web|mobile|ios|android|api|app|application|firmware|embedded)\s+(?:developer|engineer|programmer|architect|lead)\b",
    r"\b(?:developer|programmer|coder)\b",

    # 2. Specific Programming Languages & Stacks
    r"\b(?:python|java|c\+\+|c#|f#|golang|rust|javascript|typescript|react|angular|vue|django|flask|fastapi|spring\s*boot|\.net|node\.?js|php|ruby|scala)\b",

    # 3. Data Science, Analytics, Data Engineering
    r"\bdata\s+(?:scientist|science|analyst|analytics|specialist|engineer(?:ing)?|architect|modeler|pipeline)\b",
    r"\b(?:business\s+intelligence|bi|power\s*bi|tableau)\s+(?:developer|engineer|specialist|architect)\b",
    r"\b(?:big\s+data|etl)\s+(?:developer|engineer|analyst|specialist)\b",

    # 4. Machine Learning & AI
    r"\b(?:machine\s+learning|ml|deep\s+learning|computer\s+vision|nlp)\s*(?:engineer|scientist|researcher|specialist|developer)?\b",
    r"\b(?:ai|artificial\s+intelligence|agentic\s+ai|genai|generative\s+ai|llm)\s+(?:engineer|scientist|developer|specialist|lead|architect|consultant)\b",

    # 5. Cloud, DevOps, Infrastructure, SRE & Systems
    r"\b(?:cloud|devops|sre|site\s+reliability|infrastructure|platform)\s+(?:engineer|architect|specialist|developer|lead)\b",
    r"\b(?:aws|azure|gcp|kubernetes|docker|terraform)\s+(?:engineer|architect|specialist|developer|admin(?:istrator)?)\b",
    r"\b(?:systems?\s+engineer|systems?\s+architect|solutions?\s+architect|enterprise\s+architect|cloud\s+architect)\b",
    r"\b(?:network\s+engineer|network\s+architect|network\s+specialist|network\s+admin(?:istrator)?)\b",
    r"\b(?:it|information\s+technology)\s+(?:engineer|specialist|analyst|consultant|developer|architect|lead|support\s+engineer)\b",
    r"\b(?:desktop\s+support|remote\s+desktop|sysadmin|systems?\s+admin(?:istrator)?|m365\s+admin)\b",

    # 6. Cybersecurity & Security Engineering
    r"\b(?:cybersecurity|cyber\s+security|infosec|information\s+security|security\s+engineer|soc\s+analyst|penetration\s+tester|security\s+consultant|vulnerability\s+analyst|security\s+architect)\b",

    # 7. Database / SQL
    r"\b(?:database|sql|mysql|postgresql|oracle|nosql|mongodb)\s+(?:developer|engineer|specialist|dba|administrator)\b",
    r"\bba\s*\+\s*sql\b",

    # 8. QA, Testing & Automation
    r"\b(?:qa|quality\s+assurance|quality\s+engineering|automation|test(?:ing)?)\s+(?:engineer|developer|analyst|specialist|lead|architect)\b",
]


def is_genuine_tech_job(title, source_url=""):
    """
    Determine whether a job's PRIMARY role is a genuine technical role.
    Rejects:
      - Non-job boilerplate / navigation links
      - Primary non-technical roles (Sales, Marketing, HR, Accounting, etc.)
    Accepts:
      - Computer Science, IT, SWE, AI, Data, Cloud, DevOps, Security, Systems roles
    """
    t = (title or "").lower().strip()
    u = (source_url or "").lower().strip()

    if not t:
        return False

    # 1. Non-job / boilerplate check
    for p in NON_JOB_PATTERNS:
        if re.search(p, t):
            return False
    for p in NON_JOB_URL_MARKERS:
        if p in u:
            return False

    # 2. Check for explicit non-technical roles
    # If the title contains a non-technical role (e.g. 'Inside Sales - Cyber Security',
    # 'Marketing - AI Products', 'HR - Technology', 'Recruiter - Software'),
    # the PRIMARY role is non-technical, unless explicitly modified by an engineering title
    # (e.g. 'Software Engineer - HR Systems').
    for p in NON_TECH_ROLE_PATTERNS:
        match = re.search(p, t)
        if match:
            has_swe = re.search(r"\b(?:software\s+(?:engineer|developer)|developer|data\s+engineer)\b", t)
            if has_swe and match.start() > has_swe.start():
                pass
            else:
                return False

    # 3. Check for genuine technical role patterns
    for p in GENUINE_TECH_ROLE_PATTERNS:
        if re.search(p, t):
            return True

    return False


def calculate_job_priority(job):
    """
    Calculate the technical relevance priority for a job record.
    Returns:
      3 = High: Explicit IT / Software / AI / Data / Cloud / CS / Engineering role
      2 = Medium: Technical support / Systems / Network administration
      1 = Low: Non-technical or general role
      0 = Excluded / Non-Job (Navigation, boilerplate, accommodation pages)
    """
    title = (getattr(job, "title", "") or "").lower().strip()
    source_url = (getattr(job, "source_url", "") or "").lower().strip()

    # 1. Non-job / Navigation pages
    for p in NON_JOB_PATTERNS:
        if re.search(p, title):
            return 0
    for p in NON_JOB_URL_MARKERS:
        if p in source_url:
            return 0

    # 2. Non-technical primary roles
    for p in NON_TECH_ROLE_PATTERNS:
        match = re.search(p, title)
        if match:
            has_swe = re.search(r"\b(?:software\s+(?:engineer|developer)|developer|data\s+engineer)\b", title)
            if has_swe and match.start() > has_swe.start():
                pass
            else:
                return 1

    # 3. High Priority / Technical Role matches
    for pattern in GENUINE_TECH_ROLE_PATTERNS:
        if re.search(pattern, title):
            # Differentiate support/admin vs core engineering
            if re.search(r"\b(?:desktop\s+support|remote\s+desktop|helpdesk|service\s+desk|m365\s+admin)\b", title):
                return 2
            return 3

    # 4. Default to Low priority for unspecified roles
    return 1


def filter_tech_jobs(jobs, tech_only=None):
    """
    Filter a list of jobs to only genuine technical roles when tech_only is True.
    """
    if tech_only is None:
        tech_only = TECH_ONLY

    if not tech_only:
        return jobs

    return [
        j for j in jobs
        if is_genuine_tech_job(getattr(j, "title", ""), getattr(j, "source_url", ""))
    ]


def get_priority_label(priority_score):
    if priority_score >= 3:
        return "high"
    elif priority_score == 2:
        return "medium"
    elif priority_score == 1:
        return "low"
    return "excluded"
