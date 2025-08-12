from ._anvil_designer import report_discount_list_itemTemplate
from anvil import *
import anvil.server # Not strictly needed for this item template

class report_discount_list_item(report_discount_list_itemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    if self.item:
      self.lbl_item_coupon_code.text = self.item.get('coupon_code', 'N/A')
      self.lbl_item_discount_name.text = self.item.get('discount_name', 'N/A')
      self.lbl_item_status.text = str(self.item.get('status', 'N/A')).title()
      self.lbl_item_type.text = str(self.item.get('type', 'N/A')).title()

      # Display Value/Rate
      discount_type = self.item.get('type', '').lower()
      if discount_type == 'percentage':
        rate = self.item.get('amount_rate', '0')
        self.lbl_item_value_rate.text = f"{rate}%"
      elif discount_type == 'flat':
        amount_minor_units = self.item.get('amount_amount', '0')
        currency_code = self.item.get('amount_currency_code', '')
        try:
          major_units = int(str(amount_minor_units)) / 100.0
          self.lbl_item_value_rate.text = f"{currency_code} {major_units:,.2f}".strip()
        except (ValueError, TypeError):
          self.lbl_item_value_rate.text = f"{currency_code} {amount_minor_units} (raw)".strip()
      else:
        self.lbl_item_value_rate.text = 'N/A'

      # Display Target Item Name
      # The server function needs to add 'target_item_name' to self.item
      self.lbl_item_applies_to.text = self.item.get('target_item_name', 'All Items')

      # Display Usage
      times_used = self.item.get('times_used', 0)
      usage_limit = self.item.get('usage_limit')
      if usage_limit is None:
        self.lbl_item_usage.text = f"{times_used or 0} / Unlimited"
      else:
        self.lbl_item_usage.text = f"{times_used or 0} / {usage_limit}"

      # Display Expires At
      expires_at_val = self.item.get('expires_at')
      self.lbl_item_expires_at.text = expires_at_val.strftime('%Y-%m-%d') if expires_at_val else 'Never'

      # Ensure the manage button is present before trying to set its click event
      if hasattr(self, 'btn_manage_discount'):
        self.btn_manage_discount.set_event_handler('click', self.btn_manage_discount_click)
    else:
      # Clear labels if self.item is None
      self.lbl_item_coupon_code.text = ""
      self.lbl_item_discount_name.text = ""
      self.lbl_item_status.text = ""
      self.lbl_item_type.text = ""
      self.lbl_item_value_rate.text = ""
      self.lbl_item_applies_to.text = ""
      self.lbl_item_usage.text = ""
      self.lbl_item_expires_at.text = ""
      if hasattr(self, 'btn_manage_discount'):
        self.btn_manage_discount.enabled = False

  def btn_manage_discount_click(self, **event_args):
    """Handles the click of the 'Manage' button for this discount."""
    if self.item:
      # Assuming 'discount_id' is the MyBizz primary key for the discount table
      # Or use self.item.get_id() if self.item is an Anvil Table Row object and that's preferred
      discount_id_to_manage = self.item.get('discount_id') 

      if not discount_id_to_manage:
        # Fallback if 'discount_id' isn't in the item dict, try Anvil's row ID if self.item is a row
        # This depends on what the server function returns. If it returns dicts, 'discount_id' must be included.
        if isinstance(self.item,anvil.tables.Row):
          discount_id_to_manage = self.item.get_id()

      if discount_id_to_manage:
        # Open the discount management form, passing the identifier.
        # Adjust 'manage_discount_form' to the actual name of your form.
        # Adjust the parameter name if the form expects something other than 'discount_id' or 'anvil_row_id'.
        print(f"Client: Opening manage form for discount ID: {discount_id_to_manage}")
        open_form('manage_discount_form', discount_anvil_id=discount_id_to_manage) # Assuming form expects 'discount_anvil_id'
      else:
        alert("Discount identifier is missing, cannot open management form.")
    else:
      alert("No discount data to manage.")