# Test from Anvil to PC
from ._anvil_designer import a_test_formTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
import traceback


class a_test_form(a_test_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  def btn_fetch_all_schemas_click(self, **event_args):
    """This method is called when the button is clicked"""
    try:
      # Call the server function to get the users table schema
      users_schema = anvil.server.call('get_users_table_schema')

      # Format the schema as JSON for display
      formatted_schemas = json.dumps(users_schema, indent=2)

      # Display the formatted schemas in the text area
      self.ta_all_schemas.text = formatted_schemas

    except Exception as e:
      self.ta_all_schemas.text = f"An error occurred: {e}"
