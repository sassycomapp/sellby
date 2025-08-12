import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
import anvil.email


@anvil.server.callable
def generate_paddle_id():
    """Generates a unique Paddle ID (integer)."""
    # Find the highest existing paddle_id in both tables
    highest_paddle_id = 0

    # Function to extract numeric part and handle errors
    def extract_numeric_id(table):
        nonlocal highest_paddle_id
        for row in table.search(tables.order_by('paddle_id', ascending=False)):
            pid = row['paddle_id']
            if pid is not None and isinstance(pid, int):  # Check if it's an integer
                highest_paddle_id = max(highest_paddle_id, pid)
            elif pid is not None:
                print(f"Warning: Non-integer paddle_id found: {pid}, skipping.")

    # Extract IDs *before* calculating the new ID
    extract_numeric_id(app_tables.product)
    extract_numeric_id(app_tables.service)

    new_id = highest_paddle_id + 1
    return new_id

@anvil.server.callable
def create_paddle_product(table_name, row):
    """Creates a Paddle ID for a new product or service."""
    new_paddle_id = generate_paddle_id()
    if table_name == 'product':
        row.update(paddle_id=new_paddle_id)
    elif table_name == 'service':
        row.update(paddle_id=new_paddle_id)
    else:
        raise ValueError("Invalid table name.")
    return new_paddle_id

