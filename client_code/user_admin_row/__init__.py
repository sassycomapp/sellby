# Client ItemTemplate Form: user_admin_row.py
# Used in rp_users on manage_users.py

from ._anvil_designer import user_admin_rowTemplate
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Adjust path if necessary

class user_admin_row(user_admin_rowTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "user_admin_row"

    # self.item is a dictionary passed by the RepeatingPanel (manage_users.py), containing:
    #   'user_data': A dictionary with user details (email, name, enabled, role_name, role_anvil_id, anvil_user_id, etc.)
    #   'is_logged_in_user_owner': Boolean, True if the user viewing manage_users.py is an Owner.

    self.user_anvil_id = None # Store the Anvil User ID for this row's user
    self.current_role_anvil_id = None # Store the Anvil ID of the user's current role
    self.is_logged_in_user_owner = False # Store the flag from parent

    if self.item and 'user_data' in self.item:
      user_data = self.item['user_data']
      self.is_logged_in_user_owner = self.item.get('is_logged_in_user_owner', False)

      self.user_anvil_id = user_data.get('anvil_user_id')
      self.current_role_anvil_id = user_data.get('role_anvil_id')

      # Populate Labels
      self.lbl_user_email.text = user_data.get('email', "N/A")
      self.lbl_user_full_name.text = user_data.get('full_name') or f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip() or "N/A"

      status_text = "Disabled"
      if user_data.get('enabled'):
        status_text = "Enabled"
        if not user_data.get('confirmed_email'):
          status_text += " (Email Unconfirmed)"
      self.lbl_user_status_anvil.text = status_text

      self.lbl_user_current_role.text = f"Current Role: {user_data.get('role_name', 'Not Assigned')}"

      # Populate Role Assignment Dropdown
      self._populate_roles_dropdown(user_data.get('role_anvil_id'))

      # Set Button States
      if user_data.get('enabled'):
        self.btn_user_enable_disable.text = "Disable User"
        self.btn_user_enable_disable.icon = "fa:toggle-off" # Or fa:ban
      else:
        self.btn_user_enable_disable.text = "Enable User"
        self.btn_user_enable_disable.icon = "fa:toggle-on" # Or fa:check

        # Delete button visibility/enabled state (Only Owner can delete)
        # Also, prevent Owner from deleting themselves.
      is_this_user_the_logged_in_owner = False
      logged_in_user = anvil.users.get_user()
      if logged_in_user and logged_in_user.get_id() == self.user_anvil_id and self.is_logged_in_user_owner:
        is_this_user_the_logged_in_owner = True

      self.btn_user_delete.visible = self.is_logged_in_user_owner and not is_this_user_the_logged_in_owner
      self.btn_user_delete.enabled = self.is_logged_in_user_owner and not is_this_user_the_logged_in_owner

      # Save Changes button - initially disabled until a role is changed in dropdown
      self.btn_user_save_changes.enabled = False 

    else:
      # Fallback if item data is missing
      self.lbl_user_email.text = "Error: No user data"
      self.btn_user_save_changes.enabled = False
      self.btn_user_enable_disable.visible = False
      self.btn_user_delete.visible = False
      self.dd_user_assign_role.items = []
      self.dd_user_assign_role.enabled = False

      # Set event handlers for this item template's buttons/dropdown
    self.dd_user_assign_role.set_event_handler('change', self.dd_user_assign_role_change)
    self.btn_user_save_changes.set_event_handler('click', self.btn_user_save_changes_click)
    self.btn_user_enable_disable.set_event_handler('click', self.btn_user_enable_disable_click)
    self.btn_user_delete.set_event_handler('click', self.btn_user_delete_click)


  def _populate_roles_dropdown(self, user_current_role_anvil_id):
    """Fetches all roles and populates the dd_user_assign_role dropdown."""
    function_name = "_populate_roles_dropdown"
    log("DEBUG", self.module_name, function_name, "Populating roles dropdown.", {"user_email": self.lbl_user_email.text})
    try:
      # This call should be efficient as roles don't change often.
      # Consider caching roles on the manage_users form if performance is an issue for many rows.
      all_roles_data = anvil.server.call('get_all_roles') # Returns list of dicts

      dropdown_items = []
      for role_dict in all_roles_data:
        # Owner can assign any role.
        # Admin should not be able to assign 'Owner' or other 'Admin' roles.
        # This logic needs to be enforced server-side primarily, but UI can guide.
        can_assign = True
        if not self.is_logged_in_user_owner:
          if role_dict['name'] == "Owner" or role_dict['name'] == "Admin":
            can_assign = False

        if can_assign:
          dropdown_items.append( (role_dict['name'], role_dict['role_id_anvil']) )

      self.dd_user_assign_role.items = dropdown_items
      self.dd_user_assign_role.selected_value = user_current_role_anvil_id

      # Enable dropdown only if the logged-in user has permission to assign roles
      # This is a basic check; server-side will do the definitive permission check.
      # For now, assume Owner can always assign, Admin can assign non-Owner/Admin roles.
      # A more granular permission 'assign_user_roles' would be better.
      self.dd_user_assign_role.enabled = self.is_logged_in_user_owner or anvil.server.call('is_admin_user') # Simplified check

    except Exception as e:
      log("ERROR", self.module_name, function_name, f"Error populating roles dropdown: {str(e)}", {"user_email": self.lbl_user_email.text})
      self.dd_user_assign_role.items = []
      self.dd_user_assign_role.enabled = False


  def dd_user_assign_role_change(self, **event_args):
    """Enable save button if role selection has changed from current."""
    selected_role_id = self.dd_user_assign_role.selected_value
    if selected_role_id != self.current_role_anvil_id:
      self.btn_user_save_changes.enabled = True
      log("DEBUG", self.module_name, "dd_user_assign_role_change", "Role selection changed, save enabled.", {"user_email": self.lbl_user_email.text})
    else:
      self.btn_user_save_changes.enabled = False

  def btn_user_save_changes_click(self, **event_args):
    function_name = "btn_user_save_changes_click"
    selected_role_anvil_id = self.dd_user_assign_role.selected_value
  
    selected_role_name_display = "Unknown Role" 
    if self.dd_user_assign_role.selected_value is not None:
      if isinstance(self.dd_user_assign_role.items, list):
        for item_pair in self.dd_user_assign_role.items:
          if isinstance(item_pair, (list, tuple)) and len(item_pair) == 2:
            text, value = item_pair
            if value == selected_role_anvil_id:
              selected_role_name_display = text
              break
  
    if not self.user_anvil_id or selected_role_anvil_id is None:
      alert("User ID or selected role is missing.")
      log("WARNING", self.module_name, function_name, "User ID or selected role missing.", {"user_anvil_id": self.user_anvil_id, "selected_role_anvil_id": selected_role_anvil_id})
      return
  
    log_context = {"user_anvil_id": self.user_anvil_id, "new_role_anvil_id": selected_role_anvil_id, "new_role_name": selected_role_name_display}
    log("INFO", self.module_name, function_name, "Attempting to save role change for user.", log_context)
  
    try:
      anvil.server.call('assign_role_to_user', self.user_anvil_id, selected_role_anvil_id)
      Notification(f"Role for {self.lbl_user_email.text} updated to '{selected_role_name_display}'.", style="success").show()
      log("INFO", self.module_name, function_name, "Role updated successfully.", log_context)
  
      self.lbl_user_current_role.text = f"Current Role: {selected_role_name_display}" 
      self.current_role_anvil_id = selected_role_anvil_id
      self.btn_user_save_changes.enabled = False 
  
    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {str(e)}", title="Update Failed")
      log("WARNING", self.module_name, function_name, "Permission denied assigning role.", {**log_context, "error": str(e)})
      self.dd_user_assign_role.selected_value = self.current_role_anvil_id 
    except Exception as e:
      alert(f"Error updating role: {str(e)}", title="Error")
      log("ERROR", self.module_name, function_name, "Error updating role.", {**log_context, "error": str(e)})
      self.dd_user_assign_role.selected_value = self.current_role_anvil_id


  def btn_user_enable_disable_click(self, **event_args):
    """Enables or disables the user's Anvil account."""
    function_name = "btn_user_enable_disable_click"
    if not self.user_anvil_id:
      return

    current_status_enabled = self.item['user_data'].get('enabled', False)
    new_status_bool = not current_status_enabled
    action_verb = "disable" if new_status_bool is False else "enable" # For confirmation message

    log_context = {"user_anvil_id": self.user_anvil_id, "action": action_verb}

    if confirm(f"Are you sure you want to {action_verb} the user {self.lbl_user_email.text}?", title=f"Confirm User {action_verb.capitalize()}"):
      log("INFO", self.module_name, function_name, f"User confirmed {action_verb} action.", log_context)
      try:
        # We need a server function for this, e.g., 'set_user_enabled_status'
        # This function should also check permissions (e.g., Owner cannot be disabled by Admin)
        anvil.server.call('set_user_enabled_status', self.user_anvil_id, new_status_bool)

        Notification(f"User {self.lbl_user_email.text} has been {action_verb}d.", style="success").show()
        log("INFO", self.module_name, function_name, "User status updated successfully.", log_context)

        # Refresh this item's display by re-assigning self.item or calling parent to refresh
        # For simplicity, ask parent to refresh the whole list
        self.parent.raise_event('x-refresh-users') 

      except anvil.server.PermissionDenied as e:
        alert(f"Permission Denied: {str(e)}", title="Action Failed")
        log("WARNING", self.module_name, function_name, "Permission denied setting user enabled status.", {**log_context, "error": str(e)})
      except Exception as e:
        alert(f"Error updating user status: {str(e)}", title="Error")
        log("ERROR", self.module_name, function_name, "Error setting user enabled status.", {**log_context, "error": str(e)})
    else:
      log("INFO", self.module_name, function_name, f"User cancelled {action_verb} action.", log_context)


  def btn_user_delete_click(self, **event_args):
    """Deletes the user's Anvil account."""
    function_name = "btn_user_delete_click"
    if not self.user_anvil_id or not self.is_logged_in_user_owner: # Double check permission
      return

    user_email_to_delete = self.lbl_user_email.text
    log_context = {"user_anvil_id_to_delete": self.user_anvil_id, "user_email": user_email_to_delete}

    if confirm(f"WARNING: Are you absolutely sure you want to permanently delete the user {user_email_to_delete}? This action cannot be undone.", title="Confirm User Deletion", buttons=[("DELETE USER", True), ("Cancel", False)]):
      log("INFO", self.module_name, function_name, "User confirmed deletion.", log_context)
      try:
        # We need a server function for this, e.g., 'delete_user_account'
        # This function must have strong safeguards and permission checks (Owner only, cannot delete self).
        anvil.server.call('delete_user_account', self.user_anvil_id)
        Notification(f"User {user_email_to_delete} has been deleted.", style="success").show()
        log("INFO", self.module_name, function_name, "User account deleted successfully.", log_context)
        self.parent.raise_event('x-refresh-users') # Refresh list in parent
      except anvil.server.PermissionDenied as e:
        alert(f"Permission Denied: {str(e)}", title="Action Failed")
        log("WARNING", self.module_name, function_name, "Permission denied deleting user.", {**log_context, "error": str(e)})
      except Exception as e:
        alert(f"Error deleting user: {str(e)}", title="Error")
        log("ERROR", self.module_name, function_name, "Error deleting user.", {**log_context, "error": str(e)})
    else:
      log("INFO", self.module_name, function_name, "User cancelled deletion.", log_context)
