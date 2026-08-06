from resume_parser_agent.parser.deterministic_extractor import (
    extract_contact_info,
    extract_education,
    extract_experience,
    extract_name,
    extract_skills,
)


def test_extract_name_skips_contact_lines() -> None:
    text = "alex@example.com\nhttps://example.com\nAlex Chen\nSkills\nPython"

    assert extract_name(text) == "Alex Chen"


def test_extract_contact_info_normalizes_www_links() -> None:
    contact = extract_contact_info("Alex Chen\nalex@example.com\n555-123-4567\nwww.example.com")

    assert contact.name == "Alex Chen"
    assert contact.email == "alex@example.com"
    assert str(contact.links[0]) == "https://www.example.com/"


def test_extract_skills_dedupes_and_sorts_known_skills() -> None:
    assert extract_skills("Python python Docker SQL") == ["Docker", "Python", "SQL"]


def test_extract_experience_and_education_sections() -> None:
    text = """Alex Chen

Experience
- Built services
- Wrote tests

Education
Example University
"""

    assert extract_experience(text)[0].description == ["Built services", "Wrote tests"]
    assert extract_education(text)[0].institution == "Example University"
