from ._anvil_designer import report_customer_profile_txns_itemTemplate
from anvil import *
# No server calls typically needed directly from a simple item template
# from datetime import datetime # Not strictly needed if all formatting is from server-provided dates

class report_customer_profile_txns_item(report_customer_profile_txns_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    # self.item is the dictionary for a single transaction from the server.
    if self.item:
      billed_at_date = self.item.get('billed_at')
      # Display date and time for transactions
      self.lbl_txn_billed_at_value.text = billed_at_date.strftime('%Y-%m-%d %H:%M:%S') if billed_at_date else 'N/A'

      self.lbl_txn_status_value.text = self.item.get('status', 'N/A')

      # Handle earnings display (string in minor units from server)
      earnings_minor_units_str = self.item.get('details_totals_earnings', '0')
      earnings_major_units = 0.0

      try:
        if earnings_minor_units_str is None: # Should not happen if default is '0'
          earnings_minor_units_str = '0'

        earnings_minor_units_int = int(str(earnings_minor_units_str)) # Ensure string then int
        earnings_major_units = earnings_minor_units_int / 100.0
      except (ValueError, TypeError):
        # This case should ideally be handled by server sending clean data
        # or logged if conversion fails unexpectedly.
        print(f"Warning: Could not convert transaction earnings '{earnings_minor_units_str}' to number.")
        earnings_major_units = 0.0 # Default to 0.0 if conversion fails

      # Get the system currency code passed from the main form
      # The main form (report_customer_profile.py) should have added 
      # 'system_currency_code_for_display' to each transaction item.
      currency_code = self.item.get('system_currency_code_for_display', '') # Default to empty string

      self.lbl_txn_amount_value.text = f"{currency_code} {earnings_major_units:,.2f}".strip()