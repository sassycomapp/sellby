# Client Form: paddle_home.py (Reverted - No URL Fragment Handling)

from ._anvil_designer import paddle_homeTemplate
# Corrected: Using minimal explicit imports needed for THIS form, NO get_open_url
from anvil import alert, Notification, TextBox, open_form, get_open_form
import anvil.js
import anvil.users
import anvil.server
#import traceback
from anvil.js.window import open as open_window
from anvil.tables import app_tables 

# Import client-side logger and the setup form
from ..cm_logs_helper import log
from ..owner_setup_form import owner_setup_form # Adjust path if needed

class paddle_home(paddle_homeTemplate):

    def __init__(self, **properties):
      self.init_components(**properties)
      log("INFO", "paddle_home", "__init__", "Form initializing")
      self.user = None 
      self.role_name = ""
      self.user_permissions = set() 
  
      # The event handler is no longer needed with the open_form pattern.
  
      self._initialize_form_state()

# This is the complete _initialize_form_state method for paddle_home.py

# This is the complete _initialize_form_state method for paddle_home.py

    def _initialize_form_state(self):
      log("DEBUG", "paddle_home", "_initialize_form_state", "Running form state initialization")
      self.user = anvil.users.get_user()
    
      # Default state for a logged-out user
      self.user_permissions = set()
      self.role_name = "Not Logged In"
      self.lbl_welcome.text = "Please log in"
      if hasattr(self, 'btn_login'): 
        self.btn_login.visible = True
      if hasattr(self, 'btn_logout'): 
        self.btn_logout.visible = False
    
      if self.user:
        # User is logged in, fetch all their data from the server
        try:
          user_data = anvil.server.call('get_user_data_for_ui')
    
          self.lbl_welcome.text = f"Welcome, {user_data.get('email', 'N/A')}"
          self.role_name = user_data.get('role_name', 'N/A')
          self.user_permissions = set(user_data.get('permissions', []))
    
          if hasattr(self, 'btn_login'): 
            self.btn_login.visible = False
          if hasattr(self, 'btn_logout'): 
            self.btn_logout.visible = True
    
            # --- START: RESTORED LOGIC ---
            # Check if the user's profile is complete.
          if not user_data.get('profile_complete'):
            log("INFO", "paddle_home", "_initialize_form_state", "User profile is incomplete. Opening profile_completion_form.")
            # The profile_completion_form will open paddle_home again upon success.
            open_form('profile_completion_form') 
            return # Stop further execution until profile is complete.
            # --- END: RESTORED LOGIC ---
    
            # Check for initial owner setup
          owner_status = anvil.server.call('check_or_init_owner')
          if owner_status.get('setup_needed'):
            log("INFO", "paddle_home", "_initialize_form_state", "Owner setup needed, opening setup form.")
            alert(content=owner_setup_form(), title="Initial Owner Setup", large=True, buttons=[])
    
            log("INFO", "paddle_home", "_initialize_form_state", "Owner setup form closed. Finalizing RBAC initialization.")
            anvil.server.call('initialize_default_rbac_data')
    
            self._initialize_form_state()
            return
    
        except Exception as e:
          log("ERROR", "paddle_home", "_initialize_form_state", f"Error fetching user UI data from server: {str(e)}")
          alert("Could not load your user profile. Some features may be disabled.")
          self.user_permissions = set()
          self.role_name = "Error"
          self.lbl_welcome.text = "Welcome, Error"
    
      self._update_ui_based_on_permissions()


  
    def _update_ui_based_on_permissions(self):
      """
          Updates UI elements based on the user's role name and fetched permissions.
          This now happens in two stages:
          1. Set visibility for individual buttons.
          2. Set visibility for the container cards based on their contents.
          """
      log("DEBUG", "paddle_home", "_update_ui_based_on_permissions", "Updating UI based on permissions.")
  
      # --- Stage 1: Set visibility for individual components ---
  
      # Set visibility for top-level labels (always visible when this function runs)
      if hasattr(self, 'lbl_active_role'):
        self.lbl_active_role.text = f"Role: {self.role_name}"
        self.lbl_active_role.visible = True
  
      if hasattr(self, 'lbl_admin_status'):
        is_admin_role = self.role_name in ["Owner", "Admin"]
        self.lbl_admin_status.text = "Admin Privileges Active (Role Based)" if is_admin_role else ""
        self.lbl_admin_status.visible = is_admin_role
  
        # Set visibility for all permission-controlled buttons
        # Using self.user_permissions, which is populated by _initialize_form_state
      if hasattr(self, 'btn_manage_users'):
        self.btn_manage_users.visible = "view_all_users_list" in self.user_permissions
  
      if hasattr(self, 'btn_vault'):
        self.btn_vault.visible = "manage_mybizz_vault" in self.user_permissions
  
      if hasattr(self, 'btn_manage_settings'):
        self.btn_manage_settings.visible = "manage_app_settings" in self.user_permissions
  
      if hasattr(self, 'btn_manage_rbac'):
        self.btn_manage_rbac.visible = "manage_roles" in self.user_permissions
  
      if hasattr(self, 'btn_manage_prices'):
        self.btn_manage_prices.visible = "manage_prices_overrides" in self.user_permissions
  
      if hasattr(self, 'btn_manage_discounts'):
        self.btn_manage_discounts.visible = "view_discounts" in self.user_permissions
  
      if hasattr(self, 'btn_manage_product'):
        self.btn_manage_product.visible = "view_all_items" in self.user_permissions
  
      if hasattr(self, 'btn_manage_service'):
        self.btn_manage_service.visible = "view_all_items" in self.user_permissions
  
      if hasattr(self, 'btn_manage_subscription'):
        self.btn_manage_subscription.visible = "manage_subscription_groups" in self.user_permissions
  
      if hasattr(self, 'btn_manage_webhooks'):
        self.btn_manage_webhooks.visible = "view_webhook_settings" in self.user_permissions
  
      if hasattr(self, 'btn_manage_webhook_retries'):
        self.btn_manage_webhook_retries.visible = "manage_webhook_settings" in self.user_permissions
  
      if hasattr(self, 'btn_tenant_mgt'):
        self.btn_tenant_mgt.visible = self.role_name in ["Owner", "Admin"]
  
      if hasattr(self, 'btn_report_payment_failure'):
        self.btn_report_payment_failure.visible = "view_all_reports" in self.user_permissions
  
      if hasattr(self, 'btn_debug_diagnostics'):
        self.btn_debug_diagnostics.visible = self.role_name in ["Owner", "Admin"]
  
      if hasattr(self, 'btn_update_currency'):
        self.btn_update_currency.visible = "manage_app_settings" in self.user_permissions
  
      if hasattr(self, 'btn_metrics_dashboard'):
        self.btn_metrics_dashboard.visible = "view_all_reports" in self.user_permissions
  
        # Set visibility for all other report and transaction buttons
      view_reports_perm = "view_all_reports" in self.user_permissions
      if hasattr(self, 'btn_report_product_all'): 
        self.btn_report_product_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_product_sales_all'): 
        self.btn_report_product_sales_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_product_sales_single'): 
        self.btn_report_product_sales_single.visible = view_reports_perm
      if hasattr(self, 'btn_product_transaction'): 
        self.btn_product_transaction.visible = view_reports_perm
      if hasattr(self, 'btn_report_service_all'): 
        self.btn_report_service_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_service_sales_all'): 
        self.btn_report_service_sales_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_service_sales_single'): 
        self.btn_report_service_sales_single.visible = view_reports_perm
      if hasattr(self, 'btn_service_transaction'): 
        self.btn_service_transaction.visible = view_reports_perm
      if hasattr(self, 'btn_report_subscription_all'): 
        self.btn_report_subscription_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_subscription_sales_all'): 
        self.btn_report_subscription_sales_all.visible = view_reports_perm
      if hasattr(self, 'btn_report_subscription_sales_single'): 
        self.btn_report_subscription_sales_single.visible = view_reports_perm
      if hasattr(self, 'btn_subs_transaction'): 
        self.btn_subs_transaction.visible = view_reports_perm
  
        # --- Stage 2: Set visibility for container cards based on their contents ---
  
      if hasattr(self, 'crd_manage_people'):
        self.crd_manage_people.visible = self.btn_manage_users.visible
  
      if hasattr(self, 'crd_manage_main'):
        self.crd_manage_main.visible = (self.btn_manage_webhooks.visible or
                                        self.btn_manage_webhook_retries.visible or
                                        self.btn_manage_rbac.visible or
                                        self.btn_tenant_mgt.visible or
                                        self.btn_vault.visible or
                                        self.btn_manage_settings.visible or
                                        self.btn_manage_prices.visible or
                                        self.btn_manage_discounts.visible or
                                        self.btn_update_currency.visible or
                                        self.btn_debug_diagnostics.visible)
  
      if hasattr(self, 'crd_reports_main'):
        self.crd_reports_main.visible = (self.btn_metrics_dashboard.visible or
                                        self.btn_report_payment_failure.visible)
  
      if hasattr(self, 'crd_reports_product'):
        self.crd_reports_product.visible = (self.btn_manage_product.visible or
                                            self.btn_report_product_all.visible or
                                            self.btn_report_product_sales_all.visible or
                                            self.btn_report_product_sales_single.visible or
                                            self.btn_product_transaction.visible)
  
      if hasattr(self, 'crd_reports_service'):
        self.crd_reports_service.visible = (self.btn_manage_service.visible or
                                            self.btn_report_service_all.visible or
                                            self.btn_report_service_sales_all.visible or
                                            self.btn_report_service_sales_single.visible or
                                            self.btn_service_transaction.visible)
  
      if hasattr(self, 'crd_reports_subs'):
        self.crd_reports_subs.visible = (self.btn_manage_subscription.visible or
                                        self.btn_report_subscription_all.visible or
                                        self.btn_report_subscription_sales_all.visible or
                                        self.btn_report_subscription_sales_single.visible or
                                        self.btn_subs_transaction.visible)
  
      log("DEBUG", "paddle_home", "_update_ui_based_on_permissions", "UI visibility updated for all components and containers.")


    def _require_admin_or_owner(self):
      """
            Checks if the user has admin privileges (permanent or temporary).
            If not, prompts for owner password to gain temporary access.
            Returns True if the user ultimately has admin privileges, False otherwise.
            Refreshes UI state if temporary access is granted.
            """
      log("DEBUG", "paddle_home", "_require_admin_or_owner", "Checking admin requirement")
      if not self.user:
        log("WARNING", "paddle_home", "_require_admin_or_owner", "User not logged in, denying access")
        return False
    
      try:
        # Explicitly re-check admin status from server to include temporary session status
        self.is_admin = anvil.server.call('is_admin_user') 
        log("DEBUG", "paddle_home", "_require_admin_or_owner", f"Current admin status from server: {self.is_admin}")
      except Exception as e_is_admin:
        log("ERROR", "paddle_home", "_require_admin_or_owner", f"Error calling is_admin_user: {e_is_admin}")
        self.is_admin = False 
    
      if self.is_admin:
        log("DEBUG", "paddle_home", "_require_admin_or_owner", "User already has admin privileges (permanent or temporary).")
        # Ensure permissions are fresh if they gained temp admin status elsewhere
        try:
          self.user_permissions = set(anvil.server.call('get_user_permissions_for_ui'))
        except Exception: # Default to empty if error
          self.user_permissions = set()
          # self._update_ui_based_on_permissions() # This line has been removed.
        return True
    
      log("INFO", "paddle_home", "_require_admin_or_owner", "User lacks privileges or status check failed, attempting password elevation.")
      session_granted = self._check_owner_password() # This function handles its own logging
    
      if session_granted:
        log("INFO", "paddle_home", "_require_admin_or_owner", "Temp session granted by _check_owner_password.")
        # Re-evaluate admin status and permissions
        try:
          self.is_admin = anvil.server.call('is_admin_user') # Should now be true
          self.user_permissions = set(anvil.server.call('get_user_permissions_for_ui'))
          log("INFO", "paddle_home", "_require_admin_or_owner", f"Post-grant: is_admin={self.is_admin}, permissions fetched.")
        except Exception as e_post_grant:
          log("ERROR", "paddle_home", "_require_admin_or_owner", f"Error fetching status/permissions post temp session grant: {e_post_grant}")
          self.is_admin = True 
          self.user_permissions = set() # Indicate permissions might be unknown
    
          # self._update_ui_based_on_permissions() # This line has been removed.
        return self.is_admin 
      else:
        log("WARNING", "paddle_home", "_require_admin_or_owner", "Password elevation failed or cancelled, access denied.")
        return False

    # ======================
    # Login/Logout Button Handlers
    # ======================

    def btn_login_click(self, **event_args):
      """This method is called when the Login button is clicked."""
      log("INFO", "paddle_home", "btn_login_click", "Login button clicked")
      user = anvil.users.login_with_form()
      if user:
          log("INFO", "paddle_home", "btn_login_click", f"Login successful for {user['email']}")
          self._initialize_form_state() # Re-initialize form
      else:
          log("INFO", "paddle_home", "btn_login_click", "Login cancelled")

    def btn_logout_click(self, **event_args):
      """This method is called when the Logout button is clicked."""
      log("INFO", "paddle_home", "btn_logout_click", "Logout button clicked")
      user_email = self.user['email'] if self.user else "Unknown"
      anvil.users.logout()
      log("INFO", "paddle_home", "btn_logout_click", f"User {user_email} logged out")
      self._initialize_form_state() # Re-initialize form

    # ======================
    # Admin Button Click Handlers
    # ======================

# This is the complete btn_manage_users_click method for paddle_home.py

# This is the complete btn_manage_users_click method for paddle_home.py

    def btn_manage_users_click(self, **event_args):
      """Handles click for Manage Users button."""
      log("INFO", "paddle_home", "btn_manage_users_click", "Button clicked")
      if self._require_admin_or_owner():
        log("INFO", "paddle_home", "btn_manage_users_click", "Access granted, preparing to open manage_users form")
    
        # --- START: ADDED CODE ---
        # Hide the two main content containers for a clean visual transition.
        self.outlined_card_1.visible = False
        self.cp_main.visible = False
        # --- END: ADDED CODE ---
    
        open_form("manage_users")
      else:
        log("INFO", "paddle_home", "btn_manage_users_click", "Access denied")

    def btn_vault_click(self, **event_args):
        """Handles click for Vault button."""
        log("INFO", "paddle_home", "btn_vault_click", "Button clicked")
        if self._require_admin_or_owner():
            log("INFO", "paddle_home", "btn_vault_click", "Access granted, opening vault form")
            open_form("vault")
        else:
            log("INFO", "paddle_home", "btn_vault_click", "Access denied")

    # --- Tenant Management Button Handler (Using open_window) ---
    def btn_tenant_mgt_click(self, **event_args):
        """Handles click for Tenant Management button. Navigates to Hub App."""
        log("INFO", "paddle_home", "btn_tenant_mgt_click", "Button clicked")
        if self._require_admin_or_owner():
            log("INFO", "paddle_home", "btn_tenant_mgt_click", "Admin access verified, navigating to Hub App Tenant Management")
            # Define the URL for the R2Hub App
            hub_app_url = "https://3rds45nhnfnhxqss.anvil.app/SI2JQMLAAD7BHZWB5HXNIW63" # Replace with your actual Hub App URL if different
            try:
                # Use open_window to open the Hub App in a new tab/window
                open_window(hub_app_url) # Imported via anvil.js.window
            except Exception as e:
                log("ERROR", "paddle_home", "btn_tenant_mgt_click", f"Error navigating to Hub App using open_window: {e}")
                alert(f"Could not open Tenant Management form: {e}")
        else:
            # _require_admin_or_owner handles logging/alerts for denial
            log("INFO", "paddle_home", "btn_tenant_mgt_click", "Access denied by _require_admin_or_owner")

    # ======================
    # Other Management Button Handlers
    # ======================

    def btn_manage_settings_click(self, **event_args):
        log("INFO", "paddle_home", "btn_manage_settings_click", "Button clicked")
        # Assuming manage_settings handles its own permissions (admin check added there)
        open_form("manage_settings")

    def btn_manage_product_click(self, **event_args):
        log("INFO", "paddle_home", "btn_manage_product_click", "Button clicked")
        # Add permission checks here if needed, otherwise assume open access
        open_form("manage_product")

    def btn_manage_service_click(self, **event_args):
        log("INFO", "paddle_home", "btn_manage_service_click", "Button clicked")
        open_form("manage_service")

    def btn_manage_subscription_click(self, **event_args):
        log("INFO", "paddle_home", "btn_manage_subscription_click", "Button clicked")
        open_form("manage_subs")

    def btn_manage_prices_click(self, **event_args):
        log("INFO", "paddle_home", "btn_manage_prices_click", "Button clicked")
        open_form("manage_prices")

    def btn_metrics_dashboard_click(self, **event_args):
        log("INFO", "paddle_home", "btn_metrics_dashboard_click", "Button clicked")
        open_form("metrics_dashboard")

    # ======================
    # Report Button Handlers
    # ======================

    def btn_report_product_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_product_all_click", "Button clicked")
        open_form("report_product_all")

    def btn_report_product_sales_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_product_sales_all_click", "Button clicked")
        open_form("report_product_sales_all")

    def btn_report_product_sales_single_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_product_sales_single_click", "Button clicked")
        open_form("report_product_sales_single")

    def btn_report_service_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_service_all_click", "Button clicked")
        open_form("report_service_all")

    def btn_report_service_sales_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_service_sales_all_click", "Button clicked")
        open_form("report_service_sales_all")

    def btn_report_service_sales_single_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_service_sales_single_click", "Button clicked")
        open_form("report_service_sales_single")

    def btn_report_subscription_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_subscription_all_click", "Button clicked")
        open_form("report_subscription_all")

    def btn_report_subscription_sales_all_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_subscription_sales_all_click", "Button clicked")
        open_form("report_subscription_sales_all")

    def btn_report_subscription_sales_single_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_subscription_sales_single_click", "Button clicked")
        open_form("report_subscription_sales_single")

    def btn_report_payment_failure_click(self, **event_args):
        log("INFO", "paddle_home", "btn_report_payment_failure_click", "Button clicked")
        open_form("report_payment_failure")

    # ======================
    # Diagnostics Button Handler
    # ======================

    def btn_debug_diagnostics_click(self, **event_args):
      """Handles click for Diagnostics button."""
      log("INFO", "paddle_home", "btn_debug_diagnostics_click", "Button clicked")
      # Assuming diagnostics are open to all logged-in users for now
      # Add _require_admin_or_owner() check if needed
      if self.user: # Only allow if logged in
          open_form('admin_diagnostics')
      else:
          alert("Please log in to view diagnostics.")

    def btn_site_click(self, **event_args):
      """This method is called when the button is clicked"""
      open_form("home")


    def btn_update_currency_click(self, **event_args):
        """Import currency data from text area into database."""
        log("INFO", "paddle_home", "btn_update_currency_click", "Button clicked")

        try:
            # Define currency data directly in the code with your specific list
            currency_data = """
            Currency,Country
            ARS,Argentine Peso
            AUD,Australian Dollar
            BRL,Brazilian Real
            CAD,Canadian Dollar
            CHF,Swiss Franc
            CNY,Chinese Yuan
            COP,Colombian Peso
            CZK,Czech Koruna
            DKK,Danish Krone
            EUR,Euro
            GBP,Pound Sterling
            HKD,Hong Kong Dollar
            HUF,Hungarian Forint
            ILS,Israeli Shekels
            INR,Indian Rupee
            JPY,Japanese Yen
            KRW,South Korean Won
            MXN,Mexican Pesos
            NOK,Norwegian Krone
            NZD,New Zealand Dollar
            PLN,Polish Zloty
            RUB,Ruble
            SEK,Swedish Krona
            SGD,Singapore Dollar
            THB,Thai Baht
            TRY,Turkish Lira
            TWD,New Taiwan Dollar
            UAH,Ukraine Hryvnia
            USD,US Dollar
            VND,Vietnamese Dong
            ZAR,South African Rand
            """

            # Parse the CSV data from the string
            lines = [line.strip() for line in currency_data.strip().split("\n")]
            # Skip header row
            data_lines = lines[1:]

            # Create separate lists for currency and country
            currency_list = []
            country_list = []

            for line in data_lines:
                if line and "," in line:
                    # Split at the first comma (in case country names contain commas)
                    parts = line.split(",", 1)
                    if len(parts) == 2:
                        currency, country = parts
                        currency_list.append(currency.strip())
                        country_list.append(country.strip())

            log("DEBUG", "paddle_home", "btn_update_currency_click", f"Parsed {len(currency_list)} currency records")

            # Show a loading indicator - Corrected: use 'as _' for unused variable
            with Notification("Importing currency data...", style="info", timeout=None) as _:
                # Call the server function to import from the lists
                result = anvil.server.call('import_currency_from_lists', currency_list, country_list)

            log("INFO", "paddle_home", "btn_update_currency_click", f"Import result: {result}")

            # Show appropriate notification based on result
            if result.startswith("Success"):
                Notification(f"Import successful: {result.split('-')[1].strip()}", style="success", timeout=4).show()
            else:
                alert(f"Currency import failed: {result}")

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            log("ERROR", "paddle_home", "btn_update_currency_click", error_msg)
            alert(error_msg)

    def btn_manage_rbac_click(self, **event_args):
      """This method is called when the button is clicked"""
      open_form('manage_rbac')

