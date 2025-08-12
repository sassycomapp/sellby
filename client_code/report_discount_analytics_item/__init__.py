from ._anvil_designer import report_discount_analytics_itemTemplate
from anvil import *

class report_discount_analytics_item(report_discount_analytics_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    if self.item:
      self.lbl_coupon_code.text = self.item.get('coupon_code', 'N/A')
      self.lbl_description.text = self.item.get('description', 'N/A')
      self.lbl_status.text = self.item.get('status', 'N/A')

      self.lbl_times_used.text = str(self.item.get('times_used', 0))

      revenue_minor_units_val = self.item.get('total_associated_revenue_in_period', '0')
      revenue_major_units = 0.0

      try:
        # Convert string or numeric minor units to numeric major units
        if revenue_minor_units_val is None:
          revenue_minor_units_val = '0' # Default to '0' if None

        revenue_minor_units_int = int(str(revenue_minor_units_val)) # Ensure it's an int
        revenue_major_units = revenue_minor_units_int / 100.0
      except (ValueError, TypeError):
        # Handle cases where conversion might fail, though server should provide valid data
        revenue_major_units = 0.0
        print(f"Warning: Could not convert revenue value '{revenue_minor_units_val}' to number.")

      currency_code = self.item.get('system_currency_code', '')

      self.lbl_associated_revenue.text = f"{currency_code} {revenue_major_units:,.2f}".strip()

      self.lbl_transactions_in_period.text = str(self.item.get('transactions_in_period', 0))