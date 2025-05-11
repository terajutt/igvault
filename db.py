import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()
