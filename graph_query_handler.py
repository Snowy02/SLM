# graph_query_handler.py

import os
import time
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import GraphCypherQAChain
from langchain_core.output_parsers import StrOutputParser

# --- A SUPERIOR PROMPT TEMPLATE ---
# This template is highly structured, using tags to guide the LLM.
# This structure is critical for reducing latency and improving accuracy.
CYPHER_GENERATION_TEMPLATE = """
You are an expert Neo4j developer, skilled at writing precise and efficient Cypher queries.

<INSTRUCTIONS>
1.  Your task is to convert a user's question in natural language into a syntactically correct Cypher query.
2.  Base your query ONLY on the schema provided. Do not use any node labels or relationship types not listed in the schema.
3.  Pay close attention to the user's question to extract key entities and relationships. For repository names or class names, use the `name` property in your `WHERE` clause (e.g., `WHERE r.name = 'policyissuance'`).
4.  Your response MUST be ONLY the Cypher query. Do not include any introductory text, explanations, or markdown backticks.
</INSTRUCTIONS>

<SCHEMA>
{schema}
</SCHEMA>

<EXAMPLES>
{examples}
</EXAMPLES>

<QUESTION>
{question}
</QUESTION>

{error_correction}

Cypher Query:
"""

# This template is used for the self-correction mechanism
ERROR_CORRECTION_TEMPLATE = """
<CORRECTION>
The previous query you generated failed.
- **Failed Query:** `{cypher_query}`
- **Database Error:** `{error_message}`
- **Instructions:** Please analyze the error and the original question, then generate a new, corrected Cypher query.
</CORRECTION>
"""


class GraphQueryHandler:
    def __init__(self):
        try:
            self.graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "password")
            )
            # Use a more specific query to get the schema structure
            self.concise_schema = self.get_concise_schema()
            self.llm = Ollama(model="devstral:24b", temperature=0)
            
            # Use a more direct chain, as we are building the prompt manually
            self.cypher_chain = (
                PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE)
                | self.llm
                | StrOutputParser()
            )

        except Exception as e:
            raise ConnectionError(f"Failed to initialize GraphQueryHandler: {e}")

    def get_concise_schema(self) -> str:
        """
        Generates a concise, summary schema focused on node labels and relationships.
        This is far more effective and token-efficient than the default schema dump.
        """
        node_labels = self.graph.query("CALL db.labels() YIELD label RETURN label")
        relationships = self.graph.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        
        schema_str = "Node Labels:\n" + "\n".join([f"- {row['label']}" for row in node_labels])
        schema_str += "\n\nRelationships:\n" + "\n".join([f"- {row['relationshipType']}" for row in relationships])
        
        return schema_str

    def run_query(self, question: str, max_retries: int = 2):
        """
        Runs the natural language to Cypher conversion with a self-correction loop.
        """
        start_time = time.time()
        retries = 0
        error_message = ""
        generated_cypher = ""
        intermediate_steps = []

        # We'll use your original examples, but format them better for the prompt.
        examples = [
            { "question": "Find all classes in the repository 'exampleRepo'.", "query": "MATCH (r:Repository {name: 'exampleRepo'})-[:HAS_CLASSES]->(c:Class) RETURN c.name AS ClassName, c.file_path AS FilePath" },
            { "question": "Which repositories depend on the 'core-library' repository?", "query": "MATCH (r:Repository)-[:DEPENDS_ON]->(:Repository {name: 'core-library'}) RETURN r.name AS DependentRepository" },
            { "question": "List all methods in the 'UserService' class.", "query": "MATCH (:Class {name: 'UserService'})-[:HAS_METHOD]->(m:Method) RETURN m.name AS MethodName" },
            { "question": "What stored procedures does the 'BillingProcessor' class call?", "query": "MATCH (:Class {name: 'BillingProcessor'})-[:CALLS_SP]->(sp:StoredProcedure) RETURN sp.name AS StoredProcedure" }
        ]
        
        # Format examples for injection into the prompt
        example_text = "\n\n".join([f"Question: {ex['question']}\nCypher: {ex['query']}" for ex in examples])

        while retries < max_retries:
            
            correction_prompt = ""
            if error_message:
                correction_prompt = ERROR_CORRECTION_TEMPLATE.format(
                    cypher_query=generated_cypher,
                    error_message=error_message
                )

            # Generate the Cypher query
            generated_cypher = self.cypher_chain.invoke({
                "schema": self.concise_schema,
                "examples": example_text,
                "question": question,
                "error_correction": correction_prompt
            }).strip()

            step_info = {
                "attempt": retries + 1,
                "cypher_query": generated_cypher
            }

            try:
                # Execute the query
                result = self.graph.query(generated_cypher)
                end_time = time.time()
                
                step_info["status"] = "Success"
                intermediate_steps.append(step_info)
                
                return {
                    "question": question,
                    "result": result,
                    "intermediate_steps": intermediate_steps,
                    "duration_seconds": round(end_time - start_time, 2),
                }
            except Exception as e:
                # This is the self-correction part
                retries += 1
                error_message = str(e)
                
                step_info["status"] = "Failed"
                step_info["error"] = error_message
                intermediate_steps.append(step_info)

        # If all retries fail
        end_time = time.time()
        return {
            "question": question,
            "result": f"Failed to execute a valid query after {max_retries} attempts. Last error: {error_message}",
            "intermediate_steps": intermediate_steps,
            "duration_seconds": round(end_time - start_time, 2),
        }
