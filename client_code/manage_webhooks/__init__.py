# Client Module: manage_webhooks.py

from ._anvil_designer import manage_webhooksTemplate # Ensure this matches your Anvil template name
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Assuming path to client logger
from .manage_webhooks_item import manage_webhooks_item # Import the item template

class manage_webhooks(manage_webhooksTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "manage_webhooks"
    log("INFO", self.module_name, "__init__", "Form initializing.")

    # Configure RepeatingPanel
    if hasattr(self, 'rp_webhook_logs'):
      self.rp_webhook_logs.item_template = manage_webhooks_item
      # Event handler for when an item template requests a refresh of the list
      self.rp_webhook_logs.set_event_handler('x-refresh-log-list', self.btn_apply_filters_click) # Reuse filter button's action

    # Initialize Filters (Example: if you have them)
    if hasattr(self, 'dd_filter_event_type'):
      # Populate this from server or predefined list if needed
      self.dd_filter_event_type.items = [("All Event Types", None), "transaction.billed", "subscription.created"] # Example
    if hasattr(self, 'dd_filter_status'):
      self.dd_filter_status.items = [("All Statuses", None), "Processed", "Forwarded to Hub", "Forwarding Error", "Error"] # Example

    # Load initial data
    self.btn_apply_filters_click() 

  def get_filters(self):
    """Helper function to gather filter values from UI components."""
    filters = {}
    if hasattr(self, 'dp_filter_start_date') and self.dp_filter_start_date.date:
      filters['start_date'] = self.dp_filter_start_date.date
    if hasattr(self, 'dp_filter_end_date') and self.dp_filter_end_date.date:
      # Add 1 day to end_date to make it inclusive for the whole day if time is not specified
      filters['end_date'] = self.dp_filter_end_date.date 
      # Server-side logic should handle date range appropriately (e.g., end_date as exclusive upper bound)
    if hasattr(self, 'dd_filter_event_type') and self.dd_filter_event_type.selected_value:
      filters['event_type'] = self.dd_filter_event_type.selected_value
    if hasattr(self, 'dd_filter_status') and self.dd_filter_status.selected_value:
      filters['status'] = self.dd_filter_status.selected_value
    return filters

  def btn_apply_filters_click(self, **event_args):
    """Loads/refreshes the webhook log list based on current filter values."""
    log("INFO", self.module_name, "btn_apply_filters_click", "Loading/refreshing webhook logs.")

    current_filters = self.get_filters()
    log("DEBUG", self.module_name, "btn_apply_filters_click", f"Applying filters: {current_filters}")

    try:
      # Show loading state (optional: add a spinner or disable button)
      if hasattr(self, 'btn_apply_filters'): 
        self.btn_apply_filters.enabled = False
      if hasattr(self, 'btn_refresh_list'): 
        self.btn_refresh_list.enabled = False


        # Call server function to get filtered logs
        # Server function 'get_mybizz_webhook_logs' needs to accept a filters dictionary
      log_entries = anvil.server.call('get_mybizz_webhook_logs', filters=current_filters)

      if hasattr(self, 'rp_webhook_logs'):
        self.rp_webhook_logs.items = log_entries
        log("INFO", self.module_name, "btn_apply_filters_click", f"Displayed {len(log_entries)} log entries.")
      else:
        log("ERROR", self.module_name, "btn_apply_filters_click", "rp_webhook_logs component not found.")


    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}", title="Access Denied")
      log("WARNING", self.module_name, "btn_apply_filters_click", f"Permission denied: {e}")
      if hasattr(self, 'rp_webhook_logs'): 
        self.rp_webhook_logs.items = []
    except Exception as e:
      alert(f"An error occurred while loading webhook logs: {e}", title="Error")
      log("ERROR", self.module_name, "btn_apply_filters_click", f"Error: {e}")
      if hasattr(self, 'rp_webhook_logs'): 
        self.rp_webhook_logs.items = []
    finally:
      # Reset loading state
      if hasattr(self, 'btn_apply_filters'): 
        self.btn_apply_filters.enabled = True
      if hasattr(self, 'btn_refresh_list'): 
        self.btn_refresh_list.enabled = True


  def btn_refresh_list_click(self, **event_args):
    """This method is called when the Refresh List button is clicked."""
    # This can simply call the apply_filters method which reloads data
    self.btn_apply_filters_click()

  def btn_home_click(self, **event_args):
    """This method is called when the Home button is clicked."""
    log("INFO", self.module_name, "btn_home_click", "Navigating to paddle_home.")
    open_form('paddle_home') # Or your main admin dashboard