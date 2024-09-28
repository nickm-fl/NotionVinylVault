import os
from dotenv import load_dotenv
from notion_client import Client

# Load environment variables
load_dotenv()

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_TOKEN"))

# Your database ID
database_id = os.getenv("NOTION_DATABASE_ID")

try:
    # Try to query the database
    response = notion.databases.query(database_id=database_id)
    print("Successfully connected to the database!")
    print(f"Found {len(response['results'])} items.")
except Exception as e:
    print(f"An error occurred: {str(e)}")
    print("Please check your Database ID and make sure the database is shared with your integration.")