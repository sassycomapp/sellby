# Python Client Module: manage_override_form.py
# Form for creating or editing a single price override.

from ._anvil_designer import manage_override_formTemplate
from anvil import *
import anvil.server
# Removed unused imports: anvil.users, anvil.tables, anvil.tables.query, app_tables

# Assuming this form is opened as an alert from manage_price_form.py
# It needs 'price_row' (the parent price) and optionally 'override_to_edit'.

class manage_override_form(manage_override_formTemplate):
  def __init__(self, price_row=None, override_to_edit=None, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # --- Store context passed from parent ---
    self.price_row = price_row # The 'prices' table row this override belongs to
    self.override_to_edit = override_to_edit # The 'price_unit_price_overrides' row if editing, else None

    # --- Populate Currency Dropdown ---
    self.populate_currency_dropdown() # Call new method to populate

    # --- Form Setup ---
    if self.override_to_edit:
      self.lbl_override_form_title.text = "Edit Price Override"
      self.populate_fields_for_edit()
    else:
      self.lbl_override_form_title.text = "Add New Price Override"
      # Set default currency based on parent price if adding new
      if self.price_row and self.price_row.get('unit_price_currency_code'):
        self.dd_override_currency.selected_value = self.price_row.get('unit_price_currency_code')
      else:
        # If no parent price or parent price has no currency, leave dropdown at default/placeholder
        # Or select a system default if one exists and is desired
        pass 

    # --- Populate Country Dropdown/MultiSelect ---
    # Assuming a component named 'ms_override_countries' (MultiSelect Dropdown) exists
    if hasattr(self, 'ms_override_countries'):
      self.populate_country_multiselect()
      if self.override_to_edit:
        # Pre-select countries if editing
        selected_countries = self.override_to_edit.get('country_codes', [])
        if isinstance(selected_countries, list):
          self.ms_override_countries.selected = selected_countries

  def populate_currency_dropdown(self):
    """Populates the currency DropDown from the server."""
    if hasattr(self, 'dd_override_currency'):
      try:
        # Fetch (currency_code, display_name) tuples from server
        # Example: [("USD", "USD - US Dollar"), ("EUR", "EUR - Euro")]
        # The server function 'get_currency_options_for_dropdown' needs to be created.
        currency_options = anvil.server.call('get_currency_options_for_dropdown') 
        self.dd_override_currency.items = [("Select Currency...", None)] + currency_options
      except Exception as e:
        print(f"Error populating currency dropdown: {e}")
        self.dd_override_currency.items = [("Error loading currencies...", None)]

  def populate_country_multiselect(self):
    """Populates the country MultiSelect dropdown."""
    if hasattr(self, 'ms_override_countries'):
      try:
        # Using a placeholder list. Replace with actual country source if available.
        # Example: country_list = anvil.server.call('get_supported_countries_for_overrides')
        # Ensure the list contains 2-letter uppercase codes.
        placeholder_countries = ["US", "CA", "GB", "AU", "DE", "FR", "IE", "JP", "NZ", "ZA"] # Expanded example
        self.ms_override_countries.items = sorted(placeholder_countries)
      except Exception as e:
        print(f"Error populating country multiselect: {e}")
        self.ms_override_countries.items = ["Error loading countries..."]

  def populate_fields_for_edit(self):
    """Populates form fields if editing an existing override."""
    if self.override_to_edit:
      self.dd_override_currency.selected_value = self.override_to_edit.get('currency_code', None)
      self.tb_override_amount.text = self.override_to_edit.get('amount', '') # Assumes amount stored as string (minor units)
      # Country selection is handled in __init__ after populating the multiselect

  def btn_save_override_click(self, **event_args):
    """Handles saving the new or edited override."""
    # --- Validation ---
    selected_countries = []
    if hasattr(self, 'ms_override_countries'):
      selected_countries = self.ms_override_countries.selected
      if not selected_countries:
        alert("Please select at least one country for the override.")
        return
    else:
      alert("Error: Country selection component missing.")
      return

    # --- MODIFIED: Get currency from DropDown ---
    currency_code = self.dd_override_currency.selected_value 
    if not currency_code: # Check if a currency is selected
      alert("Please select a currency for the override.")
      return
    # --- END MODIFICATION ---

    amount_str = self.tb_override_amount.text.strip()
    if not amount_str.isdigit(): # Basic check for digits (minor units)
      alert("Please enter a valid amount in minor units (e.g., 1000 for $10.00). Only digits are allowed.")
      return

    if not self.price_row:
      alert("Error: Cannot save override, parent price context is missing.", title="Save Error")
      return

    # --- Prepare Data for Server ---
    override_data = {
      'price_id': self.price_row, # Pass the parent price row object
      'country_codes': selected_countries, # List of strings
      'currency_code': currency_code, # From DropDown
      'amount': amount_str # String containing digits (minor units)
    }

    # --- Call Server ---
    try:
      if self.override_to_edit:
        override_id_to_update = self.override_to_edit.get('id')
        if not override_id_to_update:
          alert("Error: Cannot update override, ID is missing.", title="Save Error")
          return
        anvil.server.call('update_price_override', override_id_to_update, override_data)
        Notification("Price override updated successfully.", style="success").show()
      else:
        anvil.server.call('create_price_override', override_data)
        Notification("Price override added successfully.", style="success").show()

      self.raise_event("x-close-alert", value=True)

    except anvil.server.ValidationError as e:
      alert(f"Validation Error: {e.err_obj if hasattr(e, 'err_obj') and e.err_obj else str(e)}", title="Save Failed")
    except Exception as e:
      alert(f"An error occurred while saving the override: {e}", title="Save Error")
      print(f"Error saving override: {e}")

  def btn_cancel_override_click(self, **event_args):
    """This method is called when the Cancel button is clicked."""
    self.raise_event("x-close-alert", value=False)