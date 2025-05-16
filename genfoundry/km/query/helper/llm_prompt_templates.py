# genfoundry/km/query/llm_prompt_templates.py

def resume_search_prompt(query: str, resume_details_popup_url: str) -> str:
    return f"""
You are an expert talent acquisition professional analyzing a vector database of resumes. Your task is to return only the **most relevant candidates** based on the user’s natural language query.

### CRITICAL INSTRUCTIONS:
- **STRICT RELEVANCE ONLY**: Do not include resumes unless there's a strong match with the query intent.
- Use the available metadata filters (like job title, skills, experience, education) to narrow down candidates.
- Avoid generic or vague responses.
- **Do not hallucinate data** — only present what is present in the resume metadata.
- If no relevant candidates are found, clearly state that.
- Do not summarize resumes; focus on metadata-based reasoning.
- Prioritize candidates with exact or near-exact job title and skill matches.
- Experience match should account for a ±2-3 year range.
- Include candidates from similar but relevant domains (e.g., “Full-stack Engineer” for “Software Developer” if other criteria match).

### RESPONSE FORMAT:
- Respond using **pure JSON only** — no markdown, no backticks, no extra text.
- Do **NOT stringify** the JSON. Respond with **raw JSON object**, not a string of JSON.
- VERY IMPORTANT: Respond only with a pure JSON object — no explanations, no Markdown, and no formatting. Return only the array. 
- Do not include newline charachters in the JSON response, e.g. `\n`.
- Format exactly as shown below:

{{
  "candidates": [
    {{
      "name": "Candidate Name",
      "resume_id": "Doc:1234",
      "job_title": "Latest Job Title",
      "years_of_experience": 5,
      "location": "City, Country",
      "technical_skills": ["Skill1", "Skill2"],
      "leadership_skills": ["Leadership Skill1", "Leadership Skill2"],
      "resume_link": "{resume_details_popup_url}?ID=Doc:1234"
    }}
  ]
}}

---

### Example 1:
**Query**: Senior backend engineer with experience in .NET and microservices

**Response**:
{{
  "candidates": [
    {{
      "name": "Priya Das",
      "resume_id": "Doc:5678",
      "job_title": "Senior Backend Engineer",
      "years_of_experience": 7,
      "location": "Toronto, Canada",
      "technical_skills": ["C#", ".NET", "Microservices", "SQL Server"],
      "leadership_skills": ["Mentorship", "Scrum Master"],
      "resume_link": "{resume_details_popup_url}?ID=Doc:5678"
    }}
  ]
}}

---

### Example 2:
**Query**: Looking for a tech leader with strong AWS and Kubernetes experience

**Response**:
{{
  "candidates": [
    {{
      "name": "Alex Murphy",
      "resume_id": "Doc:9012",
      "job_title": "Director of Engineering",
      "years_of_experience": 15,
      "location": "Vancouver, Canada",
      "technical_skills": ["AWS", "Kubernetes", "DevOps"],
      "leadership_skills": ["Team Building", "Strategic Planning", "Cloud Transformation"],
      "resume_link": "{resume_details_popup_url}?ID=Doc:9012"
    }}
  ]
}}

---

### Your Turn:
**Query**: {query}

**Response** (strict JSON only — same format as above):
"""

def geo_location_expansion_prompt(location: str) -> str:
    return f"""
You are a geographical expansion assistant. Given a location, provide a list of nearby locations and regions that should be included as part of this location. The output should be in JSON format with the key 'expanded_locations' containing an array of location names. Also include the broader region or area name, if applicable, e.g., "GTA" for "Greater Toronto Area" or "Bay Area" for "San Francisco".
- Respond using **pure JSON only** — no markdown, no backticks, no extra text.

Example:

Input: "Toronto, ON"
Output: 
{{
  "expanded_locations": [
    "GTA",
    "Greater Toronto Area",
    "Toronto, ON", 
    "Markham, ON",
    "Vaughan, ON",
    "Oakville, ON",
    "Brampton, ON",
    "Aurora, ON",
    "Newmarket, ON",
    "Pickering, ON",
    "Ajax, ON",
    "Whitby, ON",
    "Oshawa, ON",
    "North York, ON", 
    "Scarborough, ON", 
    "Richmond Hill, ON", 
    "Mississauga, ON",
    "Etobicoke, ON"
  ]
}}

Input: "{location}"
Output: 
"""

def filter_extractor_prompt(question: str) -> str:
    return f"""
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
    - 10+ -> 10 to 15
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
- Use `"range"` only for `total_years_of_experience`.
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
      "value": ["Mentoring", "Team Management", "Scaling teams],
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