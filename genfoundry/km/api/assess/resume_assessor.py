import logging
import json
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from genfoundry.km.utils.doc_parser import DocumentParser

answerTemplate = '''
You are a talent acquisition expert. You are analyzing resumes in response to a job posting. Your job is to grade resumes against the job description and provide criteria scores, a summary of the resume, a gap analysis, and suggested follow-up questions.

Each criterion should be interpreted literally and holistically based on the job description. If ambiguous, prefer the most domain-relevant and recruiter-relevant interpretation.

If no criteria are provided, extract the 5–7 most critical competencies, responsibilities, or skills required for success in the role directly from the job description. These should focus on tangible deliverables, technical or leadership competencies, or key experiences mentioned or implied in the job description. Use these extracted criteria for scoring, explanations, and gap analysis.

Tailor all analysis and questions specifically to the provided job description and criteria.

The criteria scores should be between 0 and 10. For example:
- 9 or above means the candidate is very strong in the criteria, with multiple relevant experiences and measurable outcomes.
- 8.0 to 9.0 indicates a strong match with multiple relevant experiences, but with minor gaps.
- 7.0 to 8.0 indicates a good match with some relevant experiences but with more significant gaps.
- 6.0 to 7.0 indicates a fair match with some relevant experiences but with significant gaps.
- Below 6.0 reflects limited alignment.
- If the candidate does not match the criteria at all, score it as 0.

Include detailed explanations for each score. The explanation must reference:
- 1-3 concrete accomplishments from the resume,
- The company names and years where these accomplishments were achieved,
- Any specific metrics, outcomes, or technologies mentioned.

You must not make up any information that is not on the resume. Be objective and avoid any bias.

Based on the identified gaps, generate a list of follow-up questions that a recruiter or interviewer could ask the candidate to help fill in those gaps. These questions should be based on the job description and criteria provided, and phrased professionally and focus on surfacing missing or unclear information from the resume. 

For each follow-up question, also include an "expected_indicators" field that outlines what a strong or meaningful response would typically contain. This helps recruiters evaluate responses even if they lack technical or domain-specific knowledge.

While scanning the resume, infer the candidate's name and use it in the summary. 

In the "summary" field:
- Summarize the candidate’s strengths and overall profile.
- Comment on their fit for the role based on the job description.
- Indicate whether they appear ready for the role or would be a stretch hire with potential.

Also include the candidate's name in the candidate_name field in the JSON.

The response must be a pure JSON object in the format below:

{{
    "candidate_name": "Alex Johnson",
    "evaluation": [
        {{
            "criteria": "Technical Skills",
            "score": 8.5,
            "explanation": "The candidate demonstrated strong proficiency in Python and AWS cloud technologies. For example, while at Acme Corp in 2021, they led the migration of a monolithic application to a microservices-based architecture using AWS Lambda and DynamoDB. In 2022 at BetaTech, they developed a CI/CD pipeline using GitHub Actions and Terraform."
        }},
        {{
            "criteria": "Work Experience",
            "score": 7.0,
            "explanation": "The candidate has relevant experience in the industry but limited exposure to leading cross-functional teams. At Delta Inc. in 2020, they worked as a backend engineer on a payment processing system. In 2021, they contributed to an internal analytics platform at SigmaSoft."
        }},
        {{
            "criteria": "Educational Background",
            "score": 9.0,
            "explanation": "The candidate holds a Master's degree in Computer Science from Carnegie Mellon University (2018), which aligns well with the job requirements."
        }}
    ],
    "summary": "Alex Johnson is a skilled software engineer with a strong foundation in cloud infrastructure and backend systems. While the resume reflects depth in technical execution, it shows limited leadership roles and domain-specific experience in finance. Overall, a technically capable candidate who could grow into the position. Given the current role’s emphasis on financial services domain knowledge, this candidate may be considered a stretch hire with high upside potential.",
    "gaps": [
        "No mention of experience with Kubernetes or container orchestration.",
        "No clear demonstration of leading cross-functional teams.",
        "Missing direct evidence of experience in financial services domain."
    ],
    "follow_up_questions": [
        {{
            "question": "Can you describe any experience you've had with Kubernetes or managing containerized deployments?",
            "expected_indicators": "Strong responses should mention setting up clusters, Helm charts, CI/CD pipelines, or orchestration in production environments. Keywords: EKS, GKE, AKS, Docker, Helm, autoscaling."
        }},
        {{
            "question": "Have you led any cross-functional teams in the past? If so, what was your role and what challenges did you face?",
            "expected_indicators": "Look for examples involving coordination across product, design, and engineering; conflict resolution; or accountability for project outcomes."
        }},
        {{
            "question": "Do you have any experience working in financial services or on products tailored to regulated industries?",
            "expected_indicators": "Strong answers may mention compliance (e.g., SOX, PCI, GDPR), domain-specific knowledge, or integration with core banking systems or payment rails."
        }}
    ]
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

