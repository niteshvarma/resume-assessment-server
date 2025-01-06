import logging
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

answerTemplate = '''
        You are a talent acquisition expert. You are analyzing resumes in response to a job posting. Your job is to grade resumes against the job description and provide criteria scores, and a summary of the resume. The criteria scores should be between 0 and 10. For example, 9 or above means the candidate is very good in the criteria; between 7.5 and 9.0 means a good match against the criteria; between 6.0 and 7.5 means a fair match, etc. If the candidate does not match the criteria, score it as 0.

        While scanning the resume, pick up the candidate's name, which you can use in the summary. 
        
        You must not make up any information that is not on the resume. You must be objective and not biased towards or against the candidate. 

        The scoring response should be in JSON format following the example below, where the criteria is the criteria being scored, the score is the score for how well the candidate matches the criteria, and the explanation is the explanation for the score. Please provide two concrete examples of the candidate's accomplishments for the explanation to make it more detailed. Also incude which company the accomplishments were achieved at, and the years when the accomplishments were achieved. Specific metrics or numbers mentioned to support the accomplishment provided in the resume should be included in the explanation.

        {{
            "evaluation": [
                {{
                    "criteria": "Technical Skills",
                    "score": 8.5,
                    "explanation": "The resume demonstrates strong proficiency in Python and cloud technologies."
                }},
                {{
                    "criteria": "Work Experience",
                    "score": 7.0,
                    "explanation": "The candidate has relevant industry experience but limited exposure to leadership roles."
                }},
                {{
                    "criteria": "Educational Background",
                    "score": 9.0,
                    "explanation": "The educational qualifications align well with the job requirements."
                }}
            ],
            "summary": "(Provide a summary of the candidate's experience as it relates to the job description and criteria)"
        }}

        Remember, DO NOT wrap the JSON response string with any prefix. Just return the raw JSON.

        "Job Description": {job_description}
        "Resume": {resume}
        "Criteria": {criteria}
        "Question": {question}
        '''

class ResumeAssessor:
    def __init__(self, openai_api_key, langchain_api_key, llm_model):
        logging.debug("Initializing ResumeAssessor...")
        self.openai_api_key = openai_api_key
        self.langchain_api_key = langchain_api_key
        self.llm_model = llm_model
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)
 
    def assess(self, job_description, criteria, resume, question):
        try:
            logging.debug("Assessing resume...")
            prompt = PromptTemplate(input_variables=["job_description", "resume", "criteria", "question"], 
            template=answerTemplate)
            response = self.get_llm_response(prompt, job_description, resume, criteria, question)
            return response
        except Exception as ex:
            logging.error(f"Error in assessment: {str(ex)}")
            return {f"LLM error: {str(ex)}"},500
            
    
    def get_llm_response(self, prompt, job_description, resume, criteria, question):
        try:
            inputs = {
                "job_description": job_description,
                "resume": resume,
                "criteria": criteria,
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

