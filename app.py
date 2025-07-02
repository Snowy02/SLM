You are absolutely right. My apologies for misinterpreting your goal. Your clarification makes perfect sense and is a much cleaner design.

The requirement is: Two separate, independent modes, each with its own private chat history.

If the user chooses "I am new to Marketplace", they see the guided controls and a chatbot that only logs the history of their clicks and the system's guided responses.

If the user chooses "I know what I am doing", they see the expert textbox and a chatbot that only logs the history of their typed questions and the LLM's answers.

This is a better approach, and I have implemented it by creating two distinct UI containers. The main navigation function will simply show one container and hide the other.

Key Changes in This Version:

Two Sets of Chat Components: I've created two gr.Chatbot and two gr.State components:

guided_chatbot & guided_history_state for the "Newbie" mode.

expert_chatbot & expert_history_state for the "Expert" mode.

Two UI Containers: The entire UI for each mode (controls + chatbot) is wrapped in a parent gr.Column (guided_mode_ui and expert_mode_ui).

Simplified Navigation: The navigation function is now very simple. It just makes one of these parent containers visible and hides the other.

Dedicated Handlers: Each handler function is now strictly tied to its own mode and updates only its own history state. There is no longer any shared state between them.

Separate "Clear" Buttons: Each mode gets its own button to clear its specific history.

This architecture correctly enforces the separation you described.

Final Code with Separate Chat Histories
Generated python
import gradio as gr
import pandas as pd
import json
import html
from graph_query_handler1 import GraphQueryHandler
from data_Structures import Node
from typing import Dict, List, Any

# --- Global Setup ---
custom_theme = gr.themes.Default(primary_hue="blue", secondary_hue="green", neutral_hue="orange", text_size="sm", font="Comic Sans MS")
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
        user_option = gr.Radio(choices=["I am new to Marketplace", "I know what I am doing"], interactive=True, label="Who are you?")

    # --- CONTAINER FOR "I AM NEW TO MARKETPLACE" MODE ---
    with gr.Column(visible=False) as guided_mode_ui:
        gr.Markdown("### Guided Mode Journey")
        guided_chatbot = gr.Chatbot(label="Session History", bubble_full_width=False, height=400)
        guided_history_state = gr.State([])
        clear_guided_history_button = gr.Button("🗑️ Clear Guided History", variant="stop")

        with gr.Column(border=True):
            gr.Markdown("**Follow the steps below:**")
            with gr.Row() as repository_row:
                query_for_repositories = "MATCH (n:Repository) RETURN DISTINCT n"
                repository_nodes = query_handler.extract_result_for_query(query_for_repositories)
                repositories = [x["n"]["name"] for x in repository_nodes] if repository_nodes else []
                repository_radio = gr.Radio(repositories, label="1. Select Repository", interactive=True)
            with gr.Row() as repository_action_row:
                repository_action = gr.Radio(["LIST CLASSES", "LIST DEPENDENCIES"], label="2. What would you like to do?", interactive=True)
            with gr.Row() as list_class_row:
                classes_radio_group = gr.Radio(choices=[], label="3. Select a Class", interactive=True)
            with gr.Row() as class_action_row:
                class_action_radio_group = gr.Radio(['SHOW METHODS', 'SHOW DEPENDENCIES'], label="4. Select Action for the Class", interactive=True)
            with gr.Row() as method_row:
                method_checkbox_group = gr.CheckboxGroup(choices=[], label="5. Select Methods to Explain")
                explain_code_button = gr.Button(variant="primary", value="Explain Selected Code")

    # --- CONTAINER FOR "I KNOW WHAT I AM DOING" MODE ---
    with gr.Column(visible=False) as expert_mode_ui:
        gr.Markdown("### Expert Chat Mode")
        expert_chatbot = gr.Chatbot(label="Conversation History", bubble_full_width=False, height=500)
        expert_history_state = gr.State([])
        
        with gr.Row():
            expert_question_textbox = gr.Textbox(label="Enter your question:", placeholder="e.g., 'What are the dependencies of the PaymentProcessor class?'", lines=2, scale=7)
            expert_run_button = gr.Button("Run Query", variant="primary", scale=1)
        clear_expert_history_button = gr.Button("🗑️ Clear Expert Chat", variant="stop")

    # ============================ 2. DEFINE ALL HANDLER FUNCTIONS ============================
    
    # --- Helper Functions ---
    def clear_history():
        return []

    def _format_expert_response(result_data: Dict[str, Any]) -> str:
        final_answer = result_data.get("result")
        response_md = ""
        if isinstance(final_answer, list) and final_answer:
            response_md += "### Query Result\n" + pd.DataFrame(final_answer).to_markdown(index=False)
        elif isinstance(final_answer, list) and not final_answer:
            response_md += "**Query executed successfully but returned no results.**"
        response_md += "\n\n---\n<details><summary>Click for Query Execution Details</summary>\n\n"
        for step in result_data.get('intermediate_steps', []):
            status_emoji = "✅" if step['status'] == 'Success' else "❌"
            response_md += f"**{status_emoji} Attempt {step['attempt']}**\n```cypher\n{step['cypher_query']}\n```\n"
            if step['status'] != 'Success':
                response_md += f"**Error:** {html.escape(str(step['error']))}\n"
        response_md += "</details>"
        return response_md

    # --- Main Navigation Handler ---
    def navigation(option):
        is_newbie = (option == "I am new to Marketplace")
        is_expert = (option == "I know what I am doing")
        return {
            main_page: gr.update(visible=False),
            guided_mode_ui: gr.update(visible=is_newbie),
            expert_mode_ui: gr.update(visible=is_expert),
        }

    # --- GUIDED MODE Handlers (update guided_history_state) ---
    def repository_selected_by_user(history, repo_name):
        history.append([f"Selected Repository: **{repo_name}**", "Great. What would you like to do with this repository?"])
        return history, gr.update(visible=True, value=None)

    def repository_action_selected_by_user(history, repository, action):
        user_message = f"Selected action: **{action}** for repository **{repository}**."
        if action == "LIST CLASSES":
            result = query_handler.extract_result_for_query(f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN c.name as name")
            classes = [x["name"] for x in result] if result else []
            bot_message = "Okay, here are the classes I found:\n\n* " + "\n* ".join(classes) if classes else "I couldn't find any classes."
            history.append([user_message, bot_message])
            return history, gr.update(visible=True), gr.update(choices=classes, value=None)
        elif action == "LIST DEPENDENCIES":
            history.append([user_message, "To see dependencies, please select a specific class first."])
            return history, gr.update(visible=False, value=None), gr.update(choices=[], value=None)

    def class_selected_by_user(history, class_name):
        history.append([f"Selected Class: **{class_name}**", f"Class `{class_name}` selected. What action next?"])
        return history, gr.update(visible=True, value=None)

    def class_action_selected_by_user(history, class_name, action, progress=gr.Progress(track_tqdm=True)):
        user_message = f"Requested **{action}** for class **{class_name}**."
        if not class_name: gr.Warning("Please select a class first!"); return history, gr.update(visible=False), gr.update(choices=[])
        
        if action == "SHOW DEPENDENCIES":
            result = query_handler.extract_result_for_query(f"MATCH (c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method)-[r2:CALLS_METHOD]->(target:Method) RETURN m.name as Method, type(r2) as Action, target.name as CalledMethod")
            bot_message = "### Dependencies Found:\n" + pd.DataFrame(result).to_markdown(index=False) if result else "No dependencies found."
            history.append([user_message, bot_message])
            return history, gr.update(visible=False), gr.update(choices=[], value=None)
        elif action == "SHOW METHODS":
            result = query_handler.extract_result_for_query(f"MATCH (c:Class {{name : '{class_name}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name as name")
            methods = [x["name"] for x in result] if result else []
            history.append([user_message, "Here are the methods. You can select some to explain."])
            return history, gr.update(visible=True), gr.update(choices=methods, value=None)

    def explain_code_button_handler(history, selected_methods, class_name):
        if not selected_methods: gr.Warning("Please select at least one method."); return history
        user_message = f"Requested explanation for method(s): **{', '.join(selected_methods)}**"
        bot_responses = []
        for method in selected_methods:
            query = f"MATCH (c:Class {{name: '{class_name}'}})-[:HAS_METHOD]->(m:Method {{name: '{method}'}}) RETURN m.source as source"
            result = query_handler.extract_result_for_query(query)
            if result and "source" in result[0]:
                source_code, explanation = result[0]["source"], query_handler.explain_code(result[0]["source"])
                bot_responses.append(f"### Explanation for `{method}`\n```python\n{html.escape(source_code)}\n```\n{explanation}")
            else: bot_responses.append(f"Could not retrieve source code for `{method}`.")
        history.append([user_message, "\n\n---\n\n".join(bot_responses)])
        return history

    # --- EXPERT MODE Handler (updates expert_history_state) ---
    def handle_expert_chat(question, history, progress=gr.Progress(track_tqdm=True)):
        if not question or not question.strip(): return "", history
        history.append([question, None]); yield "", history
        try:
            intent = json.loads(query_handler.identify_intent(question)).get("intent", "entity")
            if intent == "dependency":
                result_data = query_handler.run_query(question)
                history[-1][1] = _format_expert_response(result_data)
            else:
                entities = [e.strip() for e in query_handler.extract_entities(question).split(",") if e.strip()]
                result = query_handler.extract_result_for_query(f"WITH {json.dumps(entities)} AS names MATCH (n) WHERE n.name IN names RETURN n")
                if not result: history[-1][1] = "Could not find any matching code elements."
                else:
                    explanations = []
                    for item in result:
                        node = item.get("n", {})
                        if 'source' in node and 'name' in node:
                            explanation = query_handler.explain_code(node["source"])
                            explanations.append(f"### Explanation for `{html.escape(node['name'])}`\n```python\n{html.escape(node['source'])}\n```\n{explanation}")
                    history[-1][1] = "\n\n---\n\n".join(explanations)
        except Exception as e:
            gr.Error(f"An error occurred: {e}"); history[-1][1] = f"Sorry, an error occurred: {html.escape(str(e))}"
        yield "", history

    # ============================ 3. DEFINE ALL EVENT LISTENERS ============================
    user_option.change(fn=navigation, inputs=user_option, outputs=[main_page, guided_mode_ui, expert_mode_ui])

    # --- Listeners for Guided Mode ---
    clear_guided_history_button.click(fn=clear_history, outputs=[guided_history_state])
    guided_history_state.change(fn=lambda h: h, inputs=guided_history_state, outputs=guided_chatbot)
    repository_radio.change(fn=repository_selected_by_user, inputs=[guided_history_state, repository_radio], outputs=[guided_history_state, repository_action_row])
    repository_action.change(fn=repository_action_selected_by_user, inputs=[guided_history_state, repository_radio, repository_action], outputs=[guided_history_state, list_class_row, classes_radio_group])
    classes_radio_group.change(fn=class_selected_by_user, inputs=[guided_history_state, classes_radio_group], outputs=[guided_history_state, class_action_row])
    class_action_radio_group.change(fn=class_action_selected_by_user, inputs=[guided_history_state, classes_radio_group, class_action_radio_group], outputs=[guided_history_state, method_row, method_checkbox_group])
    explain_code_button.click(fn=explain_code_button_handler, inputs=[guided_history_state, method_checkbox_group, classes_radio_group], outputs=[guided_history_state])

    # --- Listeners for Expert Mode ---
    clear_expert_history_button.click(fn=clear_history, outputs=[expert_history_state])
    expert_history_state.change(fn=lambda h: h, inputs=expert_history_state, outputs=expert_chatbot)
    expert_run_button.click(fn=handle_expert_chat, inputs=[expert_question_textbox, expert_history_state], outputs=[expert_question_textbox, expert_history_state])
    expert_question_textbox.submit(fn=handle_expert_chat, inputs=[expert_question_textbox, expert_history_state], outputs=[expert_question_textbox, expert_history_state])

demo.launch(debug=True)
