# setup_database.py
import os
import psycopg2
from dotenv import load_dotenv

#load_dotenv()
# AFTER
load_dotenv(dotenv_path='backend/.env.example')
DATABASE_URL = os.getenv("DATABASE_URL")

def create_tables():
    """Connects to the database and creates tables based on schema.sql."""
    conn = None
    try:
        print("Connecting to the database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        print("✅ Connection successful.")

        # Assuming schema.sql is in the 'backend' folder
        with open('backend/schema.sql', 'r') as f:
            sql_script = f.read()

        # Execute the entire SQL script
        cursor.execute(sql_script)
        conn.commit()
        print("✅ Successfully created tables from schema.sql.")

    except FileNotFoundError:
        print("❌ Error: backend/schema.sql not found.")
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if conn:
            cursor.close()
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    create_tables()