from ._anvil_designer import report_failed_transactions_itemTemplate
from anvil import *
import anvil.server

class report_failed_transactions_item(report_failed_transactions_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Populate labels from the item dictionary (failed transaction row)
    if self.item:
      self.lbl_txn_id.text = self.item.get('paddle_id', 'N/A')

      failed_at_dt = self.item.get('failed_at') # This now comes from failed_transactions table
      self.lbl_failed_at.text = failed_at_dt.strftime('%Y-%m-%d %H:%M:%S') if failed_at_dt else 'N/A'

      # Status can be from failed_transactions table (e.g., "Logged") 
      # or the main transaction table's status (e.g., "failed")
      # The server function now provides 'status' from failed_transactions.
      self.lbl_status.text = self.item.get('status', 'N/A') 
      self.lbl_customer_email.text = self.item.get('customer_email', 'N/A')

      total_minor_units = self.item.get('total') # Attempted amount in minor units
      currency = self.item.get('currency_code', '')

      if total_minor_units is not None and currency:
        try:
          major_units = int(total_minor_units) / 100.0
          self.lbl_total.text = f"{major_units:,.2f}" # Currency code is now in lbl_currency
        except (ValueError, TypeError):
          self.lbl_total.text = str(total_minor_units) # Fallback
      elif total_minor_units is not None:
        self.lbl_total.text = str(total_minor_units) + " (No Currency)"
      else:
        self.lbl_total.text = 'N/A'

      self.lbl_currency.text = currency

      # Populate new failure reason labels
      self.lbl_failure_reason_paddle.text = self.item.get('failure_reason_paddle', 'Reason not available')
      # If you added lbl_failure_reason_mybizz:
      # self.lbl_failure_reason_mybizz.text = self.item.get('mybizz_failure_reason', 'N/A')

    else: # Fallback if self.item is None
      self.lbl_txn_id.text = "No Data"
      self.lbl_failed_at.text = ""
      self.lbl_status.text = ""
      self.lbl_customer_email.text = ""
      self.lbl_total.text = ""
      self.lbl_currency.text = ""
      self.lbl_failure_reason_paddle.text = ""
      # if hasattr(self, 'lbl_failure_reason_mybizz'):
      #     self.lbl_failure_reason_mybizz.text = ""