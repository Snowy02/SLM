Of course. As an expert in Gradio and Streamlit, I can guide you through this migration and integration process. It's a common and excellent architectural decision to unify disparate apps into a single, cohesive Gradio application.

Let's break this down step-by-step.

✅ 1. Analysis: Converting Streamlit (app.py) to Gradio

First, we'll analyze the components and logic of your Streamlit app and map them to their Gradio equivalents.

Streamlit Component/Concept	Gradio Equivalent	Analysis & Notes
st.title, st.markdown	gr.Markdown()	Straightforward conversion. Gradio's Markdown supports HTML for advanced styling.
st.text_area(...)	gr.Textbox(lines=5, ...)	gr.Textbox is the equivalent for multi-line text input.
st.button(...)	gr.Button(...)	Both are core components. The event handling is different (on_click vs. .click()).
with st.spinner(...)	Automatic on .click() / gr.Progress()	Gradio buttons show a loading animation by default. For more detailed progress, we'll use gr.Progress.
st.write, st.info, st.error	gr.Markdown, gr.HTML, gr.Error	We can use Markdown for most text outputs. gr.Error is for throwing noticeable error popups.
st.code(...)	gr.Code(...)	Direct one-to-one mapping for displaying code snippets.
st.dataframe(...)	gr.Dataframe(...)	Direct one-to-one mapping for displaying Pandas DataFrames.
st.expander(...)	gr.Accordion(...)	gr.Accordion is the Gradio component for creating collapsible sections.
st.metric(...)	gr.Textbox(...) or gr.Markdown()	Gradio doesn't have a dedicated "metric" component, but this is easily replicated with a styled Textbox or Markdown inside a gr.Row.
@st.cache_resource	Global variable instantiation	The simplest way to replicate resource caching in Gradio is to initialize the object (like your GraphQueryHandler) once at the start of the script. It will be shared across all user sessions.
st.session_state	gr.State() or direct component output/input	Streamlit re-runs the entire script on each interaction, requiring session_state. Gradio is event-driven; data flows from outputs of one function to inputs of another, or can be stored explicitly in a hidden gr.State component if needed.

The Core Logic Conversion:
The main logic in app.py is triggered by a button click. This logic will be moved into a single Python function. This function will:

Take the user's question as an input.

Perform all the steps: identify_intent, run_query, extract_entities, etc.

Instead of calling st.write or st.dataframe directly, it will return values for multiple Gradio output components.

We will use gr.update(value=..., visible=True/False) to conditionally show the correct results (e.g., show the DataFrame for a dependency query, or show the code explanation for another).

✅ 2. Integration Strategy: Combining with web.py

Your current web.py uses a radio button ("I am new..." vs. "I know what I am doing") to show/hide different rows. This is a good start, but for separating two completely different user flows, a more robust UI structure is better.

UI Structure Recommendation: gr.Tabs

We will restructure your entire app to use a gr.Tabs layout.

Tab 1: "Guided Wizard": This will contain your entire original web.py interface for new users.

Tab 2: "Expert Query": This will contain the new interface converted from your Streamlit app.

The radio button will no longer show/hide individual gr.Row components. Instead, it will switch the active tab, which is a much cleaner and more scalable user experience.

✅ 3. How-To: Implementation Details

Define a New Function for Expert Queries: We'll create handle_expert_query() that encapsulates all the logic from app.py.

Trigger the Function: The "Run Query" button within the "Expert Query" tab will trigger this new function.

Route Between Interfaces: We'll define a new navigation_tabs() function. The "Who are you?" radio button will call this function, which will simply return gr.update(selected=...) to change the visible tab in the gr.Tabs container.

✅ 4. The Integrated Code

Here is the fully integrated code. I have combined both apps, refactored the navigation to use tabs, and converted the Streamlit logic into a Gradio-compatible function. I also fixed a few minor bugs and inconsistencies from the original web.py to make it more robust.

full_app.py (replaces both web.py and app.py)

Generated python
import gradio as gr
import pandas as pd
import json
from graph_query_handler1 import GraphQueryHandler # Assuming this is your handler
from data_Structures import Node # Assuming this is your data structure
from typing import Dict, List, Tuple

# --- 1. SETUP AND INITIALIZATION ---
# This section handles setup, similar to the top of your Streamlit app.

# Initialize the theme
custom_theme = gr.themes.Default(
    primary_hue="blue",
    secondary_hue="green",
    neutral_hue="orange",
    text_size="sm",
    font="Comic Sans MS"
)

# App Title HTML
title_html = """
<div style="text-align: center; margin-top: 20px;">
    <h1 style="background: linear-gradient(to right,red,orange,yellow,green,blue,indigo,violet); -webkit-background-clip: text; color:transparent;">
        Codebase Analytica
    </h1>
    <p style="font-size: 18px; color: gray;">Decoding Complexity, One Line at a Time</p>
</div>
"""

# Initialize the graph handler once (replaces st.cache_resource)
def get_query_handler():
    try:
        return GraphQueryHandler()
    except ConnectionError as e:
        print(f"Error: {e}")
        # In a real app, you might want to handle this more gracefully
        # For now, we'll raise an error that Gradio can display.
        raise gr.Error(f"**Failed to connect to Neo4j:** {e}. Please ensure the database is running.")
    return None

query_handler = get_query_handler()
# If the handler fails to initialize, the app will stop here with the gr.Error message.


# --- 2. LOGIC FUNCTIONS ---
# This section contains all the backend logic for both the Guided and Expert flows.

# --- Logic for "Guided Wizard" Tab (from original web.py) ---

def repository_selected_by_user(selected_repo):
    # When a repository is selected, show the next set of actions.
    if selected_repo:
        return gr.update(visible=True)
    return gr.update(visible=False)

def repository_action_selected_by_user(repository, action):
    # Based on the action for a repository, show the appropriate UI.
    if action == "LIST CLASSES":
        query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN c"
        result = query_handler.extract_result_for_query(query)
        classes = [x["c"]["name"] for x in result]
        # Show the class list and update its choices
        return gr.update(visible=True, choices=classes), gr.update(visible=False)
    elif action == "CODE EXPLANATION":
        # This seems to be a placeholder in the original code, but we enable the class list view
        return gr.update(visible=True, choices=[]), gr.update(visible=False)
    elif action == "LIST DEPENDENCIES":
        # Show the dependency view
        return gr.update(visible=False), gr.update(visible=True)
    return gr.update(visible=False), gr.update(visible=False)

def class_selected_by_user(selected_class):
    # When a class is selected, show the actions for that class.
    if selected_class:
        return gr.update(visible=True), selected_class
    return gr.update(visible=False), ""

def class_action_selected_by_user(repository, class_name, action, progress=gr.Progress()):
    progress(0, desc="Starting...")
    if not class_name:
        gr.Warning("Please select a class first!")
        return gr.update(visible=False), gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
        
    if action == "SHOW DEPENDENCIES":
        progress(0.1, desc="Querying dependencies...")
        query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name : "{class_name}"}})-[:HAS_METHOD]->(m:METHOD)-[:CALLS_METHOD]->(target:Method) RETURN c.name, m.name, target.name'
        result = query_handler.extract_result_for_query(query)
        progress(0.8, desc="Generating HTML view...")
        html_code = query_handler.generate_html(query=query, output=result)
        progress(1, desc="Done.")
        return gr.update(visible=True), gr.update(visible=False), gr.update(value=html_code), None, gr.update(visible=False)
    
    elif action == "SHOW METHODS":
        progress(0.1, desc="Querying methods...")
        query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name : "{class_name}"}})-[:HAS_METHOD]->(m:METHOD) RETURN m.name'
        result = query_handler.extract_result_for_query(query)
        methods = [x["m.name"] for x in result]
        progress(1, desc="Done.")
        return gr.update(visible=False), gr.update(visible=True), None, gr.update(choices=methods), gr.update(visible=True)
    
    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()


def explain_code_button_handler(selected_methods, repository, class_name):
    if not selected_methods:
        gr.Warning("Please select at least one method to explain.")
        return gr.update(visible=False), gr.update(), gr.update()
        
    # We will explain the first selected method for this example
    method_to_explain = selected_methods[0]
    
    query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name: "{class_name}"}})-[:HAS_METHOD]->(m:METHOD {{name: "{method_to_explain}"}}) RETURN m.source'
    result = query_handler.extract_result_for_query(query)

    if result and "m.source" in result[0]:
        source_code = result[0]["m.source"]
        code_explanation = query_handler.explain_code(source_code)
        return gr.update(visible=True), gr.update(value=source_code), gr.update(value=code_explanation)
    else:
        gr.Error("Could not retrieve source code for the selected method.")
        return gr.update(visible=False), gr.update(), gr.update()


# --- Logic for "Expert Query" Tab (Converted from app.py) ---

def handle_expert_query(question, progress=gr.Progress(track_tqdm=True)):
    """
    This function encapsulates the entire logic from the Streamlit app.
    It takes a question and returns updates for all relevant Gradio components.
    """
    if not question.strip():
        gr.Warning("Please enter a question.")
        return {
            # Return updates to clear all fields and keep them hidden
            expert_results_group: gr.update(visible=False),
            expert_df_output: None,
            expert_query_details_accordion: gr.update(visible=False),
            expert_final_answer_md: None,
            expert_code_explanation_row: gr.update(visible=False),
            expert_code_output: None,
            expert_explanation_output: None
        }

    progress(0.1, desc="Identifying intent...")
    response = query_handler.identify_intent(question)
    
    try:
        response_json = json.loads(response)
        intent = response_json.get("intent")
    except (json.JSONDecodeError, TypeError):
        intent = "unknown" # Fallback if intent is not clear

    # Initialize all outputs to be hidden
    df_update = gr.update(visible=False)
    accordion_update = gr.update(visible=False)
    final_answer_update = gr.update(visible=False)
    code_exp_update = gr.update(visible=False)
    
    if intent == "dependency":
        progress(0.3, desc="Running dependency query...")
        result_data = query_handler.run_query(question)
        
        # Prepare intermediate steps for display
        details_md = f"**Original Question:**\n> {result_data['question']}\n\n"
        for i, step in enumerate(result_data['intermediate_steps']):
            status_emoji = "✅" if step['status'] == 'Success' else "❌"
            details_md += f"---\n#### {status_emoji} Attempt {step['attempt']}: {step['status']}\n"
            details_md += f"```cypher\n{step['cypher_query']}\n```\n"
            if step['status'] != 'Success':
                details_md += f"**Error:**\n> {step['error']}\n"
        
        accordion_update = gr.update(value=details_md, visible=True)

        final_answer = result_data.get("result")
        if isinstance(final_answer, list) and len(final_answer) > 0:
            df_update = gr.update(value=pd.DataFrame(final_answer), visible=True)
        elif isinstance(final_answer, list): # Empty list
             final_answer_update = gr.update(value="*Query executed successfully but returned no results.*", visible=True)
        else: # Error string
             final_answer_update = gr.update(value=f"**An error occurred:**\n\n{final_answer}", visible=True)

    else: # Fallback to entity extraction and code explanation
        progress(0.3, desc="Extracting entities...")
        entities_str = query_handler.extract_entities(question)
        entities_arr = [e.strip() for e in entities_str.split(',')]
        
        progress(0.5, desc="Querying graph for entities...")
        query = f"WITH {json.dumps(entities_arr)} AS names MATCH (n) WHERE n.name IN names RETURN n"
        result = query_handler.extract_result_for_query(query=query)
        
        # Aggregate results for display
        code_output_val = ""
        explanation_output_val = ""
        
        if not result:
            explanation_output_val = "**No entities found matching your query.**"
        
        for item in result:
            node = item["n"]
            if 'source' in node:
                progress(0.7, desc=f"Explaining code for {node.get('name', 'node')}...")
                source_code = node["source"]
                code_explanation = query_handler.explain_code(source_code)
                
                code_output_val += f"# Source for: {node.get('name', 'Unknown')}\n\n{source_code}\n\n"
                explanation_output_val += f"### Explanation for: {node.get('name', 'Unknown')}\n\n{code_explanation}\n\n---\n\n"

        if code_output_val:
            code_exp_update = gr.update(visible=True)
        else: # Handle case where entities were found but none had source code
            explanation_output_val = "**Found matching entities, but none had associated source code to display.**"


    progress(1, "Done.")
    # Return a dictionary for clarity, mapping components to their new state.
    # Gradio requires returning a tuple in the correct order.
    return {
        expert_results_group: gr.update(visible=True),
        expert_df_output: df_update,
        expert_query_details_accordion: accordion_update,
        expert_final_answer_md: final_answer_update,
        expert_code_explanation_row: code_exp_update,
        expert_code_output: gr.update(value=code_output_val),
        expert_explanation_output: gr.update(value=explanation_output_val)
    }


# --- 3. UI DEFINITION using gr.Blocks ---

with gr.Blocks(theme=custom_theme) as demo:
    gr.HTML(title_html)

    # --- Main Navigation ---
    with gr.Row():
        # This radio button now controls which Tab is active
        user_option = gr.Radio(
            choices=["I am new to Marketplace", "I know what I am doing"],
            interactive=True,
            label="Who are you?"
        )

    # --- Tabbed Interface for Different User Flows ---
    with gr.Tabs() as main_tabs:
        # --- TAB 1: GUIDED WIZARD (Original web.py UI) ---
        with gr.Tab("Guided Wizard", id=0):
            with gr.Row() as repository_row:
                query_for_repositories = "MATCH (n:Repository) RETURN DISTINCT n.name"
                repo_names = [r['n.name'] for r in query_handler.extract_result_for_query(query_for_repositories)]
                repository_radio = gr.Radio(repo_names, label="Select Repository", interactive=True)
            
            with gr.Row(visible=False) as repository_action_row:
                repository_action = gr.Radio(
                    ["LIST CLASSES", "CODE EXPLANATION", "LIST DEPENDENCIES"], 
                    label="What do you want to do?", 
                    interactive=True
                )

            with gr.Row(visible=False) as list_class_row:
                classes_radio_group = gr.Radio([], label="Select a Class", interactive=True)
            
            with gr.Row(visible=False) as class_action_row:
                class_action_radio_group = gr.Radio(
                    ['SHOW METHODS', 'SHOW DEPENDENCIES'], 
                    label="Select Action for this Class", 
                    interactive=True
                )
                action_selected_text = gr.Textbox(label="You selected", interactive=False) # Helper to store selected class

            # Outputs for Guided Wizard
            with gr.Row(visible=False) as dependencies_row:
                html_code_output = gr.HTML()
            
            with gr.Row(visible=False) as method_row:
                method_checkbox_group = gr.CheckboxGroup(choices=[], label="Select Methods to Explain")
            
            with gr.Row(visible=False) as explain_code_row_btn:
                explain_code_btn = gr.Button(variant="primary", value="Explain Selected Code")

            with gr.TabbedInterface(
                [gr.Code(label="Code"), gr.Markdown(label="Explanation")],
                tab_names=["Code", "Explanation"]
            ) as code_explanation_tab:
                # This doesn't need to be a component itself, but a container.
                # Let's redefine the output components directly.
                pass # Placeholder
            
            with gr.Row(visible=False) as code_explanation_output_row:
                 code_output = gr.Code(label="Source Code")
                 explanation_output = gr.Markdown(label="Code Explanation")


        # --- TAB 2: EXPERT QUERY (Converted Streamlit UI) ---
        with gr.Tab("Expert Query", id=1):
            with gr.Column():
                gr.Markdown("### 🧠 Codebase Knowledge Graph Explorer\nAsk a question about your codebase in natural language. The system will convert it to a Cypher query and execute it.")
                expert_question = gr.Textbox(
                    label="Enter your question here:",
                    placeholder="e.g., 'What are the dependencies of the PaymentProcessor class?' or 'Show me the code for the handle_payment method'",
                    lines=4
                )
                expert_run_btn = gr.Button("Run Query", variant="primary")
            
            # This group contains all possible results and will be shown/hidden together
            with gr.Column(visible=False) as expert_results_group:
                gr.Markdown("--- \n## Results")
                
                # For dependency results
                expert_df_output = gr.DataFrame(label="Query Results", visible=False)
                with gr.Accordion("Show Query Details", open=False, visible=False) as expert_query_details_accordion:
                    expert_query_details_md = gr.Markdown()

                # For simple text/error answers
                expert_final_answer_md = gr.Markdown(visible=False)
                
                # For code explanation results
                with gr.Row(visible=False) as expert_code_explanation_row:
                    expert_code_output = gr.Code(label="Retrieved Source Code", language='python')
                    expert_explanation_output = gr.Markdown(label="AI-Generated Explanation")

    # --- 4. EVENT HANDLING ---

    # Navigation logic to switch between tabs
    def navigation_tabs(option):
        if option == "I am new to Marketplace":
            return gr.update(selected=0)
        elif option == "I know what I am doing":
            return gr.update(selected=1)

    user_option.change(navigation_tabs, inputs=user_option, outputs=main_tabs)

    # Event handlers for "Guided Wizard"
    repository_radio.change(repository_selected_by_user, inputs=repository_radio, outputs=[repository_action_row])
    repository_action.change(
        repository_action_selected_
