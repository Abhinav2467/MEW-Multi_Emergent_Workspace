from typing import List, Dict, Any

def search_jobs_with_ai(query: str, location: str = "Remote") -> List[Dict[str, Any]]:
    return [
        {
            "id": "job_01",
            "title": f"Senior {query or 'Software Engineer'}",
            "company": "Microsoft",
            "location": location,
            "description": "Building scalable backend microservices, Python APIs, and AI integrations.",
            "url": "https://apply.careers.microsoft.com/us/en/job/10293"
        },
        {
            "id": "job_02",
            "title": f"Full Stack {query or 'Developer'}",
            "company": "Qualcomm",
            "location": location,
            "description": "Developing high-performance firmware UI and cloud application platforms.",
            "url": "https://careers.qualcomm.com/careers/job/84920"
        },
        {
            "id": "job_03",
            "title": "Machine Learning Engineer",
            "company": "Google",
            "location": location,
            "description": "Fine-tuning LLM pipelines, RAG architectures, and agentic workflows.",
            "url": "https://careers.google.com/jobs/results/948201"
        }
    ]
