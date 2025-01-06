from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from tavily import TavilyClient
import logging, os

locatonSearchAnswerTemplate = '''
        You are a helpful assistant. You are analyzing whether the candidate's location as provided in the resume is in the vicinity of the job location as per the criteria. You must use tavily_search_results_json tool for information search. You will provide a score against the location criteria.The criteria scores should be between 0 and 10. For example, 9 or above means the candidate's location fully matches the job location; between 7.5 and 9.0 means the candidate is within 50 kilometers of the job location; between 6.0 and 7.5 means the candidate is within 100 kilometers of the job location. If the candidate mentions "willing to relocate", score it as 8. If the candidate does not match the criteria, score it as 0.

        While scanning the resume, pick up the candidate's location, which you can for location matching. 
        
        You must not make up any information that is not on the resume. You must be objective and not biased towards or against the candidate. 

        The scoring response should be in JSON format following the example below, where the criteria is the criteria being scored, the score is the score for how well the candidate matches the criteria, and the explanation is the explanation for the score. Please provide two concrete examples of the candidate's accomplishments for the explanation to make it more detailed. Also incude which company the accomplishments were achieved at, and the years when the accomplishments were achieved. Specific metrics or numbers mentioned to support the accomplishment provided in the resume should be included in the explanation.

        {{
            "evaluation": [
                {{
                    "criteria": "Location",
                    "score": 10,
                    "explanation": "The candidate's location is in the vicinity of the job location."
                }}
            ],
        }}

        "Distance": {distance}
        '''

class LocationAssessorTool(BaseTool):
    name = "Location Assessor"
    description = "Use this tool when you need to assess a location provided in the resume against the location specified in the job description."

    def __init__(self):
        logging.debug("Initializing LocationAssessorTool...")

    def _run(self, resume, criteria):
        logging.debug("Assessing candidate's location score...")
        openai_api_key = os.getenv("OPENAI_API_KEY")
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        llm_model = os.getenv("LLM_MODEL")
        llm = ChatOpenAI(model_name=llm_model, temperature=0, api_key=openai_api_key)

        candidate_location = self.get_location(resume, llm)
        job_location = self.get_location(criteria, llm)
        
        question = "How far is candidate's location from the job location? Provide the approximate distance in kilometers. The candidate's location is {candidate_location} and the job location is {job_location}."

        tavily_client = TavilyClient(api_key=tavily_api_key)
        distance = tavily_client.search(question)
        prompt = PromptTemplate(input_variables=["distance"], template=locatonSearchAnswerTemplate)
        response = self.get_location_score(llm, prompt, distance=distance)
        return response


    def get_location(self, document, llm):
        locationTemplate = '''
        You are a helpful assistant. Scan the document for the candidate's location. Return the location in the format of "City, State, Country". If the country is not provided, return the location in the format of "City, State". If the location is not found, return "Unknown".

        "Document": {document}
        '''
        prompt = PromptTemplate(input_variables=["document"], template=locationTemplate)
        try:
            inputs = {
                "document": document
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

    def get_location_score(self, llm, prompt, distance):
        try:
            inputs = {
                "distance": distance
            }
            chain = prompt| llm | StrOutputParser()
            response = chain.invoke(inputs) 
            return response
        except Exception as e:
            logging.error(f"Error in get_location_score: {str(e)}")
            raise