# app.py

import streamlit as st
import pandas as pd
from graph_query_handler import GraphQueryHandler

# --- Page Configuration and Handler Initialization (Unchanged) ---
st.set_page_config(...)
query_handler = get_query_handler()
if not query_handler:
    st.stop()

# --- MODIFICATION 1: INITIALIZE STATE FOR INTERACTIVITY ---
if 'explanation_target' not in st.session_state:
    st.session_state.explanation_target = None
if 'explanation_result' not in st.session_state:
    st.session_state.explanation_result = None

# --- MODIFICATION 2: ADD UI CALLBACK FUNCTIONS ---
def request_explanation(entity_name, entity_type):
    """Sets the target for explanation in the session state when a button is clicked."""
    st.session_state.explanation_target = {"name": entity_name, "type": entity_type}
    # Clear previous results to force a re-fetch
    st.session_state.explanation_result = None

def clear_explanation():
    """Clears the explanation from the view."""
    st.session_state.explanation_target = None
    st.session_state.explanation_result = None

# --- UI Layout (Main query input is mostly unchanged) ---
st.title("🧠 Codebase Knowledge Graph Explorer")
st.markdown("Ask a question to find code (`List methods in...`) or to understand it (`Explain the class...`).")

question = st.text_area(
    "Enter your question here:",
    "What are the methods in the 'ComplexityDetails' class?",
    height=100
)

if st.button("Run Query", type="primary", use_container_width=True):
    clear_explanation() # Clear any old explanation when a new query is run
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Generating Cypher and querying the graph..."):
            st.session_state.query_result = query_handler.run_query(question)

# --- MODIFICATION 3: REWORK THE RESULTS DISPLAY ---
if 'query_result' in st.session_state and st.session_state.query_result:
    result_data = st.session_state.query_result
    st.header("📊 Query Results", divider="rainbow")
    
    # (Display Query Journey - Unchanged)
    with st.expander("Show Query Journey", ...):
        ...

    st.markdown("### Final Answer")
    final_answer = result_data.get("result")
    
    if isinstance(final_answer, list) and len(final_answer) > 0:
        # --- This is the new interactive list rendering ---
        df = pd.DataFrame(final_answer)
        st.write(f"Found {len(df)} item(s):")

        # Dynamically find the column with the entity names
        name_col = next((col for col in df.columns if 'name' in col.lower()), df.columns[0])
        entity_type = "Class" if 'class' in name_col.lower() else "Method"

        # Loop through results and create an interactive row for each
        for index, row in df.iterrows():
            entity_name = row[name_col]
            col1, col2 = st.columns([4, 1])
            with col1:
                st.info(f"**{entity_type}:** `{entity_name}`")
            with col2:
                st.button(
                    "Explain", 
                    key=f"explain_{entity_name}_{index}", # Unique key
                    on_click=request_explanation, 
                    args=(entity_name, entity_type),
                    use_container_width=True
                )

    elif isinstance(final_answer, str):
        st.error(final_answer)
    elif isinstance(final_answer, list) and len(final_answer) == 0:
        st.success("Query executed successfully but returned no results.")
    else:
        st.json(final_answer)

# --- MODIFICATION 4: ADD THE DEDICATED EXPLANATION SECTION ---
if st.session_state.explanation_target:
    target = st.session_state.explanation_target
    st.markdown("---")
    st.subheader(f"🧠 Explanation for `{target['name']}`")

    # Fetch explanation only if it hasn't been fetched yet
    if not st.session_state.explanation_result:
        with st.spinner(f"Generating explanation for {target['type'].lower()}..."):
            st.session_state.explanation_result = query_handler.get_explanation_for_entity(
                entity_name=target['name'],
                entity_type=target['type']
            )
            
    st.markdown(st.session_state.explanation_result)
    st.button("Close Explanation", on_click=clear_explanation, use_container_width=True)
