from ._anvil_designer import report_discount_analyticsTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime # Ensure datetime is imported

class report_discount_analytics(report_discount_analyticsTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.
    self.populate_status_dropdown()
    self.load_report_data()

  def populate_status_dropdown(self):
    # Statuses should match what's stored in your discount table (likely from Paddle)
    self.dd_status_filter.items = ["All", "active", "expired", "archived"]
    self.dd_status_filter.selected_value = "All"

  def load_report_data(self, **event_args):
    """Loads or reloads data for the report based on current filter selections."""
    start_date = self.dp_start_date.date
    end_date = self.dp_end_date.date

    status_filter_value = self.dd_status_filter.selected_value
    if status_filter_value == "All":
      status_filter_value = None

    # Convert date objects to datetime for server-side comparison if needed,
    # or ensure server handles date objects appropriately.
    # For "All Time", pass None for dates.

    # Ensure end_date is inclusive of the whole day if it's a date object
    # For example, if end_date is 2023-10-26, we might want to query up to 2023-10-26 23:59:59
    # However, passing date objects directly and letting the server handle it is often cleaner.
    # If start_date and end_date are None, it implies "All Time".

    try:
      alert("Fetching discount usage data...", title="Loading Report", dismissible=False)
      discount_data = anvil.server.call(
        'get_discount_usage_data',
        start_date=start_date,
        end_date=end_date,
        status_filter=status_filter_value
      )

      # Default sort: times_used (descending)
      # This sorting can be enhanced later with clickable headers
      if discount_data:
        discount_data.sort(key=lambda x: x.get('times_used', 0), reverse=True)

      self.rp_discounts.items = discount_data
      Notification("Report loaded successfully.", style="success").show()

    except Exception as e:
      Notification(f"Error loading report: {e}", style="danger", timeout=5).show()
    finally:
      # Close the "Loading Report" alert if it's still open
      # This requires a more sophisticated alert management or simply let it auto-dismiss if possible
      # For simplicity, we'll rely on the user dismissing it or it auto-dismissing.
      # If you used a persistent alert, you'd need to store a reference to it and call .hide()
      pass # Placeholder for closing persistent alert

  def btn_apply_filters_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.load_report_data()

  def btn_refresh_click(self, **event_args):
    """This method is called when the button is clicked"""
    # Option 1: Refresh with current filters (same as apply)
    self.load_report_data()
    # Option 2: Reset filters to default and then load
    # self.dp_start_date.date = None
    # self.dp_end_date.date = None
    # self.dd_status_filter.selected_value = "All"
    # self.load_report_data()