import gradio as gr
import pandas as pd
import json
from graph_query_handler1 import GraphQueryHandler # Assuming graph_query_handler1 is the correct file
from data_Structures import Node
from typing import Dict, List

# --- Existing Gradio Setup ---
custom_theme = gr.themes.Default(
    primary_hue="blue",
    secondary_hue="green",
    neutral_hue="orange",
    text_size="sm",
    font="Comic Sans MS"
)

title_html = """
<div style="text-align: center; margin-top:20px;">
    <h1 style="background: linear-gradient(to right,red,orange,yellow,green,blue,indigo,violet); -webkit-background-clip: text; color:transparent;">
        Codebase Analytica
    </h1>
    <p style="font-size: 18px; color: gray;">Decoding Complexity, One Line at a Time</p>
</div>
"""

# --- Utility Functions ---
@gr.cache_resource
def get_query_handler():
    try:
        # This function is now used by both modes
        return GraphQueryHandler()
    except ConnectionError as e:
        print(f"Error connecting to Neo4j: {e}")
        # This will show an error at the top of the Gradio app if connection fails on startup
        gr.Error(f"**Failed to initiate connection to the graph database:** {e}")
        return None

# --- Main Application Logic ---
query_handler = get_query_handler()
if not query_handler:
    # If the handler fails to initialize, we stop the app from launching.
    raise ConnectionError("Could not connect to the database. Please check your connection and restart the application.")

# ==============================================================================
# HANDLER FUNCTIONS FOR THE "I AM NEW TO MARKETPLACE" (GUIDED) MODE
# ==============================================================================

def repository_selected_by_user(selected_option):
    print(selected_option)
    return gr.update(visible=True)

def class_selected_by_user(selected_option):
    return gr.update(visible=True), selected_option

def repository_action_selected_by_user(repository, action):
    print("The method arguments are: ", repository, action)
    query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN c"
    
    if action == "CODE EXPLANATION":
        # This part of the original code had 'pass', so keeping it simple.
        # You might want to show a specific UI for this.
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
    
    elif action == "LIST CLASSES":
        print("The repository value is: ", repository)
        result = query_handler.extract_result_for_query(query)
        classes = [x["c"]["name"] for x in result]
        print("The classes are: ", classes)
        return gr.update(visible=True), gr.update(choices=classes), gr.update(visible=False)
    
    elif action == "LIST DEPENDENCIES":
        # This part of the original code had 'pass', keeping it simple.
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    
    # Default return
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def class_action_selected_by_user(repository, class_name, action, progress=gr.Progress()):
    progress(0, desc="Starting")
    
    if action == "SHOW DEPENDENCIES":
        progress(0.1, desc="Querying dependencies...")
        query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class {{name : '{class_name}'}})-[r:HAS_METHOD]->(m:Method)-[r2:CALLS_METHOD]->(target:Method) RETURN c.name as Class, m.name as Method, type(r2) as Action, target.name as CalledMethod"
        result = query_handler.extract_result_for_query(query)
        progress(0.8, desc="Generating visualization...")
        # Note: generate_html was not provided, assuming it creates an HTML table or graph.
        # If result is a list of dicts, we can make a simple table here.
        if result:
            df = pd.DataFrame(result)
            html_code = df.to_html(index=False, justify='center', border=1)
        else:
            html_code = "<p>No dependencies found for this class.</p>"
        
        progress(1, desc="Done!")
        return gr.update(visible=True), gr.update(visible=False), gr.update(value=html_code), None, gr.update(visible=False)

    elif action == "SHOW METHODS":
        progress(0.1, desc="Querying methods...")
        query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name"
        result = query_handler.extract_result_for_query(query)
        methods = [x["m.name"] for x in result]
        progress(1, desc="Done!")
        return gr.update(visible=False), gr.update(visible=True), None, gr.update(choices=methods), gr.update(visible=True)
    
    # Default return if action is not matched
    return gr.update(visible=False), gr.update(visible=False), None, None, gr.update(visible=False)


def explain_code_button_handler(selected_methods, repository, class_name):
    print("Methods Selected: ", selected_methods)
    if not selected_methods:
        gr.Warning("Please select at least one method to explain.")
        return gr.update(visible=False), None, None

    # For simplicity, this example explains the first selected method.
    # You could loop and concatenate explanations if desired.
    method_to_explain = selected_methods[0]
    
    query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method {{name: '{method_to_explain}'}}) RETURN m.source"
    print("The query is: ", query)
    result = query_handler.extract_result_for_query(query)
    print("The match is:", result)

    if result and "m.source" in result[0]:
        source_code = result[0]["m.source"]
        code_explanation = query_handler.explain_code(source_code)
        print("The explanation is: ", code_explanation)
        return gr.update(visible=True), gr.update(value=source_code), gr.update(value=code_explanation)
    else:
        gr.Error("Could not retrieve source code for the selected method.")
        return gr.update(visible=False), gr.update(), gr.update()

# ==============================================================================
# HANDLER FUNCTION FOR "I KNOW WHAT I AM DOING" (EXPERT) MODE
# This function replicates the logic from your Streamlit app
# ==============================================================================
def handle_expert_query(question, progress=gr.Progress(track_ τότε=True)):
    if not question or not question.strip():
        gr.Warning("Please enter a question before running the query.")
        return {
            expert_results_col: gr.update(visible=False),
            expert_html_output: None,
            expert_dataframe_output: None
        }

    # Show the results column immediately
    outputs = {expert_results_col: gr.update(visible=True)}
    
    progress(0, desc="Identifying intent...")
    try:
        response = query_handler.identify_intent(question)
        response_json = json.loads(response)
    except (json.JSONDecodeError, ValueError) as e:
        gr.Error(f"Failed to parse response from the language model: {e}")
        outputs[expert_html_output] = gr.update(value="<p style='color:red;'>Error: Could not understand the model's response.</p>")
        outputs[expert_dataframe_output] = gr.update(visible=False)
        return outputs

    # --- PATH 1: Dependency Intent (like the main logic in Streamlit) ---
    if response_json.get("intent") == "dependency":
        progress(0.3, desc="Generating & running Cypher query...")
        result_data = query_handler.run_query(question)

        # Build HTML for intermediate steps
        intermediate_html = "<h3>Query Execution Details</h3>"
        intermediate_html += f"<b>Original Question:</b><p><i>{result_data.get('question', 'N/A')}</i></p>"
        for step in result_data.get('intermediate_steps', []):
            status_color = 'green' if step['status'] == 'Success' else 'red'
            intermediate_html += f"<hr><b>Attempt {step['attempt']}: <span style='color:{status_color};'>{step['status']}</span></b>"
            intermediate_html += f"<pre><code class='language-cypher'>{step['cypher_query']}</code></pre>"
            if step['status'] != 'Success':
                intermediate_html += f"<p style='color:red;'><b>Error:</b> {step['error']}</p>"

        # Display final answer
        final_answer = result_data.get("result")
        if isinstance(final_answer, list) and final_answer:
            outputs[expert_dataframe_output] = gr.update(value=pd.DataFrame(final_answer), visible=True)
            outputs[expert_html_output] = gr.update(value=intermediate_html)
        elif isinstance(final_answer, list) and not final_answer:
            intermediate_html += "<hr><b>Final Result:</b><p>Query executed successfully but returned no results.</p>"
            outputs[expert_html_output] = gr.update(value=intermediate_html)
            outputs[expert_dataframe_output] = gr.update(visible=False)
        else:
            intermediate_html += f"<hr><b>Final Result:</b><p>{final_answer}</p>"
            outputs[expert_html_output] = gr.update(value=intermediate_html)
            outputs[expert_dataframe_output] = gr.update(visible=False)

    # --- PATH 2: Entity/Code Explanation Intent ---
    else:
        progress(0.3, desc="Extracting entities...")
        entities_str = query_handler.extract_entities(question)
        entities_arr = [e.strip() for e in entities_str.split(",")]
        
        progress(0.6, desc="Querying graph for entities...")
        query = f"WITH {json.dumps(entities_arr)} AS names MATCH (n) WHERE n.name IN names RETURN n"
        result = query_handler.extract_result_for_query(query=query)
        
        explanation_html = "<h3>Code Explanations</h3>"
        if not result:
            explanation_html += "<p>Could not find any matching code elements for the entities found.</p>"
        else:
            for item in progress.tqdm(result, desc="Generating explanations..."):
                node = item.get("n", {})
                if 'source' in node and 'name' in node:
                    code_explanation = query_handler.explain_code(node["source"])
                    explanation_html += f"<hr><h4>Explanation for: <code>{node['name']}</code></h4>"
                    explanation_html += f"<pre><code>{node['source']}</code></pre>"
                    explanation_html += f"<div>{code_explanation}</div>" # Markdown in an HTML component needs to be rendered
        
        outputs[expert_html_output] = gr.update(value=explanation_html)
        outputs[expert_dataframe_output] = gr.update(visible=False)
        
    return outputs


# ==============================================================================
# UI NAVIGATION CONTROL
# ==============================================================================
def navigation(option):
    if option == "I am new to Marketplace":
        # Show the guided tour, hide the expert mode
        return {
            main_page: gr.update(visible=False),
            repository_row: gr.update(visible=True),
            expert_mode_row: gr.update(visible=False)
        }
    elif option == "I know what I am doing":
        # Show the expert mode, hide the guided tour
        return {
            main_page: gr.update(visible=False),
            repository_row: gr.update(visible=False),
            expert_mode_row: gr.update(visible=True)
        }
    # Default case
    return {
        main_page: gr.update(visible=True),
        repository_row: gr.update(visible=False),
        expert_mode_row: gr.update(visible=False)
    }

# ==============================================================================
# GRADIO UI LAYOUT
# ==============================================================================
with gr.Blocks(theme=custom_theme) as demo:
    gr.HTML(title_html)

    with gr.Sidebar():
        gr.Label("Graph Schema")
        gr.Markdown("A concise summary of the graph schema provided to the LLM.")
        gr.Code(query_handler.concise_schema, language='text', interactive=False)

    # --- Initial User Choice ---
    with gr.Row(visible=True) as main_page:
        user_option = gr.Radio(
            choices=["I am new to Marketplace", "I know what I am doing"],
            interactive=True,
            label="Who are you?"
        )

    # --------------------------------------------------------------------------
    # UI ROWS FOR "I AM NEW TO MARKETPLACE" (GUIDED MODE)
    # --------------------------------------------------------------------------
    with gr.Row(visible=False) as repository_row:
        query_for_repositories = "MATCH (n:Repository) RETURN DISTINCT n"
        repository_nodes: List[Dict[str, Node]] = query_handler.extract_result_for_query(query_for_repositories)
        repositories = [x["n"]["name"] for x in repository_nodes] if repository_nodes else []
        repository_radio = gr.Radio(repositories, label="Select Repository", interactive=True)

    with gr.Row(visible=False) as repository_action_row:
        REPOSITORY_ACTIONS = ["LIST CLASSES", "LIST DEPENDENCIES", "CODE EXPLANATION"]
        repository_action = gr.Radio(REPOSITORY_ACTIONS, label="What would you like to do?", interactive=True)

    with gr.Row(visible=False) as list_class_row:
        classes_radio_group = gr.Radio(choices=[], label="Select a Class", interactive=True)

    with gr.Row(visible=False) as list_dependencies_row:
        gr.Markdown("Dependency features for the entire repository can be complex. Please select a class first.")

    with gr.Row(visible=False) as class_action_row:
        CLASS_ACTIONS = ['SHOW METHODS', 'SHOW DEPENDENCIES']
        class_action_radio_group = gr.Radio(CLASS_ACTIONS, label="Select Action for the chosen class", interactive=True)

    with gr.Row(visible=False) as dependencies_row:
        html_code_output = gr.HTML(label="Class Dependencies")

    with gr.Row(visible=False) as method_row:
        method_checkbox_group = gr.CheckboxGroup(choices=[], label="Select Methods to Explain")
    
    with gr.Row(visible=False) as explain_code_row:
        explain_code_button = gr.Button(variant="primary", value="Explain Selected Code", interactive=True)

    with gr.Tab(label="Code Explanation", visible=False) as code_explanation_tab:
        with gr.Row():
            with gr.Column(scale=1):
                code_output = gr.Code(label="Source Code", language="python", interactive=False)
            with gr.Column(scale=1):
                explanation_output = gr.Markdown(label="LLM Explanation")

    # --------------------------------------------------------------------------
    # UI ROWS FOR "I KNOW WHAT I AM DOING" (EXPERT MODE)
    # --------------------------------------------------------------------------
    with gr.Row(visible=False) as expert_mode_row:
        with gr.Column():
            gr.Markdown("## 🧠 Codebase Knowledge Graph Explorer")
            gr.Markdown("Ask a question about your codebase in natural language. The system will convert it to a Cypher query, execute it, and return the answer.")
            
            expert_question_textbox = gr.Textbox(
                label="Enter your question here:",
                placeholder="e.g., 'What are the dependencies of the PaymentProcessor class?' or 'Explain the process_payment method'",
                lines=4
            )
            
            expert_run_button = gr.Button("Run Query", variant="primary")
            
            with gr.Column(visible=False) as expert_results_col:
                expert_dataframe_output = gr.DataFrame(label="Final Answer", visible=True, wrap=True)
                expert_html_output = gr.HTML(label="Query Details & Explanations")


    # ==============================================================================
    # EVENT LISTENERS
    # ==============================================================================

    # --- Main Navigation Event ---
    all_guided_rows = [repository_row, repository_action_row, list_class_row, list_dependencies_row, class_action_row, dependencies_row, method_row, explain_code_row, code_explanation_tab]
    
    user_option.change(
        fn=navigation,
        inputs=user_option,
        outputs=[main_page, repository_row, expert_mode_row] + all_guided_rows # Ensure all are controlled
    )

    # --- Guided Mode Events ---
    repository_radio.change(
        fn=repository_selected_by_user,
        inputs=repository_radio,
        outputs=[repository_action_row]
    )
    repository_action.change(
        fn=repository_action_selected_by_user,
        inputs=[repository_radio, repository_action],
        outputs=[list_class_row, classes_radio_group, list_dependencies_row]
    )
    classes_radio_group.change(
        fn=class_selected_by_user,
        inputs=classes_radio_group,
        outputs=[class_action_row]
    )
    class_action_radio_group.change(
        fn=class_action_selected_by_user,
        inputs=[repository_radio, classes_radio_group, class_action_radio_group],
        outputs=[dependencies_row, method_row, html_code_output, method_checkbox_group, explain_code_row]
    )
    explain_code_button.click(
        fn=explain_code_button_handler,
        inputs=[method_checkbox_group, repository_radio, classes_radio_group],
        outputs=[code_explanation_tab, code_output, explanation_output]
    )

    # --- Expert Mode Event ---
    expert_run_button.click(
        fn=handle_expert_query,
        inputs=[expert_question_textbox],
        outputs=[expert_results_col, expert_html_output, expert_dataframe_output]
    )

demo.launch(debug=True)
