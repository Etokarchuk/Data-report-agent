import os
import pandas as pd
import openai
import sqlite3
import streamlit as st
import json
from dotenv import load_dotenv

# 🔐 Load API Key securely
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("⚠️ OpenAI API key is missing. Please set it in a `.env` file.")
    st.stop()

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)  # OpenAI v1.0+ usage

# 🔹 Function to upload and read the Excel file
def upload_excel(file):
    try:
        df = pd.read_excel(file)
        df.columns = df.columns.str.replace(r"\W+", "_", regex=True).str.lower()  # Sanitize column names
        return df
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"

# 🔹 Load data into SQLite (for querying)
def load_data_into_sqlite(df):
    conn = sqlite3.connect(":memory:")  # Use an in-memory database
    df.to_sql("data_table", conn, index=False, if_exists="replace")
    return conn

# 🔹 Generate SQL query dynamically based on user request
def generate_sql_query(query_text, column_names):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": (
                    "You are an AI that generates correct SQL queries for SQLite. "
                    "Return only the SQL query without explanations."
                    f"\n\nThe table `data_table` has the following columns: {', '.join(column_names)}"
                )},
                {"role": "user", "content": f"Generate an SQL query to answer: {query_text}"}
            ]
        )

        sql_query = response.choices[0].message.content.strip()
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()  # Clean formatting
        return sql_query
    except Exception as e:
        return f"❌ Error generating SQL: {str(e)}"

# 🔹 Execute the AI-generated SQL query
def execute_sql_query(query_text, df):
    try:
        conn = load_data_into_sqlite(df)
        cursor = conn.cursor()

        # Get column names for AI reference
        cursor.execute("PRAGMA table_info(data_table)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]

        # Generate SQL query from user question
        sql_query = generate_sql_query(query_text, column_names)

        # Execute the SQL query
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"❌ Error running SQL query: {str(e)}"

# 🔹 Streamlit UI
def main():
    st.title("📊 AI-Powered Spreadsheet Query App")
    st.write("Upload an Excel file, ask a question, and get structured data!")

    uploaded_file = st.file_uploader("📂 Upload your Excel file", type="xlsx")
    
    if uploaded_file:
        df = upload_excel(uploaded_file)

        if isinstance(df, pd.DataFrame):
            st.dataframe(df.head())  # Show first few rows

            query_text = st.text_input("💬 Ask a question about the data:")
            
            if query_text:
                response_df = execute_sql_query(query_text, df)
                if isinstance(response_df, pd.DataFrame):
                    st.dataframe(response_df)  # Display results as a table
                else:
                    st.write(response_df)  # Show error if needed
        else:
            st.error(df)  # Show error if file reading fails

# Run the app
if __name__ == "__main__":
    main()
