# graph_query_handler.py

import os
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import GraphCypherQAChain

class GraphQueryHandler:
    def __init__(self):
        """Initializes the handler, connecting to Neo4j and the LLM."""
        # --- Connect to Neo4j ---
        try:
            self.graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "password")
            )
            self.graph.query("RETURN 1") # Test connection
            print("Successfully connected to Neo4j for querying.")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j for querying: {e}")

        # --- Load LLM ---
        try:
            # Ensure Ollama is running and the model is pulled.
            self.llm = Ollama(model="devstral:24b", temperature=0)
            print("LLM loaded successfully.")
        except Exception as e:
            raise ConnectionError(f"Failed to load LLM. Make sure Ollama is running. Error: {e}")
            
        # --- Define Prompt Template ---
        # This prompt is engineered to be direct and clear, telling the LLM its role
        # and constraints. It explicitly forbids apologies or explanations.
        CYPHER_GENERATION_TEMPLATE = """You are an expert Neo4j developer.
Your task is to generate a Cypher query for a given question based on the provided schema.
- Only use the node labels, relationship types, and properties mentioned in the schema.
- Do not use any other labels, types, or properties.
- Do not add explanations, apologies, or any text other than the Cypher query itself.
- Ensure the query is syntactically correct and returns meaningful results for the user's question.

Schema:
{schema}

Question:
{query}

Cypher Query:"""

        # --- Create the LangChain Chain ---
        # We use GraphCypherQAChain as it's designed for exactly this Text-to-Cypher task.
        self.chain = GraphCypherQAChain.from_llm(
            graph=self.graph,
            llm=self.llm,
            cypher_prompt=PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE),
            verbose=True, # Set to True to see the generated Cypher in the console
            validate_cypher=True, # Helps catch syntax errors early
        )
        
    def get_schema(self):
        """Returns the graph schema as a string."""
        return self.graph.get_schema

    def run_query(self, question: str):
        """
        Takes a natural language question, generates a Cypher query,
        executes it, and returns the result.
        """
        print(f"Running query for question: {question}")
        try:
            result = self.chain.invoke({"query": question})
            return result
        except Exception as e:
            print(f"An error occurred during query execution: {e}")
            return {
                "query": question, 
                "intermediate_steps": [{"query": "Error generating Cypher."}],
                "result": f"An error occurred: {e}. This could be an issue with the LLM or the database. Please check the console logs."
            }