from flask import request, jsonify
from flask_restful import Resource, current_app
import logging
from .financial_summarizer import FinancialSummarizer

class Summarizer(Resource):
    def __init__(self):
        logging.debug("Initializing Summarizer HTTP handler")
        logging.debug(f"OpenAI API Key = {current_app.config['OPENAI_API_KEY']}")
        self.summarizer = FinancialSummarizer(
            openai_api_key=current_app.config['OPENAI_API_KEY'],
            pinecone_api_key=current_app.config['PINECONE_API_KEY'],
            pinecone_index=current_app.config['PINECONE_INDEX'],
            llm_model=current_app.config['LLM_MODEL']
        )


    def get(self):
        file_id = request.args.get('file_id')
        namespace = request.args.get('namespace')
        if not file_id or not namespace:
            missing_params = []
            if not file_id:
                missing_params.append("file_id")
            if not namespace:
                missing_params.append("namespace")
            return jsonify({"error": f"Missing parameters: {', '.join(missing_params)}"}), 400

        question = "You are an expert financial analyst. You are analyzing financial report of a publicly listed company. Provide the company's summary by answering the following questions: (1) What is the name of the company? (2) What is the company's background? (3) What is its market strategy? (4) What are its products? (5) What was its consolidated result? (6) What is the company's guidance and outlook? (7) What were ist financial results including Total Revenue, EBITDA, Net Income (Loss), Total Assets, Total Liability, Cash and cash equivalent. Make sure that the financial results include the units, e.g., thousands or millions. The total length of the summary should be approximately 1000-1200 words. Provide the response in markdown format."

        try:
            answer = self.summarizer.summarize(file_id, namespace, question)
            return jsonify({"AIResponse": answer})
        except Exception as e:
            logging.error(f"Summarization failed: {e}")
            return jsonify({"error": str(e)}), 500
