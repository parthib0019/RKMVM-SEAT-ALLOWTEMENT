import sqlite3
import os

# Define the path for the database in the same directory as the script
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sara.db')

def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    # This line makes the database return rows as dictionaries, which is very useful.
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create RoomInfo table
    # RoomId is the primary key.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS RoomInfo (
            RoomId TEXT PRIMARY KEY,
            totalCapacity INTEGER NOT NULL,
            BenchPerCol INTEGER NOT NULL
        )
    ''')
    
    # Create StudentInfo table
    # Year is the primary key. StudentData stores the Excel file as a BLOB.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS StudentInfo (
            InstituteName TEXT NOT NULL,
            Year TEXT PRIMARY KEY,
            StudentData BLOB NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")
