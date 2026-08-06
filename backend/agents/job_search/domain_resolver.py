"""Resolve company email domains from apply links, cache, or LLM."""

from __future__ import annotations

import os
from urllib.parse import urlparse

COMPANY_DOMAIN_CACHE = {
    "synopsys": "synopsys.com",
    "bny": "bnymellon.com",
    "tower research capital": "towerresearch.com",
    "cisco": "cisco.com",
    "google": "google.com",
    "microsoft": "microsoft.com",
    "ibm": "ibm.com",
    "docusign": "docusign.com",
    "intuit": "intuit.com",
    "hpe": "hpe.com",
    "visa": "visa.com",
    "amazon": "amazon.com",
    "mathworks": "mathworks.com",
    "amd": "amd.com",
    "lseg": "lseg.com",
    "netapp": "netapp.com",
    "aditya birla group": "adityabirla.com",
}

THIRD_PARTY_BOARDS = [
    "greenhouse.io",
    "eightfold.ai",
    "smartrecruiters.com",
    "myworkdayjobs.com",
    "linkedin.com",
    "peoplestrong.com",
]


def resolve_company_domain(company_name: str, apply_link: str, groq_api_key: str | None = None) -> str:
    parsed = urlparse(apply_link)
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    is_third_party = any(board in netloc for board in THIRD_PARTY_BOARDS)
    if not is_third_party and "." in netloc:
        parts = netloc.split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])

    name_clean = company_name.lower().strip()
    if name_clean in COMPANY_DOMAIN_CACHE:
        return COMPANY_DOMAIN_CACHE[name_clean]
    for key, value in COMPANY_DOMAIN_CACHE.items():
        if key in name_clean or name_clean in key:
            return value

    api_key = groq_api_key or os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            from langchain_groq import ChatGroq

            llm = ChatGroq(model="llama-3.1-8b-instant", groq_api_key=api_key, temperature=0.0)
            prompt = (
                f"Identify the primary domain name for the company '{company_name}'. "
                "Return ONLY the domain name (e.g. google.com), nothing else."
            )
            response = llm.invoke(prompt).content.strip().lower()
            if "." in response and len(response.split()) == 1:
                return response
        except Exception:
            pass

    return name_clean.replace(" ", "") + ".com"
