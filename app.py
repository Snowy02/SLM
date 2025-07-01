Of course! This is an excellent scenario that highlights the power and flexibility of modern UI frameworks. Migrating from a multi-framework setup (Gradio + Streamlit) to a unified Gradio application is a great way to simplify deployment and improve user experience.

Let's break down the process step-by-step.

1. Analysis: Converting Streamlit Logic to Gradio

First, let's analyze your app.py and map its Streamlit components and logic to their Gradio equivalents.

Streamlit Component/Concept	Gradio Equivalent	Analysis & Notes
st.title, st.markdown	gr.Markdown, gr.HTML	Straightforward conversion for displaying static text.
st.text_area	gr.Textbox(lines=...)	The user's natural language question input.
st.button	gr.Button	Triggers the query execution. The core event handler will be attached here.
st.spinner	gr.Progress() or Component Loading	Gradio shows a loading animation on output components by default. For more control, gr.Progress can be used within the event handler function.
@st.cache_resource	No direct equivalent	You can initialize the GraphQueryHandler once when the Gradio app starts. Gradio's architecture handles this efficiently.
st.session_state	gr.State	Used to maintain state between user interactions without displaying it. Perfect for storing the query result JSON.
st.dataframe	gr.DataFrame	For displaying tabular data from dependency queries.
st.code	gr.Code	For displaying Cypher queries and source code snippets.
st.expander	gr.Accordion	A collapsible container, ideal for showing/hiding query details.
st.error, st.warning	gr.Error(), gr.Warning()	Functions to display noticeable messages to the user.
st.sidebar	gr.Sidebar	A layout container. Your web.py already uses this, so we can place the schema there.
Conditional Rendering	gr.update(visible=True/False)	Streamlit re-runs the script, naturally hiding/showing things. In Gradio, we achieve this by returning gr.update() from an event handler to change component properties like visibility or content.

The core logic of your Streamlit app is:

Get a question.

On button click, call query_handler.identify_intent().

If intent is "dependency": Run the query and store the full result in state.

If intent is other (e.g., "explain"): Extract entities, build a new query, run it, and display code/explanations directly.

Display results based on what was stored in the session state.

We will replicate this exact flow within a single Gradio event handler function.

2. Integration Strategy: Using Tabs for a Clean UI

Your existing web.py uses a series of rows that you show and hide. This is a valid "wizard" pattern. However, when adding a completely different mode of interaction ("Expert Mode" from app.py), managing visibility for many rows can become complex.

A much cleaner and more scalable approach is to use gr.Tabs. We will structure your app like this:

Initial View: A simple radio button asking "Who are you?".

gr.Tabs (initially hidden):

Tab 1: "Guided Exploration": This will contain your original wizard-like interface (select repo, select class, etc.).

Tab 2: "Expert Mode (Natural Language)": This tab will contain the migrated Streamlit interface.

When the user makes a choice:

"I am new..." -> We show the gr.Tabs and select the "Guided Exploration" tab.

"I know what I am doing" -> We show the gr.Tabs and select the "Expert Mode" tab.

This provides excellent separation of concerns and a much better user experience.

3. The Integrated Code

Below is the complete, unified web.py file. I have corrected some minor typos from your original code (gr.Lable -> gr.Label, visbile -> visible) and refactored it to include the migrated Streamlit app logic within a new "Expert Mode" tab.

I have added extensive comments to guide you through the new sections and changes.

Generated python
# web.py (Unified Application)

import gradio as gr
import pandas as pd
import json
from graph_query_handler1 import GraphQueryHandler
from data_Structures import Node
from typing import Dict, List, Any

# --- INITIALIZATION ---
# Good practice: Initialize handlers and constants at the top.
# This function handles the connection and provides a single point of failure.
@gr.cache_data
def get_query_handler():
    """Initializes the GraphQueryHandler. Cached to avoid re-creating it."""
    try:
        print("Initializing GraphQueryHandler...")
        return GraphQueryHandler()
    except ConnectionError as e:
        print(f"CRITICAL: Failed to connect to Neo4j. {e}")
        # In a real app, you might want to stop or show a persistent error.
        # For Gradio, we'll raise an error in the UI.
        raise gr.Error(f"Failed to connect to the database: {e}")

query_handler = get_query_handler()

# --- UI DEFINITION ---
custom_theme = gr.themes.Default(
    primary_hue="blue",
    secondary_hue="green",
    neutral_hue="orange",
    text_size="sm",
    font="Comic Sans MS"
)

title_html = """
<div style="text-align: center; margin-top: 20px;">
    <h1 style="background: linear-gradient(to right, red, orange, yellow, green, blue, indigo, violet); -webkit-background-clip: text; color: transparent;">
        Codebase Analytica
    </h1>
    <p style="font-size: 18px; color: gray;">Decoding Complexity, One Line at a Time</p>
</div>
"""

# --- EVENT HANDLER LOGIC ---

# 1. Navigation Logic (The Entry Point)
def navigation(option):
    """
    Handles the initial user choice.
    Shows the main tab interface and selects the correct tab based on user's choice.
    """
    if option == "I am new to Marketplace":
        # Show the tabs and select the "Guided Exploration" tab
        return gr.update(visible=True), gr.Tabs.update(selected=0)
    elif option == "I know what I am doing":
        # Show the tabs and select the "Expert Mode" tab
        return gr.update(visible=True), gr.Tabs.update(selected=1)
    return gr.update(visible=False), gr.Tabs.update() # Default case


# 2. Logic for "Guided Exploration" Tab (Your original logic, slightly cleaned up)
def repository_action_selected_by_user(repository, action):
    if action == "CODE EXPLANATION":
        return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)
    elif action == "LIST CLASSES":
        query = f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN DISTINCT c"
        result = query_handler.extract_result_for_query(query)
        classes = [x["c"]["name"] for x in result]
        return gr.update(visible=True), gr.update(choices=classes), gr.update(visible=False)
    elif action == "LIST DEPENDENCIES":
        return gr.update(visible=False), gr.update(visible=False), gr.update(visible=True)
    return gr.update(), gr.update(), gr.update()

def class_action_selected_by_user(repository, class_name, action, progress=gr.Progress()):
    progress(0, desc="Starting...")
    if not class_name:
        gr.Warning("Please select a class first!")
        return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()
        
    if action == "SHOW DEPENDENCIES":
        progress(0.1, desc="Querying dependencies...")
        query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name : "{class_name}"}})-[:HAS_METHOD]->(m:METHOD)-[:CALLS_METHOD]->(target:Method) RETURN c.name as Class, m.name as Method, target.name as Calls'
        result = query_handler.extract_result_for_query(query)
        progress(0.8, desc="Generating HTML...")
        html_code = query_handler.generate_html(query=query, output=result)
        progress(1, desc="Done!")
        return gr.update(visible=True), gr.update(visible=False), gr.update(value=html_code), None, gr.update(visible=False)
    
    elif action == "SHOW METHODS":
        progress(0.1, desc="Querying methods...")
        query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name : "{class_name}"}})-[:HAS_METHOD]->(m:METHOD) RETURN m.name'
        result = query_handler.extract_result_for_query(query)
        methods = [x["m.name"] for x in result]
        progress(1, desc="Done!")
        return gr.update(visible=False), gr.update(visible=True), None, gr.update(choices=methods), gr.update(visible=True)
    
    return gr.update(), gr.update(), gr.update(), gr.update(), gr.update()


def explain_code_button_handler(selected_methods, repository, class_name):
    if not selected_methods:
        gr.Warning("Please select at least one method to explain.")
        return gr.update(), gr.update(), gr.update()

    # Let's explain the first selected method for simplicity in this UI
    method_to_explain = selected_methods[0]
    query = f'MATCH (n:Repository {{name: "{repository}"}})-[:HAS_CLASSES]->(c:Class {{name: "{class_name}"}})-[:HAS_METHOD]->(m:METHOD {{name: "{method_to_explain}"}}) RETURN m.source'
    result = query_handler.extract_result_for_query(query)

    if result:
        source_code = result[0]["m.source"]
        explanation = query_handler.explain_code(source_code)
        return gr.update(visible=True), gr.update(value=source_code), gr.update(value=explanation)
    else:
        gr.Error("Could not retrieve source code for the selected method.")
        return gr.update(visible=False), gr.update(), gr.update()

# 3. Logic for "Expert Mode" (Migrated from Streamlit)
def run_expert_query(question, progress=gr.Progress(track_tqdm=True)):
    """
    This function encapsulates all the logic from the Streamlit app.
    It takes a question and returns updates for all relevant UI components.
    """
    if not question or not question.strip():
        gr.Warning("Please enter a question.")
        # Return empty updates to clear previous results
        return None, None, None, None, None

    progress(0, desc="Identifying intent...")
    try:
        # This mirrors the logic from your app.py
        intent_response_str = query_handler.identify_intent(question)
        intent_response = json.loads(intent_response_str)
        intent = intent_response.get("intent")

        if intent == "dependency":
            progress(0.3, desc="Intent is 'dependency'. Generating and running Cypher...")
            # This corresponds to the st.session_state part
            query_result_data = query_handler.run_query(question)
            
            # Prepare outputs for Gradio components
            final_answer = query_result_data.get("result", [])
            df = pd.DataFrame(final_answer) if isinstance(final_answer, list) and final_answer else pd.DataFrame()
            
            # Format intermediate steps for the Accordion
            details_md = f"**Original Question:**\n> {query_result_data.get('question', 'N/A')}\n\n"
            for step in query_result_data.get('intermediate_steps', []):
                details_md += f"### Attempt {step['attempt']} ({step['status']})\n"
                details_md += f"```cypher\n{step['cypher_query']}\n```\n"
                if step['status'] != 'Success':
                    details_md += f"**Error:** {step['error']}\n"
            
            # Return updates: hide explanation, show dataframe, populate accordion
            return gr.update(visible=False), gr.update(value=df, visible=True), gr.update(value=details_md, visible=True), None, gr.update(visible=False)

        else: # Handle code explanation and other intents
            progress(0.3, desc="Intent is 'explanation'. Extracting entities...")
            entities_str = query_handler.extract_entities(question)
            entities_arr = [e.strip() for e in entities_str.split(",")]
            
            progress(0.6, desc="Querying nodes and explaining code...")
            # We will build a single markdown string with all explanations
            full_explanation = ""
            if not entities_arr or not entities_arr[0]:
                 full_explanation = "Could not identify any specific code entities in your question. Please be more specific."
            else:
                query = f"WITH {json.dumps(entities_arr)} AS names MATCH (n) WHERE n.name IN names RETURN n"
                result = query_handler.extract_result_for_query(query=query)
                
                if not result:
                    full_explanation = "Found no code matching the entities from your question."
                else:
                    for item in result:
                        node = item["n"]
                        if 'source' in node and node['source']:
                            full_explanation += f"### Explanation for `{node.get('name', 'Unknown')}`\n"
                            full_explanation += f"```python\n{node['source']}\n```\n"
                            code_explanation = query_handler.explain_code(node["source"])
                            full_explanation += f"{code_explanation}\n\n---\n\n"
            
            # Return updates: show explanation, hide dataframe, hide accordion
            return gr.update(value=full_explanation, visible=True), gr.update(visible=False), gr.update(visible=False), None, gr.update(visible=True)

    except Exception as e:
        gr.Error(f"An unexpected error occurred: {e}")
        return None, None, None, None, None


# --- GRADIO LAYOUT ---
with gr.Blocks(theme=custom_theme, title="Codebase Analytica") as demo:
    gr.HTML(title_html)
    
    # Use a State variable for the repository choice, accessible across tabs if needed
    selected_repository_state = gr.State()

    with gr.Row() as initial_choice_row:
        user_option = gr.Radio(
            choices=["I am new to Marketplace", "I know what I am doing"],
            interactive=True,
            label="How would you like to explore the codebase?"
        )

    # Main UI is within Tabs, hidden initially
    with gr.Tabs(visible=False) as main_tabs:
        # TAB 1: Guided Exploration (Your original UI)
        with gr.TabItem("Guided Exploration", id=0):
            with gr.Column():
                query_for_repositories = "MATCH (n:Repository) RETURN DISTINCT n"
                repository_nodes = query_handler.extract_result_for_query(query_for_repositories)
                repository_names = [x["n"]["name"] for x in repository_nodes]
                
                repository_radio = gr.Radio(repository_names, label="1. Select Repository")
                
                with gr.Row(visible=False) as repository_action_row:
                    REPOSITORY_ACTIONS = ["LIST CLASSES", "LIST DEPENDENCIES"]
                    repository_action = gr.Radio(REPOSITORY_ACTIONS, label="2. What do you want to do?")
                
                with gr.Row(visible=False) as list_class_row:
                    classes_radio_group = gr.Radio([], label="3. Select a Class")

                with gr.Row(visible=False) as class_action_row:
                    CLASS_ACTIONS = ['SHOW METHODS', 'SHOW DEPENDENCIES']
                    class_action_radio_group = gr.Radio(CLASS_ACTIONS, label="4. Select Action for the Class")

                with gr.Row(visible=False) as method_row:
                    method_checkbox_group = gr.CheckboxGroup(label="5. Select Methods to Explain")
                    explain_code_button = gr.Button("Explain Selected Code", variant="primary")
                
                with gr.Tab("Results") as results_tab:
                    with gr.Row(visible=False) as dependencies_html_row:
                        html_output = gr.HTML()
                    with gr.Row(visible=False) as code_explanation_row:
                        with gr.Column(scale=1):
                            code_display = gr.Code(language="python")
                        with gr.Column(scale=1):
                            explanation_display = gr.Markdown()


        # TAB 2: Expert Mode (Migrated from Streamlit)
        with gr.TabItem("Expert Mode (Natural Language)", id=1):
            with gr.Row():
                with gr.Column(scale=3):
                    question_box = gr.Textbox(
                        label="Enter your question here",
                        placeholder="e.g., 'show dependencies for the User class' or 'explain the process_payment method'",
                        lines=4
                    )
                    run_query_button = gr.Button("Run Query", variant="primary")

                    # This state holds the raw JSON result, similar to st.session_state
                    expert_query_result_state = gr.State()

                    # Result Displays
                    explanation_output = gr.Markdown(visible=False, label="Code Explanations")
                    dataframe_output = gr.DataFrame(visible=False, label="Query Results")

                with gr.Column(scale=2):
                    with gr.Accordion("Show Query Details", open=False, visible=False) as details_accordion:
                        details_output = gr.Markdown()

    # --- EVENT WIRING ---

    # Initial navigation
    user_option.change(
        fn=navigation,
        inputs=user_option,
        outputs=[main_tabs, main_tabs] # Pass main_tabs twice for gr.Tabs.update
    ).then(
        fn=lambda: gr.update(visible=False), # Hide the initial choice after selection
        outputs=[initial_choice_row]
    )
    
    # --- Wiring for Guided Tab ---
    repository_radio.change(lambda: gr.update(visible=True), outputs=[repository_action_row])
    repository_radio.change(lambda x: x, inputs=repository_radio, outputs=selected_repository_state)

    repository_action.change(
        fn=repository_action_selected_by_user,
        inputs=[repository_radio, repository_action],
        outputs=[list_class_row, classes_radio_group, gr.Row()] # Placeholder for 3rd output
    )

    classes_radio_group.change(lambda: gr.update(visible=True), outputs=[class_action_row])
    
    class_action_radio_group.change(
        fn=class_action_selected_by_user,
        inputs=[repository_radio, classes_radio_group, class_action_radio_group],
        outputs=[dependencies_html_row, method_row, html_output, method_checkbox_group, explain_code_button]
    )

    explain_code_button.click(
        fn=explain_code_button_handler,
        inputs=[method_checkbox_group, repository_radio, classes_radio_group],
        outputs=[code_explanation_row, code_display, explanation_display]
    )

    # --- Wiring for Expert Tab ---
    run_query_button.click(
        fn=run_expert_query,
        inputs=[question_box],
        outputs=[
            explanation_output,       # Corresponds to Markdown explanations
            dataframe_output,       # Corresponds to st.dataframe
            details_accordion,      # The container for details
            details_output,         # The markdown inside the accordion
            expert_query_result_state # State to hold raw results
        ]
    )


if __name__ == "__main__":
    demo.launch(debug=True)

4. How the Integration Works (Summary)

Unified Structure: The entire application is now inside a single gr.Blocks() instance. No more separate servers.

Tab-Based Navigation: The gr.Tabs component cleanly separates the two user journeys ("Guided" vs. "Expert"). The initial radio button (user_option) now controls which tab is active using gr.Tabs.update(selected=...).

Encapsulated Logic: The Streamlit app's core functionality is now in the run_expert_query function. This function is a pure Python function that takes a question and returns a series of gr.update() objects to modify the UI.

State Management: gr.State is used where st.session_state was previously needed, although in this implementation, we directly populate the UI from the event handler. It's available if more complex state management is required.

Event Binding: The "Run Query" button's .click() event is bound to run_expert_query. The inputs list tells Gradio where to get the arguments for the function (from question_box), and the outputs list tells it which components to update with the return values.

Conditional Rendering in Gradio: The run_expert_query function conditionally returns d
