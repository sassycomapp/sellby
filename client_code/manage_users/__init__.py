# Client Form: manage_users.py

from ._anvil_designer import manage_usersTemplate
from anvil import *
import anvil.server
import anvil.users
from ..cm_logs_helper import log
from ..user_admin_row import user_admin_row # Ensure this import is present

class manage_users(manage_usersTemplate):
    def __init__(self, **properties):
        self.init_components(**properties)
        # Explicitly set the item template (optional but good for debugging)
        self.rp_users.item_template = user_admin_row
        log("INFO", "manage_users", "__init__", "Form initializing")

        self.user = anvil.users.get_user()
        self.is_owner = False

        # --- Permission Check ---
        try:
            if not anvil.server.call('is_admin_user'):
                # ... (permission denied logic) ...
                log("WARNING", "manage_users", "__init__", "Access denied - Admin privileges required", {"user_email": self.user['email'] if self.user else "None"})
                alert("Access denied. Admin privileges required to view this page.")
                open_form("paddle_home")
                return

            log("INFO", "manage_users", "__init__", "Admin access verified", {"user_email": self.user['email']})
            self.is_owner = anvil.server.call('is_owner_user')
            log("INFO", "manage_users", "__init__", f"Owner status: {self.is_owner}", {"user_email": self.user['email']})

            # --- Set up event handler BEFORE loading users that might use it ---
            # Ensure the method refresh_users_list is defined below
            self.rp_users.set_event_handler('x-refresh-users', self.refresh_users_list)
            log("DEBUG", "manage_users", "__init__", "Set event handler for x-refresh-users")

            self.load_users()

        except Exception as e:
            log("ERROR", "manage_users", "__init__", f"Error during initialization or permission check: {e}", {"user_email": self.user['email'] if self.user else "None"})
            alert(f"An error occurred: {e}")
            open_form("paddle_home")

    # --- load_users method definition ---

    def load_users(self):
      """Load all users with their role details into the repeating panel."""
      module_name = "manage_users" # For client-side logging
      function_name = "load_users"
      log("INFO", module_name, function_name, "Attempting to load users with role details.")
  
      try:
        # Call the new server function that includes role details
        # This returns a list of dictionaries, each dict representing a user with their role info.
        user_list_from_server = anvil.server.call('get_all_users_with_role_details')
        log("DEBUG", module_name, function_name, f"Received {len(user_list_from_server)} users from server.")
  
        # Prepare items for the RepeatingPanel.
        # The item_template (user_admin_row) will receive a dictionary containing:
        #   'user_data': The dictionary for the user (e.g., email, name, role_name, role_anvil_id, etc.)
        #   'is_logged_in_user_owner': Boolean flag (self.is_owner)
  
        items_for_rp = []
        for user_data_dict in user_list_from_server:
          items_for_rp.append({
            'user_data': user_data_dict,
            'is_logged_in_user_owner': self.is_owner 
            # Pass any other form-level context needed by the item template here
          })
  
        self.rp_users.items = items_for_rp
        log("INFO", module_name, function_name, f"Successfully loaded {len(items_for_rp)} users into repeating panel.")
  
      except anvil.server.PermissionDenied as e:
        log("WARNING", module_name, function_name, f"Permission denied fetching users: {str(e)}", {"user_email": self.user['email'] if self.user else "None"})
        alert(f"Permission Denied: {str(e)}")
        self.rp_users.items = []
      except Exception as e:
        # It's good practice to import traceback for detailed client-side error logging during development
        # import traceback
        # log_context_error = {"user_email": self.user['email'] if self.user else "None", "trace": traceback.format_exc()}
        log_context_error = {"user_email": self.user['email'] if self.user else "None"} # Simpler for now
        log("ERROR", module_name, function_name, f"Error loading users: {str(e)}", log_context_error)
        alert(f"Error loading users: {str(e)}")
        self.rp_users.items = []


    # --- btn_home_click method definition ---
    def btn_home_click(self, **event_args):
      """This method is called when the button is clicked"""
      log("INFO", "manage_users", "btn_home_click", "Home button clicked")
      open_form('paddle_home')

   # --- refresh_users_list method definition ---
    # --- Renamed from btn_refresh_click to match event handler ---
    def refresh_users_list(self, **event_args):
        """Event handler called by child rows or refresh button to refresh the user list."""
        log("INFO", "manage_users", "refresh_users_list", "Refresh requested")
        self.load_users()

    def btn_refresh_click(self, **event_args):
      """This method is called when the button is clicked"""
      open_form('manage_users')
