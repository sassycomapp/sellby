# Client Item Template: report_transaction_single_item.py

from ._anvil_designer import report_transaction_single_itemTemplate
from anvil import *
# import anvil.server # Not typically needed for item templates if they don't make direct server calls
# from ...cm_logs_helper import log # Adjust path if logging needed

class report_transaction_single_item(report_transaction_single_itemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    # self.module_name = "report_transaction_single_item"

    # self.item is expected to be a dictionary representing one transaction line item.
    # Example keys from server (based on transaction_items table and linked data):
    # 'item_name_or_description': "Product X"
    # 'quantity': 2
    # 'unit_price_formatted': "USD 10.00" (already formatted by server)
    # 'line_subtotal_formatted': "USD 20.00"
    # 'line_discount_formatted': "USD 2.00"
    # 'line_tax_formatted': "USD 1.80"
    # 'line_total_formatted': "USD 19.80"
    # 'proration_details_display': "Prorated: 15/30 days" (optional)

    if self.item:
      self.lbl_item_name_or_description.text = self.item.get('item_name_or_description', 'N/A')
      self.lbl_item_quantity.text = str(self.item.get('quantity', 'N/A')) # Ensure it's a string

      # These amounts are assumed to be pre-formatted strings (including currency) from the server
      self.lbl_item_unit_price.text = self.item.get('unit_price_formatted', 'N/A')
      self.lbl_item_line_subtotal.text = self.item.get('line_subtotal_formatted', 'N/A')
      self.lbl_item_line_discount.text = self.item.get('line_discount_formatted', 'N/A')
      self.lbl_item_line_tax.text = self.item.get('line_tax_formatted', 'N/A')
      self.lbl_item_line_total.text = self.item.get('line_total_formatted', 'N/A')

      proration_display = self.item.get('proration_details_display')
      if proration_display:
        self.lbl_item_proration.text = proration_display
        self.lbl_item_proration.visible = True
      else:
        self.lbl_item_proration.text = ""
        self.lbl_item_proration.visible = False
    else:
      # Fallback if self.item is None
      self.lbl_item_name_or_description.text = "No item data"
      self.lbl_item_quantity.text = ""
      self.lbl_item_unit_price.text = ""
      self.lbl_item_line_subtotal.text = ""
      self.lbl_item_line_discount.text = ""
      self.lbl_item_line_tax.text = ""
      self.lbl_item_line_total.text = ""
      self.lbl_item_proration.text = ""
      self.lbl_item_proration.visible = False