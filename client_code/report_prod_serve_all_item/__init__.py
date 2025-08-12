from ._anvil_designer import report_prod_serv_all_itemTemplate
from anvil import *
import anvil.server # Not strictly needed here, but often kept by default

class report_prod_serv_all_item(report_prod_serv_all_itemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    if self.item:
      # MyBizz Item ID (P-xxxx or V-xxxx)
      self.lbl_item_id.text = self.item.get('item_id', 'N/A')

      self.lbl_item_name.text = self.item.get('name', 'N/A')

      # Description - potentially truncate if too long for a list view
      description = self.item.get('description', '')
      if description and len(description) > 75: # Example truncation length
        self.lbl_item_description.text = description[:72] + "..."
      else:
        self.lbl_item_description.text = description if description else 'N/A'

      self.lbl_item_type.text = str(self.item.get('item_type', 'N/A')).title() # e.g., "Product", "Service"
      self.lbl_item_status.text = str(self.item.get('status', 'N/A')).title() # e.g., "Active", "Archived"
      self.lbl_item_paddle_id.text = self.item.get('paddle_product_id', 'N/A')

      created_at_val = self.item.get('created_at_paddle')
      self.lbl_item_created_date.text = created_at_val.strftime('%Y-%m-%d') if created_at_val else 'N/A'

      # Default Price Display
      price_amount_minor_units = self.item.get('default_price_unit_price_amount') # String, minor units
      price_currency_code = self.item.get('default_price_currency_code')

      if price_amount_minor_units is not None and price_currency_code:
        try:
          major_units = int(str(price_amount_minor_units)) / 100.0
          self.lbl_item_default_price.text = f"{price_currency_code} {major_units:,.2f}"
        except (ValueError, TypeError):
          self.lbl_item_default_price.text = f"{price_currency_code} {price_amount_minor_units} (raw)"
      elif price_currency_code: # Amount might be 0 or missing, but currency code present
        self.lbl_item_default_price.text = f"{price_currency_code} 0.00"
      else:
        self.lbl_item_default_price.text = "N/A"

      # Ensure the manage button is present before trying to set its click event
      if hasattr(self, 'btn_manage_item'):
        self.btn_manage_item.set_event_handler('click', self.btn_manage_item_click)
    else:
      # Clear all labels if self.item is None (e.g. empty repeating panel)
      self.lbl_item_id.text = ""
      self.lbl_item_name.text = ""
      self.lbl_item_description.text = ""
      self.lbl_item_type.text = ""
      self.lbl_item_status.text = ""
      self.lbl_item_paddle_id.text = ""
      self.lbl_item_created_date.text = ""
      self.lbl_item_default_price.text = ""
      if hasattr(self, 'btn_manage_item'):
        self.btn_manage_item.enabled = False


  def btn_manage_item_click(self, **event_args):
    """Handles the click of the 'Manage' button for this item."""
    if self.item:
      item_id_to_manage = self.item.get('item_id')
      item_type_to_manage = self.item.get('item_type')

      if not item_id_to_manage or not item_type_to_manage:
        alert("Item ID or Type is missing, cannot navigate to manage form.")
        return

      if item_type_to_manage.lower() == 'product':
        # Pass item_id as 'item_id' to manage_product form, as it expects it
        open_form('manage_product', item_id=item_id_to_manage) 
      elif item_type_to_manage.lower() == 'service':
        # Pass item_id as 'item_id' to manage_service form
        open_form('manage_service', item_id=item_id_to_manage)
      else:
        alert(f"Unknown item type '{item_type_to_manage}', cannot open manage form.")
    else:
      alert("No item data to manage.")