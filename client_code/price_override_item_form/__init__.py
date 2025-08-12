# Client Module: price_override_item_form.py
# Item Template for displaying a price override.

from ._anvil_designer import price_override_item_formTemplate
from anvil import *
import anvil.server

class price_override_item_form(price_override_item_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # --- Populate Labels from self.item ---
    # self.item is automatically set by the parent RepeatingPanel.
    # It will be a row object from the 'price_unit_price_overrides' table.
    if self.item:
      # Display country codes (handle list type)
      country_codes = self.item.get('country_codes')
      if isinstance(country_codes, list):
        self.lbl_override_countries.text = ", ".join(country_codes) if country_codes else "N/A"
      else:
        self.lbl_override_countries.text = "Invalid Data"

        # Display amount (convert from minor units string if needed for display)
        amount_str = self.item.get('amount', '0')
      currency_code = self.item.get('currency_code', '')
      try:
        # Basic display - assumes minor units. More complex formatting might be needed.
        # For display, we might want to convert minor units (e.g., 1000) to major (e.g., 10.00)
        # This requires knowing the currency's decimal places - skipping for now.
        # Displaying raw minor units string for simplicity here.
        self.lbl_override_amount.text = f"{amount_str}" # Display raw minor units string
        self.lbl_override_currency.text = currency_code
      except (ValueError, TypeError):
        self.lbl_override_amount.text = "Error"
        self.lbl_override_currency.text = "Error"
    else:
      # Handle case where item is None or empty
      self.lbl_override_countries.text = "No Data"
      self.lbl_override_amount.text = ""
      self.lbl_override_currency.text = ""

    def btn_edit_override_click(self, **event_args):
      """This method is called when the Edit button is clicked."""
      # Raise an event to be handled by the parent form (manage_price_form)
      # Pass the override row object (self.item) or its ID
      if self.item:
        self.parent.raise_event('x_edit_override', override_item=self.item)
      else:
        alert("Cannot edit: No override data associated with this row.")

  def btn_delete_override_click(self, **event_args):
    """This method is called when the Delete button is clicked."""
    if self.item:
      override_id = self.item.get('id') # Get the override's unique ID
      # Simple confirmation
      if override_id and confirm(f"Are you sure you want to delete this override for {self.lbl_override_currency.text} in {self.lbl_override_countries.text}?"):
        try:
          # Call the server function directly from the item template
          anvil.server.call('delete_price_override', override_id)
          # Raise event for parent to refresh its list of overrides
          self.parent.raise_event('x_refresh_overrides')
          Notification("Override deleted.", style="success").show()
          # Remove self from parent after successful deletion
          self.remove_from_parent()
        except Exception as e:
          alert(f"Error deleting override: {e}")
      elif not override_id:
        alert("Cannot delete: Override ID missing.")
    else:
      alert("Cannot delete: No override data associated with this row.")