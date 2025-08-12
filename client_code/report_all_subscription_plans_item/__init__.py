from ._anvil_designer import report_all_subscription_plans_itemTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class report_all_subscription_plans_item(report_all_subscription_plans_itemTemplate):

    def __init__(self, **properties):
      # Set Form properties and Data Bindings.
      self.init_components(**properties)

      # self.item is a dictionary passed by the RepeatingPanel.
      # It contains data for one subscription plan price, fetched by 
      # the server function get_all_subscription_plans().
      # Expected keys (based on server function output):
      #   'mybizz_price_id', 'paddle_price_id', 'price_description',
      #   'subscription_group_name', 'linked_item_name', 'glt',
      #   'unit_price_amount', 'unit_price_currency_code',
      #   'billing_cycle_interval', 'billing_cycle_frequency',
      #   'trial_period_interval', 'trial_period_frequency',
      #   'status', 'tax_mode', 'quantity_minimum', 'quantity_maximum',
      #   'linked_item_mybizz_id', 'linked_item_anvil_id', 'linked_item_type',
      #   'created_at_anvil', 'updated_at_anvil', 'paddle_created_at', 'paddle_updated_at'

      if self.item:
        # 1. Price Description (e.g., "Standard Monthly Rate")
        self.lbl_price_description.text = self.item.get('price_description', 'N/A')

        # 2. Plan Identifier (e.g., "Mastering Math - Beginner Monthly (G1L1T2)")
        group_name = self.item.get('subscription_group_name', 'Unknown Group')
        item_name = self.item.get('linked_item_name', 'Unknown Plan')
        # GLT is often part of item_name, but can be displayed separately if needed.
        # For now, assuming item_name is descriptive enough.
        # If you want to explicitly show GLT from item_name or a separate 'glt' field:
        # glt_val = self.item.get('glt', '')
        # self.lbl_plan_identifier.text = f"{group_name} - {item_name} ({glt_val})"
        self.lbl_plan_identifier.text = f"{group_name} - {item_name}"


        # 3. Price Details (e.g., "USD 19.99")
        amount_str = self.item.get('unit_price_amount')
        currency_code = self.item.get('unit_price_currency_code', '')
        if amount_str is not None and currency_code:
          try:
            major_units = int(str(amount_str)) / 100.0
            self.lbl_price_details.text = f"{currency_code} {major_units:,.2f}"
          except (ValueError, TypeError):
            self.lbl_price_details.text = f"{currency_code} {amount_str} (raw)"
        elif amount_str is not None: # Amount but no currency
          self.lbl_price_details.text = f"{amount_str} (raw)"
        else:
          self.lbl_price_details.text = "N/A"

        # 4. Billing Cycle (e.g., "Monthly" or "Bills every 1 Month")
        interval = self.item.get('billing_cycle_interval')
        frequency = self.item.get('billing_cycle_frequency')
        if interval and frequency is not None:
          freq_str = str(frequency)
          interval_str = interval.title()
          plural_s = "s" if frequency > 1 and not interval.endswith('s') else "" # basic pluralization
          if frequency == 1 and interval == 'month':
            self.lbl_billing_cycle.text = "Monthly"
          elif frequency == 1 and interval == 'year':
            self.lbl_billing_cycle.text = "Yearly"
          elif frequency == 1 and interval == 'week':
            self.lbl_billing_cycle.text = "Weekly"
          elif frequency == 1 and interval == 'day':
            self.lbl_billing_cycle.text = "Daily"
          else:
            self.lbl_billing_cycle.text = f"Every {freq_str} {interval_str}{plural_s}"
        else:
          self.lbl_billing_cycle.text = "N/A" # Or "One-time" if that's possible (though filtered by server)

        # 5. Trial Period (Conditional Display)
        trial_interval = self.item.get('trial_period_interval')
        trial_frequency = self.item.get('trial_period_frequency')
        if trial_interval and trial_frequency is not None:
          self.lbl_trial_info.text = f"Trial: {trial_frequency} {trial_interval.title()}{'s' if trial_frequency > 1 else ''}"
          self.lbl_trial_info.visible = True
        else:
          self.lbl_trial_info.text = "No Trial" # Or set visible to False
          self.lbl_trial_info.visible = True # Keep it visible but show "No Trial"

        # 6. Status (e.g., "Active")
        self.lbl_status.text = f"Status: {str(self.item.get('status', 'N/A')).title()}"

        # 7. Paddle Price ID
        paddle_id = self.item.get('paddle_price_id')
        self.lbl_paddle_price_id.text = f"Paddle ID: {paddle_id}" if paddle_id else "Paddle ID: (Not Synced)"

        # Set up event handler for the manage button
        self.btn_manage_price.set_event_handler('click', self.manage_price_click)
        # Enable button only if we have the necessary IDs to manage the price
        self.btn_manage_price.enabled = bool(self.item.get('mybizz_price_id') and self.item.get('linked_item_anvil_id'))

      else: # Fallback if self.item is None
        self.lbl_price_description.text = "N/A"
        self.lbl_plan_identifier.text = "N/A"
        self.lbl_price_details.text = "N/A"
        self.lbl_billing_cycle.text = "N/A"
        self.lbl_trial_info.text = "N/A"
        self.lbl_trial_info.visible = False
        self.lbl_status.text = "N/A"
        self.lbl_paddle_price_id.text = "N/A"
        self.btn_manage_price.enabled = False

    def manage_price_click(self, **event_args):
      """Handles the click of the 'Manage Price' button."""
      if self.item:
        mybizz_price_id_to_manage = self.item.get('mybizz_price_id') # MyBizz PK of the price
        # The manage_price_form expects the parent item_row object or its Anvil ID.
        # The server function get_all_subscription_plans returns 'linked_item_anvil_id'
        parent_item_anvil_id = self.item.get('linked_item_anvil_id') 

        if mybizz_price_id_to_manage and parent_item_anvil_id:
          # To open manage_price_form, we need the parent item_row object.
          # We can fetch it here, or modify manage_price_form to accept item_anvil_id and fetch itself.
          # For now, let's assume manage_price_form can handle being passed the parent_item_anvil_id
          # and the price_id (or the price row itself if we fetch it here).

          # Fetch the price row to pass to manage_price_form
          try:
            price_row_to_edit = anvil.server.call('get_price', mybizz_price_id_to_manage) # Assumes get_price exists
            parent_item_row_for_form = anvil.server.call('get_item', self.item.get('linked_item_mybizz_id')) # Fetch parent item by MyBizz ID

            if price_row_to_edit and parent_item_row_for_form:
              # manage_price_form expects: item_row (parent item), price_to_edit (price row), price_type_context
              open_form(
                'manage_price_form', 
                item_row=parent_item_row_for_form, 
                price_to_edit=price_row_to_edit,
                price_type_context='recurring' # This report is for recurring prices
              )
            else:
              alert("Could not load necessary details to manage this price.")
          except Exception as e:
            alert(f"Error preparing to manage price: {e}")
        else:
          alert("Cannot manage price: Essential identifiers are missing.")
      else:
        alert("No price data to manage.") 