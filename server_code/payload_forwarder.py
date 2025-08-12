import anvil.server
import anvil.secrets
import anvil.http
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables # Needed for checking event existence
from sm_logs_mod import log
# --- Function to Forward Payload to Hub ---
# --- MODIFIED: Import vault and logging ---
from .vault_server import get_secret_for_server_use
from .sessions_server import is_admin_user # Ensure this is imported

# --- END MODIFICATION ---

# --- Constants for R2Hub (ensure these are defined if not already) ---
R2HUB_API_ENDPOINT_VAULT_KEY = "r2hub_api_endpoint"
R2HUB_TENANT_ID_VAULT_KEY = "r2hub_tenant_id"
R2HUB_API_KEY_VAULT_KEY = "r2hub_api_key"


# --- Function to Forward Payload to Hub ---
def forward_payload_to_hub(raw_payload_string, event_id): # event_id is passed from webhook_handler
  """
    Forwards the raw webhook payload to the Central R2 Hub.
    Sends Tenant ID and API Key headers for authentication, retrieved from MyBizz Vault.
    Uses sm_logs_mod for logging.
    """
  module_name = "payload_forwarder" # For logging
  function_name = "forward_payload_to_hub"
  log_context = {"event_id": event_id}

  log("INFO", module_name, function_name, "Attempting to forward payload to Hub.", log_context)
  try:
    # 1. Retrieve Hub URL, Tenant API Key, and Tenant ID from MyBizz Vault
    hub_url_base = get_secret_for_server_use(R2HUB_API_ENDPOINT_VAULT_KEY)
    tenant_id_for_hub = get_secret_for_server_use(R2HUB_TENANT_ID_VAULT_KEY)
    tenant_api_key = get_secret_for_server_use(R2HUB_API_KEY_VAULT_KEY)

    log_context['hub_url_retrieved'] = bool(hub_url_base)
    log_context['tenant_id_for_hub_retrieved'] = bool(tenant_id_for_hub)
    log_context['api_key_for_hub_retrieved'] = bool(tenant_api_key)


    if not all([hub_url_base, tenant_api_key, tenant_id_for_hub]):
      error_msg = "R2Hub forwarding configuration missing in MyBizz Vault (endpoint, tenant ID, or API key)."
      log("ERROR", module_name, function_name, error_msg, log_context)
      return False, error_msg

      # Endpoint path is defined in R2Hub's hub_receiver.py
      # Assuming hub_url_base is the full endpoint URL including /_/api/log_payload
      hub_log_url = hub_url_base
    log("DEBUG", module_name, function_name, f"Using Hub Log URL: {hub_log_url}", log_context)

    # 2. Prepare Request Headers
    headers = {
      'Content-Type': 'application/json',
      'Authorization': f'Bearer {tenant_api_key}',
      'X-Tenant-ID': tenant_id_for_hub
    }
    log_context['request_headers_prepared'] = True

    # 3. Make HTTP POST Request to Hub
    log("DEBUG", module_name, function_name, f"Sending POST to {hub_log_url}", log_context)
    response = anvil.http.request(
      url=hub_log_url,
      method='POST',
      headers=headers,
      data=raw_payload_string, # Send raw string as received
      timeout=30
    )
    log_context['hub_response_status'] = response.get_status()

    # 4. Handle Hub Response
    if 200 <= response.get_status() < 300:
      success_msg = f"Payload forwarded successfully. Hub Status: {response.get_status()}"
      log("INFO", module_name, function_name, success_msg, log_context)
      return True, success_msg
    else:
      try:
        response_body = response.get_bytes().decode('utf-8', errors='replace')
      except Exception:
        response_body = "[Could not decode response body]"
        log_context['hub_response_body'] = response_body
      error_msg = (f"Failed to forward payload. Hub Status: {response.get_status()}. Hub Response: {response_body}")
      log("ERROR", module_name, function_name, error_msg, log_context)
      return False, error_msg

  except anvil.http.HttpError as e:
    log_context['http_error_status'] = e.status
    log_context['http_error_content'] = e.content_bytes.decode('utf-8', errors='replace') if e.content_bytes else "N/A"
    error_msg = f"HTTP Error during forwarding: Status {e.status}."
    log("ERROR", module_name, function_name, error_msg, log_context)
    return False, error_msg
  except Exception as e:
    import traceback
    log_context['exception_type'] = type(e).__name__
    log_context['trace'] = traceback.format_exc()
    error_msg = f"Unexpected error during forwarding: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, log_context)
    return False, error_msg


# --- Function to Request Payload from Hub ---
@anvil.server.callable # Removed require_user=True, check is now explicit
def request_payload_from_hub(event_id):
  """
    Requests a specific raw payload from the Central R2 Hub for display.
    Authenticates using credentials from MyBizz Vault.
    Requires Admin/Owner level privileges (checked by is_admin_user()).
    Uses sm_logs_mod for logging.
    """
  module_name = "payload_forwarder"
  function_name = "request_payload_from_hub"
  user = anvil.users.get_user() # Get user for logging and permission check
  user_email_for_log = user['email'] if user else "Unknown/Not Logged In"
  log_context = {"requested_event_id": event_id, "requesting_user_email": user_email_for_log}

  # Perform permission check at the beginning of the function
  if not is_admin_user():
    log("WARNING", module_name, function_name, "Permission denied to request payload from hub.", log_context)
    raise anvil.server.PermissionDenied("Administrator privileges required to retrieve raw payloads.")

    log("INFO", module_name, function_name, "Requesting payload from Hub (permission granted).", log_context)

  # Optional: Check if event_id exists in local log first, as per original code
  # log_entry = tables.app_tables.webhook_log.get(event_id=event_id)
  # if not log_entry:
  #     error_msg = f"Event ID {event_id} not found in local webhook_log."
  #     log("WARNING", module_name, function_name, error_msg, log_context)
  #     raise anvil.server.NoServerFunctionError(error_msg) # Or return a specific error message

  try:
    # 1. Retrieve Hub URL, Tenant API Key, and Tenant ID from MyBizz Vault
    hub_url_base = get_secret_for_server_use(R2HUB_API_ENDPOINT_VAULT_KEY)
    tenant_id_for_hub = get_secret_for_server_use(R2HUB_TENANT_ID_VAULT_KEY)
    tenant_api_key = get_secret_for_server_use(R2HUB_API_KEY_VAULT_KEY)

    log_context['hub_url_base_retrieved'] = bool(hub_url_base)
    log_context['tenant_id_for_hub_retrieved'] = bool(tenant_id_for_hub)
    log_context['api_key_for_hub_retrieved'] = bool(tenant_api_key)

    if not all([hub_url_base, tenant_api_key, tenant_id_for_hub]):
      error_msg = "R2Hub retrieval configuration missing in MyBizz Vault."
      log("ERROR", module_name, function_name, error_msg, log_context)
      # Raise a more specific error that client can potentially handle or just a generic one
      raise Exception("Server configuration error: Hub connection details missing.")

      # Construct the specific endpoint URL for retrieval (from R2Hub's hub_receiver.py)
      get_endpoint_path = f'/_/api/get_payload/{event_id}'
    # Ensure hub_url_base doesn't have trailing slash if get_endpoint_path starts with one
    if hub_url_base.endswith('/') and get_endpoint_path.startswith('/'):
      hub_get_url = f"{hub_url_base.rstrip('/')}{get_endpoint_path}"
    elif not hub_url_base.endswith('/') and not get_endpoint_path.startswith('/'):
      hub_get_url = f"{hub_url_base}/{get_endpoint_path}"
    else:
      hub_get_url = f"{hub_url_base}{get_endpoint_path}"

      log("DEBUG", module_name, function_name, f"Using Hub Get URL: {hub_get_url}", log_context)

    # 2. Prepare Request Headers
    headers = {
      'Authorization': f'Bearer {tenant_api_key}',
      'X-Tenant-ID': tenant_id_for_hub
    }
    log_context['request_headers_prepared'] = True

    # 3. Make HTTP GET Request to Hub
    log("DEBUG", module_name, function_name, f"Sending GET to {hub_get_url}", log_context)
    response = anvil.http.request(
      url=hub_get_url,
      method='GET',
      headers=headers,
      timeout=30
    )
    log_context['hub_response_status_for_get'] = response.get_status()

    # 4. Handle Hub Response
    # anvil.http.request raises HttpError for non-2xx, so if we get here, status is 2xx
    payload_bytes = response.get_bytes()
    try:
      payload_string = payload_bytes.decode('utf-8')
      log("INFO", module_name, function_name, "Successfully retrieved payload from Hub.", log_context)
      return payload_string
    except UnicodeDecodeError as e:
      error_msg = f"Failed to decode Hub response: {str(e)}"
      log("ERROR", module_name, function_name, error_msg, {**log_context, "decode_error": str(e)})
      # Raise an exception that the client can understand or handle
      raise Exception(f"Received payload for {event_id}, but failed to decode it.")

  except anvil.http.HttpError as e:
    log_context['http_error_status'] = e.status
    error_body = e.content_bytes.decode('utf-8', errors='replace') if e.content_bytes else f"HTTP Error {e.status}"
    log_context['http_error_content'] = error_body
    log("ERROR", module_name, function_name, f"Hub returned HTTP error: Status {e.status}", log_context)
    raise e # Re-raise to be caught by client if needed
  except anvil.server.NoServerFunctionError as e: # If local log check (if reinstated) fails
    log("WARNING", module_name, function_name, str(e), log_context)
    raise e
  except anvil.server.PermissionDenied as e: # Catch permission denied from our check
    # Already logged, just re-raise
    raise e
  except Exception as e:
    import traceback
    log_context['exception_type'] = type(e).__name__
    log_context['trace'] = traceback.format_exc()
    error_msg = f"Unexpected error retrieving payload: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, log_context)
    # Raise a generic exception or a specific one if the client needs to distinguish
    raise Exception(f"An unexpected error occurred while retrieving payload for {event_id}.")

@anvil.server.background_task
def forward_payload_to_hub_background(log_row_id, raw_payload_string):
  module_name = "payload_forwarder_task" 
  function_name = "forward_payload_to_hub_background"
  log_context = {"mybizz_webhook_log_id": log_row_id}
  log("INFO", module_name, function_name, "Background task started.", log_context)

  log_row = None
  try:
    # ... (rest of the try block as previously provided and corrected) ...
    log_row = app_tables.webhook_log.get_by_id(log_row_id)
    if not log_row:
      log("CRITICAL", module_name, function_name, "Webhook log row not found by ID. Cannot proceed.", log_context)
      return

    event_id = log_row['event_id']
    log_context['event_id'] = event_id

    success, message = forward_payload_to_hub(raw_payload_string, event_id)

    log_context['forwarding_success'] = success
    log_context['forwarding_message'] = message

    with anvil.server.Transaction(): 
      log_row_to_update = app_tables.webhook_log.get_by_id(log_row_id)
      if not log_row_to_update:
        log("CRITICAL", module_name, function_name, "Webhook log row disappeared before update. Critical error.", log_context)
        return

      log_row_to_update['forwarded_to_hub'] = success
      current_details = log_row_to_update['processing_details'] or ""
      separator = " | " if current_details else ""
      log_row_to_update['processing_details'] = f"{current_details}{separator}Forwarding to R2Hub: {message}"

      if success:
        if 'Error' not in (log_row_to_update['status'] or ""):
          log_row_to_update['status'] = 'Forwarded to Hub'
      else:
        log_row_to_update['status'] = 'Forwarding Error'

    log("INFO", module_name, function_name, "Background task finished.", log_context)

  except Exception as e:
    # 'traceback' is now defined due to the import at the top of the file
    error_details = f"Unexpected error in background task: {str(e)}"
    log("CRITICAL", module_name, function_name, error_details, {**log_context, "trace": traceback.format_exc()})
    if log_row_id: 
      try:
        with anvil.server.Transaction():
          log_row_to_update_on_error = app_tables.webhook_log.get_by_id(log_row_id)
          if log_row_to_update_on_error:
            log_row_to_update_on_error['status'] = 'Forwarding Task Error'
            current_details_on_error = log_row_to_update_on_error['processing_details'] or ""
            separator_on_error = " | " if current_details_on_error else ""
            log_row_to_update_on_error['processing_details'] = f"{current_details_on_error}{separator_on_error}{error_details[:900]}" 
            log_row_to_update_on_error['forwarded_to_hub'] = False
      except Exception as db_update_err:
        log("CRITICAL", module_name, function_name, f"Failed to update log_row with background task error: {db_update_err}", log_context)