import pandas as pd
import openai
import sqlite3
import streamlit as st
import json
import re

# Set up OpenAI API key
openai.api_key = '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'

# Function to upload and read the Excel file
def upload_excel(file):
    try:
        df = pd.read_excel(file)
        # Rename columns to remove spaces and special characters for SQL compatibility
        original_columns = list(df.columns)
        cleaned_columns = [re.sub(r'\W+', '_', col).lower() for col in df.columns]
        df.columns = cleaned_columns
        column_mapping = dict(zip(original_columns, cleaned_columns))  # Store mapping
        return df, column_mapping
    except Exception as e:
        return None, f"Error reading file: {str(e)}"

# Function to load data into an SQLite database
def load_data_into_sqlite(df):
    conn = sqlite3.connect(":memory:")  # In-memory database
    df.to_sql("data_table", conn, index=False, if_exists="replace")
    return conn

# Function to clean SQL query returned by OpenAI
def clean_sql_query(sql_query):
    sql_query = re.sub(r"```sql|```", "", sql_query, flags=re.IGNORECASE).strip()
    return sql_query

# Function to analyze the dataset using SQL queries
def query_with_sql(query_text, df, column_mapping):
    try:
        conn = load_data_into_sqlite(df)
        cursor = conn.cursor()
        
        # Extract table schema to help AI form better queries
        cursor.execute("PRAGMA table_info(data_table)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]

        # Modify AI prompt to enforce correct column names
        formatted_column_names = {orig: new for orig, new in column_mapping.items()}
        prompt_columns = ", ".join([f"'{orig}' as `{new}`" for orig, new in formatted_column_names.items()])

        # Generate SQL query using OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "You are an AI SQL assistant that accurately queries a dataset. "
                    "Ensure the SQL query correctly matches the table schema. "
                    "Return only the SQL query without extra formatting. "
                    f"The table `data_table` has the following columns: {', '.join(column_names)}. "
                    "Use these exact column names when writing the SQL query."
                )},
                {"role": "user", "content": f"Generate a precise SQL query to answer: {query_text}"}
            ]
        )
        sql_query = response['choices'][0]['message']['content'].strip()

        # Clean up the query before execution
        sql_query = clean_sql_query(sql_query)

        # Ensure AI-generated query uses correct column names
        for orig_col, new_col in formatted_column_names.items():
            sql_query = sql_query.replace(orig_col, new_col)

        # Execute the generated SQL query
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Error running SQL query: {str(e)}"

# Function to display the result
def display_results(response_text):
    if isinstance(response_text, pd.DataFrame):
        st.dataframe(response_text)
    else:
        st.write(response_text)

# Build the app interface
def main():
    st.title("AI-powered Data Analysis App")
    st.write("Upload an Excel file, enter a query, and get accurate insights using SQL and AI.")

    uploaded_file = st.file_uploader("Upload your Excel file", type="xlsx")
    if uploaded_file:
        df, column_mapping = upload_excel(uploaded_file)

        if isinstance(df, pd.DataFrame):
            st.dataframe(df.head())
        else:
            st.error(column_mapping)  # Display error message

        query_text = st.text_input("Enter your query (e.g., 'Summarize Supplier 1' or 'Show total sales')")
        if query_text and isinstance(df, pd.DataFrame):
            response_text = query_with_sql(query_text, df, column_mapping)
            display_results(response_text)

if __name__ == "__main__":
    main()
