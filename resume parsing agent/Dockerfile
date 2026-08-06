FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip setuptools==80.9.0 \
    && python -m pip install --no-cache-dir .

CMD ["python", "-m", "resume_parser_agent.main"]
