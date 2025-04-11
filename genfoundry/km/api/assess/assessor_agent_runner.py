from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from langchain_openai import ChatOpenAI
from genfoundry.km.utils.doc_parser import DocumentParser
from .resume_assessor_tool import ResumeAssessorTool
from .location_assessor_tool import LocationAssessorTool
from langgraph.prebuilt import create_react_agent
from langchain.agents import AgentExecutor
import os
import json

class ResumeAssessorAgentRunner(Resource):
    def __init__(self):
        logging.debug("Initializing Resume Assessor Agent HTTP handler")
        os.environ["OPENAI_API_KEY"] = current_app.config['OPENAI_API_KEY']
        os.environ["LANGCHAIN_API_KEY"] = current_app.config['LANGCHAIN_API_KEY']
        os.environ["LLM_MODEL"] = current_app.config['LLM_MODEL']
        self.doc_parser = DocumentParser(current_app.config['LLAMA_CLOUD_API_KEY'])
        self.llm = ChatOpenAI(
            model_name=current_app.config['LLM_MODEL'], 
            temperature=0, 
            api_key=os.getenv("OPENAI_API_KEY"))
        
        tools = [ResumeAssessorTool(), LocationAssessorTool()]
        
        system_message = "You are a helpful recruitment assistant. Please assess the resume against the job description and criteria. You may use the tools provided to assist you. The final answer should combine the results of individual tools that are called."

        self.agent_executor = create_react_agent(self.llm, tools, state_modifier=system_message)

    def post(self):        
        if 'job_description' not in request.files or 'resume' not in request.files:
            return jsonify({"error": "Both job_description and resume files are required"}), 400

        # Get uploaded files
        job_description_file = request.files['job_description']
        resume_file = request.files['resume']
        criteria_file = request.files['criteria']

        try:
            job_description = self.doc_parser.parse_document(job_description_file)
            resume = self.doc_parser.parse_document(resume_file)
            criteria = self.doc_parser.parse_document(criteria_file)

            if not job_description or not resume or not criteria:
                return jsonify({"error": "Parsed content cannot be empty"}), 400
        except Exception as e:
            logging.error(f"Document parsing failed: {e}")
            return jsonify({"error": "Failed to parse uploaded files"}), 500
                
        try:
            question = "Please assess the resume against the job description and criteria. You may use the tools provided to assist you. The final answer should combine the results of the tools."

            assess_response = self.agent_executor.invoke({"job_description": job_description, "criteria": criteria, "resume": resume, "question": question})
            logging.debug(f"Answer: {assess_response}")

            # If the response is a JSON string, parse it
            try:
                if isinstance(assess_response, str):
                    assess_response = json.loads(assess_response)
            except json.JSONDecodeError:
                logging.warning("Agent response is not valid JSON. Returning raw response.")

            # Return the parsed JSON as the HTTP response
            return jsonify({"AIResponse": assess_response})
        except Exception as e:
            logging.error(f"Assessment failed: {e}")
            return "Server Error", 500
        

