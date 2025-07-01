Of course! I will walk you through this process with detailed, step-by-step instructions. We will go through it in two main phases:

Phase 1: Configure Your Postman "Engine" - This is where we set up the secure environment and the API calls. You only have to do this once.

Phase 2: Update Your Python Script - This is where we modify graph_query_handler.py to use the Postman engine we just built.

Let's begin.

Phase 1: Configure Your Postman "Engine"

Follow these steps inside your Postman application.

Step 1: Create the Secure Environment

The environment will hold your secret keys and the API URL. This keeps them safely out of your code.

Open Postman. On the left sidebar, click the Environments tab, then click the + button to create a new one.

Name the environment Prodigy LLM - Prod.

In the table, add the following variables. Fill in the CURRENT VALUE column with the credentials your manager gave you.

base_url: The main URL for the Prodigy API (e.g., https://api.prodigy.com)

app_id: Your application ID.

app_key: Your application secret key.

resource: The resource identifier.

bearer_token: Leave this value blank. Our script will fill it in automatically.

Your setup should look like this:

Click Save.

In the top-right corner of Postman, make sure your new Prodigy LLM - Prod environment is selected from the dropdown menu. This is a critical step!

Step 2: Create the API Collection

The collection will hold our two API requests: one for the token and one for the chat.

On the left sidebar, click the Collections tab, then click the + button.

Name the collection Prodigy LLM Chatbot.

Step 3: Create the "Get Auth Token" Request

Inside your Prodigy LLM Chatbot collection, click Add a request.

Name the request 1. Get Auth Token.

Change the request type from GET to POST.

Enter the URL for the token endpoint. We will use the base_url variable we created. You must replace /oauth2/token with the actual token endpoint path your manager provided.
{{base_url}}/oauth2/token

Go to the Body tab, select x-www-form-urlencoded, and add these key-value pairs. Notice how we use the {{...}} syntax to pull values from our environment:

KEY	VALUE
grant_type	client_credentials
client_id	{{app_id}}
client_secret	{{app_key}}
resource	{{resource}}

Now, go to the Tests tab. This script runs after the token is received. Copy and paste this exact JavaScript code into the Tests window. It extracts the token from the response and saves it to our environment.

Generated javascript
// This script runs AFTER the request is completed.
console.log("Parsing token response...");

// Check for a successful 200 OK response
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Parse the JSON response body
const responseJson = pm.response.json();

// Check if the access_token exists in the response
pm.test("Access token is present", function () {
    pm.expect(responseJson.access_token).to.not.be.empty;
});

// Save the access token to the active environment variable 'bearer_token'
if (responseJson.access_token) {
    pm.environment.set("bearer_token", responseJson.access_token);
    console.log("Bearer token saved to environment.");
} else {
    console.error("Failed to find access_token in the response.");
}


Click Save. You can click Send once to test it. If it works, you will see the bearer_token variable in your environment get populated.

Step 4: Create the "Query Chat API" Request

Add a second request to your collection and name it 2. Query Chat API.

Set the request type to POST.

Enter the URL for the chat endpoint: {{base_url}}/query/chat.

Go to the Headers tab and add the following keys and values:

KEY	VALUE
Authorization	Bearer {{bearer_token}}
api-version	1
Content-Type	application/json

Go to the Body tab, select raw, and from the dropdown menu that appears, choose JSON.

Paste the following JSON structure into the body. The {{prompt_content}} variable is a placeholder that our Python script will fill in.

Generated json
{
  "messages": [
    {
      "role": "user",
      "content": "{{prompt_content}}"
    }
  ],
  "temperature": 0.0
}
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Json
IGNORE_WHEN_COPYING_END

Click Save. Your Postman engine is now ready!

Phase 2: Update Your Python Script (graph_query_handler.py)

Now, we'll modify your Python code to call the Postman collection we just built.

Step 5: Prepare Your System and Project

Install Newman: Newman is the command-line tool that runs Postman collections. You need Node.js and npm installed for this. Open your terminal or command prompt and run:

Generated bash
npm install -g newman
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bash
IGNORE_WHEN_COPYING_END

Export Postman Files:

In Postman, right-click your Prodigy LLM Chatbot collection, select Export, and save the file as Prodigy_LLM_Chatbot.postman_collection.json in the same directory as your Python script.

Click the Environments tab, right-click your Prodigy LLM - Prod environment, select Export, and save the file as Prodigy_LLM_Prod.postman_environment.json in the same directory.

Step 6: Modify the graph_query_handler.py Script

Open your graph_query_handler.py file. We will replace the Ollama logic with our new Newman-based function. I will provide the complete, final script below. The comments highlight exactly what has been added or changed.

Here is the final, updated version of graph_query_handler.py. You can replace the entire contents of your file with this code.

Generated python
import time
import json
import subprocess # +++ ADDED +++ to run external commands
import shlex      # +++ ADDED +++ to safely format command arguments
from lnagchain_community.graphs import Neo4jGraph
from lnagchain.prompts import PromptTemplate
# from lnagchain_community.llms import Ollama # --- REMOVED ---
# from langchain.chains import GraphCypherQAChain # --- REMOVED ---
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any # +++ ADDED Any +++
from data_structures import Node
from enitites import entity


# No changes needed for your templates. They are perfect.
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

question: I cannot understand the code for class CustomerController?
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
    # --- REMOVED llm and cypher_chain from class attributes ---

    def __init__(self):
        # --- MODIFIED: Removed all LLM and LangChain initializations ---
        if self.graph is None:
            try:
                self.graph = Neo4jGraph(
                    url="bolt://nausd-wapp0013.aceins.com:7687",
                    username="neo4j",
                    password="password"
                )
                self.concise_schema = self.get_concise_schema()
            except Exception as e:
                raise ConnectionError(f"Failed to initialize GraphQueryHandler: {e}")

    # +++ ADDED THIS NEW CORE FUNCTION +++
    def _invoke_llm_via_postman(self, prompt_text: str) -> Dict[str, Any]:
        """
        Triggers the Postman collection via Newman to get an LLM response.
        This is the new "engine" for all LLM calls.
        """
        collection_path = "Prodigy_LLM_Chatbot.postman_collection.json"
        environment_path = "Prodigy_LLM_Prod.postman_environment.json"
        output_file = "newman-output.json"

        # 1. Construct the Newman command, safely injecting the prompt
        command = [
            "newman", "run", collection_path,
            "--environment", environment_path,
            "--env-var", f"prompt_content={shlex.quote(prompt_text)}",
            "--reporters", "json",
            "--reporter-json-export", output_file
        ]

        try:
            print("Executing Postman collection via Newman...")
            subprocess.run(command, check=True, capture_output=True)

            # 2. Read the result file created by Newman
            with open(output_file, 'r') as f:
                newman_result = json.load(f)

            # 3. Parse the Newman report to find the LLM's response
            # The response is in the body of the *second* request (index [1])
            raw_response_body = newman_result['run']['executions'][1]['response']['stream']['data']
            response_string = bytes(raw_response_body).decode('utf-8')
            llm_response_json = json.loads(response_string)

            # IMPORTANT: Adjust this path based on the actual Prodigy API response structure
            final_content = llm_response_json['choices'][0]['message']['content']
            
            return {"status": "success", "content": final_content.strip()}

        except subprocess.CalledProcessError as e:
            error_msg = f"Newman execution failed: {e.stderr.decode()}"
            print(error_msg)
            return {"status": "error", "content": error_msg}
        except (IOError, KeyError, IndexError, json.JSONDecodeError) as e:
            error_msg = f"Failed to parse Newman output file: {e}"
            print(error_msg)
            return {"status": "error", "content": error_msg}

    def extract_result_for_query(self,query)->str:
        return self.graph.query(query)
    
    def get_concise_schema(self) -> str:
        node_labels = self.graph.query("CALL db.labels() YIELD label RETURN label")
        relationships = self.graph.query("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType")
        schema_str = "Node Labels:\n" + "\n".join([f"- {row['label']}" for row in node_labels])
        schema_str += "\n\nRelationships:\n" + "\n".join([f"- {row['relationshipType']}" for row in relationships])
        return schema_str

    # --- MODIFIED: All methods below now use the new _invoke_llm_via_postman function ---
    def generate_html(self,query:str,output):
        prompt = HTML_TABLE_GENERATOR_TEMPLATE.format(query=query, schema=self.concise_schema, output=output)
        response = self._invoke_llm_via_postman(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def explain_code(self,code:str):
        prompt = CODE_EXPLANATION_TEMPLATE.format(code=code)
        response = self._invoke_llm_via_postman(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def identify_intent(self,question:str):
        prompt = INTENT_GENERATION_TEMPLATE.format(query=question)
        response = self._invoke_llm_via_postman(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def extract_entities(self,question:str):
        prompt = EXTRACT_ENTITY_TEMPLATE.format(question=question, entity=entity)
        response = self._invoke_llm_via_postman(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def run_query(self, question: str, max_retries: int = 2):
        start_time = time.time()
        retries = 0
        error_message = ""
        generated_cypher = ""
        intermediate_steps = []
        
        examples = [
            # ... your examples remain the same ...
        ]
        example_text = "\n\n".join([f"Question: {ex['question']}\nCypher: {ex['query']}" for ex in examples])

        while retries < max_retries:
            correction_prompt = ""
            if error_message:
                correction_prompt = ERROR_CORRECTION_TEMPLATE.format(
                    cypher_query=generated_cypher,
                    error_message=error_message
                )

            # 1. Construct the prompt
            prompt = CYPHER_GENERATION_TEMPLATE.format(
                schema=self.concise_schema,
                examples=example_text,
                question=question,
                error_correction=correction_prompt
            )

            # 2. Call the LLM via Postman/Newman
            llm_response = self._invoke_llm_via_postman(prompt)
            
            if llm_response["status"] == "error":
                return { "result": f"LLM invocation failed: {llm_response['content']}" }

            generated_cypher = llm_response["content"]
            
            step_info = {
                "attempt": retries + 1,
                "cypher_query": generated_cypher
            }

            try:
                # 3. Execute the query
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
                retries += 1
                error_message = str(e)
                step_info["status"] = "Failed"
                step_info["error"] = error_message
                intermediate_steps.append(step_info)

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

You are now all set. Your Python script no longer contains any LLM logic or credentials. It simply prepares a prompt and hands it off to your secure, reusable Postman "engine" to do the heavy lifting.
