"""Low-latency deterministic field extraction (fallback parser)."""

from __future__ import annotations

import re

from backend.models.schemas import ContactInfo, EducationItem, ExperienceItem

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://[^\s,;]+|(?:www\.)[^\s,;]+", re.IGNORECASE)
SECTION_RE = re.compile(r"^(experience|work experience|education|skills|projects)\b", re.I)
LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[^\s,;]+", re.I)
GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+", re.I)

KNOWN_SKILLS = {
    "aiohttp", "asyncio", "aws", "c", "c++", "css", "docker", "express", "fastapi",
    "flask", "git", "html", "java", "javascript", "kubernetes", "langchain",
    "langgraph", "machine learning", "mongodb", "mysql", "next", "node", "oop",
    "pinecone", "postgresql", "python", "pytorch", "rag", "react", "redis",
    "redux", "rest api", "sql", "tailwind", "tensorflow", "typescript",
}


def extract_contact_info(text: str) -> ContactInfo:
    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    linkedin_match = LINKEDIN_RE.search(text)
    github_match = GITHUB_RE.search(text)
    links = [_normalize_url(m.group(0)) for m in URL_RE.finditer(text)]

    github_url = _normalize_url(github_match.group(0)) if github_match else None
    if not github_url:
        for l in links:
            if "github.com" in l.lower():
                github_url = l
                break

    return ContactInfo(
        name=extract_name(text),
        email=email_match.group(0) if email_match else None,
        phone=_clean_phone(phone_match.group(0)) if phone_match else None,
        linkedin=_normalize_url(linkedin_match.group(0)) if linkedin_match else None,
        github=github_url,
        links=_dedupe(links),
    )


def extract_name(text: str) -> str | None:
    for line in text.splitlines()[:8]:
        stripped = line.strip()
        if not stripped or EMAIL_RE.search(stripped) or URL_RE.search(stripped):
            continue
        if SECTION_RE.search(stripped) or any(c.isdigit() for c in stripped):
            continue
        words = stripped.split()
        if 1 < len(words) <= 5 and all(_looks_like_name_token(w) for w in words):
            return stripped
    return None


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = {
        skill
        for skill in KNOWN_SKILLS
        if re.search(rf"(?<![\w+#.-]){re.escape(skill)}(?![\w+#.-])", lowered)
    }
    return sorted(skill.upper() if skill == "sql" else skill.title() for skill in found)


def extract_experience(text: str) -> list[ExperienceItem]:
    section = _section_text(text, ("experience", "work experience"), ("education", "skills", "projects"))
    if not section:
        return []
    bullets = _bullet_lines(section)
    if not bullets:
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        bullets = lines[1:4]
    return [ExperienceItem(description=bullets[:5])] if bullets else []


def extract_education(text: str) -> list[EducationItem]:
    section = _section_text(text, ("education",), ("experience", "work experience", "skills", "projects"))
    if not section:
        return []
    lines = [line.strip(" -\u2022") for line in section.splitlines() if line.strip()]
    detail_lines = [line for line in lines if not line.lower().startswith("education")]
    if not detail_lines:
        return []
    return [EducationItem(institution=detail_lines[0])]


def extract_current_role(experience: list[ExperienceItem]) -> str | None:
    for item in experience:
        if item.title:
            return item.title
        if item.description:
            return item.description[0][:80]
    return None


def calculate_confidence(contact: ContactInfo, skills: list[str], experience: list, education: list) -> float:
    score = 0.0
    if contact.name:
        score += 0.2
    if contact.email:
        score += 0.2
    if contact.phone:
        score += 0.1
    if skills:
        score += 0.2
    if experience:
        score += 0.2
    if education:
        score += 0.1
    return min(score, 1.0)


def _section_text(text: str, starts: tuple[str, ...], stops: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start_index: int | None = None
    stop_words = {w.lower() for w in stops}
    for index, line in enumerate(lines):
        normalized = line.strip().lower().rstrip(":")
        if normalized in starts:
            start_index = index
            break
    if start_index is None:
        return ""
    end_index = len(lines)
    for index in range(start_index + 1, len(lines)):
        normalized = lines[index].strip().lower().rstrip(":")
        if normalized in stop_words:
            end_index = index
            break
    return "\n".join(lines[start_index:end_index]).strip()


def _bullet_lines(text: str) -> list[str]:
    bullets = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*", "\u2022")):
            bullets.append(stripped.lstrip("-*\u2022 ").strip())
    return bullets


def _looks_like_name_token(word: str) -> bool:
    cleaned = word.strip(".,")
    return bool(cleaned) and cleaned[0].isalpha() and not any(c in cleaned for c in "@/\\")


def _clean_phone(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(value: str) -> str:
    stripped = value.rstrip(".,)")
    return stripped if stripped.lower().startswith("http") else f"https://{stripped}"


def _dedupe(links: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            result.append(link)
    return result
