import re
from pathlib import Path

from pypdf import PdfReader
from docx import Document

from app.services.skill_extractor import extract_skills, skills_to_text


def clean_resume_text(text):
    """Normalize common PDF text extraction artifacts.

    Fixes merged column headers (e.g. Tools / CloudGit, DatabasesMySQL, ProgrammingPython),
    line-wrap hyphens (e.g. Anal-\\nysis), and bracket collisions (e.g. Platform[GitHub]).
    """
    if not text:
        return ""

    # 1. Un-hyphenate line breaks (e.g. Anal-\nysis -> Analysis)
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # 2. Add spaces around brackets and parentheses colliding with words
    text = re.sub(r"([A-Za-z0-9])([\[\(])", r"\1 \2", text)
    text = re.sub(r"([\]\)])([A-Za-z0-9])", r"\1 \2", text)

    # 3. Separate category headers commonly fused in two-column/tabular PDFs
    categories = [
        r"Programming", r"Machine\s+Learning", r"Data\s+Engineering",
        r"AI\s*/\s*ML\s*/\s*NLP", r"Backend\s*/\s*APIs?", r"Databases?",
        r"Tools\s*/\s*Cloud", r"Cloud\s*/\s*Tools", r"Frameworks",
        r"Libraries", r"DevOps", r"Languages", r"Platforms", r"Web\s+Technologies",
        r"Operating\s+Systems", r"Core\s+Competencies", r"Key\s+Skills", r"Technical\s+Skills"
    ]
    cat_pat = r"(?i)\b(" + "|".join(categories) + r")(?=[A-Za-z])"
    text = re.sub(cat_pat, r"\1 ", text)

    return text


def extract_text(path):
    suffix = Path(path).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(path)

        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")

        return "\n".join(pages)

    if suffix == ".docx":
        doc = Document(path)

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)

    raise ValueError("Only PDF and DOCX resumes are supported.")


def _is_section_header(line):
    """
    Detect real resume section headers.
    Avoid treating normal sentences containing words like
    'experience' as section headers.
    """

    normalized = " ".join(line.lower().strip().split())

    headers = {
        "experience",
        "work experience",
        "professional experience",
        "work history",
        "employment",
        "internship",
        "internships",
        "education",
        "academic",
        "academic background",
        "projects",
        "project",
        "personal projects",
        "academic projects",
        "technical skills",
        "skills",
        "certifications",
        "certificates",
        "credentials",
        "relevant coursework",
        "additional",
        "professional summary",
        "summary",
    }

    return normalized in headers


def _extract_sections(text):
    sections = {
        "experience": [],
        "education": [],
        "projects": [],
        "certifications": [],
    }

    current_section = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        normalized = " ".join(line.lower().split())

        # Detect exact section headers only.
        if _is_section_header(line):
            if normalized in {
                "experience",
                "work experience",
                "professional experience",
                "work history",
                "employment",
                "internship",
                "internships",
            }:
                current_section = "experience"

            elif normalized in {
                "education",
                "academic",
                "academic background",
            }:
                current_section = "education"

            elif normalized in {
                "projects",
                "project",
                "personal projects",
                "academic projects",
            }:
                current_section = "projects"

            elif normalized in {
                "certifications",
                "certificates",
                "credentials",
            }:
                current_section = "certifications"

            else:
                current_section = None

            continue

        if current_section:
            sections[current_section].append(line)

    return sections


def parse_individual_projects(project_text):
    """Extract individual projects with name, technologies, and bullet points if discernible."""
    if not project_text:
        return []

    projects = []
    lines = [l.strip() for l in project_text.splitlines() if l.strip()]
    current = None

    for line in lines:
        is_bullet = bool(re.match(r"^[\u2022\u25cf\u25aa\u25cb\u2013\u2014\*\-\x95\ufffd]", line))
        has_proj_marker = bool(re.search(r"\[github\]|\[live\]|[\u2013\u2014\-]\s+[A-Za-z]", line, re.I))

        if has_proj_marker and not is_bullet and not re.search(r"^\s*python\b|^\s*react\b", line, re.I):
            if current:
                projects.append(current)
            current = {"name": line, "tech": "", "description": []}
        elif current and not current["tech"] and not is_bullet:
            current["tech"] = line
        elif current:
            current["description"].append(line)

    if current:
        projects.append(current)

    return projects


def parse_resume(path):
    raw_text = extract_text(path).strip()

    if not raw_text:
        raise ValueError("Could not extract readable text from resume.")

    text = clean_resume_text(raw_text)
    sections = _extract_sections(text)

    cert_text = "\n".join(sections.get("certifications", []))
    skills = extract_skills(text, cert_text=cert_text)

    experience = "\n".join(sections["experience"][:100])
    education = "\n".join(sections["education"][:60])
    projects = "\n".join(sections["projects"][:100])

    return {
        "text": text,
        "skills": skills_to_text(skills),
        "experience": experience,
        "education": education,
        "projects": projects,
        "parsed_projects": parse_individual_projects(projects),
    }