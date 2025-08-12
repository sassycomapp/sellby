import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables

@anvil.server.callable
def get_users_table_schema():
  """
    Retrieves the schema information for the 'users' data table.
    """
  table_name = "users"  # Hardcode the table name
  try:
    table = app_tables.users  # Access the table directly
    schema = {
      "name": table_name,
      "columns": []
    }
    for column in table.columns:
      schema["columns"].append({
        "name": column.name,
        "type": column.data_type.name,
        "indexed": column.indexed
      })
    return schema
  except AttributeError as e:
    return f"Error: Could not get schema for table '{table_name}'. {e}"
  except Exception as e:
    return f"An error occurred while processing table '{table_name}': {e}"