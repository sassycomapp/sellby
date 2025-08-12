from ._anvil_designer import report_customer_profileTemplate
from anvil import *
import anvil.server
# Import the Item Templates - adjust path if they are in a different client_code folder
from ..report_customer_profile_subs_item import report_customer_profile_subs_item
from ..report_customer_profile_txns_item import report_customer_profile_txns_item
from datetime import datetime # For date formatting, if needed client-side

# For system currency - this will be fetched once
SYSTEM_CURRENCY_CODE = None

class report_customer_profile(report_customer_profileTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Set Item Templates for Repeating Panels
    self.rp_subscriptions.item_template = report_customer_profile_subs_item
    self.rp_transactions.item_template = report_customer_profile_txns_item

    self.fetch_and_set_system_currency()
    self.clear_profile_display() # Initial state

  def fetch_and_set_system_currency(self):
    global SYSTEM_CURRENCY_CODE
    if SYSTEM_CURRENCY_CODE is None:
      try:
        currency_info = anvil.server.call('get_system_currency') # From helper_functions
        if currency_info and currency_info.get('currency'):
          SYSTEM_CURRENCY_CODE = currency_info['currency']
        else:
          SYSTEM_CURRENCY_CODE = "USD" # Fallback, should be configured
          alert("System currency not found, defaulting to USD for display.")
      except Exception as e:
        SYSTEM_CURRENCY_CODE = "USD" # Fallback on error
        print(f"Error fetching system currency: {e}")
        alert(f"Error fetching system currency: {e}. Defaulting to USD for display.")

  def clear_profile_display(self):
    """Clears all customer profile display elements or sets them to an 'inactive' state."""
    # Customer Details
    self.lbl_customer_name.text = "-"
    self.lbl_customer_email.text = "-"
    self.lbl_customer_status.text = "-"
    self.lbl_customer_created.text = "-" # Was lbl_customer_joined_date
    self.lbl_paddle_customer_id.text = "-" # Was lbl_customer_paddle_id_value

    # Business Details - clear and make section appear inactive
    # self.cp_business_details_section.visible = False # Original plan was to hide
    self.lbl_business_company_number_value.text = "-"
    self.lbl_business_tax_id_value.text = "-"
    # To make it appear inactive, you might set foreground color to grey or disable components
    # For simplicity, just clearing text. True "greying out" is more involved.

    # Address Section
    self.lbl_address_line1.text = "-"
    self.lbl_address_city.text = "-"
    self.lbl_address_region.text = "-"
    self.lbl_address_postal_code.text = "-"
    self.lbl_address_country.text = "-"

    # Subscriptions & Transactions
    self.rp_subscriptions.items = [] # Was rp_customer_subscriptions
    self.rp_transactions.items = []  # Was rp_customer_transactions

    # Titles - set text to indicate no data rather than hiding
    self.lbl_subscriptions_title.text = "Subscriptions (No data)"
    self.lbl_transactions_title.text = "Transactions (No data)"

    # Enable search
    self.btn_perform_search.enabled = True
    self.btn_perform_search.icon = 'fa:search'
    self.btn_perform_search.text = 'Find Customer'


  def populate_profile_display(self, profile_data):
    """Populates the form components with data from the server."""
    if not profile_data:
      self.clear_profile_display()
      alert("No profile data received.")
      return

      # Customer Details
    self.lbl_customer_name.text = profile_data.get('display_name', 'N/A')
    self.lbl_customer_email.text = profile_data.get('email', 'N/A')
    self.lbl_customer_status.text = profile_data.get('status', 'N/A')
    created_at = profile_data.get('paddle_created_at')
    self.lbl_customer_created.text = created_at.strftime('%Y-%m-%d') if created_at else 'N/A'
    self.lbl_paddle_customer_id.text = profile_data.get('paddle_id', 'N/A')

    # Business Details
    business_details = profile_data.get('business_details')
    if business_details:
      # self.cp_business_details_section.visible = True # If you were hiding it
      self.lbl_business_company_number_value.text = business_details.get('company_number', 'N/A')
      self.lbl_business_tax_id_value.text = business_details.get('tax_identifier', 'N/A')
    else:
      # self.cp_business_details_section.visible = False # If you were hiding it
      self.lbl_business_company_number_value.text = "-" # Indicate no data
      self.lbl_business_tax_id_value.text = "-"     # Indicate no data

      # Address Details
    address = profile_data.get('address_details')
    if address:
      self.lbl_address_line1.text = address.get('first_line', 'N/A')
      self.lbl_address_city.text = address.get('city', 'N/A')
      self.lbl_address_region.text = address.get('region', 'N/A')
      self.lbl_address_postal_code.text = address.get('postal_code', 'N/A')
      self.lbl_address_country.text = address.get('country_name', 'N/A')
    else:
      self.lbl_address_line1.text = "-"
      self.lbl_address_city.text = "-"
      self.lbl_address_region.text = "-"
      self.lbl_address_postal_code.text = "-"
      self.lbl_address_country.text = "-"

      # Subscriptions
    subs_list = profile_data.get('subscriptions', [])
    self.rp_subscriptions.items = subs_list
    self.lbl_subscriptions_title.text = "Subscriptions" if subs_list else "Subscriptions (None)"

    # Transactions
    # Pass SYSTEM_CURRENCY_CODE to each transaction item for formatting
    txns_list_raw = profile_data.get('transactions', [])
    txns_list_for_display = []
    if SYSTEM_CURRENCY_CODE: # Ensure it's fetched
      for txn_data in txns_list_raw:
        item_with_currency = dict(txn_data) # Create a mutable copy
        item_with_currency['system_currency_code_for_display'] = SYSTEM_CURRENCY_CODE
        txns_list_for_display.append(item_with_currency)
    else: # Fallback if currency code wasn't fetched (should not happen ideally)
      txns_list_for_display = txns_list_raw

    self.rp_transactions.items = txns_list_for_display
    self.lbl_transactions_title.text = "Transactions" if txns_list_for_display else "Transactions (None)"


  def btn_perform_search_click(self, **event_args):
    """This method is called when the search button is clicked"""
    customer_identifier = self.tb_search_identifier.text.strip()
    if not customer_identifier:
      alert("Please enter a Customer Email or Paddle ID to search.")
      return

    self.clear_profile_display() # Clear before new search

    try:
      self.btn_perform_search.enabled = False
      self.btn_perform_search.icon = 'fa:spinner'
      self.btn_perform_search.text = 'Searching...'

      profile_data = anvil.server.call('get_customer_profile', customer_identifier)

      if profile_data:
        self.populate_profile_display(profile_data)
      else:
        alert(f"No customer found matching '{customer_identifier}'.")
        # Profile remains in cleared state
    except Exception as e:
      alert(f"An error occurred: {str(e)}")
      # self.clear_profile_display() # Already cleared, or clear again if partial population occurred
    finally:
      self.btn_perform_search.enabled = True
      self.btn_perform_search.icon = 'fa:search'
      self.btn_perform_search.text = 'Find Customer'

  def tb_search_identifier_pressed_enter(self, **event_args):
    """This method is called when the user presses Enter in the TextBox"""
    self.btn_perform_search_click()