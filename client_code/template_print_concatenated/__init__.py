from ._anvil_designer import template_print_concatenatedTemplate
from anvil import * # MODIFIED: Completed the import statement
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class template_print_concatenated(template_print_concatenatedTemplate): # ADDED COLON
  def __init__(self, **properties): # MODIFIED: Added ** and COLON
    # Set Form properties and Data Bindings.
    self.init_components(**properties) # MODIFIED: Passed **properties

    # Any code you write here will run when the form opens.

    # The 'item' property is automatically populated by the RepeatingPanel.
    # Based on the server function, 'item' will be a dictionary like {'log_line': '...'}
    if self.item and 'log_line' in self.item: # ADDED COLON
      self.lbl_logs_output.text = self.item['log_line']
      # Optional Adjust alignment or appearance
      self.lbl_logs_output.align = "left" # MODIFIED: "left" is now a string
      # self.lbl_logs_output.role = "code" # If you have a CSS role for code blocks, ensure "code" is a string
    else: # ADDED COLON
      # Handle cases where item might be missing or malformed
      self.lbl_logs_output.text = "Error: Invalid log data" # MODIFIED: Error message is now a string