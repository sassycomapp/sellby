# In secret_item_form.py

from ._anvil_designer import secret_item_formTemplate
from anvil import *
import anvil.server

class secret_item_form(secret_item_formTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)
        # self.item is NOT ready here

    # Override the method called by the Repeating Panel AFTER self.item is set
    def refresh_data_bindings(self):
        # super().refresh_data_bindings() # Call if using designer data bindings

        # self.item is now expected to be a dictionary from the server
        print(f"--- refresh_data_bindings called for item: {self.item} (Type: {type(self.item)}) ---") # DEBUG

        if not isinstance(self.item, dict): # Check if it's a dictionary
            print(f"WARNING: self.item is not a dictionary in refresh_data_bindings. Item: {self.item}")
            self.lbl_key.text = "Error: Invalid data format"
            self.lbl_scope.text = ""
            self.lbl_desc.text = ""
            return

        try:
            # Access dictionary items using get() for safety, providing defaults
            key_val = self.item.get('key', 'Key Missing')
            scope_val = self.item.get('scope', 'Scope Missing')
            desc_val = self.item.get('description', 'Desc Missing')

            print(f"  Setting lbl_key.text to: {key_val}")
            print(f"  Setting lbl_scope.text to: {scope_val}")
            print(f"  Setting lbl_desc.text to: {desc_val}")

            self.lbl_key.text = key_val
            self.lbl_scope.text = scope_val
            self.lbl_desc.text = desc_val

        # Catch potential errors if self.item is missing expected keys (though .get handles this)
        # Or other unexpected issues
        except Exception as e:
            print(f"ERROR in refresh_data_bindings accessing item data: {e}")
            print(f"Problematic item: {self.item}")
            self.lbl_key.text = f"Error: {e}"
            self.lbl_scope.text = "Error"
            self.lbl_desc.text = "Error"


    def btn_delete_click(self, **event_args):
        """This method is called when the button is clicked"""
        if not isinstance(self.item, dict):
             alert("Cannot delete: Invalid item data.")
             return

        # Get key for confirmation message, default if missing
        item_key = self.item.get('key', 'Unknown Key')
        # Get the row_id we added to the dictionary on the server
        item_row_id = self.item.get('row_id')

        if item_row_id and confirm(f"Delete secret '{item_key}'?"):
             try:
                 print(f"Calling delete_secret for item row_id: {item_row_id}") # DEBUG
                 # Call the server function with the row ID
                 anvil.server.call('delete_secret', item_row_id)
                 # Raise the event for the parent RepeatingPanel to handle refresh
                 self.parent.raise_event("x-refresh")
             except Exception as e:
                 alert(f"Error deleting secret: {e}")
                 print(f"ERROR during delete: {e}")
        elif not item_row_id:
             alert("Cannot delete: Item ID is missing.")
             print(f"ERROR: Delete failed, missing 'row_id' in item dict: {self.item}")



  
 
  