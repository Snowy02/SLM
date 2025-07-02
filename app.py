import gradio as gr
import pandas as pd
import json
import html
from graph_query_handler1 import GraphQueryHandler
from data_Structures import Node
from typing import Dict, List

# --- Global Setup ---
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

# --- Utility Function to get the query handler ---
@gr.cache_resource
def get_query_handler():
    try:
        return GraphQueryHandler()
    except Exception as e:
        print(f"FATAL: Error connecting to Neo4j: {e}")
        gr.Error(f"**Failed to initiate connection to the graph database:** {e}")
        return None

# --- Main Application Logic ---
query_handler = get_query_handler()

if not query_handler:
    with gr.Blocks(theme=custom_theme) as demo:
        gr.HTML(title_html)
        gr.Error("Could not connect to the database. Please ensure the database is running and check the connection settings, then restart this application.")
    demo.launch()
    import sys
    sys.exit()

# ==============================================================================
# GRADIO UI AND LOGIC
# ==============================================================================
with gr.Blocks(theme=custom_theme) as demo:
    gr.HTML(title_html)

    # ============================ 1. DEFINE ALL UI COMPONENTS ============================
    with gr.Sidebar():
        gr.Label("Graph Schema")
        gr.Markdown("A concise summary of the graph schema provided to the LLM.")
        gr.Code(value=query_handler.concise_schema, language='plaintext', interactive=False)

    # --- Initial User Choice ---
    with gr.Row(visible=True) as main_page:
        user_option = gr.Radio(
            choices=["I am new to Marketplace", "I know what I am doing"],
            interactive=True,
            label="Who are you?"
        )

    # --- UI Components for "I AM NEW TO MARKETPLACE" (GUIDED MODE) ---
    # NOTE: All these components are now siblings, not nested in a separate gr.Blocks
    with gr.Row(visible=False) as repository_row:
        query_for_repositories = "MATCH (n:Repository) RETURN DISTINCT n"
        repository_nodes = query_handler.extract_result_for_query(query_for_repositories)
        repositories = [x["n"]["name"] for x in repository_nodes] if repository_nodes else []
        repository_radio = gr.Radio(repositories, label="Select Repository", interactive=True)

    with gr.Row(visible=False) as repository_action_row:
        REPOSITORY_ACTIONS = ["LIST CLASSES", "LIST DEPENDENCIES"]
        repository_action = gr.Radio(REPOSITORY_ACTIONS, label="What would you like to do?", interactive=True)

    with gr.Row(visible=False) as list_class_row:
        classes_radio_group = gr.Radio(choices=[], label="Select a Class", interactive=True)

    with gr.Row(visible=False) as list_dependencies_row:
        gr.Markdown("Dependency features for the entire repository can be complex. Please select a specific class first to see its dependencies.")

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
            code_output = gr.Code(label="Source Code", language="python", interactive=False, scale=1)
            explanation_output = gr.Markdown(label="LLM Explanation", scale=1)

    # --- UI Components for "I KNOW WHAT I AM DOING" (EXPERT MODE) ---
    with gr.Row(visible=False) as expert_mode_row:
        with gr.Column():
            gr.Markdown("## 🧠 Codebase Knowledge Graph Explorer (Expert Mode)")
            gr.Markdown("Ask a question about your codebase in natural language. The system will convert it to a Cypher query, execute it, and return the answer.")
            
            with gr.Row():
                expert_question_textbox = gr.Textbox(label="Enter your question here:", placeholder="e.g., 'What are the dependencies of the PaymentProcessor class?'", lines=4, scale=7)
                expert_run_button = gr.Button("Run Query", variant="primary", scale=1)
            
            with gr.Column(visible=False) as expert_results_col:
                expert_dataframe_output = gr.DataFrame(label="Query Result", visible=False, wrap=True)
                expert_html_output = gr.HTML(label="Query Details & Explanations")
    
    # --- Group components for easier visibility control ---
    guided_mode_components = [
        repository_row, repository_action_row, list_class_row, list_dependencies_row,
        class_action_row, dependencies_row, method_row, explain_code_row, code_explanation_tab
    ]
    expert_mode_components = [expert_mode_row]


    # ============================ 2. DEFINE ALL HANDLER FUNCTIONS ============================
    
    # --- Navigation Handler ---
    def navigation(option):
        updates = {}
        # Always hide the main choice page after a selection is made
        updates[main_page] = gr.update(visible=False)

        if option == "I am new to Marketplace":
            # Show the first step of the guided tour
            updates[repository_row] = gr.update(visible=True)
            # Hide all other guided components and all expert components
            for comp in guided_mode_components[1:] + expert_mode_components:
                updates[comp] = gr.update(visible=False)
        
        elif option == "I know what I am doing":
            # Show the expert mode row
            updates[expert_mode_row] = gr.update(visible=True)
            # Hide all guided components
            for comp in guided_mode_components:
                updates[comp] = gr.update(visible=False)
        
        return updates

    # --- Guided Mode Handlers (Unchanged) ---
    def repository_selected_by_user():
        return gr.update(visible=True, value=None) 

    def class_selected_by_user():
        return gr.update(visible=True, value=None)

    def repository_action_selected_by_user(repository, action):
        if action == "LIST CLASSES":
            query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN c.name as name"
            result = query_handler.extract_result_for_query(query)
            classes = [x["name"] for x in result] if result else []
            return gr.update(visible=True, choices=classes, value=None), gr.update(visible=False)
        elif action == "LIST DEPENDENCIES":
            return gr.update(visible=False, value=None), gr.update(visible=True)
        return gr.update(visible=False), gr.update(visible=False)

    def class_action_selected_by_user(repository, class_name, action, progress=gr.Progress(track_tqdm=True)):
        if not class_name:
            gr.Warning("Please select a class first!")
            return gr.update(visible=False), gr.update(visible=False), None, None, gr.update(visible=False)

        if action == "SHOW DEPENDENCIES":
            progress(0.1, desc="Querying dependencies...")
            query = f"MATCH (c:Class {{name : '{class_name}'}})-[r:HAS_METHOD]->(m:Method)-[r2:CALLS_METHOD]->(target:Method) RETURN c.name as Class, m.name as Method, type(r2) as Action, target.name as CalledMethod"
            result = query_handler.extract_result_for_query(query)
            if result:
                df = pd.DataFrame(result)
                html_code = df.to_html(index=False, justify='center', border=1, classes="gr-dataframe")
            else:
                html_code = "<p style='text-align:center; color:gray;'>No dependencies found for this class.</p>"
            return gr.update(visible=True), gr.update(visible=False), html_code, gr.update(choices=[], value=None), gr.update(visible=False)
        
        elif action == "SHOW METHODS":
            progress(0.1, desc="Querying methods...")
            query = f"MATCH (c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name as name"
            result = query_handler.extract_result_for_query(query)
            methods = [x["name"] for x in result] if result else []
            return gr.update(visible=False), gr.update(visible=True), None, gr.update(choices=methods, value=None), gr.update(visible=True)
        
        return gr.update(visible=False), gr.update(visible=False), None, gr.update(choices=[], value=None), gr.update(visible=False)

    def explain_code_button_handler(selected_methods, class_name):
        if not selected_methods:
            gr.Warning("Please select at least one method to explain.")
            return gr.update(visible=False), None, None
        
        method_to_explain = selected_methods[0]
        query = f"MATCH (c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method {{name: '{method_to_explain}'}}) RETURN m.source as source"
        result = query_handler.extract_result_for_query(query)

        if result and "source" in result[0]:
            source_code = result[0]["source"]
            code_explanation = query_handler.explain_code(source_code)
            return gr.update(visible=True), gr.update(value=source_code), gr.update(value=code_explanation)
        else:
            gr.Error("Could not retrieve source code for the selected method.")
            return gr.update(visible=False), None, None

    # --- Expert Mode Handler (Unchanged) ---
    def handle_expert_query(question, progress=gr.Progress(track_tqdm=True)):
        if not question or not question.strip():
            gr.Warning("Please enter a question before running the query.")
            return gr.update(visible=False), None, None

        progress(0, desc="Identifying intent...")
        try:
            response = query_handler.identify_intent(question)
            response_json = json.loads(response)
        except (json.JSONDecodeError, ValueError) as e:
            gr.Error(f"Failed to parse response from the language model: {e}")
            error_html = f"<p style='color:red;'>Error: Could not understand the model's response. Details: {html.escape(str(e))}</p>"
            return gr.update(visible=True), gr.update(visible=False), error_html

        intent = response_json.get("intent", "entity")
        
        if intent == "dependency":
            progress(0.3, desc="Generating & running Cypher query...")
            result_data = query_handler.run_query(question)
            intermediate_html = "<h3>Query Execution Details</h3>"
            intermediate_html += f"<b>Original Question:</b><p><i>{html.escape(result_data.get('question', 'N/A'))}</i></p>"
            for step in result_data.get('intermediate_steps', []):
                status_color = 'green' if step['status'] == 'Success' else 'red'
                intermediate_html += f"<hr><b>Attempt {step['attempt']}: <span style='color:{status_color};'>{step['status']}</span></b>"
                intermediate_html += f"<pre><code class='language-cypher'>{html.escape(step['cypher_query'])}</code></pre>"
                if step['status'] != 'Success':
                    intermediate_html += f"<p style='color:red;'><b>Error:</b> {html.escape(str(step['error']))}</p>"
            
            final_answer = result_data.get("result")
            df_update = gr.update(visible=False, value=None)
            if isinstance(final_answer, list) and final_answer:
                df_update = pd.DataFrame(final_answer)
            else:
                intermediate_html += "<hr><b>Final Result:</b><p>Query executed successfully but returned no results.</p>"
            
            return gr.update(visible=True), df_update, intermediate_html
        
        else:
            progress(0.3, desc="Extracting entities...")
            entities_str = query_handler.extract_entities(question)
            entities_arr = [e.strip() for e in entities_str.split(",") if e.strip()]
            
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
                        escaped_source = html.escape(node["source"])
                        explanation_html += f"<hr><h4>Explanation for: <code>{html.escape(node['name'])}</code></h4>"
                        explanation_html += f"<pre><code>{escaped_source}</code></pre>"
                        explanation_html += f"<div>{code_explanation}</div>"
            
            return gr.update(visible=True), gr.update(visible=False, value=None), explanation_html

    # ============================ 3. DEFINE ALL EVENT LISTENERS ============================
    
    # --- Main Navigation Event ---
    all_components = [main_page] + guided_mode_components + expert_mode_components
    user_option.change(
        fn=navigation,
        inputs=user_option,
        outputs=all_components
    )

    # --- Guided Mode Events ---
    repository_radio.change(fn=repository_selected_by_user, inputs=None, outputs=[repository_action_row])
    repository_action.change(fn=repository_action_selected_by_user, inputs=[repository_radio, repository_action], outputs=[list_class_row, list_dependencies_row])
    classes_radio_group.change(fn=class_selected_by_user, inputs=None, outputs=[class_action_row])
    class_action_radio_group.change(fn=class_action_selected_by_user, inputs=[repository_radio, classes_radio_group, class_action_radio_group], outputs=[dependencies_row, method_row, html_code_output, method_checkbox_group, explain_code_row])
    explain_code_button.click(fn=explain_code_button_handler, inputs=[method_checkbox_group, classes_radio_group], outputs=[code_explanation_tab, code_output, explanation_output])

    # --- Expert Mode Events ---
    expert_question_textbox.submit(fn=handle_expert_query, inputs=[expert_question_textbox], outputs=[expert_results_col, expert_dataframe_output, expert_html_output])
    expert_run_button.click(fn=handle_expert_query, inputs=[expert_question_textbox], outputs=[expert_results_col, expert_dataframe_output, expert_html_output])

# --- Launch the application ---
demo.launch(debug=True)
