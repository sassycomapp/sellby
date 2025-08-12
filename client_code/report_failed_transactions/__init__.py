# In report_failed_transactions.py

from ._anvil_designer import report_failed_transactionsTemplate
from anvil import *
import anvil.server
from datetime import date, timedelta # Import for default dates

# Import the Item Template
from ..report_failed_transactions_item import report_failed_transactions_item

class report_failed_transactions(report_failed_transactionsTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    self.rp_failed_transactions.item_template = report_failed_transactions_item

    # --- Initialize Filters (Optional Enhancement) ---
    if hasattr(self, 'dp_end_date') and hasattr(self, 'dp_start_date'):
      self.dp_end_date.date = date.today()
      self.dp_start_date.date = date.today() - timedelta(days=30) # Default to last 30 days

      # Rename btn_refresh to btn_apply_filters if you changed it in UI
      # Or keep btn_refresh and have it call load_failed_transactions
    if hasattr(self, 'btn_apply_filters'): # If you added a dedicated filter button
      self.btn_apply_filters.set_event_handler('click', self.load_failed_transactions)
    elif hasattr(self, 'btn_refresh'): # If using existing refresh button for filtering
      self.btn_refresh.text = "Apply Filters / Refresh" # Update text to reflect dual purpose


    self.load_failed_transactions()

  def load_failed_transactions(self, **event_args):
    """Loads the list of failed transactions from the server, applying filters."""
    start_date_filter = None
    end_date_filter = None

    if hasattr(self, 'dp_start_date') and self.dp_start_date.date:
      start_date_filter = self.dp_start_date.date
    if hasattr(self, 'dp_end_date') and self.dp_end_date.date:
      end_date_filter = self.dp_end_date.date

      # Basic validation for date range
    if start_date_filter and end_date_filter and start_date_filter > end_date_filter:
      alert("Start date cannot be after end date.")
      return

    button_to_animate = None
    if hasattr(self, 'btn_apply_filters'):
      button_to_animate = self.btn_apply_filters
    elif hasattr(self, 'btn_refresh'):
      button_to_animate = self.btn_refresh

    original_text = ""
    if button_to_animate:
      original_text = button_to_animate.text
      button_to_animate.enabled = False
      button_to_animate.icon = 'fa:spinner'
      button_to_animate.text = 'Loading...'

    try:
      failed_list = anvil.server.call('get_failed_transactions', 
                                      limit=200, # Keep or adjust limit
                                      start_date=start_date_filter,
                                      end_date=end_date_filter) 
      self.rp_failed_transactions.items = failed_list

    except Exception as e:
      alert(f"An error occurred loading failed transactions: {e}")
      self.rp_failed_transactions.items = [] 

    finally:
      if button_to_animate:
        button_to_animate.enabled = True
        button_to_animate.icon = 'fa:filter' if hasattr(self, 'btn_apply_filters') else 'fa:refresh'
        button_to_animate.text = original_text


  def btn_refresh_click(self, **event_args): # If you keep a separate refresh button
    """This method is called when the Refresh button is clicked"""
    # If dp_start_date and dp_end_date exist, this will use their current values
    self.load_failed_transactions()