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
        st.warning("Please ensure Neo4j and Ollama are running and environment variables are set.")
        return None

query_handler = get_query_handler()
if not query_handler:
    st.stop()

# --- UI Layout ---
st.title("🧠 Codebase Knowledge Graph Explorer")
st.markdown("Ask a question about your codebase in natural language. The system will convert it to a Cypher query, execute it, and even try to self-correct if it makes a mistake.")

# --- Natural Language Query Input ---
question = st.text_area(
    "Enter your question here:",
    "What are the various classes defined in the repository policyissuance?",
    height=100
)

if st.button("Run Query", type="primary", use_container_width=True):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Generating Cypher, executing, and analyzing results... This should be quick!"):
            st.session_state.query_result = query_handler.run_query(question)

# --- Results Display ---
if 'query_result' in st.session_state and st.session_state.query_result:
    result_data = st.session_state.query_result
    
    st.header("📊 Query Results", divider="rainbow")
    st.metric("Query Duration", f"{result_data.get('duration_seconds', 0)} seconds")

    # Display the intermediate steps for transparency
    with st.expander("Show Query Journey", expanded=True):
        st.markdown(f"**Original Question:**")
        st.info(result_data['question'])
        
        for i, step in enumerate(result_data['intermediate_steps']):
            st.markdown(f"---")
            if step['status'] == 'Success':
                st.markdown(f"#### ✅ Attempt {step['attempt']}: Success")
                st.code(step['cypher_query'], language="cypher")
            else:
                st.markdown(f"#### ❌ Attempt {step['attempt']}: Failed")
                st.code(step['cypher_query'], language="cypher")
                st.error(f"**Error:** {step['error']}")

    # Display the final answer
    st.markdown("### Final Answer")
    final_answer = result_data.get("result")
    
    if isinstance(final_answer, list):
        if len(final_answer) > 0:
            st.dataframe(pd.DataFrame(final_answer), use_container_width=True)
        else:
            st.success("Query executed successfully but returned no results.")
    elif isinstance(final_answer, str):
        # This will catch the error message if all retries failed
        st.error(final_answer)
    else:
        st.json(final_answer)

# --- Schema Viewer ---
with st.sidebar:
    st.header("Graph Schema")
    st.info("A concise summary of the graph schema provided to the LLM.")
    st.code(query_handler.concise_schema, language='text')
    
