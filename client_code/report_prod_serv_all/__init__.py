from ._anvil_designer import report_prod_serv_allTemplate
from anvil import *
import anvil.server
# Import the Item Template - adjust path if necessary
from ..report_prod_serv_all_item import report_prod_serv_all_item

class report_prod_serv_all(report_prod_serv_allTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Setup for Filter DropDowns
    self.dd_filter_status.items = ["All", "Active", "Archived"]
    self.dd_filter_status.selected_value = "All"

    self.dd_filter_type.items = ["All", "Product", "Service"]
    self.dd_filter_type.selected_value = "All"

    # Setup for dd_sort_by DropDown
    self.dd_sort_by.items = [
      ("Name (A-Z)", "name_asc"),
      ("Name (Z-A)", "name_desc"),
      ("Created Date (Newest First)", "created_at_desc"),
      ("Created Date (Oldest First)", "created_at_asc"),
      ("Item ID (A-Z)", "item_id_asc"),
      ("Item ID (Z-A)", "item_id_desc"),
      ("Type (A-Z)", "item_type_asc"),
      ("Type (Z-A)", "item_type_desc")
    ]
    self.dd_sort_by.selected_value = "name_asc" 

    # Set Item Template for Repeating Panel
    self.rp_items_list.item_template = report_prod_serv_all_item

    # Load the initial list
    self.load_items_list()

  def load_items_list(self, **event_args):
    """Loads or reloads data for the report based on current filter and sort selections."""
    status_filter_val = self.dd_filter_status.selected_value
    if status_filter_val == "All":
      status_filter_val = None

    type_filter_val = self.dd_filter_type.selected_value
    if type_filter_val == "All":
      type_filter_val = None
    elif type_filter_val: # Ensure it's 'product' or 'service' if not 'All'
      type_filter_val = type_filter_val.lower()


    sort_by_val = self.dd_sort_by.selected_value # This will be the server_key e.g., "name_asc"

    try:
      # Consider adding a visual loading indicator here if operations are slow
      # alert("Loading items...", dismissible=False) 

      items_data = anvil.server.call(
        'get_all_products_and_services', # Renamed server function
        status_filter=status_filter_val,
        item_type_filter=type_filter_val,
        sort_by=sort_by_val
      )

      self.rp_items_list.items = items_data

      # if alert was shown:
      # close_alert() # Or manage alert state

    except Exception as e:
      # if alert was shown:
      # close_alert() # Or manage alert state
      alert(f"An error occurred loading the items list: {e}", title="Load Error")
      self.rp_items_list.items = [] # Clear list on error

  def btn_apply_filters_sort_click(self, **event_args):
    """This method is called when the Apply button is clicked."""
    self.load_items_list()