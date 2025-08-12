# Client Form: vault.py

from ._anvil_designer import vaultTemplate
from anvil import *
import anvil.server
import anvil.users
from ..secret_item_form import secret_item_form 
# Import client-side logger
from ..cm_logs_helper import log

class vault(vaultTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    log("INFO", "vault", "__init__", "Form initializing")

    # --- SET ITEM TEMPLATE FOR REPEATING PANEL ---
    self.rp_secrets.item_template = secret_item_form
    # --- END SET ITEM TEMPLATE ---

    # Clear form fields initially
    self._clear_form()

    # Set up event handler for refresh requests from child rows (secret_item_form)
    self.rp_secrets.set_event_handler("x-refresh", self._load_secrets) 

    # Initialize vault (checks permissions and loads data)
    self._initialize_vault()

    # Ensure event handler for btn_show_credential_status_click is set if the button exists
    if hasattr(self, 'btn_show_credential_status_click'):
      # Check if the handler is already set by the designer or a previous call
      # This check is a bit verbose; usually, just setting it is fine.
      # However, to be absolutely sure not to double-add if designer also sets it (though unlikely for 'click'):
      # Note: Anvil's event system typically handles multiple calls to set_event_handler for the same event gracefully,
      # replacing the previous one. So, direct assignment is usually safe.
      self.btn_show_credential_status_click.set_event_handler('click', self.btn_show_credential_status_click)
 
    def _initialize_vault(self):
        """Check permissions and load secrets if access is allowed."""
        log("DEBUG", "vault", "_initialize_vault", "Checking permissions and loading secrets")
        try:
            # Use the central server check - allows Owner, Admin, or Temp Admin
            is_authorized = anvil.server.call('is_admin_user')
            log("INFO", "vault", "_initialize_vault", f"Admin access check result: {is_authorized}")
            log("INFO", "vault", "_initialize_vault", f"is_authorized type: {type(is_authorized)}") #Debug
    
            user = anvil.users.get_user()
            log("INFO", "vault", "_initialize_vault", f"anvil.users.get_user() value: {user}, type: {type(user)}")
    
            if not is_authorized:
                if user:
                    try:
                      user_email = user['email']
                    except Exception as e:
                      user_email = f"Error getting email: {e}"
                else:
                    user_email = "None"
    
                log("WARNING", "vault", "_initialize_vault", "Access denied", {"user_email": user_email})
                alert("You do not have permission to view this page.")
                open_form("paddle_home") # Redirect if not authorized
                # Raise exception to halt further initialization of this form
                raise PermissionError("Access Denied")
    
            # If authorized, proceed to load secrets
            self._load_secrets()
    
        except PermissionError: # Catch the specific error raised above
            # Already handled with alert/redirect, just pass to stop execution
            pass
        except Exception as e:
            # Catch other errors during permission check or initial load
            user = anvil.users.get_user()
            log("ERROR", "vault", "_initialize_vault", f"Error during initialization: {e}", {"user_email": user['email'] if user else "None"})
            alert(f"Error initializing vault access: {e}")
            # Optionally redirect on other errors too
            open_form("paddle_home")
    

    def _load_secrets(self, **event_args):
        """Fetch and display secrets in the repeating panel. Can be called directly or as an event handler."""
        # The **event_args will capture any arguments passed by the event system (like 'sender')
        # We don't actually need to *use* event_args inside this function for this purpose.
        log("DEBUG", "vault", "_load_secrets", "Attempting to load secrets")
        try:
            # Call server function (requires admin privileges)
            # This now returns a list of DICTIONARIES
            secrets_list_for_client = anvil.server.call('get_all_secrets')
            log("INFO", "vault", "_load_secrets", f"Retrieved {len(secrets_list_for_client)} secrets (as dicts) from server")
    
            # Assign the list of dictionaries to the repeating panel
            self.rp_secrets.items = secrets_list_for_client
    
        except anvil.server.PermissionDenied as e:
            log("WARNING", "vault", "_load_secrets", f"Permission denied fetching secrets: {e}")
            alert(f"Permission Denied: {e}")
            self.rp_secrets.items = [] # Clear display on permission error
        except Exception as e:
            log("ERROR", "vault", "_load_secrets", f"Error loading secrets: {e}")
            alert(f"Error loading secrets: {e}")
            self.rp_secrets.items = [] # Clear display on other errors


    def _clear_form(self):
        """Reset all input fields."""
        log("DEBUG", "vault", "_clear_form", "Clearing input fields")
        self.tb_key.text = ""
        self.ta_value.text = "" # Assuming TextArea for value
        self.tb_scope.text = ""
        self.tb_description.text = ""


    def refresh_secrets_list(self, **event_args):
        """Event handler called by child rows to refresh the secrets list."""
        log("INFO", "vault", "refresh_secrets_list", "Refresh requested from child row")
        self._load_secrets()


    # ======================
    # Button Click Handlers
    # ======================

    def btn_save_click(self, **event_args):
        """Handles saving a new or updated secret."""
        key = self.tb_key.text.strip()
        value = self.ta_value.text.strip()
        scope = self.tb_scope.text.strip()
        description = self.tb_description.text.strip()

        log("INFO", "vault", "btn_save_click", f"Save button clicked for key: '{key}'")

        if not key or not value:
            log("WARNING", "vault", "btn_save_click", "Save failed: Key or value empty")
            alert("Secret key and value are required.")
            return

        try:
            log("DEBUG", "vault", "btn_save_click", f"Calling server save_secret for key: '{key}'")
            # Server call (requires admin privileges, prevents owner password modification)
            anvil.server.call('save_secret', key, value, scope, description)

            log("INFO", "vault", "btn_save_click", f"Secret '{key}' saved successfully")
            Notification(f"Secret '{key}' saved.", style="success", timeout=2).show()
            self._load_secrets() # Refresh the list
            self._clear_form()   # Clear inputs after successful save

        except anvil.server.PermissionDenied as e:
             log("ERROR", "vault", "btn_save_click", f"Permission denied saving secret '{key}': {e}")
             Notification(f"Permission Denied: {e}", style="danger", timeout=4).show()
        except Exception as e:
            log("ERROR", "vault", "btn_save_click", f"Error saving secret '{key}': {e}")
            Notification(f"Error saving secret: {e}", style="danger", timeout=4).show()


    def btn_clear_click(self, **event_args):
        """Handles clearing the input form."""
        log("INFO", "vault", "btn_clear_click", "Clear button clicked")
        self._clear_form()


    def btn_home_click(self, **event_args):
        """Handles navigating back to the home form."""
        log("INFO", "vault", "btn_home_click", "Home button clicked")
        open_form('paddle_home')

    def btn_test_decryption_click(self, **event_args):
        """Button click handler to test decryption of a secret key."""
        # Get the key name from the input field
        key_to_test = self.tb_key.text.strip()

        if not key_to_test:
            alert("Please enter the Secret Key name you want to test in the 'Secret Key' field.")
            return

        log("INFO", "vault", "btn_test_decryption_click", f"Initiating decryption test for key: '{key_to_test}'")
        try:
            # Call the server function
            result_message = anvil.server.call('test_decryption', key_to_test)
            # Display the result message from the server
            alert(result_message)
            log("INFO", "vault", "btn_test_decryption_click", f"Test result for '{key_to_test}': {result_message}")

        except anvil.server.PermissionDenied as e:
             log("ERROR", "vault", "btn_test_decryption_click", f"Permission denied testing decryption for '{key_to_test}': {e}")
             alert(f"Permission Denied: {e}")
        except Exception as e:
            log("ERROR", "vault", "btn_test_decryption_click", f"Error testing decryption for '{key_to_test}': {e}")
            alert(f"An error occurred during the decryption test: {e}")

    def btn_show_credential_status_click(self, **event_args):
        """This method is called when the button is clicked"""
        log("INFO", "vault", "btn_show_credential_status_click", "Button clicked, opening essential_credentials_status_form")
        open_form('essential_credentials_status_form')

