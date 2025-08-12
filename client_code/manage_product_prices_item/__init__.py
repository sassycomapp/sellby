# Client Module: manage_product_prices_item.py
# Item Template for displaying a summary of a Price object for a Product.

from ._anvil_designer import manage_product_prices_itemTemplate
from anvil import *
import anvil.server

class manage_product_prices_item(manage_product_prices_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item will be a row from the 'prices' table (or a dictionary derived from it)
    if self.item:
      # Populate Description
      self.lbl_price_description.text = self.item.get('description', "No Description")

      # Populate Base Price
      amount_str = self.item.get('unit_price_amount', "0")
      currency_code = self.item.get('unit_price_currency_code', "")
      try:
        # Assuming amount_str is in minor units (e.g., "1000" for $10.00)
        major_units = int(amount_str) / 100.0
        self.lbl_base_price.text = f"{currency_code} {major_units:,.2f}"
      except (ValueError, TypeError):
        self.lbl_base_price.text = f"{currency_code} {amount_str} (raw)"

      # Populate Price Type
      price_type_raw = self.item.get('price_type', 'N/A')
      self.lbl_price_type.text = f"Type: {price_type_raw.replace('_', ' ').title()}"

      # Populate Status
      current_status = self.item.get('status', 'N/A').title() # e.g., 'Active', 'Archived'
      self.lbl_price_status.text = f"Status: {current_status}"

      # Populate Paddle Price ID (optional display)
      if hasattr(self, 'lbl_paddle_price_id'):
        paddle_id = self.item.get('paddle_price_id')
        self.lbl_paddle_price_id.text = f"Paddle ID: {paddle_id}" if paddle_id else "Paddle ID: (Not Synced)"
        self.lbl_paddle_price_id.visible = True # Or set based on preference

      # Configure Archive/Unarchive Button
      if hasattr(self, 'btn_archive_unarchive_price'):
        if current_status.lower() == 'archived':
          self.btn_archive_unarchive_price.text = "Unarchive"
          self.btn_archive_unarchive_price.icon = "fa:undo"
          self.btn_archive_unarchive_price.role = "secondary-color" 
        else:
          self.btn_archive_unarchive_price.text = "Archive"
          self.btn_archive_unarchive_price.icon = "fa:archive"
          self.btn_archive_unarchive_price.role = "destructive-color"
        self.btn_archive_unarchive_price.visible = True # Ensure it's visible
        self.btn_edit_price.enabled = (current_status.lower() == 'active') # Only allow edit if active

    else:
      # Handle case where item is None (e.g., empty repeating panel)
      self.lbl_price_description.text = "No Price Data"
      self.lbl_base_price.text = ""
      self.lbl_price_type.text = ""
      self.lbl_price_status.text = ""
      if hasattr(self, 'lbl_paddle_price_id'):
        self.lbl_paddle_price_id.text = ""

      self.btn_edit_price.enabled = False
      if hasattr(self, 'btn_archive_unarchive_price'):
        self.btn_archive_unarchive_price.visible = False

  def btn_edit_price_click(self, **event_args):
    """This method is called when the Edit Price button is clicked."""
    if self.item:
      # Raise an event to be handled by the parent form (manage_product.py)
      # Pass the full price item (self.item) to the parent.
      self.parent.raise_event('x_edit_item_price', price_item_to_edit=self.item)
    else:
      alert("Cannot edit: No price data associated with this row.")

  def btn_archive_unarchive_price_click(self, **event_args):
    """This method is called when the Archive/Unarchive Price button is clicked."""
    if self.item:
      mybizz_price_id = self.item.get('price_id') # MyBizz internal price ID
      price_desc = self.item.get('description', 'this price')
      current_status_is_active = (self.item.get('status', 'active').lower() == 'active')

      action_verb = "archive" if current_status_is_active else "unarchive (reactivate)"
      new_status_for_paddle_and_mybizz = "archived" if current_status_is_active else "active"

      if mybizz_price_id and confirm(f"Are you sure you want to {action_verb} the price '{price_desc}'?"):
        try:
          # Server function 'set_mybizz_price_status' handles MyBizz DB update
          # and attempts to sync the status to Paddle.
          anvil.server.call('set_mybizz_price_status', mybizz_price_id, new_status_for_paddle_and_mybizz)

          Notification(f"Price '{price_desc}' status set to {new_status_for_paddle_and_mybizz}.", style="success").show()

          # Parent form (manage_product.py) should refresh its list of prices
          self.parent.raise_event('x_refresh_item_prices')

        except anvil.server.PermissionDenied as e:
          alert(f"Permission Denied: {e}")
        except Exception as e:
          alert(f"Error updating price status: {e}")
      elif not mybizz_price_id:
        alert("Cannot update status: MyBizz Price ID missing.")
    else:
      alert("Cannot update status: No price data associated with this row.")