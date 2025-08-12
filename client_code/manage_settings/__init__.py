# Client Module: manage_settings.py

from ._anvil_designer import manage_settingsTemplate
from anvil import *
import anvil.server
import anvil.users
from ..cm_logs_helper import log # Import client logger

class manage_settings(manage_settingsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    log("INFO", "manage_settings", "__init__", "Form initializing")

    # --- Enforce Admin Permission Check ---
    user = anvil.users.get_user()
    if not user:
      log("WARNING", "manage_settings", "__init__", "No user logged in, redirecting.")
      open_form('paddle_home')
      return 

    try:
      if not anvil.server.call('is_admin_user'):
        log("WARNING", "manage_settings", "__init__", "Access denied - Admin privileges required", {"user_email": user['email']})
        alert("Admin privileges required to manage settings.")
        open_form('paddle_home')
        return
      else:
        log("INFO", "manage_settings", "__init__", "Admin access verified", {"user_email": user['email']})
    except Exception as e:
      log("ERROR","manage_settings","__init__", f"Permission check failed: {e}", {"user_email": user['email']})
      alert(f"Error checking permissions: {e}")
      open_form('paddle_home')
      return
      # --- End Permission Check ---

      # --- Initialize UI Elements and Load Data ---
      # Card 1: New General Setting
    self.tb_new_setting_name.text = ""
    self.tb_new_setting_value.text = ""
    self.sw_new_value_is_bool.checked = False
    self.sw_new_value_is_true.checked = False
    self.sw_new_value_is_true.enabled = False # Disabled until sw_new_value_is_bool is true

    # Card 2: Update General Setting
    self.populate_settings_dropdown()
    self.lbl_show_current_value.text = ""
    self.tb_update_value.text = ""
    self.sw_update_value_is_bool.checked = False
    self.sw_update_value_is_true.checked = False
    self.sw_update_value_is_true.enabled = False

    # Card 3: Log Level
    if not self.dd_log_level.items or len(self.dd_log_level.items) == 0:
      log("WARNING", "manage_settings", "__init__", "Log level dropdown items not set in Designer. Setting programmatically.")
      self.dd_log_level.items = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    self.refresh_log_level_display()

    # Card 4: System Currency
    self.populate_system_currency_dropdown()
    self.refresh_system_currency_display()

    # --- Set Event Handlers ---
    # Card 1
    self.btn_new_save_setting.set_event_handler('click', self.btn_new_save_setting_click)
    self.sw_new_value_is_bool.set_event_handler('change', self.sw_new_value_is_bool_change)
    # Card 2
    self.dd_setting_list.set_event_handler('change', self.dd_setting_list_change)
    self.btn_update_settings.set_event_handler('click', self.btn_update_settings_click)
    self.sw_update_value_is_bool.set_event_handler('change', self.sw_update_value_is_bool_change)
    # Card 3
    self.btn_set_log_level.set_event_handler('click', self.btn_set_log_level_click)
    self.btn_refresh_log_level.set_event_handler('click', self.btn_refresh_log_level_click)
    # Card 4
    self.btn_set_system_currency.set_event_handler('click', self.btn_set_system_currency_click)
    # General
    self.btn_home.set_event_handler('click', self.btn_home_click)

    log("INFO", "manage_settings", "__init__", "Form initialization complete.")

    # --- Card 1: New General Setting Methods ---
  def sw_new_value_is_bool_change(self, **event_args):
    """Enable/disable the boolean value switch based on the type switch."""
    is_bool_type = self.sw_new_value_is_bool.checked
    self.sw_new_value_is_true.enabled = is_bool_type
    self.tb_new_setting_value.enabled = not is_bool_type
    if is_bool_type:
      self.tb_new_setting_value.text = "" # Clear text value if switching to bool

  def btn_new_save_setting_click(self, **event_args):
    setting_name = self.tb_new_setting_name.text.strip()
    is_boolean = self.sw_new_value_is_bool.checked

    if not setting_name:
      alert("New Setting Name is required.")
      return

    setting_value_to_save = None
    bool_value_to_save = False # Default for server function if not boolean

    if is_boolean:
      setting_value_to_save = None # Not used by server if boolean
      bool_value_to_save = self.sw_new_value_is_true.checked
    else:
      setting_value_to_save = self.tb_new_setting_value.text.strip()
      if not setting_value_to_save: # Check if text value is provided if not boolean
        alert("New Setting Value is required if not a boolean type.")
        return

    log_context = {"setting_name": setting_name, "is_boolean": is_boolean, "value": bool_value_to_save if is_boolean else setting_value_to_save}
    log("INFO", "manage_settings", "btn_new_save_setting_click", "Attempting to save new setting.", log_context)
    try:
      result = anvil.server.call('save_new_setting', setting_name, setting_value_to_save, is_boolean, bool_value_to_save)
      Notification(result, style="success", timeout=3).show()
      log("INFO", "manage_settings", "btn_new_save_setting_click", f"Save new setting result: {result}", log_context)
      # Clear new setting form and refresh dropdown for update section
      self.tb_new_setting_name.text = ""
      self.tb_new_setting_value.text = ""
      self.sw_new_value_is_bool.checked = False 
      self.sw_new_value_is_true.checked = False
      self.sw_new_value_is_true.enabled = False
      self.populate_settings_dropdown() # Refresh the list
    except Exception as e:
      alert(f"Error saving new setting: {e}")
      log("ERROR", "manage_settings", "btn_new_save_setting_click", f"Error: {e}", log_context)

    # --- Card 2: Update General Setting Methods ---
  def populate_settings_dropdown(self):
    """Populates the dd_setting_list with existing app settings."""
    log("DEBUG", "manage_settings", "populate_settings_dropdown", "Populating settings dropdown.")
    try:
      # Server call 'get_settings' returns list of (setting_name, row_id) tuples
      settings_list = anvil.server.call('get_settings')
      self.dd_setting_list.items = [("Select a setting to update...", None)] + sorted(settings_list)
      self.lbl_show_current_value.text = "" # Clear current value display
      self.tb_update_value.text = ""
      self.sw_update_value_is_bool.checked = False
      self.sw_update_value_is_true.checked = False
      self.sw_update_value_is_true.enabled = False
    except Exception as e:
      alert(f"Error loading settings list: {e}")
      log("ERROR", "manage_settings", "populate_settings_dropdown", f"Error: {e}")
      self.dd_setting_list.items = [("Error loading settings...", None)]

  def dd_setting_list_change(self, **event_args):
    """Handles selection change in dd_setting_list to load current setting value."""
    selected_id = self.dd_setting_list.selected_value
    log_context = {"selected_setting_id": selected_id}
    log("DEBUG", "manage_settings", "dd_setting_list_change", "Setting selected.", log_context)

    self.lbl_show_current_value.text = ""
    self.tb_update_value.text = ""
    self.sw_update_value_is_bool.checked = False
    self.sw_update_value_is_true.checked = False
    self.sw_update_value_is_true.enabled = False
    self.tb_update_value.enabled = True


    if selected_id:
      try:
        # Server call 'get_setting_by_id' returns dict: {"setting_name", "value_text", "value_number", "value_bool"}
        setting_details = anvil.server.call('get_setting_by_id', selected_id)
        if setting_details:
          current_display_value = "Not set"
          if setting_details.get('value_bool') is not None:
            current_display_value = str(setting_details['value_bool'])
            self.sw_update_value_is_bool.checked = True
            self.sw_update_value_is_true.enabled = True
            self.sw_update_value_is_true.checked = setting_details['value_bool']
            self.tb_update_value.enabled = False
            self.tb_update_value.text = ""
          elif setting_details.get('value_number') is not None:
            current_display_value = str(setting_details['value_number'])
            self.tb_update_value.text = current_display_value
          elif setting_details.get('value_text') is not None:
            current_display_value = setting_details['value_text']
            self.tb_update_value.text = current_display_value

          self.lbl_show_current_value.text = f"Current Value: {current_display_value}"
          log("DEBUG", "manage_settings", "dd_setting_list_change", f"Loaded details for {setting_details.get('setting_name')}.", {**log_context, "details": setting_details})
        else:
          alert("Could not retrieve details for the selected setting.")
          log("WARNING", "manage_settings", "dd_setting_list_change", "get_setting_by_id returned None.", log_context)
      except Exception as e:
        alert(f"Error fetching setting details: {e}")
        log("ERROR", "manage_settings", "dd_setting_list_change", f"Error: {e}", log_context)

  def sw_update_value_is_bool_change(self, **event_args):
    """Enable/disable the boolean value switch for update section."""
    is_bool_type = self.sw_update_value_is_bool.checked
    self.sw_update_value_is_true.enabled = is_bool_type
    self.tb_update_value.enabled = not is_bool_type
    if is_bool_type:
      self.tb_update_value.text = "" # Clear text value if switching to bool

  def btn_update_settings_click(self, **event_args):
    selected_id = self.dd_setting_list.selected_value
    if not selected_id:
      alert("Please select a setting to update from the dropdown.")
      return

    is_boolean = self.sw_update_value_is_bool.checked
    new_value_to_save = None
    bool_value_to_save = False

    if is_boolean:
      new_value_to_save = None # Not used by server if boolean
      bool_value_to_save = self.sw_update_value_is_true.checked
    else:
      new_value_to_save = self.tb_update_value.text.strip()
      if not new_value_to_save: # Check if text value is provided if not boolean
        alert("New Value is required if not a boolean type.")
        return

    log_context = {"setting_id_to_update": selected_id, "is_boolean": is_boolean, "new_value": bool_value_to_save if is_boolean else new_value_to_save}
    log("INFO", "manage_settings", "btn_update_settings_click", "Attempting to update setting.", log_context)
    try:
      # Server call 'update_setting' takes (row_id, new_value, is_boolean, bool_value)
      result = anvil.server.call('update_setting', selected_id, new_value_to_save, is_boolean, bool_value_to_save)
      Notification(result, style="success", timeout=3).show()
      log("INFO", "manage_settings", "btn_update_settings_click", f"Update setting result: {result}", log_context)
      # Refresh the current value display for the selected setting
      self.dd_setting_list_change() 
    except Exception as e:
      alert(f"Error updating setting: {e}")
      log("ERROR", "manage_settings", "btn_update_settings_click", f"Error: {e}", log_context)

    # --- Card 3: Log Level Methods (Mostly from original file, adapted) ---
  def refresh_log_level_display(self):
    log("DEBUG", "manage_settings", "refresh_log_level_display", "Refreshing log level display label")
    try:
      current_level = anvil.server.call('get_current_log_level')
      log("INFO", "manage_settings", "refresh_log_level_display", f"Current log level from server: {current_level}")
      self.lbl_log_level.text = f"Current Log Level: {current_level}"
      # Keep dropdown selection as is, only update label
    except Exception as e:
      log("ERROR", "manage_settings", "refresh_log_level_display", f"Error getting current log level: {e}")
      self.lbl_log_level.text = "Error loading log level"

  def btn_set_log_level_click(self, **event_args):
    selected_level = self.dd_log_level.selected_value
    log("INFO", "manage_settings", "btn_set_log_level_click", f"Set log level button clicked. Selected: {selected_level}")
    if not selected_level:
      alert("Please select a log level from the dropdown.")
      log("WARNING", "manage_settings", "btn_set_log_level_click", "No log level selected")
      return
    try:
      log("DEBUG", "manage_settings", "btn_set_log_level_click", f"Calling server set_log_level with '{selected_level}'")
      anvil.server.call('set_log_level', selected_level)
      Notification(f"Log level set to {selected_level}", style="success", timeout=2).show()
      log("INFO", "manage_settings", "btn_set_log_level_click", f"Successfully set log level to {selected_level}")
      self.refresh_log_level_display()
    except Exception as e:
      log("ERROR", "manage_settings", "btn_set_log_level_click", f"Error setting log level to {selected_level}: {e}")
      Notification(f"Error setting log level: {e}", style="danger", timeout=4).show()
      self.refresh_log_level_display()

  def btn_refresh_log_level_click(self, **event_args):
    log("INFO", "manage_settings", "btn_refresh_log_level_click", "Refresh log level button clicked")
    self.refresh_log_level_display()

    # --- Card 4: System Currency Methods ---
  def populate_system_currency_dropdown(self):
    """Populates dd_system_currency with available currencies."""
    log("DEBUG", "manage_settings", "populate_system_currency_dropdown", "Populating system currency dropdown.")
    try:
      # Server 'get_currencies' returns list of dicts: [{'currency': 'USD', 'country': 'US Dollar', 'is_system': False}, ...]
      currencies_data = anvil.server.call('get_currencies') 

      # Format for DropDown: list of (display_text, value_object) tuples
      # Value object will be the currency dict itself for easy passing to set_system_currency
      dropdown_items = [("Select System Currency...", None)]
      for curr_dict in sorted(currencies_data, key=lambda x: x.get('currency', '')):
        display_text = f"{curr_dict.get('currency', '')} - {curr_dict.get('country', '')}"
        dropdown_items.append((display_text, curr_dict)) # Store the whole dict as value

      self.dd_system_currency.items = dropdown_items
    except Exception as e:
      alert(f"Error loading currency list: {e}")
      log("ERROR", "manage_settings", "populate_system_currency_dropdown", f"Error: {e}")
      self.dd_system_currency.items = [("Error loading currencies...", None)]

  def refresh_system_currency_display(self):
    """Gets and displays the current system currency."""
    log("DEBUG", "manage_settings", "refresh_system_currency_display", "Refreshing system currency display.")
    try:
      system_currency_data = anvil.server.call('get_system_currency') # Returns dict or None
      if system_currency_data:
        self.lbl_system_currency_code.text = f"Code: {system_currency_data.get('currency', 'N/A')}"
        self.lbl_system_currency_country.text = f"Name: {system_currency_data.get('country', 'N/A')}"
        # Optionally pre-select in dropdown if it matches
        for text, value_dict in self.dd_system_currency.items:
          if value_dict and value_dict.get('currency') == system_currency_data.get('currency'):
            self.dd_system_currency.selected_value = value_dict
            break
      else:
        self.lbl_system_currency_code.text = "Code: Not Set"
        self.lbl_system_currency_country.text = "Name: Not Set"
        self.dd_system_currency.selected_value = None
    except Exception as e:
      alert(f"Error loading system currency: {e}")
      log("ERROR", "manage_settings", "refresh_system_currency_display", f"Error: {e}")
      self.lbl_system_currency_code.text = "Error"
      self.lbl_system_currency_country.text = "Error"

  def btn_set_system_currency_click(self, **event_args):
    selected_currency_obj = self.dd_system_currency.selected_value
    if not selected_currency_obj: # selected_value is the dictionary here
      alert("Please select a system currency from the dropdown.")
      return

    log_context = {"selected_currency_data": selected_currency_obj}
    log("INFO", "manage_settings", "btn_set_system_currency_click", "Attempting to set system currency.", log_context)
    try:
      # Server 'set_system_currency' expects a dict like {'currency': 'USD', 'country': 'US Dollar'}
      success = anvil.server.call('set_system_currency', selected_currency_obj)
      if success:
        Notification("System currency updated successfully.", style="success", timeout=3).show()
        log("INFO", "manage_settings", "btn_set_system_currency_click", "System currency updated.", log_context)
        self.refresh_system_currency_display() # Refresh display
      else:
        alert("Failed to set system currency. The selected currency might not be valid or a server error occurred.")
        log("ERROR", "manage_settings", "btn_set_system_currency_click", "Server returned failure for set_system_currency.", log_context)
    except Exception as e:
      alert(f"Error setting system currency: {e}")
      log("ERROR", "manage_settings", "btn_set_system_currency_click", f"Error: {e}", log_context)

    # --- General Home Button Handler ---
  def btn_home_click(self, **event_args):
    log("INFO", "manage_settings", "btn_home_click", "Home button clicked")
    open_form('paddle_home')