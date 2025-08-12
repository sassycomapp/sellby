# Client Module: manage_price_form.py

from ._anvil_designer import manage_price_formTemplate
from anvil import *
import anvil.server
# Import the item templates and editor form
from ..price_override_item_form import price_override_item_form
from ..manage_override_form import manage_override_form # For adding/editing overrides
import json # For handling custom_data display

# Placeholder for currencies, tax modes, etc.
# In a real app, fetch from server or shared module for maintainability
COMMON_CURRENCIES = sorted(["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "ZAR"]) # Base currencies
PADDLE_TAX_MODES = ["account_setting", "internal", "external"]
PADDLE_PRICE_STATUSES = ["active", "archived"]
BILLING_INTERVALS = ["day", "week", "month", "year"]

class manage_price_form(manage_price_formTemplate):
  def __init__(self, item_row, price_to_edit=None, price_type_context='one_time', **properties):
    # item_row: The parent Item (product, service, subscription_plan) this Price belongs to.
    # price_to_edit: The Price row object if editing, else None for new.
    # price_type_context: 'one_time' or 'recurring', passed from parent to set UI.
    self.init_components(**properties)

    self.parent_item_row = item_row
    self.price_item = price_to_edit # This will be an Anvil Row object if editing
    self.price_type = price_type_context # 'one_time' or 'recurring'

    # --- Configure RepeatingPanel for Overrides ---
    self.rp_price_overrides.item_template = price_override_item_form
    # Add event handlers for events raised by price_override_item_form
    self.rp_price_overrides.set_event_handler('x_edit_override', self.edit_override_handler)
    self.rp_price_overrides.set_event_handler('x_refresh_overrides', self.load_price_overrides)


    # --- Populate Dropdowns ---
    self.dd_price_status.items = PADDLE_PRICE_STATUSES
    self.dd_base_price_currency.items = [""] + COMMON_CURRENCIES # Add blank for placeholder
    self.dd_tax_mode.items = PADDLE_TAX_MODES
    self.dd_billing_cycle_interval.items = [""] + BILLING_INTERVALS
    self.dd_trial_period_interval.items = [""] + BILLING_INTERVALS


    # --- Initialize Form Mode (Create or Edit) & UI Visibility ---
    if self.price_item: # Editing an existing price
      self.lbl_price_form_title.text = "Edit Price Details"
      self.populate_form_for_edit()
      self.load_price_overrides() # Load existing overrides
    else: # Creating a new price
      self.lbl_price_form_title.text = "Create New Price"
      self.tb_price_paddle_id.text = "(Will be assigned after sync)"
      self.dd_price_status.selected_value = "active" # Default for new
      self.dd_base_price_currency.selected_value = "" # Force selection
      self.rp_price_overrides.items = [] # No overrides for a new price yet
      # Default quantity values
      self.tb_quantity_min.text = "1"
      self.tb_quantity_max.text = "1"


      self.update_conditional_visibility()


    def update_conditional_visibility(self):
      """Shows/hides fields based on price_type and quantity checkbox."""
      is_recurring = (self.price_type == 'recurring')
      self.lbl_recurring_title.visible = is_recurring
      self.dd_billing_cycle_interval.visible = is_recurring
      self.tb_billing_cycle_frequency.visible = is_recurring
      self.lbl_trial_title.visible = is_recurring
      self.dd_trial_period_interval.visible = is_recurring
      self.tb_trial_period_frequency.visible = is_recurring

      quantity_enabled = self.chk_quantity_enabled.checked
      self.tb_quantity_min.visible = quantity_enabled
      self.tb_quantity_max.visible = quantity_enabled


  def populate_form_for_edit(self):
    """Populates form fields if editing an existing Price."""
    if self.price_item:
      self.tb_price_description.text = self.price_item.get('description', "")
      self.tb_price_paddle_id.text = self.price_item.get('paddle_price_id', "(Not synced yet)")
      self.dd_price_status.selected_value = self.price_item.get('status', 'active')
      self.tb_base_price_amount.text = self.price_item.get('unit_price_amount', "")
      self.dd_base_price_currency.selected_value = self.price_item.get('unit_price_currency_code', "")
      self.dd_tax_mode.selected_value = self.price_item.get('tax_mode')

      # Quantity
      min_qty = self.price_item.get('quantity_minimum', 1) # Default to 1 if None
      max_qty = self.price_item.get('quantity_maximum', 1) # Default to 1 if None
      self.chk_quantity_enabled.checked = not (min_qty == 1 and max_qty == 1)
      self.tb_quantity_min.text = str(min_qty)
      self.tb_quantity_max.text = str(max_qty)

      # Recurring fields (only if price_type is recurring)
      if self.price_type == 'recurring':
        self.dd_billing_cycle_interval.selected_value = self.price_item.get('billing_cycle_interval', "")
        self.tb_billing_cycle_frequency.text = str(self.price_item.get('billing_cycle_frequency', "")) \
        if self.price_item.get('billing_cycle_frequency') is not None else ""
        self.dd_trial_period_interval.selected_value = self.price_item.get('trial_period_interval', "")
        self.tb_trial_period_frequency.text = str(self.price_item.get('trial_period_frequency', "")) \
        if self.price_item.get('trial_period_frequency') is not None else ""

        custom_data_val = self.price_item.get('custom_data')
      if isinstance(custom_data_val, dict):
        try:
          self.ta_custom_data.text = json.dumps(custom_data_val, indent=2)
        except TypeError:
          self.ta_custom_data.text = str(custom_data_val) # Fallback
      elif custom_data_val is not None:
        self.ta_custom_data.text = str(custom_data_val)
      else:
        self.ta_custom_data.text = ""


    def load_price_overrides(self, **event_args):
      """Loads/refreshes the list of overrides for the current price_item."""
      if self.price_item and self.price_item.get('price_id'):
        try:
          # Pass the string ID of the price_item
          overrides_list = anvil.server.call('list_overrides_for_price', self.price_item['price_id'])
          self.rp_price_overrides.items = overrides_list
        except Exception as e:
          alert(f"Error loading currency overrides: {e}")
          self.rp_price_overrides.items = []
      else:
        self.rp_price_overrides.items = [] # No price item or ID, so no overrides


  def chk_quantity_enabled_change(self, **event_args):
    """This method is called when the chk_quantity_enabled checkbox is changed."""
    self.update_conditional_visibility()


    def btn_add_override_click(self, **event_args):
      """This method is called when the Add Currency Override button is clicked."""
      if not self.price_item or not self.price_item.get('price_id'): # Check for price_id
        alert("Please save the main Price details first before adding overrides. The Price needs an ID.")
        return

        # Open the manage_override_form as an alert, passing the parent price_row
        result = alert(
          content=manage_override_form(price_row=self.price_item), # Pass the Anvil Row of the current Price
          title="Add New Currency Override",
          large=True,
          buttons=[] # Buttons are on manage_override_form itself
        )
      if result is True: # manage_override_form raises x-close-alert with value=True on save
        self.load_price_overrides() # Refresh the list


  def edit_override_handler(self, override_item, **event_args):
    """Handles the x_edit_override event from price_override_item_form."""
    # Open manage_override_form in edit mode
    result = alert(
      content=manage_override_form(price_row=self.price_item, override_to_edit=override_item),
      title="Edit Currency Override",
      large=True,
      buttons=[]
    )
    if result is True:
      self.load_price_overrides()


    def btn_save_price_click(self, **event_args):
      """This method is called when the Save Price button is clicked."""
      # --- Basic Client-Side Validation ---
      if not self.tb_price_description.text.strip():
        alert("Price Description is required.")
        return
        if not self.dd_base_price_currency.selected_value:
          alert("Base Price Currency is required.")
          return
      base_amount_str = self.tb_base_price_amount.text.strip()
      if not base_amount_str or not base_amount_str.isdigit():
        alert("Base Price Amount is required and must be a whole number (minor units).")
        return
        if not self.dd_tax_mode.selected_value:
          alert("Tax Mode is required.")
          return

      price_data = {
        'description': self.tb_price_description.text.strip(),
        'status': self.dd_price_status.selected_value or 'active',
        'unit_price_amount': base_amount_str,
        'unit_price_currency_code': self.dd_base_price_currency.selected_value,
        'tax_mode': self.dd_tax_mode.selected_value,
      }

      # Custom Data
      custom_data_str = self.ta_custom_data.text.strip()
      if custom_data_str:
        try:
          price_data['custom_data'] = json.loads(custom_data_str)
        except json.JSONDecodeError:
          alert("Custom Data is not valid JSON. Please correct it or leave it blank.")
          return
      else:
        price_data['custom_data'] = None


        # Add quantity fields if enabled
        if self.chk_quantity_enabled.checked:
          try:
            min_qty_str = self.tb_quantity_min.text.strip()
            max_qty_str = self.tb_quantity_max.text.strip()
            price_data['quantity_minimum'] = int(min_qty_str) if min_qty_str else 1
            price_data['quantity_maximum'] = int(max_qty_str) if max_qty_str else 1

            if price_data['quantity_minimum'] < 1 or price_data['quantity_maximum'] < 1:
              raise ValueError("Quantities must be 1 or greater.")
              if price_data['quantity_minimum'] > price_data['quantity_maximum']:
                raise ValueError("Minimum quantity cannot exceed maximum quantity.")
          except ValueError as e:
            alert(f"Invalid quantity: {e}")
            return
        else: # Default quantities if not enabled
          price_data['quantity_minimum'] = 1
          price_data['quantity_maximum'] = 1


      # Add recurring fields if applicable
      if self.price_type == 'recurring':
        billing_interval = self.dd_billing_cycle_interval.selected_value
        billing_freq_str = self.tb_billing_cycle_frequency.text.strip()
        if not billing_interval or not billing_freq_str:
          alert("Billing Cycle Interval and Frequency are required for recurring prices.")
          return
          try:
            price_data['billing_cycle_interval'] = billing_interval
            price_data['billing_cycle_frequency'] = int(billing_freq_str)
            if price_data['billing_cycle_frequency'] < 1:
              raise ValueError("Billing frequency must be 1 or greater.")
          except ValueError:
            alert("Invalid billing cycle frequency. Must be a whole number.")
            return

            trial_interval = self.dd_trial_period_interval.selected_value
        trial_freq_str = self.tb_trial_period_frequency.text.strip()
        if trial_interval and trial_freq_str:
          try:
            price_data['trial_period_interval'] = trial_interval
            price_data['trial_period_frequency'] = int(trial_freq_str)
            if price_data['trial_period_frequency'] < 1:
              raise ValueError("Trial frequency must be 1 or greater.")
          except ValueError:
            alert("Invalid trial period frequency. Must be a whole number.")
            return
        elif trial_interval or trial_freq_str: # Only one is filled
          alert("Both Trial Period Interval and Frequency must be provided if setting a trial, or leave both blank.")
          return


        try:
          if self.price_item: # Editing existing Price
            price_id_to_update = self.price_item.get('price_id')
            if not price_id_to_update:
              alert("Error: Cannot update price, local Price ID is missing.")
              return
              # item_id and price_type are not sent for update as they are immutable by design here
              updated_price_row = anvil.server.call('update_price', price_id_to_update, price_data)
            self.price_item = updated_price_row # Refresh local item with updated data
            Notification("Price updated successfully.", style="success").show()
          else: # Creating new Price
            price_data['item_id'] = self.parent_item_row # Link to parent item (Anvil Row)
            price_data['price_type'] = self.price_type   # Set the type
            new_price_row = anvil.server.call('create_price', price_data)
            self.price_item = new_price_row # Update self.price_item with the new Anvil Row
            self.tb_price_paddle_id.text = new_price_row.get('paddle_price_id', "(Not synced yet)")
            self.lbl_price_form_title.text = "Edit Price Details" # Switch to edit mode
            Notification("Price created successfully. You can now add currency overrides.", style="success").show()

            # Close the alert/dialog and signal success (parent form will refresh)
            self.raise_event("x-close-alert", value=True)

        except anvil.server.ValidationError as e:
          alert(f"Validation Error: {e.err_obj if e.err_obj else str(e)}")
        except Exception as e:
          alert(f"An error occurred saving the price: {e}")


  def btn_cancel_price_click(self, **event_args):
    """This method is called when the Cancel button is clicked."""
    self.raise_event("x-close-alert", value=False)