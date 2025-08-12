# Client Form: owner_setup_form.py

from ._anvil_designer import owner_setup_formTemplate
from anvil import *
import anvil.server
# Import client-side logger
from ..cm_logs_helper import log # Assuming cm_logs_helper is in the parent directory

class owner_setup_form(owner_setup_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    log("INFO", "owner_setup_form", "__init__", "Form opened for initial owner setup")

    # Call server function to ensure the temporary "owner" role exists
    try:
      # This server function will be created in sessions_server.py
      # It will check for a role named "owner" (lowercase) and create it if not present.
      success_role_check = anvil.server.call('ensure_temporary_owner_role_exists') 
      if not success_role_check:
        alert("Critical error: Could not ensure temporary setup role exists. Please contact support.", title="Setup Prerequisite Failed")
        if hasattr(self, 'btn_set_password'): # Check if button exists
          self.btn_set_password.enabled = False
    except Exception as e:
      alert(f"Error during initial role check: {e}. Setup might fail.", title="Setup Warning")
      if hasattr(self, 'btn_set_password'): # Check if button exists
        self.btn_set_password.enabled = False

    # Clear feedback label
    if hasattr(self, 'lbl_feedback'): # Check if label exists
      self.lbl_feedback.text = ""
      self.lbl_feedback.foreground = "" 

    # Ensure password fields hide text
    if hasattr(self, 'tb_owner_password'): # Check if textbox exists
      self.tb_owner_password.hide_text = True
    if hasattr(self, 'tb_confirm_password'): # Check if textbox exists
      self.tb_confirm_password.hide_text = True

    if hasattr(self, 'btn_close'): # Check if button exists
      self.btn_close.visible = True
      self.btn_close.enabled = True
    # Ensure "Set Password" button is enabled if the role check didn't disable it
    # This logic might need refinement based on how success_role_check is used above.
    # If an exception occurred and disabled it, it should remain disabled.
    # If success_role_check is False and it was disabled, it should remain disabled.
    # Only if it was True and somehow got disabled, or was never disabled, should it be enabled.
    # The current logic in the try/except block handles disabling on failure.
    # If it passes that, btn_set_password should be in its default (likely enabled) state.
    if hasattr(self, 'btn_set_password'):
      if not self.btn_set_password.enabled: # If it was explicitly set to False due to an error
        pass # Keep it disabled
      else:
        self.btn_set_password.enabled = True # Ensure it's enabled otherwise


  def btn_set_password_click(self, **event_args):
    """This method is called when the button is clicked"""
    log("INFO", "owner_setup_form", "btn_set_password_click", "Set password button clicked")

    # Clear previous feedback
    if hasattr(self, 'lbl_feedback'):
      self.lbl_feedback.text = ""
      self.lbl_feedback.foreground = ""

    # --- 1. Get Passwords ---
    password = ""
    if hasattr(self, 'tb_owner_password'):
      password = self.tb_owner_password.text

    confirm_password = ""
    if hasattr(self, 'tb_confirm_password'):
      confirm_password = self.tb_confirm_password.text

    # --- 2. Client-Side Validation ---
    if not password or not confirm_password:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = "Please enter and confirm the password."
        self.lbl_feedback.foreground = "red"
      log("WARNING", "owner_setup_form", "btn_set_password_click", "Validation failed: Empty password fields")
      return

    if password != confirm_password:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = "Passwords do not match."
        self.lbl_feedback.foreground = "red"
      log("WARNING", "owner_setup_form", "btn_set_password_click", "Validation failed: Passwords mismatch")
      return

    MIN_PASSWORD_LENGTH = 8
    if len(password) < MIN_PASSWORD_LENGTH:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        self.lbl_feedback.foreground = "red"
      log("WARNING", "owner_setup_form", "btn_set_password_click", f"Validation failed: Password too short (length {len(password)})")
      return

    # --- 3. Call Server ---
    if hasattr(self, 'lbl_feedback'):
      self.lbl_feedback.text = "Setting password..."
      self.lbl_feedback.foreground = ""
    log("DEBUG", "owner_setup_form", "btn_set_password_click", "Client validation passed, calling server 'set_initial_owner_password'")

    try:
      success = anvil.server.call('set_initial_owner_password', password)

      if success:
        if hasattr(self, 'lbl_feedback'):
          self.lbl_feedback.text = "Owner password set successfully!"
          self.lbl_feedback.foreground = "green"
        log("INFO", "owner_setup_form", "btn_set_password_click", "Server reported owner setup successful")

        if hasattr(self, 'tb_owner_password'): 
          self.tb_owner_password.enabled = False
        if hasattr(self, 'tb_confirm_password'): 
          self.tb_confirm_password.enabled = False
        if hasattr(self, 'btn_set_password'): 
          self.btn_set_password.enabled = False
        if hasattr(self, 'btn_close'): 
          self.btn_close.visible = True 
          self.btn_close.enabled = True
      else:
        if hasattr(self, 'lbl_feedback'):
          self.lbl_feedback.text = "Setup process completed but did not report success."
          self.lbl_feedback.foreground = "orange"
        log("ERROR", "owner_setup_form", "btn_set_password_click", "Server returned non-True value unexpectedly")

    except anvil.server.PermissionDenied as e:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = f"Setup Failed: {e}" 
        self.lbl_feedback.foreground = "red"
      log("ERROR", "owner_setup_form", "btn_set_password_click", f"Permission denied by server: {e}")
    except ValueError as e:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = f"Setup Failed: {e}" 
        self.lbl_feedback.foreground = "red"
      log("ERROR", "owner_setup_form", "btn_set_password_click", f"Value error from server: {e}")
    except Exception as e:
      if hasattr(self, 'lbl_feedback'):
        self.lbl_feedback.text = f"An unexpected error occurred: {e}"
        self.lbl_feedback.foreground = "red"
      log("CRITICAL", "owner_setup_form", "btn_set_password_click", f"Unexpected exception during server call: {e}")

  def btn_close_click(self, **event_args):
    """This method is called when the Close button is clicked."""
    log("INFO", "owner_setup_form", "btn_close_click", "Close button clicked")
    self.raise_event("x-close-alert", value=True)