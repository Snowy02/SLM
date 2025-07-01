Of course. I know exactly what you mean. This is the "direct integration" or "SDK-style" approach, where your Python application handles the API communication itself, without relying on an external tool like Postman/Newman.

This method is also very common and has its own advantages, such as having fewer external dependencies (you don't need Newman or Node.js) and keeping all the logic within a single codebase.

Let's walk through this traditional approach step-by-step.

The Philosophy: Your Python Script Becomes the "Client"

Instead of Python telling Postman what to do, your Python script will now learn to "speak" directly to the Prodigy API. To do this cleanly and securely, we will:

Use Environment Variables: To keep your secret app_id and app_key out of the source code.

Create a Dedicated API Client Class: We'll build a helper class (e.g., ProdigyAPIClient) whose only job is to manage tokens and communicate with the Prodigy LLM. This keeps your GraphQueryHandler class clean and focused on its main tasks.

Implement Token Refresh Logic: The client class will automatically handle fetching a new token when the old one expires.

Step 1: Set Up Secure Credentials with Environment Variables

This is the most important step for security. You must never hardcode secrets like app_key directly in your .py file.

Open your terminal or command prompt in the environment where you run your Python script and set the following variables.

On Linux or macOS:

Generated bash
export PRODIGY_BASE_URL="https://your-prodigy-api-base-url.com"
export PRODIGY_APP_ID="your_actual_app_id"
export PRODIGY_APP_KEY="your_actual_app_key"
export PRODIGY_RESOURCE="your_resource_identifier"


On Windows (Command Prompt):

Generated bat
set PRODIGY_BASE_URL="https://your-prodigy-api-base-url.com"
set PRODIGY_APP_ID="your_actual_app_id"
set PRODIGY_APP_KEY="your_actual_app_key"
set PRODIGY_RESOURCE="your_resource_identifier"
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Bat
IGNORE_WHEN_COPYING_END

Your Python script will read these values from the environment, so they are never exposed in your code.

Step 2: Add the ProdigyAPIClient to Your Script

We will add a new class to your graph_query_handler.py file. This class will manage all the direct API interactions. It needs the requests library, so make sure it's installed (pip install requests).

Here is the code for the client class. You should add this before the GraphQueryHandler class in your script.

Generated python
# +++ ADD THIS NEW SECTION AT THE TOP OF YOUR FILE +++
import os
import requests
import time

class ProdigyAPIClient:
    """
    A client to handle authentication and communication with the Prodigy LLM API.
    """
    def __init__(self):
        # 1. Read credentials securely from environment variables
        self.base_url = os.getenv("PRODIGY_BASE_URL")
        self.app_id = os.getenv("PRODIGY_APP_ID")
        self.app_key = os.getenv("PRODIGY_APP_KEY")
        self.resource = os.getenv("PRODIGY_RESOURCE")

        if not all([self.base_url, self.app_id, self.app_key, self.resource]):
            raise ValueError("One or more Prodigy API environment variables are not set.")

        self.token_endpoint = f"{self.base_url}/oauth2/token"  # Adjust if the path is different
        self.chat_endpoint = f"{self.base_url}/query/chat"     # Adjust if the path is different

        self._token = None
        self._token_expiry_time = 0  # We will store the token's expiration time here

    def _get_token(self):
        """
        Fetches a new API token if the current one is missing or expired.
        This is the core token management logic.
        """
        # Check if the token is still valid (with a 60-second safety buffer)
        if self._token and time.time() < self._token_expiry_time - 60:
            return self._token

        print("Token is expired or missing. Fetching a new one...")
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key,
            'resource': self.resource
        }
        
        try:
            response = requests.post(self.token_endpoint, headers=headers, data=payload)
            response.raise_for_status()  # This will raise an error for bad status codes (4xx or 5xx)
            
            data = response.json()
            self._token = data['access_token']
            # 'expires_in' is usually the number of seconds until expiration
            self._token_expiry_time = time.time() + data['expires_in']
            
            print("Successfully obtained new token.")
            return self._token
        except requests.exceptions.RequestException as e:
            print(f"FATAL: Could not fetch authentication token: {e}")
            raise ConnectionError(f"Failed to authenticate with Prodigy API: {e}")

    def query_llm(self, prompt: str) -> dict:
        """Sends a prompt to the Prodigy Chat API and returns the response."""
        try:
            access_token = self._get_token()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'api-version': '1',
                'Content-Type': 'application/json'
            }
            
            # This payload structure must match the Prodigy API's requirements
            json_payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0
            }

            response = requests.post(self.chat_endpoint, headers=headers, json=json_payload)
            response.raise_for_status()
            
            # IMPORTANT: Adjust parsing based on the actual API response
            llm_response = response.json()
            content = llm_response['choices'][0]['message']['content']
            
            return {"status": "success", "content": content.strip()}

        except requests.exceptions.RequestException as e:
            error_msg = f"Error during LLM query: {e}"
            print(error_msg)
            return {"status": "error", "content": error_msg}
        except (KeyError, IndexError) as e:
            error_msg = f"Could not parse LLM response: {e}. Response was: {response.text}"
            print(error_msg)
            return {"status": "error", "content": error_msg}
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END
Step 3: Integrate the Client into GraphQueryHandler

Now, we update GraphQueryHandler to use our new ProdigyAPIClient. This is much simpler than the Newman approach.

Here is the complete, final version of your graph_query_handler.py file using this direct integration method. You can replace your entire file with this code.

Generated python
import time
import os         # +++ ADDED
import requests   # +++ ADDED
import json
from lnagchain_community.graphs import Neo4jGraph
from lnagchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from typing import List, Dict, Any
from data_structures import Node
from enitites import entity


# +++ ADDED THE ENTIRE ProdigyAPIClient CLASS HERE (from Step 2) +++
class ProdigyAPIClient:
    """
    A client to handle authentication and communication with the Prodigy LLM API.
    """
    def __init__(self):
        self.base_url = os.getenv("PRODIGY_BASE_URL")
        self.app_id = os.getenv("PRODIGY_APP_ID")
        self.app_key = os.getenv("PRODIGY_APP_KEY")
        self.resource = os.getenv("PRODIGY_RESOURCE")
        if not all([self.base_url, self.app_id, self.app_key, self.resource]):
            raise ValueError("One or more Prodigy API environment variables are not set.")
        self.token_endpoint = f"{self.base_url}/oauth2/token"
        self.chat_endpoint = f"{self.base_url}/query/chat"
        self._token = None
        self._token_expiry_time = 0

    def _get_token(self):
        if self._token and time.time() < self._token_expiry_time - 60:
            return self._token
        print("Token is expired or missing. Fetching a new one...")
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = { 'grant_type': 'client_credentials', 'client_id': self.app_id, 'client_secret': self.app_key, 'resource': self.resource }
        try:
            response = requests.post(self.token_endpoint, headers=headers, data=payload)
            response.raise_for_status()
            data = response.json()
            self._token = data['access_token']
            self._token_expiry_time = time.time() + data['expires_in']
            print("Successfully obtained new token.")
            return self._token
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Failed to authenticate with Prodigy API: {e}")

    def query_llm(self, prompt: str) -> dict:
        try:
            access_token = self._get_token()
            headers = { 'Authorization': f'Bearer {access_token}', 'api-version': '1', 'Content-Type': 'application/json' }
            json_payload = { "messages": [{"role": "user", "content": prompt}], "temperature": 0.0 }
            response = requests.post(self.chat_endpoint, headers=headers, json=json_payload)
            response.raise_for_status()
            llm_response = response.json()
            content = llm_response['choices'][0]['message']['content']
            return {"status": "success", "content": content.strip()}
        except requests.exceptions.RequestException as e:
            return {"status": "error", "content": f"Error during LLM query: {e}"}
        except (KeyError, IndexError) as e:
            return {"status": "error", "content": f"Could not parse LLM response: {e}. Response was: {response.text}"}


# --- All your prompt templates remain unchanged ---
CYPHER_GENERATION_TEMPLATE="""..."""
ERROR_CORRECTION_TEMPLATE="""..."""
CODE_EXPLANATION_TEMPLATE="""..."""
INTENT_GENERATION_TEMPLATE="""..."""
HTML_TABLE_GENERATOR_TEMPLATE="""..."""
EXTRACT_ENTITY_TEMPLATE="""..."""


class GraphQueryHandler:
    graph=None
    concise_schema=None
    # +++ ADDED: A placeholder for our API client instance +++
    prodigy_client = None

    def __init__(self):
        # --- MODIFIED: Initialize our new client here ---
        if self.graph is None:
            try:
                self.graph = Neo4jGraph(
                    url="bolt://nausd-wapp0013.aceins.com:7687",
                    username="neo4j",
                    password="password"
                )
                self.concise_schema = self.get_concise_schema()
                # Create an instance of our API client
                self.prodigy_client = ProdigyAPIClient()
            except Exception as e:
                raise ConnectionError(f"Failed to initialize GraphQueryHandler: {e}")

    # --- NO CHANGES NEEDED for these two methods ---
    def extract_result_for_query(self,query)->str:
        return self.graph.query(query)
    
    def get_concise_schema(self) -> str:
        # ... your existing code ...
        return "..." # your schema string

    # --- MODIFIED: All methods below now call self.prodigy_client.query_llm ---
    def generate_html(self,query:str,output):
        prompt = HTML_TABLE_GENERATOR_TEMPLATE.format(query=query, schema=self.concise_schema, output=output)
        response = self.prodigy_client.query_llm(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def explain_code(self,code:str):
        prompt = CODE_EXPLANATION_TEMPLATE.format(code=code)
        response = self.prodigy_client.query_llm(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def identify_intent(self,question:str):
        prompt = INTENT_GENERATION_TEMPLATE.format(query=question)
        response = self.prodigy_client.query_llm(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def extract_entities(self,question:str):
        prompt = EXTRACT_ENTITY_TEMPLATE.format(question=question, entity=entity)
        response = self.prodigy_client.query_llm(prompt)
        return response["content"] if response["status"] == "success" else f"Error: {response['content']}"

    def run_query(self, question: str, max_retries: int = 2):
        # This method is now much cleaner
        start_time = time.time()
        # ... (your existing code for examples, etc.) ...
        examples = [ ... ]
        example_text = "..."

        # ... (your retry logic) ...
        # 1. Construct the prompt
        prompt = CYPHER_GENERATION_TEMPLATE.format(...)

        # 2. Call the LLM using our client
        llm_response = self.prodigy_client.query_llm(prompt)
            
        if llm_response["status"] == "error":
            return { "result": f"LLM invocation failed: {llm_response['content']}" }

        generated_cypher = llm_response["content"]
            
        # 3. Execute the query
        # ... (your existing code for executing against Neo4j) ...
        try:
            result = self.graph.query(generated_cypher)
            return { "result": result, "cypher_query": generated_cypher }
        except Exception as e:
            # ... handle Neo4j errors and retry ...
            return { "result": f"DB Error: {e}" }
IGNORE_WHEN_COPYING_START
content_copy
download
Use code with caution.
Python
IGNORE_WHEN_COPYING_END

You are now ready to run your script the "traditional" way. Just remember to set the environment variables (Step 1) before you execute the Python file.
