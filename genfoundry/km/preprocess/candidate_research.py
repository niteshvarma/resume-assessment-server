import logging
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

candidate_research_prompt_json = '''
    You are a document transformer and you are tasked with standardizing resume text into a json string. The resume text will be provided as input and you must return a JSON string with the following format:

    {{
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "(123) 456-7890",
        "location": "San Francisco, CA",
        "linkedin": "https://linkedin.com/in/johndoe",
        "currentEmployer": "TechCorp",
        "currentRole": "Senior Engineer",
        "yearsExperience": 10,
        "currentComp": "$150,000",
        "expectedComp": "$200,000",
        "noticePeriod": "2 weeks",
        "professionalSummary": "Experienced software engineer with 10+ years...",
        "workExperience": [
            {{
                "title": "Senior Engineer",
                "company": "TechCorp",
                "startDate": "Jan 2018",
                "endDate": "Present",
                "location": "San Francisco, CA",
                "technicalEcosystem": ["Python", "Flask", "Microservices", "Kubernetes", "CI/CD Pipelines"]
            }},
            {{
                "title": "Software Engineer",
                "company": "StartupX",
                "startDate": "May 2015",
                "endDate": "Jan 2018",
                "location": "San Jose, CA",
                "technicalEcosystem": ["WebSphere", "Java", "J2EE", "Hibernate", "AJAX", "JSP"]
            }}
        ],
        "education": [
                {{
                "Degree": "B.Sc. Computer Science",
                "Institution": "Stanford University",
                "GraduationYear": "2005"
                }},
                {{
                 "Degree": "M.Sc. Computer Science",
                "Institution": "Yale University",
                "GraduationYear": "2010"               
                }}
            ],
        "certifications": [
            "AWS Certified Solutions Architect (2022)",
            "Certified Kubernetes Administrator (2021)"
        ]
    }}


**Instructions:**
1. Start with demographic information such as "Name," "Email," "Phone," "Location," and "LinkedIn."
2. Include a "ProfessionalSummary" field that summarizes the candidate's experience and career goals in your own words.
3. The `WorkExperience` array must be sorted in reverse-chronological order based on the `StartDate` or `EndDate` fields (most recent experience first). 
4. Extract "technicalEcosystem" as arrays of technologies used in each job. If none is provided, just enter: "Not provided". DO NOT GUESS.
5. The `Education` array must be sorted in reverse-chronological order based on the `GraduationYear` field (most recent education first).
6. The `Certifications` array must be sorted in reverse-chronological order based on the `Year` field (most recent certification first).
7. Return only the raw JSON string without any prefix or additional commentary.

---
Now, process the following resume:

**Input Resume:** 
{resume}

**Question:** 
{question}    
'''

class CandidateResearcher:
    def __init__(self, openai_api_key, langchain_api_key, llm_model):
        logging.debug("Initializing CandidateResearcher...")
        self.openai_api_key = openai_api_key
        self.langchain_api_key = langchain_api_key
        self.llm_model = llm_model
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)
 
    def research(self, resume_str):
        """
        Researches the candidate based on the resume into a structured format, extracting important information.
        Returns standardized research data.
        """
        try:
            logging.debug("Researching candidate based on resume...")
            research_prompt = candidate_research_prompt_json
            
            # Step 1: Standardize the resume
            prompt = PromptTemplate(
                input_variables=["resume", "question"], 
                template=research_prompt
            )
            question = "Research the candidate based on the resume text in the given format."
            research_response = self.get_llm_response(prompt, resume_str, question)
            
            response = json.loads(research_response)
            return response
        except Exception as ex:
            logging.error(f"Error in standardization: {str(ex)}")
            return {"error": str(ex)}, 500
  
    
    def get_llm_response(self, prompt, resume, question):
        try:
            inputs = {
                "resume": resume,
                "question": question
            }
        
            logging.debug(f"Inputs for chain: {inputs}")
            
            # Validate prompt is a Runnable
            if not isinstance(prompt, PromptTemplate):
                raise ValueError("Prompt must be an instance of PromptTemplate")
            
            chain = prompt| self.llm | StrOutputParser()
            response = chain.invoke(inputs) 
            return response
        except Exception as e:
            logging.error(f"Error in get_llm_response: {str(e)}")
            raise

