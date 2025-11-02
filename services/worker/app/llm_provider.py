import json
from abc import ABC, abstractmethod

import httpx
from docuparse_contracts import ResumeExtraction

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMProvider(ABC):
    @abstractmethod
    def extract_resume(self, text: str) -> ResumeExtraction: ...


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def extract_resume(self, text: str) -> ResumeExtraction:
        response = httpx.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": _build_prompt(text)}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        return ResumeExtraction(**data)


def _build_prompt(resume_text: str) -> str:
    return f"""You are a resume parser. Extract structured information from the resume text below \
and return it as a single JSON object.

Use exactly this structure (omit nothing, use null for missing optional fields):
{{
  "full_name": "string",
  "email": "string or null",
  "phone": "string or null",
  "location": "string or null",
  "summary": "string or null",
  "skills": ["string", ...],
  "experience": [
    {{
      "company": "string",
      "title": "string",
      "start": "string",
      "end": "string or null",
      "bullets": ["string", ...]
    }}
  ],
  "education": [
    {{
      "institution": "string",
      "degree": "string",
      "year": "string or null"
    }}
  ]
}}

Resume:
{resume_text}"""
