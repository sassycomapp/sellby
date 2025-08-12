# Client Module: price_list_item_form.py
# Item Template for displaying a summary of a Price object.

from ._anvil_designer import price_list_item_formTemplate
from anvil import *
import anvil.server

class price_list_item_form(price_list_item_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item will be a row from the 'prices' table
    if self.item:
      self.lbl_price_item_desc.text = self.item.get('description', "No Description")

      amount_str = self.item.get('unit_price_amount', "0")
      currency_code = self.item.get('unit_price_currency_code', "")
      self.lbl_price_item_base.text = f"Base: {amount_str} {currency_code}"

      self.lbl_price_item_type.text = f"Type: {self.item.get('price_type', 'N/A').replace('_', ' ').title()}"

      current_status = self.item.get('status', 'N/A').title()
      self.lbl_price_item_status.text = f"Status: {current_status}"

      paddle_id = self.item.get('paddle_price_id')
      if hasattr(self, 'lbl_price_item_paddle_id'):
        self.lbl_price_item_paddle_id.text = f"Paddle ID: {paddle_id}" if paddle_id else "Paddle ID: (Not Synced)"
        self.lbl_price_item_paddle_id.visible = True

        # Configure Archive Button
        if hasattr(self, 'btn_archive_price'): # Ensure button exists in designer
          if current_status.lower() == 'archived':
            self.btn_archive_price.text = "Unarchive"
            self.btn_archive_price.icon = "fa:undo" # Or fa:play, fa:toggle-on
            self.btn_archive_price.role = "secondary-color" # Or default
          else:
            self.btn_archive_price.text = "Archive"
            self.btn_archive_price.icon = "fa:archive"
            self.btn_archive_price.role = "destructive-color" # Or secondary
            self.btn_archive_price.visible = True
    else:
      # Handle case where item is None
      self.lbl_price_item_desc.text = "No Price Data"
      self.lbl_price_item_base.text = ""
      self.lbl_price_item_type.text = ""
      self.lbl_price_item_status.text = ""
      if hasattr(self, 'lbl_price_item_paddle_id'):
        self.lbl_price_item_paddle_id.text = ""
        self.btn_edit_price.enabled = False
      if hasattr(self, 'btn_archive_price'):
        self.btn_archive_price.visible = False


    def btn_edit_price_click(self, **event_args):
      """This method is called when the Edit Price button is clicked."""
      if self.item:
        self.parent.raise_event('x_edit_item_price', price_item_to_edit=self.item)
      else:
        alert("Cannot edit: No price data associated with this row.")

  def btn_archive_price_click(self, **event_args):
    """This method is called when the Archive/Unarchive Price button is clicked."""
    if self.item:
      price_id = self.item.get('price_id')
      price_desc = self.item.get('description', 'this price')
      current_status_is_active = (self.item.get('status', 'active').lower() == 'active')

      action_verb = "archive" if current_status_is_active else "unarchive (reactivate)"
      new_status_for_paddle = "archived" if current_status_is_active else "active"

      if price_id and confirm(f"Are you sure you want to {action_verb} the price '{price_desc}'?"):
        try:
          # Server function 'set_mybizz_price_status' will handle MyBizz DB update
          # and attempt to sync the status to Paddle.
          anvil.server.call('set_mybizz_price_status', price_id, new_status_for_paddle)

          Notification(f"Price '{price_desc}' status set to {new_status_for_paddle}.", style="success").show()

          # Parent form should refresh its list of prices to reflect new status
          self.parent.raise_event('x_refresh_item_prices')
          # No need to self.remove_from_parent() as the item still exists, just status changed.
        except Exception as e:
          alert(f"Error updating price status: {e}")
      elif not price_id:
        alert("Cannot update status: Price ID missing.")
    else:
      alert("Cannot update status: No price data associated with this row.")