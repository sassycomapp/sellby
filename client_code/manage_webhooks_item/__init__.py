# Client Module: manage_webhooks_item.py

from ._anvil_designer import manage_webhooks_itemTemplate # Ensure this matches your Anvil template name
from anvil import *
import anvil.server
from ..cm_logs_helper import log # Assuming path to client logger
from ..payload_viewer_dialog import payload_viewer_dialog # Assuming path

class manage_webhooks_item(manage_webhooks_itemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "manage_webhooks_item"

    # self.item will be a dictionary representing a row from app_tables.webhook_log
    if self.item:
      # Populate Event ID
      if hasattr(self, 'lbl_event_id_display'):
        self.lbl_event_id_display.text = self.item.get('event_id', 'N/A')

      # Populate Event Type
      if hasattr(self, 'lbl_event_type_display'):
        self.lbl_event_type_display.text = self.item.get('event_type', 'N/A')

      # Populate Received At
      if hasattr(self, 'lbl_received_at_display'):
        received_at_dt = self.item.get('received_at')
        if received_at_dt and hasattr(received_at_dt, 'strftime'):
          self.lbl_received_at_display.text = received_at_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
        elif received_at_dt:
          self.lbl_received_at_display.text = str(received_at_dt) # Fallback
        else:
          self.lbl_received_at_display.text = 'N/A'

      # Populate MyBizz Status
      if hasattr(self, 'lbl_mybizz_status_display'):
        self.lbl_mybizz_status_display.text = self.item.get('status', 'N/A')

      # Populate R2Hub Forward Status
      if hasattr(self, 'lbl_r2hub_forward_status_display'):
        forwarded = self.item.get('forwarded_to_hub')
        status = self.item.get('status', '').lower()
        if forwarded is True:
          self.lbl_r2hub_forward_status_display.text = "Forwarded to Hub"
          self.lbl_r2hub_forward_status_display.foreground = "green"
        elif "forwarding error" in status or "r2hub error" in status : # Check for specific error status
          self.lbl_r2hub_forward_status_display.text = "Forwarding Error"
          self.lbl_r2hub_forward_status_display.foreground = "red"
        elif forwarded is False and "processed" in status : # Processed but not forwarded (implies an issue)
          self.lbl_r2hub_forward_status_display.text = "Not Forwarded"
          self.lbl_r2hub_forward_status_display.foreground = "orange"
        elif forwarded is False :
          self.lbl_r2hub_forward_status_display.text = "Pending/Failed"
          self.lbl_r2hub_forward_status_display.foreground = "orange"
        else: # Default or unknown
          self.lbl_r2hub_forward_status_display.text = "Unknown"
          self.lbl_r2hub_forward_status_display.foreground = ""


      # Configure "Verify/Retry Hub" button visibility/enabled state
      if hasattr(self, 'btn_verify_or_retry_hub_status'):
        # Enable if not successfully forwarded or if there was a forwarding error
        can_retry = (forwarded is False) or ("forwarding error" in status) or ("r2hub error" in status)
        self.btn_verify_or_retry_hub_status.enabled = can_retry
        self.btn_verify_or_retry_hub_status.visible = True # Always visible, but enabled conditionally

    else: # Fallback if self.item is None
      if hasattr(self, 'lbl_event_id_display'): 
        self.lbl_event_id_display.text = "No Data"
      # Clear other labels as well...
      if hasattr(self, 'btn_view_payload_from_hub'): 
        self.btn_view_payload_from_hub.enabled = False
      if hasattr(self, 'btn_verify_or_retry_hub_status'): 
        self.btn_verify_or_retry_hub_status.enabled = False


  def btn_view_payload_from_hub_click(self, **event_args):
    """This method is called when the View Payload button is clicked."""
    event_id = self.item.get('event_id')
    if not event_id:
      alert("Event ID is missing for this log entry.")
      return

    log("INFO", self.module_name, "btn_view_payload_from_hub_click", f"Requesting payload for event_id: {event_id}")
    try:
      # Show a notification while fetching
      # MODIFIED: Removed 'as n' as n is not used
      with Notification("Fetching payload from R2Hub...", style="info", timeout=None): 
        payload_string = anvil.server.call('request_payload_from_hub', event_id)

      if payload_string:
        # Ensure payload_viewer_dialog is imported
        alert(
          content=payload_viewer_dialog(payload_string=payload_string, event_id=event_id),
          title=f"Raw Payload: {event_id}",
          large=True,
          buttons=[] 
        )
        log("INFO", self.module_name, "btn_view_payload_from_hub_click", f"Payload displayed for event_id: {event_id}")
      else:
        alert(f"Payload for event '{event_id}' not found in R2Hub or could not be retrieved.", title="Payload Not Found")
        log("WARNING", self.module_name, "btn_view_payload_from_hub_click", f"Server returned no payload for event_id: {event_id}")

    except anvil.http.HttpError as e:
      alert(f"Failed to retrieve payload from R2Hub for event '{event_id}':\nStatus {e.status} - {e.content}", title="R2Hub Error")
      log("ERROR", self.module_name, "btn_view_payload_from_hub_click", f"R2Hub HTTP Error for event_id {event_id}: {e.status} - {e.content}")
    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}", title="Access Denied")
      log("WARNING", self.module_name, "btn_view_payload_from_hub_click", f"Permission denied for event_id {event_id}: {e}")
    except Exception as e:
      alert(f"An unexpected error occurred while fetching payload for event '{event_id}':\n{e}", title="Error")
      log("ERROR", self.module_name, "btn_view_payload_from_hub_click", f"Unexpected error for event_id {event_id}: {e}")

  def btn_verify_or_retry_hub_status_click(self, **event_args):
    """This method is called when the Verify/Retry Hub button is clicked."""
    log_row_anvil_id = self.item.get_id() # Get the Anvil Row ID of the webhook_log entry
    event_id = self.item.get('event_id')

    if not log_row_anvil_id:
      alert("Log entry ID is missing. Cannot proceed.")
      return

    log("INFO", self.module_name, "btn_verify_or_retry_hub_status_click", f"Initiating Verify/Retry for log_id: {log_row_anvil_id}, event_id: {event_id}")
    try:
      # Show a notification
      Notification(f"Attempting to verify/retry forwarding for event {event_id}...", style="info").show()

      # Server function will check R2Hub and update MyBizz log if needed.
      # It might also re-trigger forwarding if appropriate and payload is available to it.
      result_message = anvil.server.call('resend_or_verify_payload_with_hub', log_row_anvil_id)

      alert(result_message, title="Hub Status Update")
      log("INFO", self.module_name, "btn_verify_or_retry_hub_status_click", f"Server response for log_id {log_row_anvil_id}: {result_message}")

      # Refresh the parent repeating panel to show updated status
      if self.parent:
        self.parent.raise_event('x-refresh-log-list')

    except anvil.server.PermissionDenied as e:
      alert(f"Permission Denied: {e}", title="Access Denied")
      log("WARNING", self.module_name, "btn_verify_or_retry_hub_status_click", f"Permission denied for log_id {log_row_anvil_id}: {e}")
    except Exception as e:
      alert(f"An error occurred during Verify/Retry for event '{event_id}':\n{e}", title="Error")
      log("ERROR", self.module_name, "btn_verify_or_retry_hub_status_click", f"Error for log_id {log_row_anvil_id}: {e}")