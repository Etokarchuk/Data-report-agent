import os
import pandas as pd
import openai
import sqlite3
import streamlit as st
import json
import re
from dotenv import load_dotenv

# 🔐 Load API key securely from .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    st.error("⚠️ OpenAI API key is missing. Please set it in a `.env` file.")
    st.stop()

# Function to upload and read the Excel file
def upload_excel(file):
    try:
        df = pd.read_excel(file)
        df.columns = [re.sub(r'\W+', '_', col).lower() for col in df.columns]  # Sanitize column names
        return df
    except Exception as e:
        return f"Error reading file: {str(e)}"

# Function to load data into an SQLite database
def load_data_into_sqlite(df):
    conn = sqlite3.connect(":memory:")  # In-memory database
    df.to_sql("data_table", conn, index=False, if_exists="replace")
    return conn

# Function to generate SQL query using OpenAI
def generate_sql_query(query_text, column_names):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": (
                    "You are an AI assistant that queries an SQLite dataset using SQL."
                    "Ensure that the SQL query exactly matches the table schema. "
                    f"The table `data_table` has the following columns: {', '.join(column_names)}."
                )},
                {"role": "user", "content": f"Generate an SQL query to answer: {query_text}"}
            ]
        )
        sql_query = response['choices'][0]['message']['content'].strip()
        sql_query = re.sub(r"```sql|```", "", sql_query, flags=re.IGNORECASE).strip()  # Remove markdown formatting
        return sql_query
    except Exception as e:
        return f"Error generating SQL: {str(e)}"

# Function to analyze data and return results
def query_data(query_text, df):
    try:
        conn = load_data_into_sqlite(df)
        cursor = conn.cursor()

        # Extract column names
        cursor.execute("PRAGMA table_info(data_table)")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]

        sql_query = generate_sql_query(query_text, column_names)

        # Execute SQL query
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
        return result_df
    except Exception as e:
        return f"Error running SQL query: {str(e)}"

# Streamlit UI
def main():
    st.title("🔍 AI-powered Data Analysis App")
    st.write("Upload an Excel file, enter a question, and get AI-powered insights!")

    uploaded_file = st.file_uploader("📂 Upload your Excel file", type="xlsx")
    if uploaded_file:
        df = upload_excel(uploaded_file)

        if isinstance(df, pd.DataFrame):
            st.dataframe(df.head())  # Show sample data

            query_text = st.text_input("💬 Ask a question about the data:")
            if query_text:
                response = query_data(query_text, df)
                if isinstance(response, pd.DataFrame):
                    st.dataframe(response)  # Show results as a table
                else:
                    st.write(response)  # Show error messages
        else:
            st.error(df)  # Show error if file reading fails

if __name__ == "__main__":
    main()
