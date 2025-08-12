from ._anvil_designer import report_customer_profile_subs_itemTemplate
from anvil import *
# No server calls typically needed directly from a simple item template
# from datetime import datetime # Not strictly needed if all formatting is from server-provided dates

class report_customer_profile_subs_item(report_customer_profile_subs_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    # self.item is the dictionary for a single subscription from the server.
    if self.item:
      self.lbl_sub_plan_product_name.text = self.item.get('plan_product_name', 'N/A')

      sub_status = self.item.get('status', 'N/A')
      self.lbl_sub_status_value.text = sub_status

      # Determine and display the relevant date based on status
      relevant_date_label_text = "Next Billing:" # Default for active/trialing
      relevant_date_value = self.item.get('next_billed_at')

      if sub_status and isinstance(sub_status, str): # Ensure status is a string
        sub_status_lower = sub_status.lower()
        if 'paused' in sub_status_lower:
          relevant_date_label_text = "Paused On:"
          relevant_date_value = self.item.get('paused_at')
        elif 'canceled' in sub_status_lower or 'cancelled' in sub_status_lower : # Handle both spellings
          relevant_date_label_text = "Canceled On:"
          relevant_date_value = self.item.get('canceled_at')
          # 'active' or 'trialing' will use the default next_billed_at

      self.lbl_sub_relevant_date_label.text = relevant_date_label_text
      self.lbl_sub_relevant_date_value.text = relevant_date_value.strftime('%Y-%m-%d') if relevant_date_value else 'N/A'

      started_at_date = self.item.get('started_at')
      self.lbl_sub_started_date_value.text = started_at_date.strftime('%Y-%m-%d') if started_at_date else 'N/A'