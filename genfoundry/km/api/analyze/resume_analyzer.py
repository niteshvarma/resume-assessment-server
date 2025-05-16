import logging
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from genfoundry.km.utils.doc_parser import DocumentParser

logger = logging.getLogger(__name__)

answerTemplate = '''
You are a Resume Consistency Checker AI.

Your job is to analyze resumes for internal consistency and plausibility. Carefully read the resume provided below and perform the following tasks:

1. **Overlapping Roles** – Identify any job roles with overlapping date ranges.
2. **Skills vs Roles** – Flag any skills claimed that do not have clear evidence of use in any of the listed roles.
3. **Exaggerated Claims** – Identify implausible claims such as very senior titles early in the career, or claiming more years of experience than possible for a technology.
4. **Inconsistent Dates** – Look for any inconsistencies in the dates of employment, such as gaps or overlaps that don't make sense.
5. **Education vs Experience** – Check if the education level is consistent with the years of experience claimed.
6. **Job Titles** – Look for any job titles that seem inflated or inconsistent with the roles described.
7. **Company Names** – Check for any inconsistencies in company names or locations. Does the candidate list a company that doesn't exist or is not well-known?
8. **Job Descriptions** – Look for generic description phrases that could apply to any job, rather than specific accomplishments or responsibilities.
9. **Inconsistent Metrics** – Check for any metrics or achievements that seem exaggerated or inconsistent with the role.
10. **Summary + Risk Score** – Write a brief summary of your findings and assign a risk score based on severity:
   - Low: Mostly consistent
   - Medium: Some questionable elements
   - High: Many inconsistencies or clearly inflated claims

Respond only in the following JSON format:

{{
  "summary": "<concise summary of consistency findings>",
  "redFlags": [
    "<each inconsistency or suspicious item as a bullet>"
  ],
  "riskScore": "Low" | "Medium" | "High"
}}

For example:
{{
  "summary": "The resume shows some inconsistencies in job titles, dates of employment and claimed skills. The candidate has overlapping roles at Company A and Company B, and the job title at Company C seems inflated for the role described. The metrics about amount saved ($20MM) claimed for Company E seem exaggerated.",
  "redFlags": [
    "Overlapping roles at Company A and Company B from Jan 2020 to Mar 2021.",
    "Claimed 10 years of experience in Python, but education was completed in 2015.",
    "Job title at Company C seems inflated for the role described.",
    "Resume entry for Company D sound generic that could apply to any role.",
    "Metrics about amount saved ($20MM) claimed for Company E seem exaggerated.",
    "Company F does not exist in public records."
  ],
  "riskScore": "High"
}}

For each red flag, provide a brief explanation of why it is a concern and which part of the resume it relates to.

When analyzing this resume, carefully consider the full education history. Do not assume that the most recent degree represents the start of the candidate’s career. If multiple degrees are present, prioritize the earliest for assessing total experience.

Be conservative in your analysis. If you are unsure about a claim, do not mark it as a red flag. Focus on clear inconsistencies or implausible claims.

Remember, DO NOT wrap the JSON response string with any prefix, backticks, etc. Just return the raw JSON.

Now, here is the resume you need to analyze:

"Resume": {resume}
'''


class ResumeAnalyzer:
    def __init__(self, openai_api_key, langchain_api_key, llm_model):
        logger.debug("Initializing ResumeAnalyzer...")
        self.openai_api_key = openai_api_key
        self.langchain_api_key = langchain_api_key
        self.llm_model = llm_model
        self.llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)
 
    def assess(self, resume):
        try:
            logger.debug("Assessing resume...")
            prompt = PromptTemplate(input_variables=["resume"], 
            template=answerTemplate)
            response = self.get_llm_response(prompt,resume)
            return response
        except Exception as ex:
            logger.error(f"Error in assessment: {str(ex)}")
            return {f"LLM error: {str(ex)}"},500
            
    
    def get_llm_response(self, prompt, resume):
        try:
            inputs = {
                "resume": resume,
            }
        
            logger.debug(f"Inputs for chain: {inputs}")
            
            # Validate prompt is a Runnable
            if not isinstance(prompt, PromptTemplate):
                raise ValueError("Prompt must be an instance of PromptTemplate")
            
            chain = prompt| self.llm | StrOutputParser()
            response = chain.invoke(inputs) 
            logger.debug(f"LLM response: {response}")
            return response
        except Exception as e:
            logger.error(f"Error in get_llm_response: {str(e)}")
            raise

