# Client Form: manage_webhook_retries.py

from ._anvil_designer import manage_webhook_retriesTemplate
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Assuming path to client logger
from .manage_webhook_retries_item import manage_webhook_retries_item # Import the new item template
from ..payload_viewer_dialog import payload_viewer_dialog # For viewing raw payload

class manage_webhook_retries(manage_webhook_retriesTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "manage_webhook_retries"
    log("INFO", self.module_name, "__init__", "Form initializing.")

    # Configure RepeatingPanel
    self.rp_waiting_payloads.item_template = manage_webhook_retries_item
    # Event handlers raised from the item template
    self.rp_waiting_payloads.set_event_handler('x_attempt_reprocess', self.handle_attempt_reprocess_event)
    self.rp_waiting_payloads.set_event_handler('x_clear_item', self.handle_clear_item_event)
    self.rp_waiting_payloads.set_event_handler('x_view_payload', self.handle_view_payload_event)

    # Populate Filter Dropdown
    self.dd_filter_by_status.items = [
      ("All Actionable", None), 
      ("Pending Retry - Missing Link", "Pending Retry - Missing Link"),
      ("Max Retries - Manual Review", "Max Retries Reached - Manual Review"),
      ("Forwarding Task Error", "Forwarding Task Error"),
      ("MyBizz Processing Error", "MyBizz Processing Error"),
      ("R2Hub Forwarding Error", "R2Hub Forwarding Error")
    ]
    self.dd_filter_by_status.selected_value = None # Default to "All Actionable"

    # Set event handlers for form controls
    self.dd_filter_by_status.set_event_handler('change', self.dd_filter_by_status_change)
    self.btn_refresh.set_event_handler('click', self.btn_refresh_click)

    # Add Home button navigation if navbar_links is used for that
    if hasattr(self.navbar_links, 'btn_home'): # Example if you add a home button to navbar_links
      self.navbar_links.btn_home.set_event_handler('click', self.go_home)


      # Load initial data
    self.load_webhook_logs()
    log("INFO", self.module_name, "__init__", "Form initialization complete.")

  def load_webhook_logs(self, **event_args):
    """Loads webhook logs based on the selected filter."""
    selected_status_filter = self.dd_filter_by_status.selected_value
    log_context = {"status_filter": selected_status_filter}
    log("INFO", self.module_name, "load_webhook_logs", "Loading webhook logs for retry UI.", log_context)

    self.btn_refresh.enabled = False
    self.btn_refresh.icon = 'fa:spinner'
    self.btn_refresh.text = 'Loading...'

    try:
      # Server function needs to handle status_filter=None for "All Actionable"
      log_entries = anvil.server.call('get_webhook_logs_for_retry_ui', status_filter=selected_status_filter)
      self.rp_waiting_payloads.items = log_entries
      log("INFO", self.module_name, "load_webhook_logs", f"Displayed {len(log_entries)} log entries.", log_context)
    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}", title="Access Denied")
      log("WARNING", self.module_name, "load_webhook_logs", f"Permission denied: {e}", log_context)
      self.rp_waiting_payloads.items = []
    except Exception as e:
      alert(f"An error occurred while loading webhook logs: {e}", title="Error")
      log("ERROR", self.module_name, "load_webhook_logs", f"Error: {e}", {**log_context, "trace": str(e)}) # Basic trace
      self.rp_waiting_payloads.items = []
    finally:
      self.btn_refresh.enabled = True
      self.btn_refresh.icon = 'fa:refresh'
      self.btn_refresh.text = 'Refresh List'

  def dd_filter_by_status_change(self, **event_args):
    """Handles filter change and reloads the list."""
    self.load_webhook_logs()

  def btn_refresh_click(self, **event_args):
    """Handles refresh button click."""
    self.load_webhook_logs()

    # --- Event Handlers from Item Template ---
  def handle_attempt_reprocess_event(self, webhook_log_anvil_id, **event_args):
    """Handles the x_attempt_reprocess event from the item template."""
    log_context = {"webhook_log_anvil_id": webhook_log_anvil_id}
    log("INFO", self.module_name, "handle_attempt_reprocess_event", "Attempting to reprocess item.", log_context)
    try:
      with Notification("Attempting to reprocess webhook...", style="info", timeout=2):
        result_message = anvil.server.call('trigger_reprocess_webhook_log', webhook_log_anvil_id)
      alert(result_message, title="Reprocess Attempt")
      log("INFO", self.module_name, "handle_attempt_reprocess_event", f"Server response: {result_message}", log_context)
      self.load_webhook_logs() # Refresh the list
    except Exception as e:
      alert(f"Error triggering reprocess: {e}", title="Error")
      log("ERROR", self.module_name, "handle_attempt_reprocess_event", f"Error: {e}", log_context)

  def handle_clear_item_event(self, webhook_log_anvil_id, **event_args):
    """Handles the x_clear_item event (mark as resolved/ignored)."""
    log_context = {"webhook_log_anvil_id": webhook_log_anvil_id}
    log("INFO", self.module_name, "handle_clear_item_event", "Attempting to mark item as resolved/cleared.", log_context)

    if confirm("Are you sure you want to mark this item as resolved/cleared from the active retry list?"):
      try:
        with Notification("Updating item status...", style="info", timeout=2):
          result_message = anvil.server.call('mark_webhook_log_resolved', webhook_log_anvil_id)
        Notification(result_message, style="success").show() # Show success from server
        log("INFO", self.module_name, "handle_clear_item_event", f"Server response: {result_message}", log_context)
        self.load_webhook_logs() # Refresh the list
      except Exception as e:
        alert(f"Error marking item as resolved: {e}", title="Error")
        log("ERROR", self.module_name, "handle_clear_item_event", f"Error: {e}", log_context)
    else:
      log("INFO", self.module_name, "handle_clear_item_event", "User cancelled clear action.", log_context)

  def handle_view_payload_event(self, event_id_for_payload, **event_args):
    """Handles the x_view_payload event to show raw payload."""
    log_context = {"event_id_for_payload": event_id_for_payload}
    log("INFO", self.module_name, "handle_view_payload_event", "Requesting to view raw payload.", log_context)
    if not event_id_for_payload:
      alert("Event ID is missing for this log entry. Cannot view payload.")
      return

    try:
      with Notification("Fetching payload from R2Hub...", style="info", timeout=None) as n:
        payload_string = anvil.server.call('request_payload_from_hub', event_id_for_payload)

      if payload_string is not None: # Check for None explicitly, as empty string is a valid payload
        alert(
          content=payload_viewer_dialog(payload_string=payload_string, event_id=event_id_for_payload),
          title=f"Raw Payload: {event_id_for_payload}",
          large=True,
          buttons=[]
        )
        log("INFO", self.module_name, "handle_view_payload_event", "Payload displayed.", log_context)
      else:
        alert(f"Payload for event '{event_id_for_payload}' not found in R2Hub or could not be retrieved.", title="Payload Not Found")
        log("WARNING", self.module_name, "handle_view_payload_event", "Server returned no payload.", log_context)
    except anvil.http.HttpError as e:
      alert(f"Failed to retrieve payload from R2Hub for event '{event_id_for_payload}':\nStatus {e.status} - {e.content}", title="R2Hub Error")
      log("ERROR", self.module_name, "handle_view_payload_event", f"R2Hub HTTP Error: {e.status} - {e.content}", log_context)
    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}", title="Access Denied")
      log("WARNING", self.module_name, "handle_view_payload_event", f"Permission denied: {e}", log_context)
    except Exception as e:
      alert(f"An unexpected error occurred while fetching payload for event '{event_id_for_payload}':\n{e}", title="Error")
      log("ERROR", self.module_name, "handle_view_payload_event", f"Unexpected error: {e}", log_context)

  def go_home(self, **event_args):
    """Navigates to the main dashboard or home form."""
    log("INFO", self.module_name, "go_home", "Navigating to paddle_home.")
    open_form('paddle_home') # Or your main admin dashboard form name