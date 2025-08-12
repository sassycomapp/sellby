# Client Form: manage_rbac.py

from ._anvil_designer import manage_rbacTemplate
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Adjust path if necessary
from ..role_list_item_form import role_list_item_form 
from ..permission_assignment_item_form import permission_assignment_item_form 

class manage_rbac(manage_rbacTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.module_name = "manage_rbac_form" 
    log("INFO", self.module_name, "__init__", "Form initializing.")

    self.tabs_main_rbac.set_event_handler('tab_click', self.tabs_main_rbac_tab_click)

    self.rp_roles.item_template = role_list_item_form
    self.rp_permissions_for_role.item_template = permission_assignment_item_form

    self.rp_roles.set_event_handler('x-edit-role', self.handle_edit_role_event)
    self.rp_roles.set_event_handler('x-delete-role', self.handle_delete_role_event)
    self.btn_save_role.set_event_handler('click', self.btn_save_role_click)
    self.btn_clear_role_form.set_event_handler('click', self.btn_clear_role_form_click)
    self.btn_delete_role.set_event_handler('click', self.btn_delete_main_form_role_click) 

    self.dd_select_role_for_permissions.set_event_handler('change', self.dd_select_role_for_permissions_change)
    self.btn_save_role_permissions.set_event_handler('click', self.btn_save_role_permissions_click)

    self.btn_load_base_permissions.set_event_handler('click', self.btn_load_base_permissions_click)
    self.btn_reset_permissions.set_event_handler('click', self.btn_reset_permissions_click)

    if hasattr(self, 'btn_exit'): 
      self.btn_exit.set_event_handler('click', self.btn_exit_click) 

    self.selected_role_for_edit_anvil_id = None 
    self.all_permissions_cache = [] 

    self._clear_role_form_fields()

    # Directly call the tab_click handler for the first tab (index 0)
    # Assuming the first tab is "Role Management". Adjust title if different in designer.
    self.tabs_main_rbac_tab_click(tab_index=0, tab_title="Role Management") 

    self._load_roles_into_ui() 
    self._load_all_permissions_cache() 

    log("INFO", self.module_name, "__init__", "Form initialization complete.")

  def tabs_main_rbac_tab_click(self, tab_index, tab_title, **event_args):
    """Handles visibility of content panels when a tab is clicked."""
    log("DEBUG", self.module_name, "tabs_main_rbac_tab_click", f"Tab '{tab_title}' (index {tab_index}) clicked.")

    self.cp_role_management.visible = False
    self.cp_permission_assignment.visible = False

    if tab_index == 0: # Assuming Role Management is the first tab (index 0)
      self.cp_role_management.visible = True
      # Data for rp_roles is loaded in __init__ or by _load_roles_into_ui if explicitly called by user/refresh
    elif tab_index == 1: # Assuming Permission Assignment is the second tab (index 1)
      self.cp_permission_assignment.visible = True
      # Data for dd_select_role_for_permissions and all_permissions_cache is loaded in __init__
      # Populate/refresh permissions for the selected role if one is selected
      if self.dd_select_role_for_permissions.selected_value:
        self._populate_permissions_rp_for_selected_role()
      else:
        self.rp_permissions_for_role.items = [] # Clear if no role selected

  def _clear_role_form_fields(self):
    """Clears the input fields in the 'Add/Edit Role' section."""
    log("DEBUG", self.module_name, "_clear_role_form_fields", "Clearing role form fields.")
    self.selected_role_for_edit_anvil_id = None
    self.tb_role_name.text = ""
    self.ta_role_description.text = ""
    self.chk_is_system_role.checked = False
    self.chk_is_system_role.enabled = False 
    self.btn_delete_role.visible = False
    self.lbl_add_edit_role_title.text = "Add New Role"
    self.btn_save_role.text = "Create Role"

  # In manage_rbac.py

  def _load_roles_into_ui(self, **event_args):
    """Fetches all roles and populates rp_roles and dd_select_role_for_permissions."""
    function_name = "_load_roles_into_ui"
    # Ensure self.module_name is defined in __init__ (e.g., self.module_name = "manage_rbac_form")
    log("INFO", self.module_name, function_name, "Attempting to load all roles into UI.")
    try:
      all_roles_data = anvil.server.call('get_all_roles') # This is from sm_rbac_mod.py

      # Populate the RepeatingPanel for role management
      if hasattr(self, 'rp_roles'):
        self.rp_roles.items = all_roles_data 
        log("DEBUG", self.module_name, function_name, f"Populated rp_roles with {len(all_roles_data)} roles.")

      # Populate the DropDown for permission assignment
      if hasattr(self, 'dd_select_role_for_permissions'):
        dropdown_items = [("Select a Role to Configure Permissions...", None)] 
        for role_dict in all_roles_data:
          role_name = role_dict.get('name')
          role_anvil_id = role_dict.get('role_id_anvil')

          if role_name and role_anvil_id: # Only add if role_name and role_id_anvil are valid
            dropdown_items.append( (role_name, role_anvil_id) ) 
          else:
            # Log if a role is skipped due to missing critical data
            log("WARNING", self.module_name, function_name, 
                f"Skipping role in dropdown due to missing name or anvil_id: {role_dict.get('role_id_mybizz', 'Unknown MyBizz ID')}")

        current_selected_dd_role_anvil_id = self.dd_select_role_for_permissions.selected_value
        self.dd_select_role_for_permissions.items = dropdown_items

        # Try to reselect the previously selected value if it still exists in the new items list
        if any(item[1] == current_selected_dd_role_anvil_id for item in dropdown_items if item[1] is not None):
          self.dd_select_role_for_permissions.selected_value = current_selected_dd_role_anvil_id
        elif current_selected_dd_role_anvil_id is not None: 
          # If previous selection is no longer valid, clear it and the permissions panel
          self.dd_select_role_for_permissions.selected_value = None
          if hasattr(self, 'rp_permissions_for_role'):
            self.rp_permissions_for_role.items = []

        log("DEBUG", self.module_name, function_name, "Populated dd_select_role_for_permissions.")

    except anvil.server.PermissionDenied as e:
      log("WARNING", self.module_name, function_name, f"Permission denied loading roles: {str(e)}")
      alert(f"Permission Denied: {str(e)}")
      if hasattr(self, 'rp_roles'): 
        self.rp_roles.items = []
      if hasattr(self, 'dd_select_role_for_permissions'): 
        self.dd_select_role_for_permissions.items = [("Error loading roles", None)]
    except Exception as e:
      log("ERROR", self.module_name, function_name, f"Error loading roles into UI: {str(e)}")
      alert(f"An error occurred while loading roles: {str(e)}")
      if hasattr(self, 'rp_roles'): 
        self.rp_roles.items = []
      if hasattr(self, 'dd_select_role_for_permissions'): 
        self.dd_select_role_for_permissions.items = [("Error loading roles", None)]

  def _load_all_permissions_cache(self):
    """Fetches all system permissions and caches them."""
    function_name = "_load_all_permissions_cache"
    log("INFO", self.module_name, function_name, "Attempting to load and cache all permissions.")
    try:
      self.all_permissions_cache = anvil.server.call('get_all_permissions') 
      log("DEBUG", self.module_name, function_name, f"Cached {len(self.all_permissions_cache)} permissions.")
    except Exception as e:
      self.all_permissions_cache = []
      log("ERROR", self.module_name, function_name, f"Error caching permissions: {str(e)}")
      alert(f"Could not load system permissions: {str(e)}")

  def _populate_permissions_rp_for_selected_role(self):
    """Populates rp_permissions_for_role based on the cached all_permissions
           and the permissions assigned to the currently selected role in the dropdown."""
    function_name = "_populate_permissions_rp_for_selected_role"
    selected_role_anvil_id = self.dd_select_role_for_permissions.selected_value
    log_context = {"selected_role_anvil_id": selected_role_anvil_id}

    self.rp_permissions_for_role.items = []
    if not selected_role_anvil_id:
      log("DEBUG", self.module_name, function_name, "No role selected in dropdown.", log_context)
      return
    if not self.all_permissions_cache:
      log("WARNING", self.module_name, function_name, "Permissions cache is empty. Cannot populate RP.", log_context)
      self._load_all_permissions_cache()
      if not self.all_permissions_cache: 
        alert("Failed to load permission definitions. Please try refreshing.", role="negative")
        return

    log("INFO", self.module_name, function_name, "Populating permissions RP for selected role.", log_context)
    try:
      permissions_for_selected_role_names = anvil.server.call('get_permissions_for_role', selected_role_anvil_id) 
      log("DEBUG", self.module_name, function_name, f"Fetched {len(permissions_for_selected_role_names)} assigned permissions for selected role.", log_context)

      items_for_rp = []
      for perm_dict in self.all_permissions_cache: 
        perm_dict_copy = perm_dict.copy() 
        perm_dict_copy['is_assigned'] = perm_dict_copy['name'] in permissions_for_selected_role_names
        items_for_rp.append(perm_dict_copy)

      self.rp_permissions_for_role.items = items_for_rp
      log("INFO", self.module_name, function_name, "Populated rp_permissions_for_role.", log_context)

    except anvil.server.PermissionDenied as e:
      log("WARNING", self.module_name, function_name, f"Permission denied loading permissions for role: {str(e)}", log_context)
      alert(f"Permission Denied: {str(e)}")
    except Exception as e:
      log("ERROR", self.module_name, function_name, f"Error loading permissions for role: {str(e)}", log_context)
      alert(f"An error occurred while loading permissions for the role: {str(e)}")

  def dd_select_role_for_permissions_change(self, **event_args):
    """Handles change event for the role selection dropdown in permission assignment tab."""
    function_name = "dd_select_role_for_permissions_change"
    selected_role_anvil_id = self.dd_select_role_for_permissions.selected_value
    log("INFO", self.module_name, function_name, "Role selected for permission assignment.", {"selected_role_anvil_id": selected_role_anvil_id})
    self._populate_permissions_rp_for_selected_role()

  def btn_save_role_click(self, **event_args):
    """Saves a new or updated custom role."""
    function_name = "btn_save_role_click"
    role_name = self.tb_role_name.text.strip()
    role_description = self.ta_role_description.text.strip()
    log_context = {"role_name": role_name, "selected_role_for_edit_anvil_id": self.selected_role_for_edit_anvil_id}

    if not role_name:
      alert("Role Name is required.")
      return

    log("INFO", self.module_name, function_name, "Attempting to save role.", log_context)
    try:
      if self.selected_role_for_edit_anvil_id: 
        role_being_edited = next((r for r in self.rp_roles.items if r['role_id_anvil'] == self.selected_role_for_edit_anvil_id), None)
        if role_being_edited and role_being_edited.get('is_system_role'):
          alert(f"System role '{role_being_edited.get('name')}' name and description cannot be modified here.", title="Modification Not Allowed")
          log("WARNING", self.module_name, function_name, f"Attempt to modify system role '{role_being_edited.get('name')}' denied.", log_context)
          return

        anvil.server.call('update_custom_role', self.selected_role_for_edit_anvil_id, role_name, role_description)
        Notification(f"Role '{role_name}' updated successfully.", style="success").show()
        log("INFO", self.module_name, function_name, "Role updated.", log_context)
      else: 
        anvil.server.call('create_custom_role', role_name, role_description)
        Notification(f"Role '{role_name}' created successfully.", style="success").show()
        log("INFO", self.module_name, function_name, "New role created.", log_context)

      self._clear_role_form_fields()
      self._load_roles_into_ui() 

    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {str(e)}", title="Error")
      log("WARNING", self.module_name, function_name, "Permission denied saving role.", {**log_context, "error": str(e)})
    except ValueError as ve: 
      alert(str(ve), title="Save Failed")
      log("WARNING", self.module_name, function_name, "Validation error saving role.", {**log_context, "error": str(ve)})
    except Exception as e:
      alert(f"Error saving role: {str(e)}", title="Error")
      log("ERROR", self.module_name, function_name, "Error saving role.", {**log_context, "error": str(e)})

  def btn_clear_role_form_click(self, **event_args):
    """Clears the role input form fields."""
    log("INFO", self.module_name, "btn_clear_role_form_click", "Clear role form button clicked.")
    self._clear_role_form_fields()
      
  def btn_delete_main_form_role_click(self, **event_args):
    """Deletes the role currently loaded in the main form for editing."""
    function_name = "btn_delete_main_form_role_click"
    if self.selected_role_for_edit_anvil_id:
      role_data_to_delete = next((r for r in self.rp_roles.items if r['role_id_anvil'] == self.selected_role_for_edit_anvil_id), None)
      if role_data_to_delete:
        self.handle_delete_role_event(role_data_to_delete) 
      else:
        log("WARNING", self.module_name, function_name, "Could not find role data for deletion from main form.", {"selected_id": self.selected_role_for_edit_anvil_id})
        alert("Could not find role data to delete. Please refresh the role list.", role="negative")
    else:
      log("DEBUG", self.module_name, function_name, "Main form delete button clicked but no role selected in form.")
      alert("No role is currently loaded in the form to delete.")

  def btn_save_role_permissions_click(self, **event_args):
    """Saves the permission assignments for the currently selected role."""
    function_name = "btn_save_role_permissions_click"
    selected_role_anvil_id = self.dd_select_role_for_permissions.selected_value
    selected_role_display_name = "Unknown Role"
    if self.dd_select_role_for_permissions.items and selected_role_anvil_id:
      for name, val_id in self.dd_select_role_for_permissions.items:
        if val_id == selected_role_anvil_id:
          selected_role_display_name = name
          break

    if not selected_role_anvil_id:
      alert("Please select a role before saving permissions.")
      return

    assigned_permission_names = []
    for item_form_instance in self.rp_permissions_for_role.get_components():
      if hasattr(item_form_instance, 'chk_assign_permission') and item_form_instance.chk_assign_permission.checked:
        if item_form_instance.item and 'name' in item_form_instance.item:
          assigned_permission_names.append(item_form_instance.item['name']) 
        else:
          log("WARNING", self.module_name, function_name, "Item form instance in RP missing item or item name.", {"component": item_form_instance})

    log_context = {"selected_role_anvil_id": selected_role_anvil_id, 
                   "selected_role_name": selected_role_display_name, 
                   "assigned_permission_names_count": len(assigned_permission_names)}
    log("INFO", self.module_name, function_name, "Attempting to save permission assignments for role.", log_context)

    try:
      anvil.server.call('update_permissions_for_role', selected_role_anvil_id, assigned_permission_names)
      Notification(f"Permissions for role '{selected_role_display_name}' updated successfully.", style="success").show()
      log("INFO", self.module_name, function_name, "Permissions updated successfully.", log_context)
      self._populate_permissions_rp_for_selected_role() 
    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {str(e)}", title="Error")
      log("WARNING", self.module_name, function_name, "Permission denied saving permissions.", {**log_context, "error": str(e)})
    except Exception as e:
      alert(f"Error saving permissions: {str(e)}", title="Error")
      log("ERROR", self.module_name, function_name, "Error saving permissions.", {**log_context, "error": str(e)})

  def btn_load_base_permissions_click(self, **event_args):
      """Calls server to initialize/ensure default RBAC data."""
      module_name = self.module_name 
      function_name = "btn_load_base_permissions_click"
      log("INFO", module_name, function_name, "Load Base Permissions button clicked.")
      
      try:
          result_message = anvil.server.call('initialize_default_rbac_data')
          Notification(result_message, style="success", timeout=4).show()
          log("INFO", module_name, function_name, f"Server call 'initialize_default_rbac_data' completed. Message: {result_message}")
          self._load_roles_into_ui() 
          self._load_all_permissions_cache() 
          if self.dd_select_role_for_permissions.selected_value:
              self._populate_permissions_rp_for_selected_role()
          else:
              self.rp_permissions_for_role.items = []

      except anvil.server.PermissionDenied as e:
          log("WARNING", module_name, function_name, f"Permission denied by server: {str(e)}")
          alert(f"Permission Denied: {str(e)}")
      except Exception as e:
          log("ERROR", module_name, function_name, f"Error calling 'initialize_default_rbac_data': {str(e)}")
          alert(f"An error occurred: {str(e)}")

  def btn_reset_permissions_click(self, **event_args):
    """Calls server to reset system role permissions to their defaults."""
    module_name = self.module_name # Assuming self.module_name is defined in __init__
    function_name = "btn_reset_permissions_click"
    log("INFO", module_name, function_name, "Reset Permissions button clicked.")
  
    confirmed = confirm(
      "WARNING: This will reset all permissions for the standard system roles (Owner, Admin, Tech, User, Visitor) "
      "back to their original MyBizz defaults. Any custom permission assignments you've made "
      "to these system roles will be lost. Custom roles you created will NOT be affected. Are you sure you want to proceed?",
      title="Confirm Reset System Role Permissions",
      buttons=[("Yes, Reset System Roles", True), ("Cancel", False)]
    )
    if not confirmed:
      log("INFO", module_name, function_name, "User cancelled resetting system role permissions.")
      return
    try:
      # MODIFIED: Call the new orchestrator function
      result_message = anvil.server.call('start_system_role_permissions_reset') 
  
      Notification(result_message, style="info", timeout=5).show() # Changed to info, as it's an initiation message
      log("INFO", module_name, function_name, f"Server call 'start_system_role_permissions_reset' completed. Message: {result_message}")
  
      # Note: Since the actual reset happens in the background,
      # an immediate refresh here might not show the final state.
      # The user should be informed that it's a background process.
      # For now, we can still refresh the UI, but it might not be fully up-to-date instantly.
      self._load_roles_into_ui()
      self._load_all_permissions_cache()
      if self.dd_select_role_for_permissions.selected_value:
        self._populate_permissions_rp_for_selected_role()
      else:
        self.rp_permissions_for_role.items = []
    except anvil.server.PermissionDenied as e:
      log("WARNING", module_name, function_name, f"Permission denied by server: {str(e)}")
      alert(f"Permission Denied: {str(e)}")
    except Exception as e:
      log("ERROR", module_name, function_name, f"Error calling 'start_system_role_permissions_reset': {str(e)}")
      alert(f"An error occurred: {str(e)}")

  def handle_edit_role_event(self, role_data_dict, **event_args):
    print(f"DEBUG - manage_rbac_form - handle_edit_role_event - Event 'x-edit-role' received. Data: {role_data_dict}") 

    if role_data_dict:
      self.selected_role_for_edit_anvil_id = role_data_dict.get('role_id_anvil')
      self.tb_role_name.text = role_data_dict.get('name', '')
      # print(f"DEBUG - handle_edit_role_event - Set tb_role_name.text to: {self.tb_role_name.text}") # Keep for debugging if needed
      if hasattr(self, 'ta_role_description'):
        self.ta_role_description.text = role_data_dict.get('description', '')
        # print(f"DEBUG - handle_edit_role_event - Set ta_role_description.text to: {self.ta_role_description.text}")

      is_system = role_data_dict.get('is_system_role', False)
      self.chk_is_system_role.checked = is_system
      self.chk_is_system_role.enabled = False 

      self.lbl_add_edit_role_title.text = f"Edit Role: {role_data_dict.get('name', '')}"
      self.btn_save_role.text = "Update Role"

      if is_system:
        self.tb_role_name.visible = False
        if hasattr(self, 'ta_role_description'): 
          self.ta_role_description.visible = False
        self.btn_save_role.visible = False 
        self.btn_delete_role.visible = False 
        # print("DEBUG - handle_edit_role_event - System role: hid/disabled relevant fields.")
      else: # Custom Role
        self.tb_role_name.visible = True
        self.tb_role_name.enabled = True
        if hasattr(self, 'ta_role_description'): 
          self.ta_role_description.visible = True
          self.ta_role_description.enabled = True
        self.btn_save_role.visible = True
        self.btn_save_role.enabled = True
        self.btn_delete_role.visible = True 
        self.btn_delete_role.enabled = True
        # print("DEBUG - handle_edit_role_event - Custom role: UI updated for editing.")

      # --- ADD NOTIFICATION FOR USER ---
      Notification("Role details loaded below. System role names/descriptions cannot be changed.", 
                   title="Role Loaded for Edit", 
                   style="info", 
                   timeout=3).show()
      # --- END NOTIFICATION ---

    else:
      print("WARNING - manage_rbac_form - handle_edit_role_event - No role_data_dict received.")
      self._clear_role_form_fields()
      
  def handle_delete_role_event(self, role_data_dict, **event_args):
    print(f"DEBUG - manage_rbac_form - handle_delete_role_event - Event 'x-delete-role' received. Data: {role_data_dict}")
    # Original log call for reference, can be removed if print is sufficient for debugging
    # log("INFO", self.module_name, "handle_delete_role_event", "Delete role event received from item template.", {"role_data": role_data_dict})
  
    role_anvil_id = role_data_dict.get('role_id_anvil')
    role_name = role_data_dict.get('name')
    is_system = role_data_dict.get('is_system_role', False)
  
    if is_system:
      alert(f"System role '{role_name}' cannot be deleted.", title="Deletion Not Allowed")
      # log("WARNING", self.module_name, "handle_delete_role_event", f"Attempt to delete system role '{role_name}' denied.", {"role_anvil_id": role_anvil_id})
      print(f"WARNING - manage_rbac_form - Attempt to delete system role '{role_name}' denied.")
      return
  
    if role_anvil_id and confirm(f"Are you sure you want to delete the custom role '{role_name}'? This action cannot be undone and will remove it from any users assigned this role.", title="Confirm Delete Role", buttons=[("DELETE ROLE", True), ("Cancel", False)]): # Ensure confirm returns True/False
      # log("INFO", self.module_name, "handle_delete_role_event", f"User confirmed deletion of role '{role_name}'.", {"role_anvil_id": role_anvil_id})
      print(f"INFO - manage_rbac_form - User confirmed deletion of role '{role_name}'.")
      try:
        anvil.server.call('delete_custom_role', role_anvil_id)
        Notification(f"Role '{role_name}' deleted successfully.", style="success").show()
        # log("INFO", self.module_name, "handle_delete_role_event", f"Role '{role_name}' deleted by server.", {"role_anvil_id": role_anvil_id})
        print(f"INFO - manage_rbac_form - Role '{role_name}' deleted by server.")
        self._load_roles_into_ui() 
        if self.selected_role_for_edit_anvil_id == role_anvil_id:
          self._clear_role_form_fields()
      except anvil.server.PermissionDenied as e:
        alert(f"Permission Denied: {str(e)}", title="Error")
        # log("WARNING", self.module_name, "handle_delete_role_event", f"Permission denied deleting role '{role_name}'.", {"role_anvil_id": role_anvil_id, "error": str(e)})
        print(f"WARNING - manage_rbac_form - Permission denied deleting role '{role_name}'. Error: {str(e)}")
      except ValueError as ve: 
        alert(str(ve), title="Deletion Prevented")
        # log("WARNING", self.module_name, "handle_delete_role_event", f"Server prevented deletion of role '{role_name}'.", {"role_anvil_id": role_anvil_id, "error": str(ve)})
        print(f"WARNING - manage_rbac_form - Server prevented deletion of role '{role_name}'. Error: {str(ve)}")
      except Exception as e:
        alert(f"Error deleting role '{role_name}': {str(e)}", title="Error")
        # log("ERROR", self.module_name, "handle_delete_role_event", f"Error deleting role '{role_name}'.", {"role_anvil_id": role_anvil_id, "error": str(e)})
        print(f"ERROR - manage_rbac_form - Error deleting role '{role_name}'. Error: {str(e)}")
    else: 
      if role_anvil_id: # Only log cancellation if a role was actually up for deletion
        # log("INFO", self.module_name, "handle_delete_role_event", f"User cancelled deletion of role '{role_name}'.", {"role_anvil_id": role_anvil_id})
        print(f"INFO - manage_rbac_form - User cancelled deletion of role '{role_name}'.")

      
  def btn_exit_click(self, **event_args):
      """This method is called when the btn_exit is clicked."""
      log("INFO", self.module_name, "btn_exit_click", "Exit button clicked, navigating to paddle_home.")
      open_form('paddle_home')