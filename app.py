# app.py

import streamlit as st
import pandas as pd
from graph_query_handler import GraphQueryHandler

# --- Page Configuration ---
st.set_page_config(
    page_title="Codebase Knowledge Graph Explorer",
    page_icon="🧠",
    layout="wide"
)

# --- State Management ---
@st.cache_resource
def get_query_handler():
    try:
        return GraphQueryHandler()
    except ConnectionError as e:
        st.error(f"**Failed to initialize connection:** {e}", icon="🚨")
        return None

query_handler = get_query_handler()
if not query_handler:
    st.stop()

# --- UI Layout ---
st.title("🧠 Codebase Knowledge Graph Explorer")
st.markdown("Ask a question to find code (`List all classes in...`) or to understand it (`Explain the functionality of...`).")

# --- Natural Language Query Input ---
question = st.text_area(
    "Enter your question here:",
    "Explain the functionality of the 'BillingProcessor' class",
    height=100
)

if st.button("Run Query", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Analyzing question and querying knowledge base..."):
            st.session_state.query_result = query_handler.run_query(question)

# --- Results Display ---
if 'query_result' in st.session_state and st.session_state.query_result:
    result_data = st.session_state.query_result
    
    st.header("📊 Query Results", divider="rainbow")
    st.metric("Query Duration", f"{result_data.get('duration_seconds', 0)} seconds")

    # Display the intermediate steps for transparency
    with st.expander("Show Query Journey", expanded=True):
        if result_data.get('intermediate_steps'):
            for step in result_data['intermediate_steps']:
                key = list(step.keys())[0]
                value = step[key]
                st.write(f"**{key.replace('_', ' ').title()}:**")
                if 'cypher' in key:
                    st.code(value, language="cypher")
                else:
                    st.info(value)

    # Display the final answer
    st.markdown("### Final Answer")
    final_answer = result_data.get("result")
    
    if isinstance(final_answer, list):
        if len(final_answer) > 0:
            st.dataframe(pd.DataFrame(final_answer), use_container_width=True)
        else:
            st.success("Query executed successfully but returned no results.")
    elif isinstance(final_answer, str):
        # This will now display both explanations and error messages
        st.markdown(final_answer) # Use markdown to render formatted explanations
    else:
        st.json(final_answer)

# --- Schema Viewer ---
with st.sidebar:
    st.header("Graph Schema")
    st.info("A concise summary of the graph schema provided to the LLM.")
    st.code(query_handler.concise_schema, language='text')
