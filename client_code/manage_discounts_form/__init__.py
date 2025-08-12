# Client Module: manage_discounts_form.py
import json
from ._anvil_designer import manage_discounts_formTemplate
from anvil import *
import anvil.server
import anvil.users # For permission checks if needed client-side, though server enforces
from ..cm_logs_helper import log # Assuming this path is correct

# Import the item template for the listing panel
from ..report_discount_list_item import report_discount_list_item # As per blueprint

class manage_discounts_form(manage_discounts_formTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "manage_discounts_form"
    log("INFO", self.module_name, "__init__", "Form initializing.")

    self.current_discount_anvil_id = None # Stores Anvil ID of discount being viewed/archived
    self.current_discount_data = None # Stores full data of loaded discount

    # --- Configure RepeatingPanel for Listing Discounts ---
    if hasattr(self, 'rp_discounts_list'):
      self.rp_discounts_list.item_template = report_discount_list_item
      # Event handler if items in rp_discounts_list are made clickable to load details:
      # self.rp_discounts_list.set_event_handler('x_view_discount_details', self._handle_view_discount_from_rp)

      # --- Initialize UI Elements and Load Initial Data ---
    self._set_ui_mode_create_new() # Default to create new mode

    # Populate static dropdowns
    self.dd_discount_type_paddle.items = [
      ("Select Type...", None),
      ("Percentage", "percentage"),
      ("Flat Amount", "flat")
    ]
    # Duration type could be more dynamic if needed, for now, as per blueprint
    # self.dd_duration_type.items = [("Select Duration...", None), ("Forever", "forever"), ("Repeating", "repeating"), ("One Time", "one_time")]


    # Populate dynamic dropdowns
    self._populate_target_item_dropdown()
    self._populate_currency_dropdown() # For flat amount currency
    self._populate_load_discount_dropdown() # For selecting existing discounts
    self._load_and_display_discounts_in_rp() # For the listing panel

    # --- Set Event Handlers ---
    if hasattr(self, 'sw_action_mode'):
      self.sw_action_mode.set_event_handler('change', self.sw_action_mode_change)
    if hasattr(self, 'dd_load_discount'):
      self.dd_load_discount.set_event_handler('change', self.dd_load_discount_change)

    self.dd_discount_type_paddle.set_event_handler('change', self._update_ui_for_discount_type)
    if hasattr(self, 'chk_discount_recurring'):
      self.chk_discount_recurring.set_event_handler('change', self._update_ui_for_recurring)

    self.btn_save_discount.set_event_handler('click', self.btn_save_discount_click)
    self.btn_clear_discount_form.set_event_handler('click', self.btn_clear_discount_form_click)
    if hasattr(self, 'btn_archive_discount'):
      self.btn_archive_discount.set_event_handler('click', self.btn_archive_discount_click)

    if hasattr(self, 'btn_home'):
      self.btn_home.set_event_handler('click', self.btn_home_click)
    if hasattr(self, 'btn_refresh_list'): # Assuming a refresh button for the list
      self.btn_refresh_list.set_event_handler('click', self._load_and_display_discounts_in_rp)


    log("INFO", self.module_name, "__init__", "Form initialization complete.")

    # --- UI Mode and Population Methods ---
  def _set_ui_mode_create_new(self):
    """Sets the UI to 'Create New Discount' mode."""
    log("DEBUG", self.module_name, "_set_ui_mode_create_new", "Setting UI to Create New mode.")
    if hasattr(self, 'sw_action_mode'):
      self.sw_action_mode.checked = True # Assuming True means "Create New"

    self.lbl_edit_mode_title.text = "Create New Discount"
    self.current_discount_anvil_id = None
    self.current_discount_data = None

    if hasattr(self, 'dd_load_discount'):
      self.dd_load_discount.selected_value = None
      self.dd_load_discount.enabled = False

    self._clear_form_fields()
    self._set_fields_readonly(False) # Enable fields for creation
    self._update_ui_for_discount_type() # Update visibility based on default type
    self._update_ui_for_recurring()

    self.btn_save_discount.visible = True
    self.btn_save_discount.enabled = True
    self.btn_save_discount.text = "Save New Discount"
    if hasattr(self, 'btn_archive_discount'):
      self.btn_archive_discount.visible = False
    self.btn_clear_discount_form.enabled = True
    if hasattr(self, 'lbl_paddle_discount_id_display'):
      self.lbl_paddle_discount_id_display.text = "(Not Synced Yet)"


  def _set_ui_mode_view_existing(self):
    """Sets the UI to 'View Existing Discount' mode."""
    log("DEBUG", self.module_name, "_set_ui_mode_view_existing", "Setting UI to View Existing mode.")
    if hasattr(self, 'sw_action_mode'):
      self.sw_action_mode.checked = False # Assuming False means "View Existing"

    if hasattr(self, 'dd_load_discount'):
      self.dd_load_discount.enabled = True

      # If a discount is already selected in dd_load_discount, load it. Otherwise, clear.
    if hasattr(self, 'dd_load_discount') and self.dd_load_discount.selected_value:
      self._load_discount_for_view(self.dd_load_discount.selected_value)
    else:
      self._clear_form_fields() # Clear if no discount selected yet
      self.lbl_edit_mode_title.text = "Select a Discount to View/Archive"
      self._set_fields_readonly(True) # All fields start as readonly
      if hasattr(self, 'btn_archive_discount'):
        self.btn_archive_discount.visible = False # Hide until a discount is loaded

    self.btn_save_discount.visible = False # No saving in view mode
    self.btn_clear_discount_form.enabled = False


  def _clear_form_fields(self):
    """Clears all input fields in the discount creation/editing section."""
    log("DEBUG", self.module_name, "_clear_form_fields", "Clearing discount form input fields.")
    if hasattr(self, 'dd_target_item'): 
      self.dd_target_item.selected_value = None
    if hasattr(self, 'tb_discount_description_mybizz'): 
      self.tb_discount_description_mybizz.text = ""
    if hasattr(self, 'tb_discount_code'): 
      self.tb_discount_code.text = ""
    if hasattr(self, 'dd_discount_status_mybizz'): 
      self.dd_discount_status_mybizz.selected_value = "active" # Default

    self.dd_discount_type_paddle.selected_value = None # Default to placeholder
    if hasattr(self, 'tb_discount_rate_percent'): 
      self.tb_discount_rate_percent.text = ""
    if hasattr(self, 'tb_discount_amount_flat'): 
      self.tb_discount_amount_flat.text = ""
    if hasattr(self, 'dd_discount_currency_flat'): 
      self.dd_discount_currency_flat.selected_value = None

    if hasattr(self, 'chk_discount_recurring'): 
      self.chk_discount_recurring.checked = False
    if hasattr(self, 'tb_max_recurring_intervals'): 
      self.tb_max_recurring_intervals.text = ""
    if hasattr(self, 'tb_usage_limit'): 
      self.tb_usage_limit.text = ""
    if hasattr(self, 'dp_expires_at'): 
      self.dp_expires_at.date = None
    if hasattr(self, 'ta_custom_data_mybizz'): 
      self.ta_custom_data_mybizz.text = ""
    if hasattr(self, 'lbl_paddle_discount_id_display'): 
      self.lbl_paddle_discount_id_display.text = "(Not Synced Yet)"

    self._update_ui_for_discount_type()
    self._update_ui_for_recurring()

  def _set_fields_readonly(self, is_readonly):
    """Sets the enabled/disabled state of form fields."""
    log("DEBUG", self.module_name, "_set_fields_readonly", f"Setting fields readonly: {is_readonly}")

    # Fields that are part of the core definition and become readonly after creation
    core_definition_fields = [
      getattr(self, name, None) for name in 
      ['dd_target_item', 'tb_discount_description_mybizz', 'tb_discount_code', 
       'dd_discount_type_paddle', 'tb_discount_rate_percent', 
       'tb_discount_amount_flat', 'dd_discount_currency_flat',
       'chk_discount_recurring', 'tb_max_recurring_intervals',
       'tb_usage_limit', 'dp_expires_at', 'ta_custom_data_mybizz']
    ]
    for field in core_definition_fields:
      if field:
        field.enabled = not is_readonly

        # Status is special: always editable for archiving, but defaults for new
    if hasattr(self, 'dd_discount_status_mybizz'):
      if is_readonly and self.current_discount_data: # Viewing existing
        self.dd_discount_status_mybizz.enabled = (self.current_discount_data.get('status') == 'active') # Only allow changing from active to archive
      else: # Creating new
        self.dd_discount_status_mybizz.enabled = not is_readonly # Enabled for new, but defaults to active


  def _populate_target_item_dropdown(self):
    """Populates dd_target_item with Products, Services, and priced Subscription Plans."""
    if hasattr(self, 'dd_target_item'):
      try:
        # Server function needs to return list of (display_name, item_id_anvil)
        items = anvil.server.call('list_target_items_for_discount_dropdown')
        self.dd_target_item.items = [("Select Item for Discount...", None)] + items
      except Exception as e:
        log("ERROR", self.module_name, "_populate_target_item_dropdown", f"Error: {e}")
        self.dd_target_item.items = [("Error loading items...", None)]

    def _populate_currency_dropdown(self):
      """Populates dd_discount_currency_flat."""
      if hasattr(self, 'dd_discount_currency_flat'):
        try:
          currencies = anvil.server.call('get_currency_options_for_dropdown') # (display, value)
          self.dd_discount_currency_flat.items = [("Select Currency...", None)] + currencies
        except Exception as e:
          log("ERROR", self.module_name, "_populate_currency_dropdown", f"Error: {e}")
          self.dd_discount_currency_flat.items = [("Error loading currencies...", None)]

    def _populate_load_discount_dropdown(self):
      """Populates dd_load_discount with existing MyBizz discounts."""
      if hasattr(self, 'dd_load_discount'):
        try:
          # Server function returns list of (display_name, discount_anvil_id)
          discounts = anvil.server.call('list_mybizz_discounts_for_dropdown')
          self.dd_load_discount.items = [("Select Discount to View/Archive...", None)] + discounts
        except Exception as e:
          log("ERROR", self.module_name, "_populate_load_discount_dropdown", f"Error: {e}")
          self.dd_load_discount.items = [("Error loading discounts...", None)]

    def _load_and_display_discounts_in_rp(self, **event_args):
      """Loads all discounts and displays them in rp_discounts_list."""
      if hasattr(self, 'rp_discounts_list'):
        try:
          # This server call should return a list of dictionaries suitable for report_discount_list_item
          discount_list_items = anvil.server.call('get_all_discounts_for_report_list') # New server function
          self.rp_discounts_list.items = discount_list_items
          log("INFO", self.module_name, "_load_and_display_discounts_in_rp", f"Loaded {len(discount_list_items)} discounts into RP.")
        except Exception as e:
          log("ERROR", self.module_name, "_load_and_display_discounts_in_rp", f"Error loading discounts for RP: {e}")
          self.rp_discounts_list.items = []


    def _load_discount_for_view(self, discount_anvil_id):
      """Fetches and displays details of an existing discount in read-only mode."""
      if not discount_anvil_id:
        self._clear_form_fields()
        self.lbl_edit_mode_title.text = "Select a Discount to View/Archive"
        if hasattr(self, 'btn_archive_discount'): 
          self.btn_archive_discount.visible = False
        return

      log("DEBUG", self.module_name, "_load_discount_for_view", f"Loading discount ID: {discount_anvil_id}")
      try:
        discount_data = anvil.server.call('get_mybizz_discount_details', discount_anvil_id)
        if discount_data:
          self.current_discount_anvil_id = discount_anvil_id
          self.current_discount_data = discount_data

          self.lbl_edit_mode_title.text = f"Details for: {discount_data.get('coupon_code') or discount_data.get('discount_name', 'N/A')}"

          if hasattr(self, 'dd_target_item'):
            # Find and select the target item. This requires dd_target_item to be populated
            # with item_id as value. The server should return target_item_id.
            self.dd_target_item.selected_value = discount_data.get('target_item_id') 

          if hasattr(self, 'tb_discount_description_mybizz'): 
            self.tb_discount_description_mybizz.text = discount_data.get('discount_name', '')
          if hasattr(self, 'tb_discount_code'): 
            self.tb_discount_code.text = discount_data.get('coupon_code', '')
          if hasattr(self, 'dd_discount_status_mybizz'): 
            self.dd_discount_status_mybizz.selected_value = discount_data.get('status', 'archived')

          self.dd_discount_type_paddle.selected_value = discount_data.get('type')
          if hasattr(self, 'tb_discount_rate_percent'): 
            self.tb_discount_rate_percent.text = discount_data.get('amount_rate', '')
          if hasattr(self, 'tb_discount_amount_flat'): 
            self.tb_discount_amount_flat.text = discount_data.get('amount_amount', '')
          if hasattr(self, 'dd_discount_currency_flat'): 
            self.dd_discount_currency_flat.selected_value = discount_data.get('amount_currency_code')

          if hasattr(self, 'chk_discount_recurring'):
            # Paddle 'recurring' is boolean. MyBizz 'duration_type' might be 'repeating'.
            # For simplicity, if Paddle 'recurring' is true, check the box.
            # This assumes 'recurring' boolean is returned by get_mybizz_discount_details
            is_recurring = discount_data.get('recurring', False) 
            self.chk_discount_recurring.checked = is_recurring
          if hasattr(self, 'tb_max_recurring_intervals'): 
            self.tb_max_recurring_intervals.text = str(discount_data.get('duration_in_months', '')) if discount_data.get('duration_in_months') is not None else ""

          if hasattr(self, 'tb_usage_limit'): 
            self.tb_usage_limit.text = str(discount_data.get('usage_limit', '')) if discount_data.get('usage_limit') is not None else ""
          if hasattr(self, 'dp_expires_at'): 
            self.dp_expires_at.date = discount_data.get('expires_at') # Assumes datetime object
          if hasattr(self, 'ta_custom_data_mybizz'): 
            self.ta_custom_data_mybizz.text = discount_data.get('custom_data_mybizz_json_str', '') # Assuming server sends JSON string

          if hasattr(self, 'lbl_paddle_discount_id_display'): 
            self.lbl_paddle_discount_id_display.text = f"Paddle ID: {discount_data.get('paddle_id', '(Not Synced)')}"

          self._set_fields_readonly(True)
          self._update_ui_for_discount_type()
          self._update_ui_for_recurring()

          if hasattr(self, 'btn_archive_discount'):
            self.btn_archive_discount.visible = True
            self.btn_archive_discount.enabled = (discount_data.get('status') == 'active')
            self.btn_archive_discount.text = "Archive Discount" if discount_data.get('status') == 'active' else "Unarchive Discount" # Or just "Archive"
        else:
          alert(f"Could not load details for discount ID: {discount_anvil_id}")
          self._clear_form_fields()
      except Exception as e:
        alert(f"Error loading discount details: {e}")
        log("ERROR", self.module_name, "_load_discount_for_view", f"Error: {e}")
        self._clear_form_fields()

    def _update_ui_for_discount_type(self, **event_args):
      """Shows/hides amount/rate fields based on selected discount type."""
      discount_type = self.dd_discount_type_paddle.selected_value
      is_percentage = (discount_type == 'percentage')
      is_flat = (discount_type == 'flat')

      if hasattr(self, 'tb_discount_rate_percent'): 
        self.tb_discount_rate_percent.visible = is_percentage
      if hasattr(self, 'tb_discount_amount_flat'): 
        self.tb_discount_amount_flat.visible = is_flat
      if hasattr(self, 'dd_discount_currency_flat'): 
        self.dd_discount_currency_flat.visible = is_flat

        # Clear non-relevant fields
      if is_percentage:
        if hasattr(self, 'tb_discount_amount_flat'): 
          self.tb_discount_amount_flat.text = ""
        if hasattr(self, 'dd_discount_currency_flat'): 
          self.dd_discount_currency_flat.selected_value = None
      elif is_flat:
        if hasattr(self, 'tb_discount_rate_percent'): 
          self.tb_discount_rate_percent.text = ""


    def _update_ui_for_recurring(self, **event_args):
      """Shows/hides max recurring intervals field."""
      if hasattr(self, 'chk_discount_recurring') and hasattr(self, 'tb_max_recurring_intervals'):
        self.tb_max_recurring_intervals.visible = self.chk_discount_recurring.checked
        if not self.chk_discount_recurring.checked:
          self.tb_max_recurring_intervals.text = ""

    # --- Event Handlers ---
    def sw_action_mode_change(self, **event_args):
      """Switches between Create New and View Existing modes."""
      if hasattr(self, 'sw_action_mode') and self.sw_action_mode.checked:
        self._set_ui_mode_create_new()
      else:
        self._set_ui_mode_view_existing()

    def dd_load_discount_change(self, **event_args):
      """Loads selected discount details when in View Existing mode."""
      if hasattr(self, 'sw_action_mode') and not self.sw_action_mode.checked: # If in View mode
        selected_discount_id = self.dd_load_discount.selected_value
        self._load_discount_for_view(selected_discount_id)

    # def _handle_view_discount_from_rp(self, discount_anvil_id_from_item, **event_args):
    #     """Handles event from RP item click to load discount for viewing."""
    #     if hasattr(self, 'sw_action_mode'): self.sw_action_mode.checked = False # Switch to view mode
    #     if hasattr(self, 'dd_load_discount'): self.dd_load_discount.selected_value = discount_anvil_id_from_item
    #     # dd_load_discount_change will then trigger _load_discount_for_view

    def btn_clear_discount_form_click(self, **event_args):
      """Clears the form fields when in Create New mode."""
      if hasattr(self, 'sw_action_mode') and self.sw_action_mode.checked: # Only if in create mode
        self._clear_form_fields()
        self.lbl_edit_mode_title.text = "Create New Discount" # Reset title
        if hasattr(self, 'lbl_paddle_discount_id_display'): 
          self.lbl_paddle_discount_id_display.text = "(Not Synced Yet)"


    def btn_save_discount_click(self, **event_args):
      """Gathers data and calls server to save a new discount."""
      log("INFO", self.module_name, "btn_save_discount_click", "Save New Discount button clicked.")

      discount_data = {}

      # Target Item
      if hasattr(self, 'dd_target_item'):
        discount_data['target_item_anvil_id'] = self.dd_target_item.selected_value
        if not discount_data['target_item_anvil_id']:
          alert("Please select the Product, Service, or Plan this discount applies to.")
          return
      else: # Should not happen if UI is correct
        alert("Target item selector missing.")
        return

        # MyBizz Description/Name
      if hasattr(self, 'tb_discount_description_mybizz'):
        discount_data['discount_name'] = self.tb_discount_description_mybizz.text.strip()
        if not discount_data['discount_name']:
          alert("MyBizz Discount Name/Description is required.")
          return

        # Coupon Code
      if hasattr(self, 'tb_discount_code'):
        discount_data['coupon_code'] = self.tb_discount_code.text.strip()
        # Coupon code can be optional for Paddle if discount applied via API, but MyBizz might require it.
        # For now, let's make it optional on client, server can validate if Paddle needs it based on other settings.

        # MyBizz Status (always 'active' for new, server sets Paddle status)
      discount_data['status_mybizz'] = 'active' 

      # Type and Value
      discount_data['type'] = self.dd_discount_type_paddle.selected_value
      if not discount_data['type']:
        alert("Please select a Discount Type (Percentage or Flat Amount).")
        return

      if discount_data['type'] == 'percentage':
        if hasattr(self, 'tb_discount_rate_percent'):
          rate_str = self.tb_discount_rate_percent.text.strip()
          try:
            float(rate_str) # Validate it's a number
            discount_data['amount_rate'] = rate_str # Send as string "10.5"
          except ValueError:
            alert("Invalid percentage rate. Please enter a number (e.g., 10 or 10.5).")
            return
      elif discount_data['type'] == 'flat':
        if hasattr(self, 'tb_discount_amount_flat'):
          amount_str = self.tb_discount_amount_flat.text.strip()
          if not amount_str.isdigit():
            alert("Flat amount must be a whole number in minor units (e.g., 1000 for $10.00).")
            return
          discount_data['amount_amount'] = amount_str
        if hasattr(self, 'dd_discount_currency_flat'):
          discount_data['amount_currency_code'] = self.dd_discount_currency_flat.selected_value
          if not discount_data['amount_currency_code']:
            alert("Currency is required for a flat amount discount.")
            return

        # Recurring Settings
      if hasattr(self, 'chk_discount_recurring'):
        discount_data['recurring'] = self.chk_discount_recurring.checked
        if discount_data['recurring'] and hasattr(self, 'tb_max_recurring_intervals'):
          intervals_str = self.tb_max_recurring_intervals.text.strip()
          if intervals_str:
            try:
              intervals = int(intervals_str)
              if intervals < 1: 
                raise ValueError()
              discount_data['duration_in_months'] = intervals # Maps to Paddle's max_recurring_intervals
            except ValueError:
              alert("Max Recurring Intervals must be a whole number greater than 0.")
              return
              # If recurring is true but no intervals, Paddle might default or error.
              # MyBizz can decide if it's mandatory if recurring is checked. For now, optional.

        # Usage Limit
      if hasattr(self, 'tb_usage_limit'):
        usage_limit_str = self.tb_usage_limit.text.strip()
        if usage_limit_str:
          try:
            discount_data['usage_limit'] = int(usage_limit_str)
            if discount_data['usage_limit'] < 1: 
              raise ValueError()
          except ValueError:
            alert("Usage Limit must be a whole number greater than 0, or blank for unlimited.")
            return

        # Expires At
      if hasattr(self, 'dp_expires_at') and self.dp_expires_at.date:
        discount_data['expires_at'] = self.dp_expires_at.date 
        # Server will need to format this as ISO 8601 string for Paddle

        # Custom Data (MyBizz internal)
      if hasattr(self, 'ta_custom_data_mybizz'):
        custom_data_str = self.ta_custom_data_mybizz.text.strip()
        if custom_data_str:
          try:
            discount_data['custom_data_mybizz'] = json.loads(custom_data_str)
          except json.JSONDecodeError:
            alert("MyBizz Custom Data is not valid JSON. Please correct or leave blank.")
            return

      log("DEBUG", self.module_name, "btn_save_discount_click", f"Calling server 'save_mybizz_discount' with data: {discount_data}")
      try:
        # Server function 'save_mybizz_discount' will handle DB and Paddle creation.
        # It should return the new MyBizz discount row or relevant details.
        new_discount_details = anvil.server.call('save_mybizz_discount', discount_data)
        Notification("New discount saved and sync initiated with Paddle.", style="success").show()
        log("INFO", self.module_name, "btn_save_discount_click", f"New discount saved: {new_discount_details.get('coupon_code') if new_discount_details else 'N/A'}")

        self._load_and_display_discounts_in_rp() # Refresh the list in RP
        self._populate_load_discount_dropdown() # Refresh the selection dropdown
        self._set_ui_mode_create_new() # Reset form for another new one

      except anvil.server.ValidationError as ve:
        alert(f"Validation Error: {ve.err_obj if hasattr(ve, 'err_obj') and ve.err_obj else str(ve)}")
        log("WARNING", self.module_name, "btn_save_discount_click", f"Server validation error: {ve}")
      except anvil.http.HttpError as he: # Catch Paddle API errors specifically if server re-raises them
        alert(f"Paddle API Error: {he.status} - {he.content}. Discount saved in MyBizz but Paddle sync failed. Check details or try archiving and recreating.")
        log("ERROR", self.module_name, "btn_save_discount_click", f"Paddle API error: {he}")
        self._load_and_display_discounts_in_rp() 
        self._populate_load_discount_dropdown()
      except Exception as e:
        alert(f"An error occurred while saving the discount: {e}")
        log("ERROR", self.module_name, "btn_save_discount_click", f"General error: {e}")


    def btn_archive_discount_click(self, **event_args):
      """Archives the currently loaded discount."""
      if not self.current_discount_anvil_id or not self.current_discount_data:
        alert("No discount selected to archive.")
        return

      discount_code = self.current_discount_data.get('coupon_code', self.current_discount_data.get('discount_name', 'this discount'))
      current_status = self.current_discount_data.get('status', 'unknown')

      if current_status == 'archived':
        # Implement Unarchive if desired, or just inform
        alert(f"Discount '{discount_code}' is already archived.")
        # If unarchiving:
        # action_verb = "unarchive"
        # new_status_for_paddle = "active"
        return 

      action_verb = "archive"
      new_status_for_paddle = "archived"

      if confirm(f"Are you sure you want to {action_verb} the discount '{discount_code}'? This will also attempt to {action_verb} it in Paddle."):
        log("INFO", self.module_name, "btn_archive_discount_click", f"User confirmed {action_verb} for discount ID: {self.current_discount_anvil_id}")
        try:
          # Server function handles MyBizz status update and Paddle sync
          # Let's assume a function like 'set_mybizz_discount_status'
          anvil.server.call('set_mybizz_discount_status', self.current_discount_anvil_id, new_status_for_paddle)
          Notification(f"Discount '{discount_code}' has been {action_verb}d.", style="success").show()

          # Refresh data
          self._load_and_display_discounts_in_rp()
          self._populate_load_discount_dropdown()
          # Reload the current discount to reflect new status or clear form
          if hasattr(self, 'dd_load_discount') and self.dd_load_discount.selected_value == self.current_discount_anvil_id:
            self._load_discount_for_view(self.current_discount_anvil_id) 
          else: # If it was somehow deselected, or to be safe
            self._set_ui_mode_view_existing() # This will try to reload or clear

        except anvil.server.PermissionDenied as pe:
          alert(f"Permission Denied: {pe}")
        except anvil.http.HttpError as he:
          alert(f"Paddle API Error: {he.status} - {he.content}. MyBizz status may have been updated, but Paddle sync failed. Please check Paddle dashboard.")
        except Exception as e:
          alert(f"An error occurred: {e}")
          log("ERROR", self.module_name, "btn_archive_discount_click", f"Error during {action_verb}: {e}")
      else:
        log("INFO", self.module_name, "btn_archive_discount_click", f"User cancelled {action_verb} for discount ID: {self.current_discount_anvil_id}")


    def btn_home_click(self, **event_args):
      """Navigates to the home form."""
      log("INFO", self.module_name, "btn_home_click", "Home button clicked.")
      open_form('paddle_home')