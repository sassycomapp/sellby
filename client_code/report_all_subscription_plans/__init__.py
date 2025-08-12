from ._anvil_designer import report_all_subscription_plansTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ..report_all_subscription_plans_item import report_all_subscription_plans_item 

class report_all_subscription_plans(report_all_subscription_plansTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Set the item template for the RepeatingPanel
    self.rp_subscription_plans.item_template = report_all_subscription_plans_item

    # Initialize and populate filter/sort DropDowns
    self._populate_filter_dropdowns()
    self._populate_sort_dropdown()

    # Set event handlers for buttons
    self.btn_apply_filters.set_event_handler('click', self.apply_filters_and_sort)
    self.btn_clear_filters.set_event_handler('click', self.clear_filters_and_load)
    self.btn_refresh_list.set_event_handler('click', self.load_plans) # Refresh uses current filters
    self.btn_home.set_event_handler('click', self.go_home)

    # Load initial data
    self.load_plans()

  def _populate_filter_dropdowns(self):
    # Populate Status Filter
    self.dd_filter_status.items = [
      ("All Statuses", None), 
      ("Active", "active"), 
      ("Archived", "archived")
    ]
    self.dd_filter_status.selected_value = None

    # Populate Subscription Group Filter
    try:
      # This server function needs to return a list of (display_name, group_anvil_id) tuples
      # Example: [("Mastering Math", "anvil_id_for_mm_group"), ...]
      # We'll use get_subscription_group_list which returns (name, anvil_id)
      groups = anvil.server.call('get_subscription_group_list') 
      group_items = [("All Subscription Groups", None)] + groups
      self.dd_filter_subscription_group.items = group_items
      self.dd_filter_subscription_group.selected_value = None
    except Exception as e:
      alert(f"Error loading subscription groups for filter: {e}")
      self.dd_filter_subscription_group.items = [("Error loading groups", None)]


  def _populate_sort_dropdown(self):
    self.dd_sort_by.items = [
      ("Price Description (A-Z)", "price_desc_asc"), 
      ("Subscription Group Name (A-Z)", "group_name_asc"), 
      ("Linked Item Name (A-Z)", "item_name_asc"),
      ("Status (A-Z)", "status_asc"),
      ("Last Updated (Newest First)", "updated_at_desc"), # Default sort from server is by group, item, price desc
      ("Price Description (Z-A)", "price_desc_desc"), 
      ("Subscription Group Name (Z-A)", "group_name_desc"), 
      ("Linked Item Name (Z-A)", "item_name_desc"),
      ("Status (Z-A)", "status_desc"),
      ("Last Updated (Oldest First)", "updated_at_asc")
    ]
    # The server function get_all_subscription_plans now handles default sorting.
    # This dropdown is for user-override. Let's default to "Price Description (A-Z)"
    # or leave it blank to use server default. For now, let's set a client default.
    self.dd_sort_by.selected_value = "price_desc_asc" 

    def load_plans(self, **event_args):
      """Loads or reloads data for the report based on current filter and sort selections."""
      status_filter = self.dd_filter_status.selected_value
      group_filter_anvil_id = self.dd_filter_subscription_group.selected_value
      # sort_by_key = self.dd_sort_by.selected_value # Line removed as sort_by_key is not used yet

      # Show loading state (optional)
      # self.btn_apply_filters.enabled = False
      # self.btn_apply_filters.icon = 'fa:spinner'
      # self.btn_refresh_list.enabled = False
      # self.btn_refresh_list.icon = 'fa:spinner'

      try:
        all_plan_prices = anvil.server.call('get_all_subscription_plans')

        # --- Client-Side Filtering (Example) ---
        filtered_items = all_plan_prices
        if status_filter:
          filtered_items = [p for p in filtered_items if p.get('status') == status_filter]

        if group_filter_anvil_id:
          # This client-side filter for group requires the server to return 
          # 'subscription_group_anvil_id' or similar in each item dictionary.
          # Assuming 'get_all_subscription_plans' now returns 'subscription_group_anvil_id'
          # (If not, this filter part needs adjustment based on available data)
          # For now, let's assume it's available for demonstration of filtering.
          # If 'subscription_group_anvil_id' is not in self.item from server, this will not work.
          # We need to ensure the server function `get_all_subscription_plans` returns
          # the Anvil ID of the subscription_group for each price.
          # Let's assume it returns it under a key like 'group_anvil_id_for_filtering'.
          # This part needs to align with what the server actually sends.
          # For now, I will comment out this specific filter line as it depends on
          # a server-side change we haven't explicitly made to get_all_subscription_plans yet.
          # filtered_items = [p for p in filtered_items if p.get('subscription_group_anvil_id_from_server') == group_filter_anvil_id]
          pass # Placeholder for group filtering logic

          # Client-side sorting based on sort_by_key would go here if implemented.
          # For now, relying on server's default sort.

        self.rp_subscription_plans.items = filtered_items

      except Exception as e:
        alert(f"An error occurred loading the subscription plan prices: {e}", title="Load Error")
        self.rp_subscription_plans.items = []
      finally:
        # Reset loading state (optional)
        # self.btn_apply_filters.enabled = True
        # self.btn_apply_filters.icon = 'fa:filter'
        # self.btn_refresh_list.enabled = True
        # self.btn_refresh_list.icon = 'fa:refresh'
        pass

  def apply_filters_and_sort(self, **event_args):
    """Called when the 'Apply Filters & Sort' button is clicked."""
    self.load_plans()

  def clear_filters_and_load(self, **event_args):
    """Resets filters to default and reloads the data."""
    self.dd_filter_status.selected_value = None
    self.dd_filter_subscription_group.selected_value = None
    # self.dd_sort_by.selected_value = "price_desc_asc" # Or whatever default sort
    self.load_plans()

  def go_home(self, **event_args):
    """Navigates to the home form."""
    open_form('paddle_home')