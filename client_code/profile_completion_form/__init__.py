from ._anvil_designer import profile_completion_formTemplate
from anvil import alert, open_form
import anvil.server
from ..cm_logs_helper import log

class profile_completion_form(profile_completion_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.module_name = "profile_completion_form"

    # Set the instruction text for the user.
    self.lbl_instructions.text = "Welcome! To continue, please complete your profile."

    # Set the event handler for the save button.
    self.btn_save_profile.set_event_handler('click', self.btn_save_profile_click)

  def btn_save_profile_click(self, **event_args):
    """This method is called when the Save and Continue button is clicked."""
    first_name = self.tb_first_name.text.strip()
    last_name = self.tb_last_name.text.strip()

    # --- Client-side validation ---
    if not first_name:
      alert("First Name is required.", title="Incomplete Profile")
      return
    if not last_name:
      alert("Last Name is required.", title="Incomplete Profile")
      return

    # --- Disable button to prevent multiple clicks ---
    self.btn_save_profile.enabled = False
    self.btn_save_profile.text = "Saving..."

    try:
      # --- Call the server function to update the user's profile ---
      anvil.server.call('update_user_profile_names', first_name, last_name)

      # --- Success: Navigate back to the main dashboard ---
      log("INFO", self.module_name, "btn_save_profile_click", "Profile saved successfully.")
      open_form('paddle_home')

    except Exception as e:
      # --- Handle any errors from the server ---
      log("ERROR", self.module_name, "btn_save_profile_click", f"Error saving profile: {str(e)}")
      alert(f"An error occurred while saving your profile: {e}", title="Save Failed")

      # --- Re-enable the button on failure ---
      self.btn_save_profile.enabled = True
      self.btn_save_profile.text = "Save and Continue"