import logging

from resume_parser_agent.logging_config import configure_logging, get_logger


def test_configure_logging_sets_root_level() -> None:
    configure_logging("debug")

    assert logging.getLogger().level == logging.DEBUG


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("resume_parser_agent.tests")

    assert logger.name == "resume_parser_agent.tests"
