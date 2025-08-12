# Client Form: essential_credentials_status_form.py

from ._anvil_designer import essential_credentials_status_formTemplate
from anvil import *
import anvil.server
from ..cm_logs_helper import log

class essential_credentials_status_form(essential_credentials_status_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    log("INFO", "essential_credentials_status_form", "__init__", "Form initializing")

    if hasattr(self, 'lbl_form_title'):
      self.lbl_form_title.text = "Essential Credentials Status"

    if hasattr(self, 'btn_close'):
      self.btn_close.set_event_handler('click', self.btn_close_click)

    self.load_credential_statuses()
    log("INFO", "essential_credentials_status_form", "__init__", "Form initialization complete")

  def load_credential_statuses(self, **event_args):
    """Fetches credential statuses from the server and updates the UI."""
    log("INFO", "essential_credentials_status_form", "load_credential_statuses", "Loading credential statuses")
    try:
      # This server function will return a dictionary like:
      # {'PADDLE_API_KEY': True, 'paddle_webhook_secret': False, ...}
      # where True means "Set" and False means "Not Set".
      statuses = anvil.server.call('get_essential_credentials_status')
      log("DEBUG", "essential_credentials_status_form", "load_credential_statuses", f"Statuses received: {statuses}")

      # Define a mapping from vault key to UI component prefixes
      # Using your provided component names (adjust if typos were corrected in designer)
      credential_ui_map = {
        "PADDLE_API_KEY": {"label": self.lbl_paddle_api_key, "status_text": self.lbl_paddle_api_key_status_text, "icon": self.img_paddle_api_key_icon},
        "paddle_webhook_secret": {"label": self.lbl_paddle_webhook_secret, "status_text": self.lbl_paddle_webhook_secret_status_text, "icon": self.img_paddle_webhook_secret_icon},
        "paddle_client_token": {"label": self.lbl_paddle_client_token, "status_text": self.lbl_paddle_client_token_status_text, "icon": self.img_paddle_client_token_icon},
        "paddle_seller_id": {"label": self.lbl_paddle_seller_id, "status_text": self.lbl_paddle_seller_id_status_text, "icon": self.img_paddle_seller_id_icon},
        "paddle_webhook_url": {"label": self.lbl_paddle_webhook_url, "status_text": self.lbl_paddle_webhook_url_status_text, "icon": self.img_paddle_webhook_url_icon},
        "paddle_customer_portal_url": {"label": self.lbl_paddle_customer_portal_url, "status_text": self.lbl_paddle_customer_portal_url_ststatus_text, "icon": self.image_customer_portal_icon}, # Typo in UI list: _ststatus_text
        "r2hub_api_endpoint": {"label": self.lbl_r2hub_api_endpoint, "status_text": self.lbl_r2hub_api_endpoint_status_text, "icon": self.img_r2hub_api_endpoint_icon}, # Typo in UI list: r2hub
        "r2hub_tenant_id": {"label": self.lbl_r2hub_tenant_id, "status_text": self.lbl_r2hub_tenant_id_status_text, "icon": self.img_r2hub_tenant_id_icon}, # Typo in UI list: r2hub
        "r2hub_api_key": {"label": self.lbl_r2hub_api_key, "status_text": self.lbl_r2hub_api_key_status_text, "icon": self.img_r2hub_api_key_icon} # Typo in UI list: r2hub
      }

      for key, components in credential_ui_map.items():
        is_set = statuses.get(key, False) # Default to False (Not Set) if key is missing

        if hasattr(components["status_text"], 'text'):
          components["status_text"].text = "Set" if is_set else "Not Set"
          components["status_text"].foreground = "green" if is_set else "red"

        if hasattr(components["icon"], 'source'):
          if is_set:
            components["icon"].source = "fa:check-circle" # Green check
            components["icon"].foreground = "green"
          else:
            components["icon"].source = "fa:times-circle" # Red X
            components["icon"].foreground = "red"

            # Set the main label text (e.g., "Paddle API Key:")
            # This assumes the label text in the designer is just a placeholder or empty.
            # If it's already correct in the designer, this part can be skipped.
            # For example:
            # if hasattr(components["label"], 'text'):
            #    components["label"].text = f"{key.replace('_', ' ').title()}:"


    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}")
      log("ERROR", "essential_credentials_status_form", "load_credential_statuses", f"Permission denied by server: {e}")
    except Exception as e:
      alert(f"An error occurred while loading credential statuses: {e}")
      log("ERROR", "essential_credentials_status_form", "load_credential_statuses", f"Unexpected error: {e}")
      # Optionally clear all status texts/icons on error

  def btn_close_click(self, **event_args):
    """This method is called when the Close button is clicked."""
    log("INFO", "essential_credentials_status_form", "btn_close_click", "Close button clicked")
    # If opened as an alert:
    self.raise_event("x-close-alert", value=True) 
    # If opened by open_form, and needs to navigate back, e.g., to vault:
    # open_form('vault') 

  def btn_update_credentials_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('essential_credentials_form')
