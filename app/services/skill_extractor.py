import re

# Canonical skills used by ScrapeFlow resume/job matching.
SKILLS = [
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "rust", "sql",
    "flask", "fastapi", "django", "node.js", "express", "spring", "spring boot",
    "rest api", "graphql", "microservices",
    "html", "css", "react", "angular", "vue",
    "mysql", "postgresql", "mongodb", "redis", "sqlite",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "git", "github",
    "linux", "ci/cd", "jenkins", "devops",
    "machine learning", "deep learning", "artificial intelligence", "nlp",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "langchain",
    "transformers", "data analysis", "data engineering", "data visualization",
    "feature engineering", "eda", "spark", "hadoop", "power bi", "tableau", "excel",
    "sqlalchemy", "pydantic", "jwt", "beautifulsoup", "requests", "ocr",
    "data cleaning", "data preprocessing", "data transformation",
    "classification", "regression", "cross-validation", "fine-tuning",
    "supervised learning", "unsupervised learning", "statistical analysis",
    "aiops", "opsramp", "splunk", "bmc", "dynatrace", "new relic", "appdynamics",
    "elk", "grafana", "servicenow itom", "servicenow", "service desk", "uipath",
    "automation anywhere", "blue prism", "agentic ai", "llm",
    "communication", "leadership", "problem solving", "analytical thinking",
    "critical thinking", "time management", "stakeholder management",
    "presentation skills", "process improvement",
]

SKILL_ALIASES = {
    "problem-solving": "problem solving",
    "problem solving skills": "problem solving",
    "problem-solving skills": "problem solving",
    "data analytics": "data analysis",
    "data analysis skills": "data analysis",
    "data analytics skills": "data analysis",
    "exploratory data analysis": "data analysis",
    "eda": "data analysis",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "microsoft office excel": "excel",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest api development": "rest api",
    "financial market": "financial markets",
    "financial markets analysis": "financial markets",
    "economic": "economics",
    "economic analysis": "economics",
    "machine-learning": "machine learning",
    "deep-learning": "deep learning",
    "artificial intelligence / machine learning": "artificial intelligence",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "powerbi": "power bi",
    "nodejs": "node.js",
    "node js": "node.js",
    "postgres": "postgresql",
    "postgres sql": "postgresql",
    "mongo": "mongodb",
    "mongo db": "mongodb",
    "fast api": "fastapi",
    "amazon web services": "aws",
    "aws cloud": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "service now": "servicenow",
    "service-now": "servicenow",
    "dev-ops": "devops",
    "dev ops": "devops",
    "tesseract ocr": "ocr",
    "tesseract": "ocr",
    "beautiful soup": "beautifulsoup",
    "bs4": "beautifulsoup",
    "json web token": "jwt",
    "json web tokens": "jwt",
    "sql alchemy": "sqlalchemy",
    "cross validation": "cross-validation",
    "fine tuning": "fine-tuning",
    "data pre-processing": "data preprocessing",
    "statistics": "statistical analysis",
    "servicenow it operations management": "servicenow itom",
    "agentic ai systems": "agentic ai",
    "large language model": "llm",
    "large language models": "llm",
    "presentation": "presentation skills",
    "stakeholder": "stakeholder management",
}

SOFT_SKILLS = {
    "communication", "leadership", "problem solving", "analytical thinking",
    "critical thinking", "time management", "stakeholder management",
    "presentation skills", "process improvement",
}


def _normalize_text(text):
    if not text:
        return ""
    text = str(text).lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_skill(skill):
    value = _normalize_text(skill)
    if not value:
        return ""
    value = re.sub(r"\s*/\s*", " / ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return SKILL_ALIASES.get(value, value)


def _contains_phrase(text, phrase):
    text = _normalize_text(text)
    phrase = _normalize_text(phrase)
    if not text or not phrase:
        return False
    if phrase == "c":
        pattern = r"(?<![a-z0-9_-])c(?![a-z0-9+#])"
    else:
        pattern = rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])"
    return bool(re.search(pattern, text))


def extract_skills(text, include_soft=True, cert_text=""):
    """Extract known canonical skills.

    Job matching calls this with include_soft=False so generic soft skills
    cannot overwhelm concrete technical requirements.
    """
    if not text:
        return []

    # Non-certification text used to avoid treating certification provider names
    # (e.g. "Google Cloud" in certificate titles) as claimed technical tools:
    non_cert_text = text
    if cert_text:
        non_cert_text = text.replace(cert_text, " ")

    found = set()
    allowed = set(SKILLS)
    if not include_soft:
        allowed -= SOFT_SKILLS

    for skill in allowed:
        if _contains_phrase(text, skill):
            found.add(_normalize_skill(skill))

    for alias, canonical in SKILL_ALIASES.items():
        if canonical in SOFT_SKILLS and not include_soft:
            continue
        # Provider-only alias check: if an alias like "google cloud" -> "gcp" only appears
        # inside the certification block, do not falsely extract it as a technical skill:
        target_text = non_cert_text if canonical == "gcp" and alias in ("google cloud", "google cloud platform") else text
        if _contains_phrase(target_text, alias):
            found.add(_normalize_skill(canonical))

    return sorted(found)


def skills_to_text(skills):
    if not skills:
        return ""
    normalized = {
        _normalize_skill(skill)
        for skill in skills
        if _normalize_skill(skill)
    }
    return ", ".join(sorted(normalized))
