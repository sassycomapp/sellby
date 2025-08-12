# report_transaction_single.py
from ._anvil_designer import report_transaction_singleTemplate
from anvil import *
import anvil.server
# Import the new item template
from .report_transaction_single_item import report_transaction_single_item 

class report_transaction_single(report_transaction_singleTemplate):
  def __init__(self, transaction_id=None, **properties):
    self.init_components(**properties)
    self.transaction_id = transaction_id

    # Configure the new RepeatingPanel for line items
    self.rp_transaction_items.item_template = report_transaction_single_item
    self.rp_transaction_items.items = [] # Initialize as empty

    # Hide line items section title initially
    if hasattr(self, 'lbl_line_items_heading'): # Assuming you add a title like "Line Items"
      self.lbl_line_items_heading.visible = False

    self.load_transaction_details()

  def load_transaction_details(self):
    """Fetches and displays the details for the specified transaction, including line items."""
    if not self.transaction_id:
      alert("No Transaction ID provided.")
      self.clear_all_fields() # Use a more comprehensive clear function
      return

    try:
      # Server function now expected to return line_items as well
      txn_data = anvil.server.call('get_single_transaction', self.transaction_id) 

      if not txn_data:
        alert(f"Transaction details not found for ID: {self.transaction_id}")
        self.clear_all_fields()
        return

        # Populate Core Transaction Labels
      self.lbl_transaction_id.text = txn_data.get('paddle_id', 'N/A')
      self.lbl_status.text = txn_data.get('status', 'N/A')

      billed_at = txn_data.get('billed_at')
      self.lbl_billed_at.text = billed_at.strftime('%Y-%m-%d %H:%M:%S') if billed_at else 'N/A'

      # Format main transaction total
      total_val_str = txn_data.get('details_totals_total') # Expecting minor units string
      currency_code = txn_data.get('currency_code', '')
      if total_val_str is not None and currency_code:
        try:
          major_units = int(total_val_str) / 100.0
          self.lbl_total.text = f"{currency_code} {major_units:,.2f}"
        except (ValueError, TypeError):
          self.lbl_total.text = f"{currency_code} {total_val_str} (raw)"
      elif total_val_str is not None:
        self.lbl_total.text = f"{total_val_str} (raw, currency N/A)"
      else:
        self.lbl_total.text = 'N/A'

        # Hide the separate currency label as it's now part of lbl_total
      if hasattr(self, 'lbl_currency'):
        self.lbl_currency.visible = False 

      self.lbl_origin.text = txn_data.get('origin', 'N/A')

      # Populate Customer Details
      customer_details = txn_data.get('customer_details')
      if customer_details:
        self.lbl_customer_email.text = customer_details.get('email', 'N/A')
        self.lbl_customer_name.text = customer_details.get('full_name', 'N/A')
        self.lbl_customer_heading.visible = True
      else:
        self.lbl_customer_email.text = "N/A"
        self.lbl_customer_name.text = "N/A"
        self.lbl_customer_heading.visible = False

        # Populate Subscription Details
      subscription_details = txn_data.get('subscription_details')
      if subscription_details:
        self.lbl_subscription_id.text = subscription_details.get('paddle_id', 'N/A')
        self.lbl_subscription_status.text = subscription_details.get('status', 'N/A')
        self.lbl_subscription_heading.visible = True
      else:
        self.lbl_subscription_id.text = "N/A"
        self.lbl_subscription_status.text = "N/A"
        self.lbl_subscription_heading.visible = False

        # Populate Discount Details
      discount_details = txn_data.get('discount_details')
      if discount_details:
        self.lbl_discount_code.text = discount_details.get('coupon_code', 'N/A')
        self.lbl_discount_description.text = discount_details.get('description', 'N/A')
        self.lbl_discount_heading.visible = True
      else:
        self.lbl_discount_code.text = "N/A"
        self.lbl_discount_description.text = "N/A"
        self.lbl_discount_heading.visible = False

        # --- Populate Line Items ---
      line_items = txn_data.get('line_items', []) # Expecting a list of dicts
      self.rp_transaction_items.items = line_items
      if hasattr(self, 'lbl_line_items_heading'): # Assuming you add a title like "Line Items"
        self.lbl_line_items_heading.visible = bool(line_items)


    except Exception as e:
      alert(f"An error occurred loading transaction details: {e}")
      self.clear_all_fields()

  def clear_all_fields(self):
    """Clears all display labels and the repeating panel."""
    self.lbl_transaction_id.text = ""
    self.lbl_status.text = ""
    self.lbl_billed_at.text = ""
    self.lbl_total.text = ""
    if hasattr(self, 'lbl_currency'): # If it still exists
      self.lbl_currency.visible = False
    self.lbl_origin.text = ""

    self.lbl_customer_email.text = ""
    self.lbl_customer_name.text = ""
    self.lbl_customer_heading.visible = False

    self.lbl_subscription_id.text = ""
    self.lbl_subscription_status.text = ""
    self.lbl_subscription_heading.visible = False

    self.lbl_discount_code.text = ""
    self.lbl_discount_description.text = ""
    self.lbl_discount_heading.visible = False

    self.rp_transaction_items.items = []
    if hasattr(self, 'lbl_line_items_heading'):
      self.lbl_line_items_heading.visible = False


  def btn_close_click(self, **event_args):
    """This method is called when the button is clicked"""
    # This form is typically opened from report_transaction_all.
    # A simple way to "close" it is to navigate back or clear content
    # if it's loaded into a main form's content panel.
    # If opened as an alert, self.raise_event("x-close-alert", value=True) would work.
    # For now, assuming it replaces content on a main form or is part of a navigation flow.
    open_form('report_transaction_all') # Example: Navigate back to the list