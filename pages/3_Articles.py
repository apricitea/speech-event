import streamlit as st
import pandas as pd
import os
from sqlalchemy import create_engine

with open('C:/code/github/speech-event/credentials.env') as file:
    for line in file:
        if line.startswith('#') or not line.strip():
            continue
        key, value = line.strip().split('=', 1)
        os.environ[key] = value

# Define your PostgreSQL connection details
db_user = os.getenv('user')
db_pass = os.getenv('pass')
db_host = os.getenv('host')
db_port = os.getenv('port')
db_name = os.getenv('name')

# Create the connection string
connection_string = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
engine = create_engine(connection_string)

# Helper function to connect to PostgreSQL and retrieve articles
def get_articles_from_db(keyword=None, start_date=None, end_date=None):
    
    # Create the connection using SQLAlchemy
    connection = engine.connect()
    
    # Construct the SQL query with placeholders
    query = """
    SELECT 
        t.article_title
        , t.article_date_published
        , t.article_date_accessed
        , t.article_link
        , t.article_content 
    FROM 
        public.textual_data AS t
    WHERE 
        1=1
    """
    
    params = {}
    
    if keyword:
        query += " AND t.article_title ILIKE %(keyword)s"
        params['keyword'] = f"%{keyword}%"
    if start_date:
        query += " AND t.article_date_published >= %(start_date)s"
        params['start_date'] = start_date
    if end_date:
        query += " AND t.article_date_published <= %(end_date)s"
        params['end_date'] = end_date
    
    # Execute the query and retrieve the data into a DataFrame
    articles = pd.read_sql(query, connection, params=params)
    
    # Close the connection
    connection.close()
    
    return articles

def app():
    st.title("Articles")

    # Keyword Search
    keyword = st.text_input("Search by keyword:")

    # Date Range Filter
    start_date = st.date_input("Start date", pd.to_datetime("2018-01-01"))
    end_date = st.date_input("End date", pd.to_datetime("today"))

    # Fetch and display articles based on user input
    if st.button("Search"):
        articles = get_articles_from_db(keyword, start_date, end_date)
        
        if not articles.empty:
            st.subheader(f"Found {len(articles)} articles")
            st.dataframe(articles)  # Display the articles in a table format
        else:
            st.write("No articles found.")

# Call the function to display the page
app()
