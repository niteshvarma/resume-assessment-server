import os
import json
import logging
import uuid
from pinecone import Pinecone
from llama_index.vector_stores.pinecone import PineconeVectorStore
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex, StorageContext, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import IndexNode
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

logging.basicConfig(level=logging.DEBUG)


class PineconeVectorizer:
    def __init__(self) -> None:
        logging.debug("Initializing PineconeVectorizer")

        # OpenAI settings
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_llm = OpenAI(api_key=self.openai_api_key, model="gpt-4", temperature=0.0)
        llm_model = os.getenv('LLM_MODEL')
        Settings.llm = OpenAI(model=llm_model, temperature=0.0)
        embed_model = OpenAIEmbedding(model="text-embedding-ada-002")
        Settings.embed_model = embed_model

        # Pinecone settings
        self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
        self.pinecone_index_name = os.getenv('PINECONE_INDEX', 'default-index')
        #self.pinecone_namespace = os.getenv('PINECONE_NAMESPACE', 'resumes')

        # Initialize Pinecone connection
        self.pinecone_client = Pinecone(api_key=self.pinecone_api_key)

        # Configure the Pinecone vector store
        #self.vector_store = PineconeVectorStore(
        #    index_name=pinecone_index_name,
        #    api_key=pinecone_api_key,
        #    namespace=pinecone_namespace
        #)

    def vectorize_and_store_resume(self, resume_id: str, text_resume: dict, metadata: dict, tenant_id: str):
        """
        Vectorizes and stores the standardized resume and metadata in Pinecone.

        Args:
            resume_id (str): Unique identifier for the resume.
            text_resume (str): The standardized JSON representation of the resume.
            metadata (dict): Metadata extracted from the resume (e.g., latest job title, career domain, etc.).
        """
        try:
            logging.debug(f"Vectorizing and storing resume {resume_id}")
            logging.debug(f"Text resume:\n {text_resume}")
            logging.debug(f"Metadata:\n {metadata}")
            metadata["doc_id"] = resume_id
            logging.debug("Creating Document object for resume and metadata")
            resume_doc = Document(
                text=text_resume,
                metadata=metadata,
                id_=str(uuid.uuid4())
            )            

            # Initialize JsonNodeParser with custom settings
            logging.debug("Initializing Parser...")
            #json_node_parser = JSONNodeParser(
            #    include_metadata=True,      # Include metadata in each node
            #    include_prev_next_rel=True  # Maintain node relationships
            #)
            node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

            # Parse nodes using JSONNodeParser
            logging.debug("Parsing nodes from document...")
            nodes = node_parser.get_nodes_from_documents([resume_doc])
            logging.debug(f"Nodes parsed successfully: {len(nodes)} nodes found.")

            # Store nodes in Pinecone
            logging.debug("Storing nodes in Pinecone...")
            vectorstore = self.get_tenant_vectorestore(tenant_id)
            storage_ctx = StorageContext.from_defaults(vector_store=vectorstore)
            index = VectorStoreIndex(storage_context=storage_ctx, 
                                     nodes=[])
            index.insert_nodes(nodes)

            logging.debug(f"Resume {resume_id} successfully stored in Pinecone.")
        except Exception as e:
            logging.error(f"Error vectorizing and storing resume {resume_id}: {e}")
            raise

    def vectorize_and_store_text_resume(self, resume_id: str, 
                                   resume: str, 
                                   metadata: dict,
                                   tenant_id: str):
        """
        Vectorizes and stores the standardized resume and metadata in Pinecone.

        Args:
            resume_id (str): Unique identifier for the resume.
            standardized_resume (dict): The standardized JSON representation of the resume.
            metadata (dict): Metadata extracted from the resume (e.g., latest job title, career domain, etc.).
        """
        try:
            logging.debug(f"Vectorizing and storing resume {resume_id}")
            logging.debug(f"Standardized resume:\n {resume}")
            logging.debug(f"Metadata:\n {metadata}")
            metadata["doc_id"] = resume_id
            #resume_str = json.dumps(resume)
            logging.debug("Creating Document object for resume and metadata")
            resume_doc = Document(
                text=resume,
                metadata=metadata,
                id_=resume_id
            )            

            # Initialize JsonNodeParser with custom settings
            logging.debug("Initializing Parser...")
            #json_node_parser = JSONNodeParser(
            #    include_metadata=True,      # Include metadata in each node
            #    include_prev_next_rel=True  # Maintain node relationships
            #)

            logging.debug("Parsing nodes from document...")
            ##############
            # Ther following was the original working code (if the following code does not work, revert to this)
            node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

            # Parse nodes using JSONNodeParser
            nodes = node_parser.get_nodes_from_documents([resume_doc])
            ##############
            # Parse nodes recursively - added as a substitution for the above code
            #nodes = self._parse_recursively([resume_doc])
            ##############
            logging.debug(f"Nodes parsed successfully: {len(nodes)} nodes found.")

            # Store nodes in Pinecone
            logging.debug("Storing nodes in Pinecone...")
            vectorstore = self.get_tenant_vectorestore(tenant_id)

            storage_ctx = StorageContext.from_defaults(vector_store=vectorstore)
            index = VectorStoreIndex(storage_context=storage_ctx, 
                                     nodes=[])
            index.insert_nodes(nodes)

            logging.debug(f"Resume {resume_id} successfully stored in Pinecone.")

        except Exception as e:
            logging.error(f"Error vectorizing and storing resume {resume_id}: {e}")
            raise

    
    def delete_resume(self, resume_id: str, tenant_id: str):
        """
        Deletes a resume from the Pinecone index.

        Args:
            resume_id (str): Unique identifier for the resume.
        """
        try:
            logging.debug(f"Deleting resume {resume_id}")
            vectorstore = self.get_tenant_vectorestore(tenant_id)
            storage_ctx = StorageContext.from_defaults(vector_store=vectorstore)
            pinecone_index = VectorStoreIndex(storage_context=storage_ctx, nodes=[])
            pinecone_index.delete(resume_id)
            logging.debug(f"Resume {resume_id} successfully deleted from Pinecone.")
        except Exception as e:
            logging.error(f"Error deleting resume {resume_id}: {e}")
            raise

    def _parse_recursively(self, base_nodes):
        sub_chunk_sizes = [256, 512]
        sub_node_parsers = [
            SentenceSplitter(chunk_size=c, chunk_overlap=20) for c in sub_chunk_sizes
        ]

        all_nodes = []
        for base_node in base_nodes:
            for n in sub_node_parsers:
                sub_nodes = n.get_nodes_from_documents([base_node])
                sub_inodes = [
                    IndexNode.from_text_node(sn, base_node.node_id) for sn in sub_nodes
                ]
                all_nodes.extend(sub_inodes)

            # also add original node to node
            original_node = IndexNode.from_text_node(base_node, base_node.node_id)
            all_nodes.append(original_node)
        
        return all_nodes
    
    def get_tenant_vectorestore(self, tenant_id):
        """Returns the Pinecone namespace for the tenant."""
        pinecone_namespace = f"{tenant_id}_Resumes_NS"  # Per-tenant namespace
        vector_store = PineconeVectorStore(
            index_name=self.pinecone_index_name,
            api_key=self.pinecone_api_key,
            namespace=pinecone_namespace
        )
        return vector_store
