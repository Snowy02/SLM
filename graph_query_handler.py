# graph_query_handler.py

import os
import time
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

# --- PROMPT TEMPLATES ---

# 1. Router Prompt: Classifies the user's intent.
ROUTER_TEMPLATE = """
You are an expert at understanding user questions about codebases.
Your task is to classify the user's question into one of two categories based on its intent:

1. `cypher`: The user is asking to find, list, count, or locate entities. These questions can be answered by a direct database query.
   Examples: "List all classes in the policyissuance repository.", "Which methods does the 'UserService' class have?", "Find repositories that depend on 'core-library'."

2. `explain`: The user is asking for an explanation, summary, or description of a code entity's functionality. This requires retrieving the code and then summarizing it.
   Examples: "Explain the functionality of the 'BillingProcessor' class.", "What does the 'AuthenticationService' do?", "Summarize the 'main' method in 'Program.cs'."

<QUESTION>
{question}
</QUESTION>

Category:
"""

# 2. Cypher Generation Prompt: Now includes instructions for explanation queries.
CYPHER_GENERATION_TEMPLATE = """
You are an expert Neo4j developer. Your task is to convert a user's question into a Cypher query based on the provided schema.

<INSTRUCTIONS>
1.  Base your query ONLY on the schema provided.
2.  For repository or class names, use the `name` property (e.g., `WHERE r.name = 'policyissuance'`).
3.  **IMPORTANT**: If the user's question is for an **explanation** of a class or method, you MUST retrieve its source code. The property is called `source`. For example: `RETURN c.name as name, c.source as source_code`.
4.  Your response MUST be ONLY the Cypher query. Do not include any text, explanations, or backticks.
</INSTRUCTIONS>

<SCHEMA>
{schema}
</SCHEMA>

<QUESTION>
{question}
</QUESTION>

Cypher Query:
"""

# 3. Explanation Prompt: A new prompt dedicated to code summarization.
EXPLANATION_TEMPLATE = """
You are a senior software engineer and an expert at explaining complex code in simple terms.
A user has asked a question about a class. You have been given the source code for that class.

<INSTRUCTIONS>
1.  Analyze the provided source code, including its properties, methods, and overall structure.
2.  Based on the code, provide a clear, concise, and helpful explanation that directly answers the user's question.
3.  Format your answer in Markdown for readability. Start with a high-level summary and then provide more detail if relevant (e.g., key responsibilities, important methods).
</INSTRUCTIONS>

<USER_QUESTION>
{question}
</USER_QUESTION>

<SOURCE_CODE>
{source_code}
</SOURCE_CODE>

Explanation:
"""


class GraphQueryHandler:
    def __init__(self):
        try:
            self.graph = Neo4jGraph(
                url=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                username=os.getenv("NEO4J_USERNAME", "neo4j"),
                password=os.getenv("NEO4J_PASSWORD", "password")
            )
            self.concise_schema = self.get_concise_schema()
            self.llm = Ollama(model="devstral:24b", temperature=0)

            # --- Define the Chains ---
            self.router_chain = (
                PromptTemplate.from_template(ROUTER_TEMPLATE) | self.llm | StrOutputParser()
            )
            self.cypher_chain = (
                PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE) | self.llm | StrOutputParser()
            )
            self.explanation_chain = (
                PromptTemplate.from_template(EXPLANATION_TEMPLATE) | self.llm | StrOutputParser()
            )

        except Exception as e:
            raise ConnectionError(f"Failed to initialize GraphQueryHandler: {e}")

    def get_concise_schema(self) -> str:
        # (This function remains unchanged from the previous version)
        node_labels = self.graph.query("CALL db.labels() YIELD label RETURN label")
        relationships = self.graph.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        schema_str = "Node Labels:\n" + "\n".join([f"- {row['label']}" for row in node_labels])
        schema_str += "\n\nRelationships:\n" + "\n".join([f"- {row['relationshipType']}" for row in relationships])
        return schema_str

    def run_query(self, question: str):
        """
        Orchestrates the query process based on recognized intent.
        """
        start_time = time.time()
        
        # --- Step 1: Classify Intent ---
        intent = self.router_chain.invoke({"question": question}).strip().lower()
        
        intermediate_steps = [{"recognized_intent": intent}]

        # --- Step 2: Route to the appropriate logic ---
        if intent == 'explain':
            # --- Explanation Path ---
            generated_cypher = self.cypher_chain.invoke({
                "schema": self.concise_schema,
                "question": question
            }).strip()
            intermediate_steps.append({"generated_cypher": generated_cypher})

            try:
                code_data = self.graph.query(generated_cypher)
                if not code_data:
                    return {"result": "I couldn't find the class you asked about. Please check the name and try again.", "intermediate_steps": intermediate_steps}

                # Assuming the first result is the one we want to explain
                source_code = code_data[0].get('source_code', '')
                if not source_code:
                     return {"result": f"I found the class '{code_data[0].get('name')}', but I couldn't find its source code to explain.", "intermediate_steps": intermediate_steps}

                explanation = self.explanation_chain.invoke({
                    "question": question,
                    "source_code": source_code
                })
                intermediate_steps.append({"status": "Generated Explanation"})
                
                return {
                    "result": explanation,
                    "intermediate_steps": intermediate_steps,
                    "duration_seconds": round(time.time() - start_time, 2)
                }

            except Exception as e:
                return {"result": f"An error occurred while trying to generate an explanation: {e}", "intermediate_steps": intermediate_steps}

        elif intent == 'cypher':
            # --- Cypher Path (Lookup) ---
            generated_cypher = self.cypher_chain.invoke({
                "schema": self.concise_schema,
                "question": question
            }).strip()
            intermediate_steps.append({"generated_cypher": generated_cypher})

            try:
                result = self.graph.query(generated_cypher)
                return {
                    "result": result,
                    "intermediate_steps": intermediate_steps,
                    "duration_seconds": round(time.time() - start_time, 2)
                }
            except Exception as e:
                 return {"result": f"The generated Cypher query failed: {e}. Query: {generated_cypher}", "intermediate_steps": intermediate_steps}
        else:
            return {"result": "I'm sorry, I'm not sure how to answer that question. I can find code entities or explain their functionality.", "intermediate_steps": intermediate_steps}
