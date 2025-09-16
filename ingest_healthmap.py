# # ingest_healthmap.py

# import os
# import requests
# import psycopg2
# import psycopg2.extras 
# from dotenv import load_dotenv

# # Load environment variables from a .env file for local development
# #load_dotenv()
# # ingest_healthmap.py
# load_dotenv(dotenv_path='backend/.env.example')
# # --- Configuration ---
# # Get the database connection URL from environment variables.
# # Render sets this for you automatically.
# DATABASE_URL = os.getenv("DATABASE_URL")
# # Replace with the actual mock feed URL you are using.
# HEALTHMAP_API_URL = "https://dummyjson.com/posts" # Example URL

# def fetch_data():
#     """Fetches new alert data from the HealthMap feed."""
#     print("Fetching data from HealthMap API...")
#     try:
#         response = requests.get(HEALTHMAP_API_URL)
#         response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
#         print("✅ Successfully fetched data.")
#         return response.json()
#     except requests.exceptions.RequestException as e:
#         print(f"❌ Error fetching data: {e}")
#         return None

# def store_data(alerts_data):
#     """Stores alert data into the PostgreSQL database."""
#     if not alerts_data:
#         print("No data to store.")
#         return

#     if not DATABASE_URL:
#         print("❌ DATABASE_URL environment variable not set. Cannot connect to the database.")
#         return

#     conn = None
#     try:
#         conn = psycopg2.connect(DATABASE_URL)
#         cursor = conn.cursor()
#         print("✅ Successfully connected to the database.")

#         # This query assumes your table is named 'alerts' and has columns matching the fields below.
#         # ON CONFLICT(id) DO NOTHING ensures that you don't insert duplicate alerts if the script runs again.
#         # This requires 'id' to be a PRIMARY KEY or have a UNIQUE constraint in your table.
#         insert_query = """
#         INSERT INTO alerts (id, title, location, date) 
#         VALUES (%s, %s, %s, %s)
#         ON CONFLICT (id) DO NOTHING;
#         """

#         records_to_insert = []
#         for alert in alerts_data:
#             # Adapt the .get() methods below to match the exact keys in your JSON feed
#             record = (
#                 alert.get('id'),
#                 alert.get('title'),
#                 alert.get('location'),
#                 alert.get('date')
#             )
#             records_to_insert.append(record)
        
#         # Use execute_batch for efficient bulk insertion
#         psycopg2.extras.execute_batch(cursor, insert_query, records_to_insert)
#         conn.commit()
        
#         # cursor.rowcount gives the number of rows affected by the last command
#         print(f"✅ Successfully processed {cursor.rowcount} new records.")

#     except psycopg2.Error as e:
#         print(f"❌ Database error: {e}")
#     finally:
#         if conn:
#             cursor.close()
#             conn.close()
#             print("Database connection closed.")

# # if __name__ == "__main__":
# #     data = fetch_data()
# #     if data:
# #         # Assuming the alerts are in a list, if they are nested in a key, adjust this
# #         # e.g., if JSON is {"alerts": [...]}, use data.get("alerts")
# #         store_data(data)




# # AFTER
# if __name__ == "__main__":
#     data = fetch_data()
#     if data:
#         # Get the list from the "posts" key in the JSON response
#         posts_list = data.get("posts") 
#         store_data(posts_list)        

# ingest_healthmap.py

#Updated code 
import os
import requests
import psycopg2
import psycopg2.extras 
from dotenv import load_dotenv

# Load environment variables from your specified file
load_dotenv(dotenv_path='backend/.env.example')

# --- Configuration ---
DATABASE_URL = os.getenv("DATABASE_URL")
API_URL = "https://dummyjson.com/posts"

def fetch_data():
    """Fetches new post data from the mock API."""
    print("Fetching data from API...")
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        print("✅ Successfully fetched data.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data: {e}")
        return None

def store_data(posts_data):
    """Stores post data into the PostgreSQL 'alerts' table."""
    if not posts_data:
        print("No data to store.")
        return

    if not DATABASE_URL:
        print("❌ DATABASE_URL environment variable not set.")
        return

    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Successfully connected to the database.")

        # --- KEY CHANGE 1: The SQL query now matches your schema.sql ---
        # We insert into title, description, and source.
        # The database will auto-generate the 'id' because it's a SERIAL PRIMARY KEY.
        # We add ON CONFLICT(title) DO NOTHING to prevent creating duplicate alerts.
        # This requires a unique constraint on the title, which is good practice.
        # For it to work, you might need to run:
        # ALTER TABLE alerts ADD CONSTRAINT title_unique UNIQUE (title);
        insert_query = """
        INSERT INTO alerts (title, description, source) 
        VALUES (%s, %s, %s)"""
        # ON CONFLICT (title) DO NOTHING;
        

        records_to_insert = []
        for post in posts_data:
            # --- KEY CHANGE 2: We now map the API data to your table columns ---
            # API 'body' -> table 'description'
            # API 'tags' array -> table 'source' (as a comma-separated string)
            record = (
                post.get('title'),
                post.get('body'),
                ', '.join(post.get('tags', [])) # Joins the list of tags into a single string
            )
            records_to_insert.append(record)
        
        psycopg2.extras.execute_batch(cursor, insert_query, records_to_insert)
        conn.commit()
        
        print(f"✅ Successfully processed {cursor.rowcount} new records.")

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    data = fetch_data()
    if data:
        posts_list = data.get("posts") 
        store_data(posts_list)