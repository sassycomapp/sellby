# Client Item Template: manage_webhook_retries_item.py

from ._anvil_designer import manage_webhook_retries_itemTemplate
from anvil import *
import anvil.server
from ...cm_logs_helper import log # Adjusted path assuming cm_logs_helper is two levels up

class manage_webhook_retries_item(manage_webhook_retries_itemTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.module_name = "manage_webhook_retries_item"
    # self.item is a dictionary representing a row from app_tables.webhook_log
    # Expected keys: 'event_id', 'event_type', 'received_at', 'status', 
    #                'retry_count', 'last_retry_timestamp', 'processing_details', 
    #                and the Anvil row ID (implicitly available via self.item.get_id() if self.item is a Row,
    #                or needs to be passed explicitly if self.item is just a dict from server).
    # For simplicity, assuming server sends dicts that include an 'anvil_id' or similar.

    if self.item:
      self.lbl_event_id.text = self.item.get('event_id', 'N/A')
      # Using lbl_event_type as per your image, though lbl_event_type is more standard
      self.lbl_event_type.text = self.item.get('event_type', 'N/A')

      received_at_dt = self.item.get('received_at')
      if received_at_dt and hasattr(received_at_dt, 'strftime'):
        self.lbl_received_at.text = received_at_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
      elif received_at_dt:
        self.lbl_received_at.text = str(received_at_dt)
      else:
        self.lbl_received_at.text = 'N/A'

      self.lbl_current_status.text = self.item.get('status', 'N/A')

      # Corrected component name from your image: lbl_retry_count to lbl_retry_count
      self.lbl_retry_count.text = str(self.item.get('retry_count', 0)) 

      last_retried_dt = self.item.get('last_retry_timestamp') # Assuming this key from server
      if last_retried_dt and hasattr(last_retried_dt, 'strftime'):
        self.lbl_last_retried.text = last_retried_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
      elif last_retried_dt:
        self.lbl_last_retried.text = str(last_retried_dt)
      else:
        self.lbl_last_retried.text = 'Never'

      self.lbl_processing_details.text = self.item.get('processing_details', '')
      # Truncate long processing details if necessary for UI
      if len(self.lbl_processing_details.text) > 150: # Example length
        self.lbl_processing_details.text = self.lbl_processing_details.text[:147] + "..."
        self.lbl_processing_details.tooltip = self.item.get('processing_details', '')


        # Enable/Disable rerun button based on status (optional, parent might also control)
        # Example: Disable if "Max Retries Reached" or "Resolved"
        # current_status = self.item.get('status', '').lower()
        # self.btn_rerun.enabled = not ("max retries" in current_status or "resolved" in current_status)

    else:
      # Fallback if self.item is None
      self.lbl_event_id.text = "No Data"
      self.lbl_event_type.text = ""
      self.lbl_received_at.text = ""
      self.lbl_current_status.text = ""
      self.lbl_retry_count.text = ""
      self.lbl_last_retried.text = ""
      self.lbl_processing_details.text = ""
      self.btn_rerun.enabled = False
      self.btn_clear.enabled = False

      # Add a button to view raw payload (not in your image, but discussed)
      # If you add a btn_view_payload_item to the item template designer:
      # self.btn_view_payload_item.set_event_handler('click', self.btn_view_payload_item_click)


  def btn_rerun_click(self, **event_args):
    """This method is called when the Rerun button is clicked."""
    # Get the Anvil ID of the webhook_log row.
    # This assumes the server function 'get_webhook_logs_for_retry_ui' includes
    # the Anvil row ID in each dictionary it returns, e.g., as 'anvil_id'.
    webhook_log_anvil_id = self.item.get('anvil_id') # Or self.item.get_id() if self.item is a Row

    if webhook_log_anvil_id:
      log("DEBUG", self.module_name, "btn_rerun_click", f"Rerun clicked for log Anvil ID: {webhook_log_anvil_id}")
      self.parent.raise_event('x_attempt_reprocess', webhook_log_anvil_id=webhook_log_anvil_id)
    else:
      log("WARNING", self.module_name, "btn_rerun_click", "Cannot rerun: Anvil ID missing from item.", {"item_data": self.item})
      alert("Cannot rerun: Log item identifier is missing.")

  def btn_clear_click(self, **event_args):
    """This method is called when the Clear button is clicked."""
    webhook_log_anvil_id = self.item.get('anvil_id') # Or self.item.get_id()

    if webhook_log_anvil_id:
      log("DEBUG", self.module_name, "btn_clear_click", f"Clear clicked for log Anvil ID: {webhook_log_anvil_id}")
      self.parent.raise_event('x_clear_item', webhook_log_anvil_id=webhook_log_anvil_id)
    else:
      log("WARNING", self.module_name, "btn_clear_click", "Cannot clear: Anvil ID missing from item.", {"item_data": self.item})
      alert("Cannot clear: Log item identifier is missing.")

    # If you add a "View Payload" button to the item template:
    # def btn_view_payload_item_click(self, **event_args):
    #     """Handles click for viewing raw payload for this specific item."""
    #     event_id_for_payload = self.item.get('event_id')
    #     if event_id_for_payload:
    #         log("DEBUG", self.module_name, "btn_view_payload_item_click", f"View payload clicked for event_id: {event_id_for_payload}")
    #         self.parent.raise_event('x_view_payload', event_id_for_payload=event_id_for_payload)
    #     else:
    #         log("WARNING", self.module_name, "btn_view_payload_item_click", "Cannot view payload: event_id missing from item.", {"item_data": self.item})
    #         alert("Cannot view payload: Event ID is missing for this item.")from ._anvil_designer import manage_webhook_retries_itemTemplate
