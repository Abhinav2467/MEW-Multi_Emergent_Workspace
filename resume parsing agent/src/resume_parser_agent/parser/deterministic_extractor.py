"""Low-latency deterministic field extraction."""

import re

from pydantic import HttpUrl

from resume_parser_agent.schemas import ContactInfo, EducationItem, ExperienceItem


EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
URL_RE = re.compile(r"https?://[^\s,;]+|(?:www\.)[^\s,;]+", re.IGNORECASE)
SECTION_RE = re.compile(r"^(experience|work experience|education|skills|projects)\b", re.I)

KNOWN_SKILLS = {
    "aiohttp",
    "asyncio",
    "aws",
    "c",
    "css",
    "docker",
    "fastapi",
    "flask",
    "git",
    "html",
    "java",
    "javascript",
    "kubernetes",
    "machine learning",
    "mysql",
    "oop",
    "postgresql",
    "python",
    "pytorch",
    "react",
    "redis",
    "sql",
    "tensorflow",
}


def extract_contact_info(text: str) -> ContactInfo:
    """Extract name, email, phone, and links."""

    email_match = EMAIL_RE.search(text)
    phone_match = PHONE_RE.search(text)
    links = [_normalize_url(match.group(0)) for match in URL_RE.finditer(text)]

    return ContactInfo(
        name=extract_name(text),
        email=email_match.group(0) if email_match else None,
        phone=_clean_phone(phone_match.group(0)) if phone_match else None,
        links=_dedupe_links(links),
    )


def extract_name(text: str) -> str | None:
    """Infer a likely resume name from the first non-section line."""

    for line in text.splitlines()[:8]:
        stripped = line.strip()
        if not stripped or EMAIL_RE.search(stripped) or URL_RE.search(stripped):
            continue
        if SECTION_RE.search(stripped) or any(char.isdigit() for char in stripped):
            continue
        words = stripped.split()
        if 1 < len(words) <= 5 and all(_looks_like_name_token(word) for word in words):
            return stripped
    return None


def extract_skills(text: str) -> list[str]:
    """Extract known skills from the full resume text and skills section."""

    lowered = text.lower()
    found = {
        skill
        for skill in KNOWN_SKILLS
        if re.search(rf"(?<![\w+#.-]){re.escape(skill)}(?![\w+#.-])", lowered)
    }
    return sorted(skill.title() if skill != "sql" else "SQL" for skill in found)


def extract_experience(text: str) -> list[ExperienceItem]:
    """Extract simple experience bullets from the experience section."""

    section = _section_text(text, ("experience", "work experience"), ("education", "skills", "projects"))
    if not section:
        return []

    bullets = _bullet_lines(section)
    if not bullets:
        lines = [line.strip() for line in section.splitlines() if line.strip()]
        bullets = lines[1:4]

    return [ExperienceItem(description=bullets[:5])] if bullets else []


def extract_education(text: str) -> list[EducationItem]:
    """Extract a simple education entry from the education section."""

    section = _section_text(text, ("education",), ("experience", "work experience", "skills", "projects"))
    if not section:
        return []

    lines = [line.strip(" -\u2022") for line in section.splitlines() if line.strip()]
    detail_lines = [line for line in lines if not line.lower().startswith("education")]
    if not detail_lines:
        return []

    first = detail_lines[0]
    return [EducationItem(institution=first)]


def _section_text(text: str, starts: tuple[str, ...], stops: tuple[str, ...]) -> str:
    lines = text.splitlines()
    start_index: int | None = None
    stop_words = {word.lower() for word in stops}

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
    return bool(cleaned) and cleaned[0].isalpha() and not any(char in cleaned for char in "@/\\")


def _clean_phone(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_url(value: str) -> str:
    stripped = value.rstrip(".,)")
    return stripped if stripped.lower().startswith("http") else f"https://{stripped}"


def _dedupe_links(links: list[str]) -> list[HttpUrl]:
    seen: set[str] = set()
    result: list[HttpUrl] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            result.append(HttpUrl(link))
    return result
