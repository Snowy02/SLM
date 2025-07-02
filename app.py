Of course. Your manager's feedback is excellent and points to a crucial aspect of prompt engineering for graph databases. The LLM needs to know not just what nodes and relationships exist, but how they connect. Providing explicit relationship patterns is the key to improving query accuracy.

I will make the one necessary change to your graph_query_handler.py file to address this. The change will be exclusively inside the get_concise_schema method, as you requested.

The Problem

Your current get_concise_schema method lists node labels and relationship types separately.
Current Schema Output:

Generated code
Node Labels:
- Repository
- Class
- Controller
Relationships:
- HAS_CLASSES
- HAS_ROUTES


The LLM has to guess that the relationship is (Repository)-[:HAS_CLASSES]->(Class) and not, for example, (Controller)-[:HAS_CLASSES]->(Repository).

The Solution

We will modify get_concise_schema to query the database's schema visualization capabilities. This allows us to generate a list of explicit connection patterns, which is exactly what the LLM needs to see.

New Schema Output:

Generated code
Node Labels:
- Repository
- Class
- Controller

Relationship Patterns:
- (Repository)-[:HAS_CLASSES]->(Class)
- (Repository)-[:HAS_ROUTES]->(Controller)
... and so on
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
IGNORE_WHEN_COPYING_END

This removes all guesswork for the LLM and will significantly improve the quality of the generated Cypher queries.

Modified graph_query_handler.py

Here is your file with the single, targeted change in the get_concise_schema method. No other part of the code has been altered.

Generated python
import time
# Corrected typo in langchain imports
from langchain_community.graphs import Neo4jGraph
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.chains import GraphCypherQAChain
from langchain_core.output_parsers import StrOutputParser
from typing import List,Dict
from data_structures import Node
from enitites import entity


#prompt template specifically written for cypher generation
CYPHER_GENERATION_TEMPLATE="""
You are an expert Neo4j developer,skilled at writing precise and efficient Cypher queries.

<INSTRUCTUIONS>
1. Your task is to convert a user's question in natural language into a syntactically correct Cypher query.
2. Base your query ONLY on the schema provided. Do not use any node labels or relationship types not listed in the schema.
3. Pay close attention to the user's question to extract key entities and relationships. For repository names or class names, use the `name` property in your `WHERE` clause (e.g, `WHERE r.name = 'policyissuance'`).
4. Your response MUST be ONLY the Cypher query. Do not include any introduction text,explanations,or markdown backticks.
</INSTRUCTUIONS>

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

#self-correction mechanism if the query generation has failed previously
ERROR_CORRECTION_TEMPLATE="""
<CORRECTION>
The previous query you generated failed.
- **Failed Query:** `{cypher_query}`
- **Database Error:** `{error_message}`
- **Instructions:** Please analyze the error and the original question, then generate, then generate a new, correct Cypher query.
</CORRECTION>
"""

CODE_EXPLANATION_TEMPLATE="""
You are an expert dotnetcore & C# assistant. Given a code, you will explain each line of code line by line. Use a markdown for output.

Ensure each line of code is explained.

**code to explain is**
`{code}`

"""

INTENT_GENERATION_TEMPLATE="""
You are an expert natural lnaguage analyzer. You ca identify the intent of a user based on the question. You should respond in JSON format. The format of
response should be a json. The key should be called intent. The value can be either depndency or explantion.

<examples>
question: I am updating the DataStructure AccountRenewalSessionData. What is the potential impact
The json value should be dependency

question: Can you explain the code for method GetCustomer?
The json value should be explanation

question: I cannot understand thecode for class CustomerController?
The json value should be explanation

question: I am working on customer repository. I will change method GetCustomer. Qhat are the dependent classes and methods.
The json value should be dependency

</examples>
**user question is** `{query}`

**your response is**
"""

HTML_TABLE_GENERATOR_TEMPLATE="""
You are an expert HTML code generator assistant. Given a output of Neo4j query, you will generate a data table. Generate the html for the given output. Do not provide any explanation or context, respond with only relevant HTML code. Do not generate the Doctype declaration, html element, head section or body section. Just generate the table section.
Any styling should be part of the table, row or cell tag. Generate the table for entire output provided.

For more context, the neo4j query was {query}

The schema in neo4j is {schema}

**output** {output}

The html returned is:

"""

EXTRACT_ENTITY_TEMPLATE="""
You are an expert assistant that can identify the name of repository, class, methods, controllers, data structures etc from the user question.

This is the list of entity that are available in the system `{entity}`

Your job is to perform a exact match with the entity provided and extract entities listed in user question. If exact match returns zero results, the 
perform fuzzy match and provide top 3 match.

**user question is** `{question}`

Respond with the entities seperated by coma
"""


class GraphQueryHandler:
    graph=None
    concise_schema=None
    llm=None
    cypher_chain=None
    def __init__(self):
        if self.graph==None and self.concise_schema==None and self.llm==None and self.cypher_chain==None:
            try:
                self.graph = Neo4jGraph(
                    url="bolt://nausd-wapp0013.aceins.com:7687",
                    username="neo4j",
                    password="password"
                )
                self.concise_schema = self.get_concise_schema()
                self.llm = Ollama(model="devstral:24b",base_url="http://nausd-wapp021.aceins.com:11434", temperature=0)
                self.cypher_chain = (
                    PromptTemplate.from_template(CYPHER_GENERATION_TEMPLATE)
                    | self.llm
                    | StrOutputParser()
                )
            except Exception as e:
                raise ConnectionError(f"Failed to initialize GraphQueryHandler: {e}")
    def extract_result_for_query(self,query)->str:
        return self.graph.query(query)
    
    ### MODIFIED METHOD ###
    def get_concise_schema(self) -> str:
        """
        Generates a concise, summary schema focused on node labels and explicit 
        relationship patterns to guide the LLM effectively.
        """
        # Fetch all unique node labels
        node_labels_query = "CALL db.labels() YIELD label RETURN label"
        node_labels_result = self.graph.query(node_labels_query)
        node_labels = [row['label'] for row in node_labels_result]
        
        # Fetch all relationship patterns
        schema_query = "CALL db.schema.visualization()"
        schema_result = self.graph.query(schema_query)
        
        # The result of the visualization query is a list containing one dictionary
        if not schema_result:
            return "Could not retrieve schema."

        relationships = schema_result[0]['relationships']
        
        # Create a mapping from internal node ID to its primary label
        nodes = schema_result[0]['nodes']
        id_to_label = {node['id']: node['labels'][0] for node in nodes}

        # Use a set to store unique relationship patterns
        relationship_patterns = set()
        for rel in relationships:
            start_node_label = id_to_label.get(rel['startNode'], 'Unknown')
            end_node_label = id_to_label.get(rel['endNode'], 'Unknown')
            rel_type = rel['type']
            pattern = f"({start_node_label})-[:{rel_type}]->({end_node_label})"
            relationship_patterns.add(pattern)

        # Build the final schema string
        schema_str = "Node Labels:\n" + "- " + "\n- ".join(sorted(node_labels))
        schema_str += "\n\nRelationship Patterns:\n" + "- " + "\n- ".join(sorted(list(relationship_patterns)))
        
        return schema_str
    ### END OF MODIFIED METHOD ###

    def generate_html(self,query:str,output):
        prompt_template=PromptTemplate.from_template(HTML_TABLE_GENERATOR_TEMPLATE)
        print("Started")
        chain=prompt_template|self.llm|StrOutputParser()
        start_time=time.time()
        response=chain.invoke({"query":query,"schema":self.concise_schema,"output":output})
        end_time=time.time()
        print("Duration to get response: ",round(end_time-start_time,2))
        print("Ended")
        return response
    def explain_code(self,code:str):
        prompt_template=PromptTemplate.from_template(CODE_EXPLANATION_TEMPLATE)
        print("Started")
        chain=prompt_template|self.llm|StrOutputParser()
        start_time=time.time()
        response=chain.invoke({"code":code})
        end_time=time.time()
        print("Duration to get response: ",round(end_time-start_time,2))
        print("Ended")
        return response
    def identify_intent(self,question:str):
        prompt_template=PromptTemplate.from_template(INTENT_GENERATION_TEMPLATE)
        print("Started")
        chain=prompt_template|self.llm|StrOutputParser()
        start_time=time.time()
        response=chain.invoke({"query":question})
        end_time=time.time()
        print("Duration to get response: ",round(end_time-start_time,2))
        print("Ended")
        return response
    def extract_entities(self,question:str):
        prompt_template=PromptTemplate.from_template(EXTRACT_ENTITY_TEMPLATE)
        print("Started")
        chain=prompt_template|self.llm|StrOutputParser()
        start_time=time.time()
        response=chain.invoke({"question":question,"entity":entity})
        end_time=time.time()
        print("Duration to get response: ",round(end_time-start_time,2))
        print("Ended")
        return response
    def run_query(self, question: str, max_retries: int = 2):
        """
        Runs the natural language to Cypher conversion with a self-correction loop.
        """
        start_time = time.time()
        retries = 0
        error_message = ""
        generated_cypher = ""
        intermediate_steps = []
        #EXAMPLES
        examples = [
            { "question": "Find all classes in the repository 'exampleRepo'.", "query": "MATCH (r:Repository {name: 'exampleRepo'})-[:HAS_CLASSES]->(c:Class) RETURN c.name AS ClassName, c.file_path AS FilePath" },
            { "question": "Which repositories depend on the 'core-library' repository?", "query": "MATCH (r:Repository)-[:DEPENDS_ON]->(:Repository {name: 'core-library'}) RETURN r.name AS DependentRepository" },
            { "question": "List all methods in the 'UserService' class.", "query": "MATCH (:Class {name: 'UserService'})-[:HAS_METHOD]->(m:Method) RETURN m.name AS MethodName" },
            { "question": "What stored procedures does the 'BillingProcessor' class call?", "query": "MATCH (:Class {name: 'BillingProcessor'})-[:CALLS_SP]->(sp:StoredProcedure) RETURN sp.name AS StoredProcedure" },
            {"question":"What are the controllers in the 'api-getaway' repository?","query":"MATCH (r:Repository {name: 'api-gateway'})-[:HAS_CONTROLLER]->(c:Controller) RETURN c.name AS ControllerName, c.file_path AS FilePath"}
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
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END
