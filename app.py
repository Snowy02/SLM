# web.py

import gradio as gr
from graph_query_handler1 import GraphQueryHandler
# I assume you have these defined elsewhere. If not, these are placeholders.
# from data_Structures import Node 
from typing import Dict, List

# --- Initialize Query Handler ---
# It's better to initialize this once at the start.
query_handler = GraphQueryHandler()

# --- THEME and TITLE (Unchanged) ---
custom_theme = gr.themes.Default(...)
title_html = """..."""

# --- Main Application UI ---
with gr.Blocks(theme=custom_theme) as demo:
    
    # --- Define Components First ---
    gr.HTML(title_html)
    
    # User journey selection
    with gr.Row(visible=True) as main_page:
        user_option = gr.Radio(
            choices=["I am new to Marketplace", "I know what I am doing"], 
            interactive=True, 
            label="Who are you?"
        )

    # --- REPOSITORY SELECTION ---
    with gr.Row(visible=False) as repository_row:
        # Fetch repositories once, not inside a function if possible
        try:
            repo_query = "MATCH (n:Repository) RETURN DISTINCT n.name as name"
            repositories = [x["name"] for x in query_handler.extract_result_for_query(repo_query)]
        except Exception as e:
            gr.Warning(f"Could not fetch repositories: {e}")
            repositories = ["Error fetching repos"]

        repository_radio = gr.Radio(repositories, label="Select Repository", elem_id="selected_repository")

    # --- REPOSITORY ACTION ---
    with gr.Row(visible=False) as repository_action_row:
        REPOSITORY_ACTIONS = ["LIST CLASSES", "LIST DEPENDENCIES"]
        repository_action = gr.Radio(REPOSITORY_ACTIONS, label="What do you want to do?")

    # --- CLASS LISTING ---
    with gr.Row(visible=False) as list_class_row:
        classes_radio_group = gr.Radio([], label="Select a Class", interactive=True)
    
    # --- CLASS ACTION ---
    with gr.Row(visible=False) as class_action_row:
        CLASS_ACTIONS = ['SHOW METHODS', 'SHOW DEPENDENCIES']
        class_action_radio_group = gr.Radio(CLASS_ACTIONS, label="What do you want to do with this class?")

    # --- METHOD LISTING ---
    with gr.Row(visible=False) as method_row:
        chkbox_group = gr.CheckboxGroup(choices=[], label="Select method(s) to explain")
        explain_code_button = gr.Button(variant="primary", value="Explain Selected Methods", interactive=True)

    # --- OUTPUT DISPLAYS ---
    with gr.Row(visible=False) as dependencies_row:
        html_code = gr.HTML()

    with gr.Tab(label="Code Explanation") as code_explanation_tab:
        with gr.Row():
            with gr.Column(scale=1):
                code_display = gr.Code(label="Source Code", language="csharp")
            with gr.Column(scale=1):
                explanation_display = gr.Markdown(label="LLM Explanation")

    # --- HANDLER FUNCTIONS ---
    
    def navigation(option):
        if option == "I am new to Marketplace":
            return gr.update(visible=False), gr.update(visible=True)
        # This seems to be the same, maybe it's a placeholder for future logic
        elif option == "I know what I am doing":
            return gr.update(visible=False), gr.update(visible=True)
        return gr.update(), gr.update()

    def repository_selected(repo_name):
        return gr.update(visible=True)

    ### REFACTORED: ADDED PROGRESS INDICATOR ###
    def handle_repository_action(repository, action, progress=gr.Progress()):
        progress(0, desc="Processing your request...")
        if action == "LIST CLASSES":
            progress(0.3, desc="Querying database for classes...")
            query = f'MATCH (:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class) RETURN DISTINCT c.name as name'
            result = query_handler.extract_result_for_query(query)
            classes = [x["name"] for x in result]
            progress(1, desc="Done!")
            # Show class list, hide dependency view
            return gr.update(visible=True, choices=classes), gr.update(visible=False)
        
        elif action == "LIST DEPENDENCIES":
            progress(0.3, desc="Querying database for dependencies...")
            query = f'MATCH (r:Repository {{name: "{repository}"}})-[:DEPENDS_ON]->(d:Repository) RETURN d.name as name'
            result = query_handler.extract_result_for_query(query)
            # Assuming you want to display this in the HTML component
            html_output = "<h3>Dependencies:</h3><ul>" + "".join([f"<li>{x['name']}</li>" for x in result]) + "</ul>"
            progress(1, desc="Done!")
            # Show dependency view, hide class list
            return gr.update(visible=False), gr.update(visible=True, value=html_output)
        return gr.update(), gr.update()

    def class_selected(class_name):
        # Simply reveal the next set of options
        return gr.update(visible=True)

    ### REFACTORED: ADDED PROGRESS INDICATOR ###
    def handle_class_action(repository, class_name, action, progress=gr.Progress()):
        progress(0, desc="Processing your request...")
        if action == "SHOW METHODS":
            progress(0.3, desc="Querying database for methods...")
            query = f'MATCH (:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(:Class {{name: "{class_name}"}})-[:HAS_METHOD]->(m:Method) RETURN m.name as name'
            result = query_handler.extract_result_for_query(query)
            methods = [x["name"] for x in result]
            progress(1, desc="Done!")
            # Show method list, hide dependency view
            return gr.update(visible=True, choices=methods), gr.update(visible=False)
        
        elif action == "SHOW DEPENDENCIES":
            progress(0.3, desc="Querying database for dependencies...")
            query = f'MATCH (:Class {{name: "{class_name}"}})-[:HAS_METHOD]->(m:Method)-[:CALLS_METHOD]->(target:Method) RETURN DISTINCT m.name as Method, target.name as Calls'
            result = query_handler.extract_result_for_query(query)
            # Create a simple HTML table for display
            html_output = "<h3>Method Dependencies:</h3><table border='1'><tr><th>Method</th><th>Calls</th></tr>"
            for row in result:
                html_output += f"<tr><td>{row['Method']}</td><td>{row['Calls']}</td></tr>"
            html_output += "</table>"
            progress(1, desc="Done!")
            # Show dependency view, hide method list
            return gr.update(visible=False), gr.update(visible=True, value=html_output)
        return gr.update(), gr.update()
    
    ### REFACTORED: ADDED PROGRESS INDICATOR ###
    def handle_explain_code(selected_methods, repository, class_name, progress=gr.Progress(track_tqdm=True)):
        if not selected_methods:
            gr.Warning("Please select at least one method to explain.")
            return None, None
        
        # A bit of a simplification: explain the first selected method for now.
        # Explaining multiple methods requires a more complex UI update.
        method_to_explain = selected_methods[0]
        
        progress(0.1, desc=f"Fetching source for '{method_to_explain}'...")
        query = f'MATCH (:Class {{name: "{class_name}"}})-[:HAS_METHOD]->(m:Method {{name: "{method_to_explain}"}}) RETURN m.source as source'
        result = query_handler.extract_result_for_query(query)
        
        if not result:
            gr.Error("Could not find the source code for the selected method.")
            return None, None
        
        source_code = result[0]["source"]
        
        progress(0.5, desc="LLM is analyzing the code...")
        # Assuming you have an `explain_code` method in your handler
        code_explanation = query_handler.explain_code(source_code)
        
        progress(1, desc="Explanation complete!")
        return source_code, code_explanation

    # --- Wire up Components to Handlers ---
    user_option.change(navigation, inputs=[user_option], outputs=[main_page, repository_row])
    repository_radio.change(repository_selected, inputs=[repository_radio], outputs=[repository_action_row])
    repository_action.change(
        handle_repository_action, 
        inputs=[repository_radio, repository_action], 
        outputs=[classes_radio_group, dependencies_row]
    )
    classes_radio_group.change(class_selected, inputs=[classes_radio_group], outputs=[class_action_row])
    class_action_radio_group.change(
        handle_class_action,
        inputs=[repository_radio, classes_radio_group, class_action_radio_group],
        outputs=[chkbox_group, dependencies_row]
    )
    explain_code_button.click(
        handle_explain_code,
        inputs=[chkbox_group, repository_radio, classes_radio_group],
        outputs=[code_display, explanation_display]
    )

demo.launch()
