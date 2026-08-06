"""Confidence scoring for deterministic extraction."""

from resume_parser_agent.schemas import ParsedResume


def calculate_confidence(resume: ParsedResume) -> float:
    """Score extraction completeness on a conservative 0.0 to 1.0 scale."""

    score = 0.0
    if resume.contact.name:
        score += 0.2
    if resume.contact.email:
        score += 0.2
    if resume.contact.phone:
        score += 0.1
    if resume.skills:
        score += 0.2
    if resume.experience:
        score += 0.2
    if resume.education:
        score += 0.1
    return min(score, 1.0)
