
# --- Ensure this import line is present at the top ---
from ._anvil_designer import payload_viewer_dialogTemplate
from anvil import * # Keep existing imports if needed, but explicit is better
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

# Class definition now correctly uses the imported Template
class payload_viewer_dialog(payload_viewer_dialogTemplate):
    # The __init__ method expects arguments passed when the form is opened
    # Ensure payload_string and event_id are passed when calling alert() or open_form()
    def __init__(self, payload_string, event_id, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run when the form opens.
        # Store data if needed (using self.item is standard for forms)
        self.item = {'payload': payload_string, 'event_id': event_id}
        # Display the payload string in the text area
        # Ensure you have a TextArea component named 'payload_text_area' in the designer
        if hasattr(self, 'payload_text_area'):
            self.payload_text_area.text = payload_string
        else:
            print("Warning: TextArea component named 'payload_text_area' not found in payload_viewer_dialog.")
