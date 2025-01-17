import logging
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

resume_standardization_prompt = '''
    You are a document transformer and you are tasked with standardizing resume text into a json string. The resume text will be provided as input and you must return a JSON string with the following format:

        {{
            "Name": "",
            "Email": "",
            "Phone": "",
            "Location": "",
            "LinkedIn": "",
            "ProfessionalSumary": "",
            "CurrentJobTitle": "",
            "YearsOfExperience": "",
            "TechnicalSkills": [],
            "LeadershipSkills": [],
            "WorkExperience": [
                {{
                "JobTitle": "",
                "Company": "",
                "StartDate": "",
                "EndDate": "",
                "Accomplishments": ""
                }}
            ],
            "Education": [
                {{
                "Degree": "",
                "Institution": "",
                "GraduationYear": ""
                }}
            ],
            "Certifications": [
                {{
                "CertificationName": "",
                "Year": ""
                }}
            ]

        }}

**Instructions:**
1. Start with demographic information such as "Name," "Email," "Phone," "Location," and "LinkedIn."
2. Include a "ProfessionalSummary" field that summarizes the candidate's experience and career goals in your own words.
3. The `WorkExperience` array must be sorted in reverse-chronological order based on the `StartDate` or `EndDate` fields (most recent experience first). 
4. Retain the "Accomplishments" field exactly as it appears in the resume. This means:
   - Retain the original text verbatim. DO NOT summarize, truncate, or alter. Maintain all details, including technical terms and formatting.
  - Preserve all bullet points, line breaks, and original formatting.
   - Treat this field as immutable and copy it verbatim from the input resume.
   - Retain all nested or multiline bullet points as-is.
   - DO NOT truncate any content. If a bullet point spans multiple lines, combine them while preserving the original structure and content.
5. Extract "TechnicalSkills" and "LeadershipSkills" as arrays:
   - **TechnicalSkills:** Identify keywords and phrases related to technical expertise, tools, programming languages, frameworks, or technologies mentioned in the resume. If a "Skills" section is present, use the listed technical skills directly. If not, infer technical skills from the entire resume.
   - **LeadershipSkills:** Identify keywords and phrases related to leadership qualities, team management, strategic decision-making, mentoring, or similar attributes. If a "Skills" section is present, use the listed leadership skills directly. If not, infer leadership skills from the entire resume.
   - Ensure no repetition in the extracted skills, and format each skill as a unique item in the array. DO NOT collapse similar sounding skills, e.g., Java and JavaScript and C and C++.
6. The `Education` array must be sorted in reverse-chronological order based on the `GraduationYear` field (most recent education first).
7. The `Certifications` array must be sorted in reverse-chronological order based on the `Year` field (most recent certification first).
8. Return only the raw JSON string without any prefix or additional commentary.

Here are examples:

### Example 1
Input Resume:
John Doe
...
Work Experience:
- Senior Director at TechCorp (Jan 2015 - Dec 2020)
  Accomplishments:
Led the transformation of Dayforce's $400M+ payroll management business, driving end-to-end modernization of platform technology and processes to enable scalability, resilience, and operational excellence. 
- Strategic Roadmap & Executive Alignment: Designed and executed a $30M, 4-year modernization roadmap for payroll platforms. Collaborated with executive stakeholders through regular interlock sessions to align technical initiatives with business priorities. 
- Platform Modernization & Cloud Strategy: Directed a comprehensive Azure cloud migration, re-engineering payroll tax and payments systems using microservices, Kubernetes, and Kafka. 

Desired JSON Output:
{{ 
    "Name": "John Doe",
    ...
    "WorkExperience": [
        {{ 
            "JobTitle": "Senior Director",
            "Company": "TechCorp",
            "StartDate": "2015-01",
            "EndDate": "2020-12",
            "Accomplishments": "- Led the transformation of Dayforce's $400M+ payroll management business, driving end-to-end modernization of platform technology and processes to enable scalability, resilience, and operational excellence. \n- Strategic Roadmap & Executive Alignment: Designed and executed a $30M, 4-year modernization roadmap for payroll platforms. Collaborated with executive stakeholders through regular interlock sessions to align technical initiatives with business priorities. \n - Platform Modernization & Cloud Strategy: Directed a comprehensive Azure cloud migration, re-engineering payroll tax and payments systems using microservices, Kubernetes, and Kafka."
        }}
    ]
}}

Now, process the following resume:

**Input Resume:** 
{resume}

**Question:** 
{question}    
'''

metadata_prompt = """
            Analyze the following resume and extract the following details as JSON:
            - Latest Job Title
            - Career Domain (e.g., tech, medical, sales, education)
            - Total Years of Experience
            - Technical Skills (list 5-10)
            - Leadership Skills (list 5-10)
            - Highest Education Level
            - Current Location (City/State/Country if available)

            The JSON response format should be as follows:
            {{
                "latest_job_title": "",
                "career_domain": "",
                "total_years_of_experience": 0,
                "technical_skills": [],
                "leadership_skills": [],
                "highest_education_level": "",
                "current_location": ""
            }}           
            
            Resume:
            {resume}

            Return only the raw JSON string without any prefix, wrapper or additional commentary.
            """


class ResumeStandardizer:
    def __init__(self, openai_api_key, langchain_api_key, llm_model):
        logging.debug("Initializing ResumeStandardizer...")
        self.openai_api_key = openai_api_key
        self.langchain_api_key = langchain_api_key
        self.llm_model = llm_model
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)
 
    """
    def standardize(self, resume_str):
        try:
            logging.debug("Standardizing resume...")
            prompt = PromptTemplate(input_variables=["resume", "question"], 
            template=resume_prompt_template)
            question = "Standardize the resume text into a JSON string"
            response = self.get_llm_response(prompt, resume_str, question)
            return response
        except Exception as ex:
            logging.error(f"Error in assessment: {str(ex)}")
            return {f"LLM error: {str(ex)}"},500
    """

    def standardize(self, resume_str):
        """
        Standardizes the resume into a structured JSON format and extracts metadata.
        Returns a dictionary with both standardized resume content and metadata.
        """
        try:
            logging.debug("Standardizing resume...")
            
            # Step 1: Standardize the resume
            prompt = PromptTemplate(
                input_variables=["resume", "question"], 
                template=resume_standardization_prompt
            )
            question = "Standardize the resume text into a JSON string"
            standardized_response = self.get_llm_response(prompt, resume_str, question)
            standardized_resume = json.loads(standardized_response)

            # Step 2: Extract metadata
            metadata = self.extract_metadata(resume_str)

            # Step 3: Combine and return
            result = {
                "standardized_resume": standardized_resume,
                "metadata": metadata
            }
            return result
        except Exception as ex:
            logging.error(f"Error in standardization: {str(ex)}")
            return {"error": str(ex)}, 500

    def extract_metadata(self, resume_str):
        """
            Extracts metadata like job title, domain, years of experience, etc., from the resume text.
        """
        try:
            logging.debug("Extracting metadata from resume...")
            
            prompt = PromptTemplate(input_variables=["resume"], template=metadata_prompt)
            metadata_response = self.get_llm_response(prompt, resume_str, "")
            logging.debug(f"Metadata response: {metadata_response}")
            metadata = json.loads(metadata_response)
            return metadata
        except Exception as ex:
            logging.error(f"Error in extracting metadata: {str(ex)}")
            return {"error": str(ex)}
  
    
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

