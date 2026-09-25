import re
from datetime import datetime

from app.services.skill_extractor import extract_skills


SKILL_ALIASES = {
    "amazon web services": "aws",
    "aws cloud": "aws",
    "google cloud": "gcp",
    "google cloud platform": "gcp",
    "microsoft azure": "azure",
    "python programming": "python",
    "fast api": "fastapi",
    "scikit learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "node js": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "postgres sql": "postgresql",
    "mongo": "mongodb",
    "mongo db": "mongodb",
    "restful api": "rest api",
    "restful apis": "rest api",
    "rest apis": "rest api",
    "rest api development": "rest api",
    "data analytics": "data analysis",
    "data analytics skills": "data analysis",
    "exploratory data analysis": "data analysis",
    "eda": "data analysis",
    "microsoft excel": "excel",
    "ms excel": "excel",
    "powerbi": "power bi",
    "service now": "servicenow",
    "service-now": "servicenow",
    "dev-ops": "devops",
    "dev ops": "devops",
    "large language model": "llm",
    "large language models": "llm",
}


def _normalize(text):
    if not text:
        return ""
    text = str(text).lower()
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_skill(skill):
    value = _normalize(skill)
    if not value:
        return ""
    if value in SKILL_ALIASES:
        return SKILL_ALIASES[value]
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return SKILL_ALIASES.get(value, value)


def _get_normalized_skills(skills):
    return {
        _normalize_skill(skill)
        for skill in (skills or [])
        if _normalize_skill(skill)
    }


# Conservative relationships: related gets partial credit, never exact credit.
RELATED_SKILLS = {
    "flask": {"fastapi", "django", "rest api"},
    "fastapi": {"flask", "django", "rest api"},
    "django": {"flask", "fastapi", "rest api"},
    "rest api": {"fastapi", "flask", "django", "express", "spring boot"},
    "express": {"rest api"},
    "spring boot": {"rest api"},
    "devops": {"aws", "azure", "gcp", "docker", "kubernetes", "linux", "ci/cd", "jenkins"},
    "ci/cd": {"jenkins", "devops"},
    "jenkins": {"ci/cd", "devops"},
    "linux": {"devops"},
    "sql": {"sqlite", "postgresql", "mysql", "mongodb"},
    "mysql": {"postgresql", "sqlite"},
    "postgresql": {"mysql", "sqlite"},
    "sqlite": {"mysql", "postgresql"},
    "machine learning": {"scikit-learn", "tensorflow", "pytorch"},
    "scikit-learn": {"machine learning"},
    "tensorflow": {"machine learning", "deep learning"},
    "pytorch": {"machine learning", "deep learning"},
    "deep learning": {"tensorflow", "pytorch", "machine learning"},
    "react": {"angular", "vue"},
    "angular": {"react", "vue"},
    "vue": {"react", "angular"},
    "docker": {"kubernetes", "devops"},
    "kubernetes": {"docker", "devops"},
    "servicenow itom": {"servicenow"},
    "servicenow": {"servicenow itom"},
    "agentic ai": {"llm", "artificial intelligence"},
    "llm": {"agentic ai", "artificial intelligence"},
    "artificial intelligence": {"machine learning", "agentic ai", "llm"},
}


def _related_resume_matches(job_skills, resume_skills):
    related = {}
    for job_skill in job_skills:
        if job_skill in resume_skills:
            continue
        found = sorted(RELATED_SKILLS.get(job_skill, set()) & resume_skills)
        if found:
            related[job_skill] = found
    return related


def _skill_score(job_skills, resume_skills):
    if not job_skills:
        return 0, [], [], {}

    related = _related_resume_matches(job_skills, resume_skills)
    exact = sorted(job_skills & resume_skills)
    missing = sorted(job_skills - resume_skills - set(related))

    points = float(len(exact)) + (0.45 * len(related))
    score = round((points / len(job_skills)) * 100)

    return max(0, min(100, score)), exact, missing, related


def _get_job_text(job):
    return f"{job.title or ''} {job.description or ''}"


def _get_job_skills(job):
    skills = set(extract_skills(_get_job_text(job), include_soft=False))
    raw_skills = getattr(job, "skills", None)
    if raw_skills:
        if isinstance(raw_skills, str):
            skills.update(extract_skills(raw_skills, include_soft=False))
            for item in re.split(r"[,;|\n]+", raw_skills):
                cleaned = item.strip()
                if cleaned:
                    norm = _normalize_skill(cleaned)
                    if norm:
                        skills.add(norm)
        elif isinstance(raw_skills, (list, set, tuple)):
            for item in raw_skills:
                norm = _normalize_skill(item)
                if norm:
                    skills.add(norm)
    return _get_normalized_skills(skills)


def _extract_required_experience(text, raw_exp=""):
    full_text = f"{text or ''} {raw_exp or ''}"
    if raw_exp and not re.search(r"years?|yrs?", str(raw_exp), re.I):
        full_text += f" {raw_exp} years"
    text = _normalize(full_text)
    candidates = []

    for match in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b",
        text,
    ):
        candidates.append((float(match.group(1)), float(match.group(2))))

    for match in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b",
        text,
    ):
        candidates.append((float(match.group(1)), None))

    for match in re.finditer(
        r"\b(?:minimum\s+of\s+)?(\d+(?:\.\d+)?)\s*(?:or\s+more|or\s+above|or\s+higher)\s*(?:years?|yrs?)\b",
        text,
    ):
        candidates.append((float(match.group(1)), None))

    for match in re.finditer(
        r"\b(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience\b",
        text,
    ):
        candidates.append((float(match.group(1)), None))

    if not candidates:
        if any(x in text for x in ("entry level", "entry-level", "fresher", "freshers", "no experience required")):
            return {"min_years": 0, "max_years": 1, "display": "0-1 years", "specified": True}
        return {"min_years": None, "max_years": None, "display": "Not specified", "specified": False}

    minimum, maximum = max(candidates, key=lambda x: x[0])

    return {
        "min_years": minimum,
        "max_years": maximum,
        "display": f"{minimum:g}+ years" if maximum is None else f"{minimum:g}-{maximum:g} years",
        "specified": True,
    }


def _extract_resume_experience(resume):
    text = _normalize(resume.experience)

    if not text:
        return {"years": 0, "display": "No professional experience found", "status": "Entry-level"}

    explicit = re.search(
        r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+)?experience\b",
        text,
    )
    if explicit:
        years = float(explicit.group(1))
        return {"years": years, "display": f"{years:g} years", "status": "Detected from professional experience"}

    current_year = datetime.now().year
    ranges = re.findall(r"\b(20\d{2})\s*[-–]\s*(20\d{2}|present|current|now)\b", text)

    total_months = 0
    for start_raw, end_raw in ranges:
        start = int(start_raw)
        if start < 1990 or start > current_year:
            continue
        end = current_year if end_raw in {"present", "current", "now"} else int(end_raw)
        if end >= start:
            total_months += (end - start) * 12

    if total_months:
        years = round(total_months / 12, 1)
        return {"years": years, "display": f"{years:g} years", "status": "Estimated from employment dates"}

    if "intern" in text or "internship" in text:
        return {"years": 0, "display": "Internship experience only", "status": "Entry-level"}

    return {"years": 0, "display": "Professional experience not measurable", "status": "Entry-level"}


def _experience_score(required, candidate):
    minimum = required["min_years"]
    maximum = required["max_years"]
    years = candidate["years"]

    if minimum is None:
        return 50
    if years >= minimum:
        return 100 if maximum is None or years <= maximum else 90
    if years <= 0:
        return 0

    ratio = years / minimum
    if ratio >= 0.75:
        return 65
    if ratio >= 0.50:
        return 45
    if ratio >= 0.25:
        return 30
    return 15


def _extract_education_requirement(job_text):
    text = _normalize(job_text)

    if re.search(r"\bph\.?\s*d\b|\bdoctorate\b", text):
        return {"required": "PhD / Doctorate", "type": "phd", "specified": True}
    if re.search(r"\bmaster(?:'s)?\b|\bm\.?\s*tech\b|\bm\.?\s*e\b|\bmba\b|\bmsc\b|\bm\.?\s*sc\b", text):
        return {"required": "Master's degree", "type": "master", "specified": True}
    if re.search(r"\bbachelor(?:'s)?\b|\bb\.?\s*tech\b|\bb\.?\s*e\b|\bb\.?\s*sc\b", text):
        return {"required": "Bachelor's degree", "type": "bachelor", "specified": True}

    return {"required": "Not specified", "type": None, "specified": False}


def _detect_graduation_year(text):
    years = re.findall(r"\b(19\d{2}|20\d{2})\b", text or "")
    return max((int(y) for y in years), default=None)


def _education_score(job_text, resume_education):
    requirement = _extract_education_requirement(job_text)
    education = _normalize(resume_education)

    if not requirement["specified"]:
        return {"score": None, "required": "Not specified", "status": "Not specified by job"}
    if not education:
        return {"score": 0, "required": requirement["required"], "status": "Not detected"}

    current_year = datetime.now().year
    grad_year = _detect_graduation_year(resume_education)

    if requirement["type"] == "phd":
        if "phd" in education or "ph.d" in education or "doctorate" in education:
            return {"score": 100, "required": requirement["required"], "status": "Match"}
        if "master" in education or "m.tech" in education or "mba" in education:
            return {"score": 55, "required": requirement["required"], "status": "Partial match"}
        return {"score": 20, "required": requirement["required"], "status": "Does not match"}

    if requirement["type"] == "master":
        if any(x in education for x in ("master", "m.tech", "mtech", "m.e", "mba", "msc", "m.sc")):
            return {"score": 100, "required": requirement["required"], "status": "Match"}
        if any(x in education for x in ("bachelor", "b.tech", "btech", "b.e", "b.sc", "bsc")):
            status = "Pursuing" if grad_year and grad_year > current_year else "Partial match"
            return {"score": 40 if status == "Pursuing" else 55, "required": requirement["required"], "status": status}
        return {"score": 20, "required": requirement["required"], "status": "Does not match"}

    if any(x in education for x in ("bachelor", "b.tech", "btech", "b.e", "b.sc", "bsc")):
        status = "Pursuing" if grad_year and grad_year > current_year else "Match"
        return {"score": 80 if status == "Pursuing" else 100, "required": requirement["required"], "status": status}

    return {"score": 30, "required": requirement["required"], "status": "Does not match"}


def _project_relevance(job_skills, related_skills, resume):
    project_text = _normalize(resume.projects)

    if not project_text:
        return {"score": 0, "status": "No projects detected", "exact_matches": [], "related_evidence": []}
    if not job_skills:
        return {"score": 50, "status": "No concrete project requirements detected", "exact_matches": [], "related_evidence": []}

    exact_matches = []
    related_evidence = []

    # 1. Exact job skills in project text
    for skill in sorted(job_skills):
        phrase = _normalize(skill).replace("-", " ")
        if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", project_text):
            exact_matches.append(skill)

    # 2. Related project evidence for job skills not matched exactly
    # E.g. SQLite / SQLAlchemy / PostgreSQL / MySQL demonstrate database work without being an exact match for SQL:
    db_project_evidence = {"sqlite", "sqlalchemy", "postgresql", "mysql", "mongodb"}

    for skill in sorted(job_skills):
        if skill in exact_matches:
            continue

        found_evidence = []
        candidate_related = related_skills.get(skill, [])
        for r_skill in candidate_related:
            r_phrase = _normalize(r_skill).replace("-", " ")
            if re.search(rf"(?<![a-z0-9]){re.escape(r_phrase)}(?![a-z0-9])", project_text):
                found_evidence.append(r_skill)

        # For database/SQL skills, also check related DB tools in project evidence:
        if skill == "sql" and not found_evidence:
            for db_tool in sorted(db_project_evidence):
                if re.search(rf"(?<![a-z0-9]){re.escape(db_tool)}(?![a-z0-9])", project_text):
                    found_evidence.append(db_tool)

        if found_evidence:
            related_evidence.append({"skill": skill, "evidence": sorted(set(found_evidence))})

    exact_count = len(exact_matches)
    related_count = len(related_evidence)

    score = round(((exact_count * 1.0 + related_count * 0.45) / len(job_skills)) * 100)
    score = max(0, min(100, score))

    if exact_matches or related_evidence:
        parts = []
        if exact_matches:
            parts.append(f"{exact_count} exact ({', '.join(exact_matches)})")
        if related_evidence:
            rel_strs = [f"{item['skill']} via {', '.join(item['evidence'][:2])}" for item in related_evidence]
            parts.append(f"{related_count} related evidence ({'; '.join(rel_strs)})")
        status = "Project evidence: " + " and ".join(parts)
    else:
        status = "No relevant project skills detected"

    return {
        "score": score,
        "status": status,
        "exact_matches": exact_matches,
        "related_evidence": related_evidence,
    }


def _job_is_analyzable(job):
    """Return False for scraped navigation/info pages that are not job listings."""
    if not job:
        return False

    title = _normalize(getattr(job, "title", ""))
    description = _normalize(getattr(job, "description", ""))
    source_url = _normalize(getattr(job, "source_url", ""))

    invalid_titles = {
        "request an accommodation",
        "interview tips",
        "faqs",
        "transparency faqs",
        "learn more about our recruiting and workplace accommodations",
        "privacy policy",
        "terms of use",
        "cookie policy",
        "accessibility",
    }

    if title in invalid_titles:
        return False

    non_job_url_markers = (
        "/forms/create",
        "/hiring-tips/",
        "/hiringfaqs",
        "/transparency",
        "/accessibility",
    )
    if any(marker in source_url for marker in non_job_url_markers):
        return False

    job_skills = _get_job_skills(job)
    return len(description.strip()) >= 50 or len(job_skills) > 0


def match_job(job, resume):
    if not _job_is_analyzable(job):
        return {
            "job_title": job.title,
            "company": getattr(getattr(job, "company", None), "name", None),
            "location": getattr(job, "location", None),
            "score": 0,
            "label": "Not enough data",
            "recommendation": (
                "This record is not a complete job listing. "
                "The scraped page does not contain a usable job description, "
                "so a resume match cannot be calculated."
            ),
            "skill_score": 0,
            "experience_score": 0,
            "education_score": None,
            "projects_score": 0,
            "matching_skills": [],
            "related_skills": [],
            "missing_skills": [],
            "experience": {
                "required": "Not available",
                "candidate": "Not evaluated",
                "years": 0,
                "status": "Job description unavailable",
            },
            "education": {
                "required": "Not available",
                "candidate": resume.education[:500] if resume.education else "Not detected",
                "status": "Job description unavailable",
            },
            "projects": {
                "score": 0,
                "status": "Not evaluated because this is not a complete job listing",
            },
            "breakdown": {
                "skills": 0,
                "experience": 0,
                "education": None,
                "projects": 0,
            },
            "resume": {
                "skills": resume.skill_list(),
                "experience": resume.experience,
                "education": resume.education,
                "projects": resume.projects,
            },
            "match_debug": {
                "analyzable": False,
                "reason": "Incomplete/non-job scraped page",
            },
        }

    job_skills = _get_job_skills(job)
    resume_skills = _get_normalized_skills(resume.skill_list())

    skill_score, matched, missing, related = _skill_score(job_skills, resume_skills)

    required_experience = _extract_required_experience(
        job.description, getattr(job, "experience", "")
    )
    candidate_experience = _extract_resume_experience(resume)
    if required_experience["specified"] and required_experience["min_years"] and required_experience["min_years"] > 0:
        if candidate_experience["years"] < required_experience["min_years"]:
            candidate_experience = {
                "years": candidate_experience["years"],
                "display": f"{candidate_experience['years']:g} years professional experience" if candidate_experience["years"] > 0 else "0 years professional experience",
                "status": "Does not meet minimum experience",
            }
    experience_score = _experience_score(required_experience, candidate_experience)

    education_result = _education_score(
        f"{job.title or ''} {job.description or ''}", resume.education
    )
    education_score = education_result["score"]

    projects_result = _project_relevance(job_skills, related, resume)
    projects_score = projects_result["score"]

    # Senior roles: experience is deliberately strong so a junior resume
    # cannot get an inflated score just by matching a few technologies.
    if required_experience["specified"] and required_experience["min_years"] >= 5:
        weights = {"skills": 0.45, "experience": 0.40, "education": 0.10, "projects": 0.05}
    else:
        weights = {"skills": 0.55, "experience": 0.20, "education": 0.15, "projects": 0.10}

    dimensions = [(skill_score, weights["skills"])]
    if required_experience["specified"]:
        dimensions.append((experience_score, weights["experience"]))
    if education_result["required"] != "Not specified" and education_score is not None:
        dimensions.append((education_score, weights["education"]))
    if resume.projects:
        dimensions.append((projects_score, weights["projects"]))

    total_weight = sum(weight for _, weight in dimensions)
    score = round(sum(value * weight for value, weight in dimensions) / total_weight)
    score = max(0, min(100, score))

    if not job_skills and not required_experience["specified"] and education_result["required"] == "Not specified":
        score = 0
        label = "Insufficient job data"
    elif score >= 80:
        label = "Strong match"
    elif score >= 60:
        label = "Good match"
    elif score >= 40:
        label = "Partial match"
    else:
        label = "Low match"

    rec_parts = [label + "."]
    if matched:
        rec_parts.append(f"Exact matches: {', '.join(matched[:6])}.")
    if related:
        related_text = "; ".join(
            f"{job_skill.title() if job_skill != 'sql' else 'SQL'} (demonstrated via {', '.join(found[:3]).upper()})"
            for job_skill, found in sorted(related.items())
        )
        rec_parts.append(f"Related evidence: {related_text}.")
    if missing:
        rec_parts.append(f"Missing requirements: {', '.join(missing[:6])}.")
    if required_experience["specified"] and candidate_experience["years"] < required_experience["min_years"]:
        rec_parts.append(
            f"Experience gap: role asks for {required_experience['display']}; "
            f"candidate has {candidate_experience['display']} ({candidate_experience['status'].lower()})."
        )
    if education_result["required"] == "Not specified":
        rec_parts.append("Education: Not specified by job (N/A).")

    company_name = getattr(getattr(job, "company", None), "name", None)

    return {
        "job_title": job.title,
        "company": company_name,
        "location": job.location,
        "score": score,
        "label": label,
        "recommendation": " ".join(rec_parts),
        "skill_score": skill_score,
        "experience_score": experience_score,
        "education_score": education_score,
        "projects_score": projects_score,
        "matching_skills": matched,
        "related_skills": [
            {"required": required, "candidate": candidates}
            for required, candidates in sorted(related.items())
        ],
        "missing_skills": missing,
        "experience": {
            "required": required_experience["display"],
            "candidate": candidate_experience["display"],
            "years": candidate_experience["years"],
            "status": candidate_experience["status"],
        },
        "education": {
            "required": education_result["required"],
            "candidate": resume.education[:500] if resume.education else "Not detected",
            "status": education_result["status"],
        },
        "projects": {
            "score": projects_score,
            "status": projects_result["status"],
        },
        "breakdown": {
            "skills": skill_score,
            "experience": experience_score,
            "education": education_score,
            "projects": projects_score,
        },
        "resume": {
            "skills": resume.skill_list(),
            "experience": resume.experience,
            "education": resume.education,
            "projects": resume.projects,
        },
        "match_debug": {
            "job_skill_count": len(job_skills),
            "exact_skill_count": len(matched),
            "related_skill_count": len(related),
            "missing_skill_count": len(missing),
            "job_skills": sorted(job_skills),
        },
    }
