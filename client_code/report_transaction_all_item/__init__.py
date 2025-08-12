# report_transaction_all_item.py

from ._anvil_designer import report_transaction_all_itemTemplate
from anvil import *
import anvil.server
# Assuming cm_logs_helper is in the parent directory if logging is needed here
# from ..cm_logs_helper import log 

class report_transaction_all_item(report_transaction_all_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item is a dictionary passed by the RepeatingPanel, 
    # containing data from the get_all_transactions server call.

    if self.item:
      # Populate Transaction ID
      if hasattr(self, 'lbl_txn_id'):
        self.lbl_txn_id.text = self.item.get('paddle_id', 'N/A')

      # Populate Customer Email
      if hasattr(self, 'lbl_customer_email'):
        self.lbl_customer_email.text = self.item.get('customer_email', 'N/A')

      # Populate Billed At (and format datetime)
      if hasattr(self, 'lbl_billed_at'):
        billed_at_dt = self.item.get('billed_at')
        if billed_at_dt:
          try:
            self.lbl_billed_at.text = billed_at_dt.strftime('%Y-%m-%d %H:%M:%S')
          except AttributeError: 
            self.lbl_billed_at.text = str(billed_at_dt) 
        else:
          self.lbl_billed_at.text = 'N/A'

      # Populate Subscription Link (Paddle ID)
      if hasattr(self, 'lbl_sub_link'):
        self.lbl_sub_link.text = self.item.get('subscription_paddle_id', 'None')

      # Populate Status
      if hasattr(self, 'lbl_status'):
        self.lbl_status.text = self.item.get('status', 'N/A')

      # Populate Discount Link (Coupon Code)
      if hasattr(self, 'lbl_discount_link'):
        self.lbl_discount_link.text = self.item.get('discount_code', 'None')

      # Populate Formatted Total and Currency
      if hasattr(self, 'lbl_total'):
        total_val_str = self.item.get('total') # Expecting string from Paddle (minor units)
        currency_code = self.item.get('currency_code', '')

        if total_val_str is not None and currency_code:
          try:
            # Convert minor units string to major units float for formatting
            major_units = int(total_val_str) / 100.0
            self.lbl_total.text = f"{currency_code} {major_units:,.2f}" 
          except (ValueError, TypeError):
            # Fallback if conversion fails, display raw values
            self.lbl_total.text = f"{currency_code} {total_val_str} (raw)"
        elif total_val_str is not None: # Has total but no currency code
          self.lbl_total.text = f"{total_val_str} (raw, currency N/A)"
        else:
          self.lbl_total.text = 'N/A'

      # lbl_currency is no longer explicitly set as it's part of lbl_total
      # If lbl_currency still exists in your UI and you want to hide it:
      if hasattr(self, 'lbl_currency'):
        self.lbl_currency.visible = False 
        # Or you can remove it from the designer if it's truly redundant now.

      # Set up event handler for the button
      if hasattr(self, 'btn_view_details'):
        self.btn_view_details.set_event_handler('click', self.btn_view_details_click)
    else:
      # Handle case where self.item is None
      if hasattr(self, 'lbl_txn_id'): 
        self.lbl_txn_id.text = "No Data"
      if hasattr(self, 'lbl_customer_email'): 
        self.lbl_customer_email.text = ""
      if hasattr(self, 'lbl_billed_at'): 
        self.lbl_billed_at.text = ""
      if hasattr(self, 'lbl_sub_link'): 
        self.lbl_sub_link.text = ""
      if hasattr(self, 'lbl_status'): 
        self.lbl_status.text = ""
      if hasattr(self, 'lbl_discount_link'): 
        self.lbl_discount_link.text = ""
      if hasattr(self, 'lbl_total'): 
        self.lbl_total.text = ""
      if hasattr(self, 'lbl_currency'): 
        self.lbl_currency.visible = False # Hide if no data too
      if hasattr(self, 'btn_view_details'): 
        self.btn_view_details.enabled = False

  def btn_view_details_click(self, **event_args):
    """This method is called when the View Details button is clicked."""
    if self.item and self.item.get('paddle_id'):
      transaction_paddle_id = self.item['paddle_id']
      open_form('report_transaction_single', transaction_id=transaction_paddle_id)
    else:
      alert("Cannot view details: Transaction ID is missing.")