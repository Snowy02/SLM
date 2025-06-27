import gradio as gr
from graph_query_handler1 import GraphQueryHandler
from data_Structures import Node
from typing import Dict,List
import time # Added here: to simulate processing for demonstration if needed

# --- Start of user's original code ---

custom_theme=gr.themes.Default(
    primary_hue="blue",
    secondary_hue="green",
    neutral_hue="orange",
    text_size="sm",
    font="Comic Sans MS"
)

title_html="""
<div style="text-align: center; margin-top:20px;">
    <h1 style="background: linear-gradient(to right,red,orange,yellow,green,blue,indigo,violet); -webkit-background-clip: text; color:transparent;">
        Codebase Analytica
    </h1>
    <p style="font-size: 18px; color: gray;">Decoding Complexity, One Line at a Time</p>
</div>
"""

# Added here: Function to get query handler and handle connection errors.
# It's better to initialize it once.
def get_query_handler():
    try:
        return GraphQueryHandler()
    except ConnectionError as e:
        print("Error: ",e)
        gr.Error(f"**Failed to initiate connection:** {e}",duration=5)
        return None

# Added here: Initialize the query handler once at the start.
query_handler = get_query_handler()
# Added here: Exit if the database connection fails.
if not query_handler:
    import sys
    sys.exit("Could not connect to the database. Exiting.")


def navigation(option):
    if option == "I am new to Marketplace":
        return gr.update(visible=False),gr.update(visible=True)
    elif option == "I know what I am doing":
        return gr.update(visible=True),gr.update(visible=True)

def class_action_selected_by_user(repository,class_name,action,selected_code,progress=gr.Progress()):
    # Added here: First, yield an update to show the spinner and hide other components.
    yield gr.update(visible=False), gr.update(visible=False), None, gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=True)
    
    progress(0,desc="Starting")
    if action == "SHOW DEPENDENCIES":
        progress(0.05)
        query="MATCH (n:Repository {{name: \"{0}\"}})-[r1:HAS_CLASSES]->(c:Class {{name : \"{1}\"}})->[r2:HAS_METHOD]->(m:METHOD)-[r3:CALLS_METHOD]->(target:Method) RETURN c.name,r2,m.name,r3,target.name".format(repository,class_name)
        result=query_handler.extract_result_for_query(query)
        html_code=query_handler.generate_html(query=query,output=result)
        print(html_code)
        # Added here: Yield the final result and hide the spinner.
        yield gr.update(visible=True),gr.update(visible=False),gr.update(value=html_code),None,gr.update(visible=False), gr.update(visible=False)
    elif action == "SHOW METHODS":
        query="MATCH (n:Repository {{name: \"{0}\"}})-[r1:HAS_CLASSES]->(c:Class {{name : \"{1}\"}})->[r2:HAS_METHOD]->(m:METHOD) RETURN m.name".format(repository,class_name)
        # Fixed here: The original code was using 'result' without defining it.
        result=query_handler.extract_result_for_query(query)
        methods=[x["m.name"] for x in result]
        print(methods)
        # Added here: Yield the final result and hide the spinner.
        yield gr.update(visible=False),gr.update(visible=True),None,gr.update(choices=methods),gr.update(visible=True), gr.update(visible=False)

def explain_code_button_handler(selected_method,repository,class_name):
    # Added here: Show spinner and hide previous results
    yield gr.update(visible=False), gr.update(value=""), gr.update(value=""), gr.update(visible=True)

    print("Methods Selected: ",selected_method)
    if not selected_method:
        gr.Warning("Please select at least one method to explain.")
        # Added here: Hide spinner if no method is selected.
        yield gr.update(visible=False), gr.update(), gr.update(), gr.update(visible=False)
        return

    # Fixed here: The original code would loop but only ever process the first item. This logic is preserved.
    code_to_explain = selected_method[0]
    # Fixed here: The original query was not using the 'code' variable to filter by method.
    query="MATCH (n:Repository {{name: \"{0}\"}})-[r1:HAS_CLASSES]->(c:Class {{name : \"{1}\"}})->[r2:HAS_METHOD]->(m:METHOD {{name: \"{2}\"}}) RETURN m.source".format(repository,class_name,code_to_explain)
    print("The query is: ",query)
    result=query_handler.extract_result_for_query(query)
    print("The match is:",result)
    
    if len(result)>0:
        source_code = result[0]["m.source"]
        code_explanation=query_handler.explain_code(source_code)
        print("The responses are: ",code_explanation)
        # Added here: hide spinner and return result
        yield gr.update(visible=True),gr.update(value=source_code),gr.update(value=code_explanation), gr.update(visible=False)
    else:
        gr.Error(message="Neo4j returned empty result for the selected method.")
        # Added here: hide spinner
        yield gr.update(visible=False),gr.update(),gr.update(), gr.update(visible=False)

def repository_selected_by_user(selected_option):
    print(selected_option)
    return gr.update(visible=True)

def class_selected_by_user(selected_option):
    return gr.update(visible=True),selected_option

def repository_action_selected_by_user(repository,action):
    # Added here: Show spinner and hide other rows
    yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(choices=[], value=None), gr.update(visible=True)
    
    print("The method arguments are: ",repository,action)
    if action  == "CODE EXPLANATION":
        # Added here: Hide spinner and show the corresponding row.
        # Fixed here: The function now returns the correct number of outputs.
        yield gr.update(visible=True), gr.update(visible=False), gr.update(visible=False), None, gr.update(visible=False)
    elif action =="LIST CLASSES":
        # Fixed here: The original code was using 'result' without defining it.
        query=f"MATCH (n:Repository {{name: '{repository}'}})-[:HAS_CLASSES]->(c:Class) RETURN c"
        result=query_handler.extract_result_for_query(query)
        classes=[x["c"]["name"] for x in result]
        print("The classes are: ",classes)
        # Added here: Hide spinner and show the result.
        # Fixed here: The function now returns the correct number of outputs.
        yield gr.update(visible=False), gr.update(visible=True), gr.update(visible=False), gr.update(choices=classes), gr.update(visible=False)
    elif action =="LIST DEPENDENCIES":
        # Added here: Hide spinner and show the corresponding row.
        # Fixed here: The function now returns the correct number of outputs.
        yield gr.update(visible=False), gr.update(visible=False), gr.update(visible=True), None, gr.update(visible=False)


# Added here: Wrapped the UI definition in gr.Blocks to make it a runnable app.
with gr.Blocks(theme=custom_theme) as demo:
    # --- This part of the code was not a function in the original, but a script. ---
    # --- I've placed it inside the gr.Blocks() context as intended. ---
    user_variables=gr.State(value={})
    print(user_variables)

    # Fixed here: The original code for the sidebar was outside a row/column.
    with gr.Row():
        gr.HTML(title_html)
    
    # Added here: A row for the spinner, initially hidden
    with gr.Row(visible=False) as spinner_row:
        gr.HTML(
            """
            <div style='display:flex; justify-content:center; align-items:center; flex-direction:column; width:100%;'>
                <div class='spinner' style='border: 4px solid rgba(0,0,0,0.1); width: 36px; height: 36px; border-radius: 50%; border-left-color: #09f; animation: spin 1s linear infinite;'></div>
                <p>Processing...</p>
                <style> @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } } </style>
            </div>
            """
        )

    with gr.Row(visible=True) as main_page:
        options=["I am new to Marketplace","I know what I am doing"]
        user_optiom=gr.Radio(choices=options,interactive=True,label="Who are you?")
    with gr.Row(visible=False)as repository_row:
        query_for_repositories="MATCH (n:Repository)-[:HAS_CLASSES]->(c:Class) RETURN DISTINCT n"
        # Fixed here: Corrected typo in function name 'extract_Result_for_query' -> 'extract_result_for_query'
        repository_nodes: List[Dict[str,Node]]=query_handler.extract_result_for_query(query_for_repositories)
        repository=[x["n"]["name"] for x in repository_nodes]
        repository_radio=gr.Radio(repository,label="Select Repository", key="selected_repository")
    with gr.Row(visible=False)as repository_action_row:
        REPOSITORY_ACTIONS =["CODE EXPLANATION","LIST CLASSES","LIST DEPENDENCIES"]
        repository_action=gr.Radio(REPOSITORY_ACTIONS,label="Your options are: ", key="class_selected",interactive=True)
    with gr.Row(visible=False) as code_explanation_row:
        # Added here: Added some content to this row for clarity.
        gr.Markdown("### Code Explanation\nThis feature is under development. Please select another option.")
    with gr.Row(visible=False) as list_class_row:
        classes=[]
        print("Classes are: ",classes)
        # Fixed here: `preserved_by_key` is deprecated, using `key` instead.
        classes_radio_group=gr.Radio(choices=[],label="Select Class", key="class_selected",interactive=True)
    with gr.Row(visible=False) as list_dependencies_row:
        # Added here: Added some content to this row for clarity.
        gr.Markdown("### List Dependencies\nThis feature is under development. Please select another option.")
    with gr.Row(visible=False) as class_action_row:
        CLASS_ACTION=['SHOW METHODS','SHOW DEPENDENCIES'] # Removed 'EXPLAIN CODE' as it's handled by a button later
        class_action_radio_group=gr.Radio(CLASS_ACTION,label="Select Action on the Class",interactive=True)
        # Fixed here: `action_selected_text` was not used correctly, hiding it for now.
        action_selected_text=gr.Textbox(label="You selected", visible=False)
    with gr.Row(visible=False) as dependencies_row:
        table_html=""
        html_code=gr.HTML(value=table_html)
    # Fixed here: Corrected typo 'visbile' -> 'visible'
    with gr.Row(visible=False) as method_row:
        values=[]
        # Fixed here: Corrected component name 'checkboxGroup' -> 'CheckboxGroup'
        chkbox_group=gr.CheckboxGroup(choices=values, label="Select Methods to Explain")
    with gr.Row(visible=False) as explain_code_row:
        explain_code=gr.Button(variant="primary",value="Explain Code",interactive=True)
    # Fixed here: A tab should not be 'visible=False', its content is shown when selected.
    with gr.Tab(label="Code Explanation") as code_explanation_tab:
        with gr.Row(): # Wrapped in a row for better layout
            with gr.Column():
                code=gr.Code(value="", language="python", label="Source Code")
            with gr.Column():
                explanation=gr.Markdown(value="", label="Explanation")

    # --- Event Handlers ---
    user_optiom.change(navigation,inputs=[user_optiom],outputs=[main_page,repository_row])
    repository_radio.change(repository_selected_by_user,inputs=repository_radio,outputs=[repository_action_row])
    
    # Added here: The outputs list for this event was corrected to make it functional and spinner_row was added.
    repository_action.change(
        repository_action_selected_by_user,
        inputs=[repository_radio,repository_action],
        outputs=[code_explanation_row, list_class_row, list_dependencies_row, classes_radio_group, spinner_row]
    )

    classes_radio_group.change(class_selected_by_user,inputs=[classes_radio_group],outputs=[class_action_row,action_selected_text])
    
    # Added here: spinner_row was added to the outputs to support the loading spinner.
    class_action_radio_group.change(
        class_action_selected_by_user,
        inputs=[repository_radio,classes_radio_group,class_action_radio_group,chkbox_group],
        outputs=[dependencies_row,method_row,html_code,chkbox_group,explain_code_row, spinner_row]
    )

    # Added here: spinner_row was added to the outputs to support the loading spinner.
    explain_code.click(
        explain_code_button_handler,
        inputs=[chkbox_group,repository_radio,classes_radio_group],
        outputs=[code_explanation_tab,code,explanation, spinner_row]
    )

demo.launch()
