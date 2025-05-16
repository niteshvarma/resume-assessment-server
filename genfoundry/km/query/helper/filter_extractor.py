import json
import logging
from typing import Any, Dict, Optional
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from genfoundry.km.query.helper.filter_normalizer import FilterNormalizer
import os

class FilterExtractor:
    def __init__(self, llm: Optional[Any] = None):
        llm_model = os.getenv("LLM_MODEL")
        self.llm = llm or ChatOpenAI(model=llm_model, temperature=0)
        self.prompt = PromptTemplate(
            input_variables=["question"],
            template = """
You are a resume search assistant. From the user query, extract a list of structured filters in JSON format to help search a candidate database.

Rules:
- Always return a JSON object with a top-level `filters` key, whose value is a list of filter objects.
- Only use these keys: 
  - "job_title"
  - "career_domain"
  - "years_of_experience"
  - "technical_skills"
  - "leadership_skills"
  - "highest_education_level"
  - "location"


Key definitions:
- "job_title": Extract the job title(s) mentioned and include alternative industry titles (e.g. if "VP of Engineering", include ["VP of Engineering", "Director of Engineering", "Head of Engineering"]). Limit to 3–5 titles. Use `operator: "in"` with a list of titles.
- "career_domain": Choose from this predefined list only: ["Technology", "Finance & Accounting", "Healthcare", "Education", "Sales & Marketing", "Human Resources", "Legal", "Operations", "Engineering", "Design", "Customer Support", "Product Management"]. Do not invent new domains. If there is confusion between "Technology" and "Engineering", infer from the context - if the context is software or computer hardware, categorize it as "Technology" career_domain, else categorize it as "Engineering".
- "technical_skills": Extract specific technologies, tools, frameworks, platforms, or domain experience (e.g. "B2B SaaS", "AWS", "React", "Cloud Infrastructure"). Include domain-specific or industry context if relevant.
- "leadership_skills": Extract leadership traits or roles if mentioned (e.g. "Mentoring", "Team Management", "Strategy").
- "years_of_experience": Convert a specific number into a range as follows:
    - 2 → 1 to 4
    - 5 → 3 to 7
    - 10 → 9 to 12
    - 10+ → 10 to 15
    - 12 → 10 to 15
    - 12+ → 12 to 15
    - 15 → 12 to 18
    - 15+ → 15 to 20
    - 20 → 15 to 25
- If the number is not in the list, use a buffer of ±2–3 years. For example, if the query states "17 years", return a range of 15 to 20 years.
    Use `"operator": "range"` and a dict with "min" and "max".
- "highest_education_level": Extract degree level if stated (e.g. "PhD", "Master's", "Bachelor's").
- "location": Use the city or region from the query.


Operators:
- Use `"=="` for scalar values (e.g., "PhD", "Toronto").
- Use `"contains"` for skill lists (technical or leadership).
- Use `"range"` only for `years_of_experience`.
- Use `"in"` for job title alternatives.

IMPORTANT:
- Do NOT prepend or follow the JSON response with any text or explanation.
- Only include fields explicitly mentioned or strongly implied in the query.

Format:
{{
  "filters": [
    {{
      "key": "job_title",
      "value": ["VP of Engineering", "Director of Engineering", "Head of Engineering"],
      "operator": "in"
    }},
    {{
      "key": "years_of_experience",
      "value": {{"min": 12, "max": 18}},
      "operator": "range"
    }},
    {{
      "key": "technical_skills",
      "value": ["Technology Architecture", "B2B SaaS", "Cloud Infrastructure", "AWS", "React"],
      "operator": "contains"
    }},
    {{
      "key": "leadership_skills",
      "value": ["Mentoring", "Team Management", "Scaling teams"],
      "operator": "contains"
    }},
    {{
      "key": "career_domain",
      "value": "Engineering",
      "operator": "=="
    }},
    {{
      "key": "location",
      "value": "London, UK",
      "operator": "=="
    }}
  ]
}}

Now process this query:
Query: {question}
"""

        )

    def extract(self, question: str) -> Dict[str, Any]:
        try:
            prompt_input = self.prompt.format(question=question)
            result = self.llm.invoke(prompt_input)

            content = getattr(result, "content", str(result))
            logging.info(f"[FilterExtractor] LLM response content: {content}")

            parsed_result = json.loads(content)
            logging.info(f"[FilterExtractor] Parsed result: {parsed_result}")

            raw_filters = {
                f["key"]: f["value"]
                for f in parsed_result.get("filters", [])
                if "key" in f and "value" in f
            }

            return FilterNormalizer.normalize(raw_filters)

        except Exception as e:
            logging.error(f"[FilterExtractor] Failed to extract filters: {e}")
            return {}  # ← return a plain dict even on failure