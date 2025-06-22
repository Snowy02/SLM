# In app.py, inside the results display section

final_answer = result_data.get("result")

if isinstance(final_answer, list):
    # This handles the cypher_lookup path
    if len(final_answer) > 0:
        st.dataframe(pd.DataFrame(final_answer), use_container_width=True)
    else:
        st.success("Query executed successfully but returned no results.")
elif isinstance(final_answer, str):
    # This NEW part handles the method_explanation path
    st.markdown(final_answer) # Use st.markdown to render the formatted explanation
else:
    st.json(final_answer)
