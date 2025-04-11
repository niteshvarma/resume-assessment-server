import logging
import json
import os
import re
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import QueryFusionRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core.llms import ChatMessage
from llama_index.core import Settings
import nest_asyncio

Temp = (
    """
        - The list MUST include the following for each candidate in the response: candidate's name, latest job title, years of experience, Technical skills, Leadership skills, Current location, Resume ID (the doc_id of their resume)
        
        - Once the markdown response is generated, for each candidate in the list, hyperlink each candidate's name in the following format: {url}/resumedetails?ID=resume_id. Substitute resume_id in the hyperlink with the resume's doc_id. For example, if the doc_id is "Doc:91a7682d-cabe-4d03", the name is hyperlinked with "http://localhost:5001/resumedetails?ID=Doc:91a7682d-cabe-4d03".
        - Finally, delete the Resume Id from the markdown response before returning it.

        Here is an example response:
            1. **Remco Jorna**
                - Latest Job Title: ""
                - Total Years of Experience: ""
                - Technical Skills: ""
                - Leadership Skills: ""
                - Location: ""
                - Resume ID: Doc:91a7682d-cabe-4d03

            2. **David Jones**
                - Latest Job Title: ""
                - Total Years of Experience: ""
                - Technical Skills: ""
                - Leadership Skills: ""
                - Location: ""
                - Resume ID: ""

            """
)

class FusionRetrieverSearcher:
    def __init__(self):
        logging.debug("Initializing FusionRetrieverSearcher with OpenAI and Pinecone settings.")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index = os.getenv("PINECONE_INDEX")
        self.llm_model = os.getenv("LLM_MODEL")
        self.resume_details_popup_url = os.getenv("RESUME_DETAILS_POPUP_URL")
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        logging.debug("LLM model: " + self.llm_model)
        Settings.llm = OpenAI(model=self.llm_model, temperature=0.0)
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        Settings.embed_model = embed_model
        nest_asyncio.apply()
        logging.debug("FusionRetrieverSearcher initialized.")

    def search(self, namespace, query):
        logging.debug("Inside search method")
        url = self.resume_details_popup_url
        num_queries = 4


        fusion_search_response = self._search_with_fusion_retriever(namespace, num_queries,query)
        logging.debug(f"Search response: {fusion_search_response}")
        #hyperlinked_response = self._insert_hyperlinks(first_response, url)
        #return hyperlinked_response
        formatted_response = self._markdown_formatter(fusion_search_response, url)
        logging.debug(f"Formatted response: {formatted_response}")
        return formatted_response

    def _search_with_fusion_retriever(self, namespace, num_queries, query):
        FUSION_SEARCH_PROMPT = (
            """
            You are an expert resume analyzer. Extract matching candidates's information from the retrieved metadata within the context information **ONLY**.

            -----
            ## **🚨 STRICT INSTRUCTIONS (DO NOT IGNORE) 🚨**
            1. **ONLY use metadata fields provided in the context.**  
            2. **DO NOT invent or assume any missing details. If a field is missing, write `"N/A"` instead.**  
            3. **Ensure all metadata fields are extracted:**
                - Candidate Name
                - Latest Job Title
                - Career Domain
                - Total Years of Experience
                - Technical Skills
                - Leadership Skills
                - Highest Education Level
                - Current Location
                - Resume ID (doc_id)

            -----
            
            **💡 Example of Correct Output:**
            ```
            Candidate Name: John Doe
            Latest Job Title: Senior Software Engineer
            Career Domain: Software Development
            Total Years of Experience: 10
            Technical Skills: Python, AWS, Kubernetes
            Leadership Skills: Team Management, Agile
            Highest Education Level: Master's Degree
            Current Location: New York, USA
            Resume ID: Doc:1234
            ```

            **🚨 DO NOT OMIT any of these fields. If a field is missing, write "N/A".**

            -----
            
            **Input query:**  
            Query: {query}  

            **Context:**  
            {context_str}

            """
        )
        try:
            vector_store = PineconeVectorStore(
                index_name=self.pinecone_index, 
                api_key=self.pinecone_api_key, 
                namespace=namespace)
            vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
            
            retriever = QueryFusionRetriever(
                [vector_index.as_retriever()],
                similarity_top_k=5,
                num_queries=num_queries,  # set this to 1 to disable query generation
                use_async=True,
                verbose=True,
                query_gen_prompt= FUSION_SEARCH_PROMPT 
            )

            query_engine = RetrieverQueryEngine.from_args(retriever)
            logging.debug("Running query engine with question.")
                        
            result = query_engine.query(query)

            response_str = json.dumps(result.response)
            response_str = response_str.replace("\\n", "\n")  # Replace escaped newlines
            # Clean up leading/ending quotes and leading hyphen
            response_str = response_str.strip().strip('"').strip("'")  # Remove leading/trailing quotes
            response_str = re.sub(r"^-\s*", "", response_str)  # Remove leading hyphen with optional space
            logging.debug(f"Search response: {response_str}")
            return response_str
        except Exception as ex:
            logging.error(f"Error in search: {str(ex)}")
            raise

    def _insert_hyperlinks(self, raw_output_from_first_call, url):
        """
        Insert hyperlinks for each candidate name in the response.
        """
        HYPERLINKING_PROMPT = f"""
        You are a Markdown formatting assistant. Your task is to convert the given list of candidates into properly formatted Markdown.

        ## **Instructions (MUST FOLLOW)**
        1. **Format each candidate’s name as a Markdown hyperlink using this exact pattern:**
        [Candidate Name]({url}?ID=doc_id)
        For example: [John Doe]({url}?ID=Doc:1234)
        **Note: MUST be a clickable hyperlink**
        2. **Do not modify any other information in the list.**  
        3. **Ensure all Markdown syntax is correct and well-formed.**  
        4. **If a candidate already has a hyperlink, keep it unchanged.**  
        5. **Return ONLY the corrected Markdown list. Do NOT add explanations or extra text.**

        ---

        ### **Input List (Unformatted Candidates)**
        {raw_output_from_first_call}
        """


    def _markdown_formatter(self, raw_output, url):
        """
        Format the raw output into a Markdown list.
        """
        REFORMAT_PROMPT = (
            f"""
            Reformat the following resume data into valid Markdown.

            -----
            ## **STRICT INSTRUCTIONS:**
            1. **Format the output as a numbered Markdown list (`1.`, `2.`, etc.).**
            2. **Use the following structure for each candidate:**
            
            ```
            1. **[Candidate Name]({url}/resume?ID=<Doc ID>)**
                - **Latest Job Title:** <Job Title>
                - **Years of Experience:** <Years>
                - **Technical Skills:** <List of skills>
                - **Leadership Skills:** <List of skills>
                - **Current Location:** <Location>
                - **Resume ID:** <Doc ID>
            ```

            3. **DO NOT modify any candidate details.**  
            4. **DO NOT add explanations, extra text, or summaries.**  
            5. **Return ONLY valid Markdown (no additional formatting).**

            -----
            
            **Input resume data:**
            {raw_output}
            """
        )

        messages = [ChatMessage(role="system", content=REFORMAT_PROMPT )]
        resp = OpenAI().chat(messages)
        return resp

