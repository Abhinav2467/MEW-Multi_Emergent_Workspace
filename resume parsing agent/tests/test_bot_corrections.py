from resume_parser_agent.bot.corrections import apply_local_correction
from resume_parser_agent.schemas import ContactInfo, ParsedResume


def test_apply_local_name_correction() -> None:
    resume = ParsedResume(contact=ContactInfo(name="Wrong Name"))

    corrected = apply_local_correction(resume, "My name is Regandla Sai Yasvitha")

    assert corrected is not None
    assert corrected.contact.name == "Regandla Sai Yasvitha"


def test_apply_local_email_and_phone_correction() -> None:
    resume = ParsedResume(contact=ContactInfo(email="old@example.com"))

    corrected = apply_local_correction(
        resume,
        "Email: new@example.com Phone: +91 99999 88888",
    )

    assert corrected is not None
    assert corrected.contact.email == "new@example.com"
    assert corrected.contact.phone == "+91 99999 88888"


def test_apply_local_correction_returns_none_when_no_field_found() -> None:
    resume = ParsedResume(contact=ContactInfo(name="Jane Doe"))

    assert apply_local_correction(resume, "this is wrong") is None
