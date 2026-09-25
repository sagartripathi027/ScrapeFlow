import unittest
from app.services.skill_extractor import extract_skills
from app.services.resume_parser import clean_resume_text


class TestResumeExtraction(unittest.TestCase):
    def test_cpp_does_not_create_c(self):
        text = "Programming Languages: Python, C++, JavaScript, SQL"
        skills = extract_skills(text)
        self.assertIn("c++", skills)
        self.assertNotIn("c", skills, "C++ must not automatically produce C")

    def test_standalone_c_is_detected(self):
        text = "Programming Languages: Python, C, C++, JavaScript, SQL"
        skills = extract_skills(text)
        self.assertIn("c", skills, "Standalone C should be detected when actually present")
        self.assertIn("c++", skills)

    def test_git_survives_merged_pdf_text(self):
        merged_text = "Databases SQLite\nTools / CloudGit, GitHub, Linux, Docker, AWS"
        cleaned = clean_resume_text(merged_text)
        skills = extract_skills(cleaned)
        self.assertIn("git", skills, "Git must be detected after cleaning merged 'CloudGit'")
        self.assertIn("github", skills)
        self.assertIn("docker", skills)

    def test_mysql_survives_merged_pdf_text(self):
        merged_text = "DatabasesMySQL, PostgreSQL, MongoDB, SQLite"
        cleaned = clean_resume_text(merged_text)
        skills = extract_skills(cleaned)
        self.assertIn("mysql", skills, "MySQL must be detected after cleaning merged 'DatabasesMySQL'")
        self.assertIn("postgresql", skills)
        self.assertIn("sqlite", skills)

    def test_google_cloud_cert_does_not_create_gcp(self):
        resume_text = (
            "Tools / Cloud: Git, GitHub, Linux, Docker, AWS (Basic)\n"
            "CERTIFICATIONS\n"
            "• Generative AI: Gemini for Data Analysis & ML Workflow – Google Cloud (2025)\n"
            "• Oracle Cloud Infrastructure 2025 AI Foundations Associate – Oracle (2025)"
        )
        cert_text = (
            "• Generative AI: Gemini for Data Analysis & ML Workflow – Google Cloud (2025)\n"
            "• Oracle Cloud Infrastructure 2025 AI Foundations Associate – Oracle (2025)"
        )
        skills = extract_skills(resume_text, cert_text=cert_text)
        self.assertNotIn("gcp", skills, "Google Cloud inside certification must not create GCP skill")
        self.assertIn("aws", skills)
        self.assertIn("docker", skills)

    def test_gcp_detected_when_in_tools_or_experience(self):
        resume_text = (
            "Tools / Cloud: Git, Google Cloud Platform, Docker, AWS\n"
            "CERTIFICATIONS\n"
            "• Generative AI: Gemini – Google Cloud (2025)"
        )
        cert_text = "• Generative AI: Gemini – Google Cloud (2025)"
        skills = extract_skills(resume_text, cert_text=cert_text)
        self.assertIn("gcp", skills, "Legitimate GCP mention in tools must be detected")

    def test_sqlalchemy_detected_when_present(self):
        text = "Backend / APIs: FastAPI, Flask, SQLAlchemy, Pydantic"
        skills = extract_skills(text)
        self.assertIn("sqlalchemy", skills, "SQLAlchemy must be detected when explicitly present")

    def test_pydantic_detected_when_present(self):
        text = "Backend / APIs: FastAPI, Flask, SQLAlchemy, Pydantic"
        skills = extract_skills(text)
        self.assertIn("pydantic", skills, "Pydantic must be detected when explicitly present")


if __name__ == "__main__":
    unittest.main()
