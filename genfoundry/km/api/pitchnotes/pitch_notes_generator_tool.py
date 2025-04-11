import logging, os
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

prompt_template = '''
        You are a talent acquisition expert. You are analyzing candidates' credentials based on their resumes in response to a job posting. Your job is to grade resumes against the provided criteria scores and generate a structured summary.

        **Instructions (MUST FOLLOW):**

        1. You MUST be objective in your assessment. Do not grade based on personal biases, familiarity with the candidate's name or gender. Grade purely based on the content of the resume and the recruiter’s notes.

        2. The criteria scores should be between 0 and 10:
           - **9 or above**: Exceptional experience in the criteria. MUST only be given if it is evidenced across multiple roles and at scale.
           - **7.5 to 9.0**: Good match against the criteria.  
           - **6.0 to 7.5**: Fair match.  
           - **Below 6.0**: Weak or missing experience.  
           - **0**: No relevant experience.

        3. **Extract the candidate's name directly from the resume** and use it in the summary and the `"name"` attribute of the JSON response.  
           - **If the name is missing from the resume, return `"Unknown"`** in the `"name"` attribute.  
           - **DO NOT infer or assume a name** based on context.

        4. **You must not make up any information** that is not explicitly stated in the resume. The evaluation must be fully objective and based only on the provided content.

        5. **The scoring response MUST be in JSON format** exactly as per the example below:  
           - Each `"criteria"` field should contain the criterion name.  
           - Each `"score"` field should be a number between **0 and 10**.  
           - Each `"explanation"` field should provide **2-3 concrete examples** from the candidate’s resume, including:
              - **Specific accomplishments** related to the criterion.  
              - **Company name and the year** the accomplishment took place.  
              - **Any metrics, percentages, or KPIs** explicitly mentioned in the resume.
            - DO NOT repeat candidate's accomplishments and  information across different criteria.
            - DO find supporting information from the entirety of the candidate's work experience, without docusing on any one specific job.

        6. **You MUST NOT estimate or calculate the candidate's years of experience.**  
           - Only use the years of experience if it is explicitly stated in the resume.  
           - If experience duration is not provided, do not infer it.

        7. The summary should provide a profile based on accomplishments across the complete work history and also highlight key educational achievements.

        8. **Important: DO NOT wrap the JSON response in any prefix, explanation, or quotes. Just return the raw JSON.**

        Example JSON response:

        {{
            "name": (Infer from resume),
            "evaluation": [
                {{
                    "criteria": "Technical Skills",
                    "score": 8.5,
                    "explanation": "The resume demonstrates strong proficiency in Python and cloud technologies as evidenced by John's work at Acme, Inc. (2020-2023), where he developed and deployed microservices using AWS Lambda and Terraform."
                }},
                {{
                    "criteria": "Work Experience",
                    "score": 7.0,
                    "explanation": "The candidate has relevant industry experience, having worked at XYZ Corp (2018-2021) as a software engineer, but has limited exposure to leadership roles."
                }},
                {{
                    "criteria": "Educational Background",
                    "score": 9.0,
                    "explanation": "Holds a Master’s degree in Computer Science from Stanford University (2015), which aligns well with the job requirements."
                }}
            ],
            "summary": "John Doe has strong technical expertise in cloud computing and Python development, with experience working at Acme, Inc. and XYZ Corp. His educational background is highly relevant, holding a Master’s degree in Computer Science from Stanford University. However, his leadership experience is limited."
        }}

        "Resume": {resume}
        "Notes": {notes}
        "Criteria": {criteria}
        "Question": {question}
        '''

class PitchNotesGenerator():

    def __init__(self):
        logging.debug("Initializing PitchNotesGeneratorTool...")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
        llm_model = os.getenv("LLM_MODEL")
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)


    def assess(self, resume, notes, criteria, question):    
        try:
            logging.debug("Assessing resume...")
            prompt = PromptTemplate(input_variables=["resume", "notes", "criteria", "question"], 
            template=prompt_template)
            response = self.get_llm_response(prompt, resume, notes, criteria, question)
            return response
        except Exception as ex:
            logging.error(f"Error in assessment: {str(ex)}")
            return {f"LLM error: {str(ex)}"},500

    def get_llm_response(self, prompt, resume, notes, criteria, question):
        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")
            llm_model = os.getenv("LLM_MODEL")
            llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)

            inputs = {
                "resume": resume,
                "notes": notes,
                "criteria": criteria,
                "question": question
            }
        
            logging.debug(f"Inputs for chain: {inputs}")
            
            # Validate prompt is a Runnable
            if not isinstance(prompt, PromptTemplate):
                raise ValueError("Prompt must be an instance of PromptTemplate")
            
            chain = prompt| llm | StrOutputParser()
            response = chain.invoke(inputs) 
            return response
        except Exception as e:
            logging.error(f"Error in get_llm_response: {str(e)}")
            raise
