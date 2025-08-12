from ._anvil_designer import report_discount_listTemplate
from anvil import *
import anvil.server
# Import the Item Template - adjust path if necessary
from ..report_discount_list_item import report_discount_list_item # Assuming it's in a parent client_code folder

class report_discount_list(report_discount_listTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Setup for Filter DropDowns
    self.dd_filter_discount_status.items = ["All", "Active", "Archived", "Expired"] # Add other statuses if applicable
    self.dd_filter_discount_status.selected_value = "All"

    self.dd_filter_discount_type.items = ["All", "Percentage", "Flat"] # Match 'type' values in your discount table
    self.dd_filter_discount_type.selected_value = "All"

    # Setup for dd_sort_discounts_by DropDown
    self.dd_sort_discounts_by.items = [
      ("Coupon Code (A-Z)", "coupon_code_asc"),
      ("Coupon Code (Z-A)", "coupon_code_desc"),
      ("Discount Name (A-Z)", "discount_name_asc"),
      ("Discount Name (Z-A)", "discount_name_desc"),
      ("Status (A-Z)", "status_asc"),
      ("Expires At (Newest First)", "expires_at_desc"),
      ("Expires At (Oldest First)", "expires_at_asc"),
      ("Times Used (Most First)", "times_used_desc")
    ]
    self.dd_sort_discounts_by.selected_value = "coupon_code_asc" 

    # Set Item Template for Repeating Panel
    self.rp_all_discounts.item_template = report_discount_list_item

    # Load the initial list
    self.load_discounts_list_data()

  def load_discounts_list_data(self, **event_args):
    """Loads or reloads data for the discount list based on current filter and sort selections."""
    status_filter_val = self.dd_filter_discount_status.selected_value
    if status_filter_val == "All":
      status_filter_val = None

    type_filter_val = self.dd_filter_discount_type.selected_value
    if type_filter_val == "All":
      type_filter_val = None
    elif type_filter_val: # Ensure it's lowercase if not 'All'
      type_filter_val = type_filter_val.lower() # e.g., 'percentage', 'flat'

    sort_by_val = self.dd_sort_discounts_by.selected_value # This will be the server_key e.g., "coupon_code_asc"

    try:
      # alert("Loading discounts...", dismissible=False) # Optional loading indicator

      # Call the server function in sm_discount_mod.py
      discounts_data = anvil.server.call(
        'get_all_discounts_for_report_list', # Using the admin-only function
        status_filter=status_filter_val,
        type_filter=type_filter_val,
        sort_by=sort_by_val
      )

      self.rp_all_discounts.items = discounts_data

      # close_alert() # If loading indicator was shown

    except Exception as e:
      # close_alert() # If loading indicator was shown
      alert(f"An error occurred loading the discounts list: {e}", title="Load Error")
      self.rp_all_discounts.items = [] # Clear list on error

  def btn_apply_discount_filters_sort_click(self, **event_args): # Renamed from btn_apply_discount
    """This method is called when the Apply button is clicked."""
    self.load_discounts_list_data()