# report_transaction_all.py

from ._anvil_designer import report_transaction_allTemplate
from anvil import *
import anvil.server
from datetime import date, timedelta

# Import the Item Template
from ..report_transaction_all_item import report_transaction_all_item 
# Assuming cm_logs_helper is in the parent directory if logging is needed
# from ..cm_logs_helper import log 

class report_transaction_all(report_transaction_allTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # --- Pagination State ---
    self.current_page = 1
    self.page_size = 15 # Or whatever you prefer as a default
    self.total_transactions = 0
    self.total_pages = 1

    # --- Initialize Filters & Sort ---
    self.dd_status_filter.items = [
      ("All Statuses", None), 
      ("paid", "paid"), # Use lowercase to match typical Paddle status
      ("failed", "failed"), 
      ("completed", "completed"), # Often used interchangeably with paid
      ("billed", "billed"), # Intermediate state
      ("canceled", "canceled"),
      ("past_due", "past_due")
      # Add other relevant statuses from your system/Paddle
    ]
    self.dd_status_filter.selected_value = None # Default to "All Statuses"

    # Set default date range (e.g., last 30 days)
    self.dp_end_date.date = date.today()
    self.dp_start_date.date = date.today() - timedelta(days=30)

    # Populate Sort Dropdown
    self.dd_sort_criteria.items = [
      ("Date (Newest First)", "billed_at_desc"), #(Default)
      ("Date (Oldest First)", "billed_at_asc"),
      ("Amount (Highest First)", "total_desc"),
      ("Amount (Lowest First)", "total_asc"),
      ("Customer Email (A-Z)", "customer_email_asc"),
      ("Customer Email (Z-A)", "customer_email_desc"),
      ("Status (A-Z)", "status_asc"),
      ("Status (Z-A)", "status_desc")
    ]
    self.dd_sort_criteria.selected_value = "billed_at_desc" # Default sort

    # Set Item Template for Repeating Panel
    self.rp_transactions.item_template = report_transaction_all_item

    # Set event handlers for new controls
    self.dd_sort_criteria.set_event_handler('change', self.filter_or_sort_changed)
    self.btn_previous_page.set_event_handler('click', self.btn_previous_page_click)
    self.btn_next_page.set_event_handler('click', self.btn_next_page_click)

    # Existing filter button handler
    self.btn_filter.set_event_handler('click', self.filter_or_sort_changed)
    # Also trigger load on date/status change if desired (optional)
    # self.dp_start_date.set_event_handler('change', self.filter_or_sort_changed)
    # self.dp_end_date.set_event_handler('change', self.filter_or_sort_changed)
    # self.dd_status_filter.set_event_handler('change', self.filter_or_sort_changed)


    # --- Load Initial Data ---
    self.load_transactions()

  def filter_or_sort_changed(self, **event_args):
    """Common handler for when filters or sort order change."""
    self.current_page = 1 # Reset to first page when filters/sort change
    self.load_transactions()

  def load_transactions(self):
    """Loads transaction data based on filters, sort, and pagination."""
    start_date = self.dp_start_date.date
    end_date = self.dp_end_date.date
    status_filter = self.dd_status_filter.selected_value
    sort_by_value = self.dd_sort_criteria.selected_value

    # Basic validation for date range
    if start_date and end_date and start_date > end_date:
      alert("Start date cannot be after end date.")
      return

    self.btn_filter.enabled = False
    self.btn_filter.icon = 'fa:spinner'
    # self.btn_filter.text = 'Loading...' # Or keep as "Apply Filters"

    try:
      # Server function now returns a dict: {'items': [...], 'total_count': X}
      response_dict = anvil.server.call(
        'get_all_transactions',
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter,
        sort_by=sort_by_value,
        page_number=self.current_page,
        page_size=self.page_size
      )

      transactions_list = response_dict.get('items', [])
      self.total_transactions = response_dict.get('total_count', 0)

      self.rp_transactions.items = transactions_list
      self.update_pagination_controls()

    except Exception as e:
      alert(f"An error occurred while loading transactions: {e}")
      self.rp_transactions.items = [] 
      self.total_transactions = 0
      self.update_pagination_controls() # Still update to show "Page 0 of 0" or similar
    finally:
      self.btn_filter.enabled = True
      self.btn_filter.icon = 'fa:filter' 
      # self.btn_filter.text = 'Apply Filters & Sort'

  def update_pagination_controls(self):
    """Updates the pagination buttons and label based on current state."""
    if self.total_transactions == 0:
      self.total_pages = 0
      self.current_page = 0 # Or 1 if you prefer to show "Page 1 of 0"
    else:
      self.total_pages = (self.total_transactions + self.page_size - 1) // self.page_size # Ceiling division

    self.lbl_page_info.text = f"Page {self.current_page} of {self.total_pages}"

    self.btn_previous_page.enabled = (self.current_page > 1)
    self.btn_next_page.enabled = (self.current_page < self.total_pages)

    # Hide pagination controls if only one page or no results
    self.btn_previous_page.visible = (self.total_pages > 1)
    self.lbl_page_info.visible = (self.total_pages > 0) # Show even for 1 page
    self.btn_next_page.visible = (self.total_pages > 1)


  def btn_previous_page_click(self, **event_args):
    """Handles click for the Previous Page button."""
    if self.current_page > 1:
      self.current_page -= 1
      self.load_transactions()

  def btn_next_page_click(self, **event_args):
    """Handles click for the Next Page button."""
    if self.current_page < self.total_pages:
      self.current_page += 1
      self.load_transactions()