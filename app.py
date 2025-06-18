# app.py

import streamlit as st
import pandas as pd
from graph_query_handler import GraphQueryHandler, ConnectionError

# --- Page Configuration ---
st.set_page_config(
    page_title="Codebase Knowledge Graph Explorer",
    page_icon="🧠",
    layout="wide"
)

# --- State Management ---
# Use session_state to store the query handler and results
# to avoid re-initializing on every interaction.
if 'query_handler' not in st.session_state:
    try:
        st.session_state.query_handler = GraphQueryHandler()
    except ConnectionError as e:
        st.session_state.query_handler = None
        st.error(f"**Failed to initialize connection:** {e}", icon="🚨")
        st.warning("Please ensure Neo4j and Ollama are running and environment variables are set.")
        st.stop()

if 'query_result' not in st.session_state:
    st.session_state.query_result = None

# --- UI Layout ---
st.title("🧠 Codebase Knowledge Graph Explorer")
st.markdown("Query your enterprise codebase using guided natural language. The system will convert your selections into a Cypher query and retrieve the results from the Neo4j graph.")

# --- Guided Query Builder ---
st.header("🔍 Guided Query Builder", divider="rainbow")
st.markdown("Construct your query by selecting entities and relationships from the dropdowns.")

# Two columns for a cleaner layout
col1, col2, col3 = st.columns(3)

with col1:
    # Let's get the main node types from the schema for the dropdowns
    # In a real scenario, you might curate this list.
    node_types = ["Repository", "Class", "Method", "Controller", "StoredProcedure"]
    start_node_type = st.selectbox("I want to find a...", node_types, key="start_node")
    start_node_name = st.text_input(f"Enter a specific {start_node_type} name (optional, leave blank for all):", key="start_name")

with col2:
    # Relationship types can also be curated
    relationship_types = ["that depends on", "that has", "that calls"]
    relationship = st.selectbox("What is the relationship?", relationship_types, key="relation")

with col3:
    end_node_type = st.selectbox("...another...", node_types, key="end_node")
    end_node_name = st.text_input(f"Enter a specific {end_node_type} name (optional, leave blank for all):", key="end_name")

# Button to trigger the query
if st.button("Generate & Run Query", type="primary", use_container_width=True):
    # --- Prompt Construction ---
    # This is the core of our "guided prompting" strategy. We build a clear,
    # unambiguous sentence from the user's selections.
    
    question_parts = [f"Find all {start_node_type}s"]
    if start_node_name:
        question_parts.append(f'named "{start_node_name}"')
    
    # Map UI selection to a more natural phrase for the LLM
    rel_phrase_map = {
        "that depends on": "that depends on a",
        "that has": "that has a",
        "that calls": "that calls a"
    }
    question_parts.append(rel_phrase_map.get(relationship, relationship))
    
    question_parts.append(f"{end_node_type}")
    if end_node_name:
        question_parts.append(f'named "{end_node_name}"')

    final_question = " ".join(question_parts)
    
    st.session_state.generated_question = final_question

    with st.spinner("Generating Cypher and querying the graph..."):
        handler = st.session_state.query_handler
        st.session_state.query_result = handler.run_query(final_question)

# --- Results Display ---
if st.session_state.query_result:
    result_data = st.session_state.query_result

    st.header("📊 Query Results", divider="rainbow")

    # Display the intermediate steps (generated question and Cypher) for transparency
    with st.expander("Show Query Details", expanded=True):
        st.markdown(f"**Generated Question:**")
        st.info(st.session_state.generated_question)
        
        # Extract the generated Cypher query from the intermediate steps
        cypher_query = "Could not extract Cypher query."
        if result_data.get("intermediate_steps") and len(result_data["intermediate_steps"]) > 0:
            if 'query' in result_data["intermediate_steps"][0]:
                 cypher_query = result_data["intermediate_steps"][0]['query']

        st.markdown(f"**Generated Cypher:**")
        st.code(cypher_query, language="cypher")

    # Display the final answer
    st.markdown("**Answer:**")
    
    final_answer = result_data.get("result", "No result found.")
    
    # Try to format the result as a DataFrame if it's a list of dicts
    try:
        if isinstance(final_answer, list) and len(final_answer) > 0:
            df = pd.DataFrame(final_answer)
            st.dataframe(df, use_container_width=True)
        elif isinstance(final_answer, str):
            st.success(final_answer)
        else:
            st.json(final_answer)
    except Exception as e:
        st.warning(f"Could not display result as a table. Raw output below. Error: {e}")
        st.json(final_answer)

# --- Schema Viewer ---
with st.sidebar:
    st.header("Graph Schema")
    st.info("This is the schema the LLM uses to generate queries.")
    with st.spinner("Loading schema..."):
        schema = st.session_state.query_handler.get_schema()
        st.code(schema, language='text')