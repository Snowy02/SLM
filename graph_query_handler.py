# graph_query_handler.py

import os
import time
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain_core.output_parsers import StrOutputParser

### NEW: PROMPT TEMPLATES FOR THE NEW PIPELINE ###

# 1. Router Prompt: Classifies the user's intent. This is the first step.
ROUTER_TEMPLATE = """
You are an expert at classifying user questions about a software codebase.
Your task is to categorize the user's question into one of two types:

1. `cypher_lookup`: The user is asking to find, list, count, or locate entities.
   These questions can be answered by querying the graph structure.
   Examples: "List all classes in the policyissuance repository.", "Which methods does the 'UserService' class have?", "Find all controllers."

2. `method_explanation`: The user is asking for an explanation, summary, or description of a specific method's functionality.
   Examples: "Explain the functionality of the 'calculatePremium' method.", "What does the 'validateUser' method do?", "Summarize the 'ConnectToDatabase' method."

Based on the user's question below, provide one of the two category labels and nothing else.

<QUESTION>
{question}
</QUESTION>

Category:
"""

# 2. Cypher Generation Prompt: This is largely unchanged but its role is now clearer.
CYPHER_GENERATION_TEMPLATE = """
You are an expert Neo4j developer, skilled at writing precise and efficient Cypher queries.

<INSTRUCTIONS>
1.  Your task is to convert a user's question in natural language into a syntactically correct Cypher query.
2.  Base your query ONLY on the schema provided. Do not use any node labels or relationship types not listed in the schema.
3.  For repository, class, or method names, use the `name` property in a `WHERE` clause (e.g., `WHERE n.name = 'calculatePremium'`).
4.  If the user asks for an explanation of a method, you MUST generate a query to retrieve its `source` property. Example: `MATCH (m:Method {{name: 'calculatePremium'}}) RETURN m.source AS source_code`.
5.  Your response MUST be ONLY the Cypher query. Do not include any introductory text, explanations, or markdown backticks.
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

Cypher Query:
"""

# 3. Explanation Prompt: A new, dedicated prompt for code summarization.
EXPLANATION_TEMPLATE = """
You are a senior software engineer acting as a helpful code assistant.
Your task is to explain a method's functionality based on its source code.

<INSTRUCTIONS>
1.  Analyze the provided source code, including its name, parameters, logic, and any inline comments.
2.  Provide a clear, concise, and helpful explanation of what the method does, in a way that a non-expert could understand.
3.  Start with a high-level summary of the method's purpose.
4.  If the method is complex, you can use bullet points to describe its key steps or logic.
5.  Format your answer in clean Markdown.
</INSTRUCTIONS>

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

            ### NEW: INITIALIZE ALL REQUIRED CHAINS ###
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
        # (This function is unchanged and correct)
        node_labels = self.graph.query("CALL db.labels() YIELD label RETURN label")
        relationships = self.graph.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        schema_str = "Node Labels:\n" + "\n".join([f"- {row['label']}" for row in node_labels])
        schema_str += "\n\nRelationships:\n" + "\n".join([f"- {row['relationshipType']}" for row in relationships])
        return schema_str

    ### REFACTORED: run_query is now the main orchestrator/router ###
    def run_query(self, question: str):
        """
        Orchestrates the query process by first classifying the user's intent
        and then routing to the appropriate handler.
        """
        start_time = time.time()
        
        # Step 1: Use the router to determine the user's intent
        intent = self.router_chain.invoke({"question": question}).strip().lower()

        intermediate_steps = [{"recognized_intent": intent}]

        # Step 2: Route to the appropriate handler based on intent
        if intent == 'method_explanation':
            result = self._handle_method_explanation(question, intermediate_steps)
        elif intent == 'cypher_lookup':
            result = self._handle_cypher_lookup(question, intermediate_steps)
        else:
            result = {
                "result": "I'm sorry, I can only answer questions to find code entities or to explain specific methods.",
                "intermediate_steps": intermediate_steps
            }
        
        # Add duration and return
        result["duration_seconds"] = round(time.time() - start_time, 2)
        return result

    ### NEW: Handler for cypher lookups (contains your original logic) ###
    def _handle_cypher_lookup(self, question: str, intermediate_steps: list, max_retries: int = 1):
        """
        Handles questions that require a direct Cypher query to the graph.
        """
        retries = 0
        error_message = ""
        generated_cypher = ""
        
        # Your original few-shot examples are perfect for this path.
        examples = [
            { "question": "Find all classes in the repository 'exampleRepo'.", "query": "MATCH (r:Repository {name: 'exampleRepo'})-[:HAS_CLASSES]->(c:Class) RETURN c.name AS ClassName, c.file_path AS FilePath" },
            { "question": "Which repositories depend on 'core-library'?", "query": "MATCH (r:Repository)-[:DEPENDS_ON]->(:Repository {name: 'core-library'}) RETURN r.name AS DependentRepository" },
            { "question": "What are the controllers in 'api-gateway'?", "query": "MATCH (:Repository {name: 'api-gateway'})-[:HAS_ROUTES]->(c:Controller) RETURN c.name AS ControllerName" }
        ]
        example_text = "\n\n".join([f"Question: {ex['question']}\nCypher: {ex['query']}" for ex in examples])

        while retries <= max_retries:
            generated_cypher = self.cypher_chain.invoke({
                "schema": self.concise_schema,
                "examples": example_text,
                "question": question,
                "error_correction": "" # No self-correction for simplicity in this path for now
            }).strip()
            
            intermediate_steps.append({"cypher_query_generation_attempt": generated_cypher})
            try:
                # Execute the query
                result = self.graph.query(generated_cypher)
                intermediate_steps.append({"status": "Success"})
                return {"result": result, "intermediate_steps": intermediate_steps}
            except Exception as e:
                retries += 1
                error_message = str(e)
        
        return {"result": f"Failed to execute a valid query. Last error: {error_message}", "intermediate_steps": intermediate_steps}

    ### NEW: Handler for method explanations ###
    def _handle_method_explanation(self, question: str, intermediate_steps: list):
        """
        Handles questions asking to explain a method. This is a two-step process:
        1. Generate Cypher to fetch the method's source code.
        2. Use another LLM call to explain the source code.
        """
        # Step 1: Generate Cypher to get the source code
        # We don't need few-shot examples here as the task is very specific.
        fetch_code_cypher = self.cypher_chain.invoke({
            "schema": self.concise_schema,
            "examples": "", # No examples needed for this targeted task
            "question": question,
            "error_correction": ""
        }).strip()

        intermediate_steps.append({"fetch_code_cypher": fetch_code_cypher})

        # Step 2: Execute the query to get the code
        try:
            code_data = self.graph.query(fetch_code_cypher)
            if not code_data or 'source_code' not in code_data[0]:
                return {"result": "I found the method, but I couldn't retrieve its source code to explain.", "intermediate_steps": intermediate_steps}
            
            source_code = code_data[0]['source_code']
            intermediate_steps.append({"status": "Source code retrieved successfully."})

            # Step 3: Use the explanation chain to summarize the code
            explanation = self.explanation_chain.invoke({
                "source_code": source_code
            })
            
            return {"result": explanation, "intermediate_steps": intermediate_steps}

        except Exception as e:
            return {"result": f"An error occurred. I may have generated a bad query to find the method. Error: {e}", "intermediate_steps": intermediate_steps}
