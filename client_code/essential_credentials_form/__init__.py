# Client Form: essential_credentials_form.py

from ._anvil_designer import essential_credentials_formTemplate
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Assuming cm_logs_helper is in the parent directory

class essential_credentials_form(essential_credentials_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    log("INFO", "essential_credentials_form", "__init__", "Form initializing")

    # --- Configure UI Elements ---
    if hasattr(self, 'lbl_popup_title'): 
      self.lbl_popup_title.text = "Set Essential Application Credentials"

    if hasattr(self, 'tb_paddle_api_key'):
      self.tb_paddle_api_key.hide_text = True
    if hasattr(self, 'tb_paddle_webhook_secret'):
      self.tb_paddle_webhook_secret.hide_text = True
    if hasattr(self, 'tb_paddle_client_token'):
      self.tb_paddle_client_token.hide_text = True
    if hasattr(self, 'tb_r2hub_api_key'):
      self.tb_r2hub_api_key.hide_text = True

    if hasattr(self, 'btn_save_credentials'):
      self.btn_save_credentials.text = "Save All Credentials"
      self.btn_save_credentials.set_event_handler('click', self.btn_save_credentials_click)

      # Configure btn_close_popup as the primary modal closer
    if hasattr(self, 'btn_close_popup'): 
      self.btn_close_popup.text = "Close" 
      self.btn_close_popup.visible = True 
      self.btn_close_popup.set_event_handler('click', self.btn_close_popup_click)

      # If btn_cancel exists and should also close the modal, or be hidden
    if hasattr(self, 'btn_cancel'):
      if self.btn_cancel is not self.btn_close_popup: # If it's a different button instance
        # Option 1: Make btn_cancel also close the modal
        # self.btn_cancel.text = "Cancel"
        # self.btn_cancel.set_event_handler('click', self.btn_close_popup_click) # Reuse handler
        # self.btn_cancel.visible = True

        # Option 2: Hide btn_cancel if btn_close_popup is the sole closer
        self.btn_cancel.visible = False
        # If btn_cancel IS btn_close_popup (same instance), it's already configured.

    if hasattr(self, 'lbl_feedback'):
      self.lbl_feedback.text = ""
      self.lbl_feedback.foreground = "" 


    if hasattr(self, 'btn_close_popup'): 
      self.btn_close_popup.text = "Close" 
      self.btn_close_popup.set_event_handler('click', self.btn_close_popup_click)

    log("INFO", "essential_credentials_form", "__init__", "Form initialization complete")

    # Handler for cancel/close button
  def btn_cancel_click(self, **event_args):
    """This method is called when the Cancel or Close button is clicked."""
    log("INFO", "essential_credentials_form", "btn_cancel_click", "Cancel button clicked")
    # If this form is opened as an alert, this will close it.
    # Pass a value (e.g., False or None) to indicate cancellation if needed by the caller.
    self.raise_event("x-close-alert", value=False) 

  def btn_save_credentials_click(self, **event_args):
    """This method is called when the Save All Credentials button is clicked."""
    log("INFO", "essential_credentials_form", "btn_save_credentials_click", "Save button clicked")
    self.lbl_feedback.text = ""
    self.lbl_feedback.foreground = ""

    # --- Collect Data ---
    credentials = {
      "PADDLE_API_KEY": self.tb_paddle_api_key.text.strip() if hasattr(self, 'tb_paddle_api_key') else None,
      "paddle_webhook_secret": self.tb_paddle_webhook_secret.text.strip() if hasattr(self, 'tb_paddle_webhook_secret') else None,
      "paddle_client_token": self.tb_paddle_client_token.text.strip() if hasattr(self, 'tb_paddle_client_token') else None,
      "paddle_seller_id": self.tb_paddle_seller_id.text.strip() if hasattr(self, 'tb_paddle_seller_id') else None,
      "paddle_customer_portal_url": self.tb_paddle_customer_portal_url.text.strip() if hasattr(self, 'tb_paddle_customer_portal_url') else None,
      "r2hub_api_endpoint": self.tb_r2hub_api_endpoint.text.strip() if hasattr(self, 'tb_r2hub_api_endpoint') else None,
      "r2hub_tenant_id": self.tb_r2hub_tenant_id.text.strip() if hasattr(self, 'tb_r2hub_tenant_id') else None,
      "r2hub_api_key": self.tb_r2hub_api_key.text.strip() if hasattr(self, 'tb_r2hub_api_key') else None,
    }

    # --- Client-Side Validation (Basic) ---
    required_fields_map = {
      "PADDLE_API_KEY": "Paddle API Key",
      "paddle_webhook_secret": "Paddle Webhook Secret",
      "paddle_seller_id": "Paddle Seller ID",
      "r2hub_api_endpoint": "R2Hub API Endpoint URL",
      "r2hub_tenant_id": "R2Hub Tenant ID",
      "r2hub_api_key": "R2Hub API Key",
      # paddle_client_token is often optional, paddle_customer_portal_url is optional
    }

    missing_fields = []
    for key, display_name in required_fields_map.items():
      if not credentials.get(key): # Checks for None or empty string after strip()
        missing_fields.append(display_name)

    if missing_fields:
      self.lbl_feedback.text = f"Please provide: {', '.join(missing_fields)}."
      self.lbl_feedback.foreground = "red"
      log("WARNING", "essential_credentials_form", "btn_save_credentials_click", f"Validation failed, missing fields: {missing_fields}")
      return

      # --- Call Server Function ---
    self.lbl_feedback.text = "Saving credentials..."
    log("DEBUG", "essential_credentials_form", "btn_save_credentials_click", "Calling server 'save_multiple_secrets'")

    try:
      # Prepare data for server: list of dicts [{key, value, scope, description}, ...]
      # Descriptions are from initialize_tenant.txt
      secrets_to_save = [
        {"key": "PADDLE_API_KEY", "value": credentials["PADDLE_API_KEY"], "scope": "Paddle", "description": "Live Paddle API Key for server-to-server calls."},
        {"key": "paddle_webhook_secret", "value": credentials["paddle_webhook_secret"], "scope": "Paddle", "description": "Paddle Webhook Signing Secret."},
        {"key": "paddle_client_token", "value": credentials["paddle_client_token"], "scope": "Paddle", "description": "Paddle Client-Side Token (Public Key)."},
        {"key": "paddle_seller_id", "value": credentials["paddle_seller_id"], "scope": "Paddle", "description": "Paddle Vendor/Seller ID."},
        {"key": "r2hub_api_endpoint", "value": credentials["r2hub_api_endpoint"], "scope": "R2Hub", "description": "API endpoint URL for R2Hub logging."},
        {"key": "r2hub_tenant_id", "value": credentials["r2hub_tenant_id"], "scope": "R2Hub", "description": "Tenant ID for R2Hub."},
        {"key": "r2hub_api_key", "value": credentials["r2hub_api_key"], "scope": "R2Hub", "description": "API Key for R2Hub authentication."}
      ]
      # Add optional field if provided
      if credentials["paddle_customer_portal_url"]:
        secrets_to_save.append(
          {"key": "paddle_customer_portal_url", "value": credentials["paddle_customer_portal_url"], "scope": "Paddle", "description": "Paddle Customer Portal Link."}
        )

        # We need a server function that can save multiple secrets.
        # Let's assume `vault_server.py` will have `save_multiple_secrets(secrets_list)`
      anvil.server.call('save_multiple_secrets', secrets_to_save)

      self.lbl_feedback.text = "Credentials saved successfully!"
      self.lbl_feedback.foreground = "green"
      log("INFO", "essential_credentials_form", "btn_save_credentials_click", "Credentials saved successfully by server.")

      # Optionally, close the form on success if it's a modal
      # self.raise_event("x-close-alert", value=True) 
      # Or disable save button to prevent resubmission
      self.btn_save_credentials.enabled = False

    except anvil.server.PermissionDenied as e:
      self.lbl_feedback.text = f"Save Failed: {e}"
      self.lbl_feedback.foreground = "red"
      log("ERROR", "essential_credentials_form", "btn_save_credentials_click", f"Permission denied by server: {e}")
    except ValueError as e: # Catch validation errors from server
      self.lbl_feedback.text = f"Save Failed: {e}"
      self.lbl_feedback.foreground = "red"
      log("ERROR", "essential_credentials_form", "btn_save_credentials_click", f"Validation error from server: {e}")
    except Exception as e:
      self.lbl_feedback.text = f"An unexpected error occurred: {e}"
      self.lbl_feedback.foreground = "red"
      log("CRITICAL", "essential_credentials_form", "btn_save_credentials_click", f"Unexpected exception: {e}")

    # In essential_credentials_form.py

  def btn_close_popup_click(self, **event_args):
      """This method is called when btn_close_popup is clicked. 
           Navigates back to the status form."""
      log("INFO", "essential_credentials_form", "btn_close_popup_click", "Close button clicked, navigating to essential_credentials_status_form.")
      open_form('essential_credentials_status_form')
