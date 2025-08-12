# Server Module: payload_retry.py

import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import json
from datetime import datetime, timezone
import traceback # Ensure traceback is imported

# Assuming these modules are in the same directory or accessible via Python's import path
from .sm_logs_mod import log
from .sessions_server import is_admin_user # For permission checks
from .payload_forwarder import request_payload_from_hub # To fetch payload from R2Hub
# Import the _process_... functions from webhook_handler.py
from .webhook_handler import _process_transaction, _process_subscription, _process_product, _process_price, _process_customer, _process_discount


@anvil.server.callable(require_user=True)
def get_webhook_logs_for_retry_ui(status_filter=None):
    """
    Fetches webhook logs for the retry management UI, applying optional status filter.
    Returns a list of dictionaries, each including the Anvil row ID.
    """
    module_name = "payload_retry"
    function_name = "get_webhook_logs_for_retry_ui"
    
    if not is_admin_user():
        log("WARNING", module_name, function_name, "Permission denied to view webhook logs for retry.")
        raise anvil.server.PermissionDenied("Admin privileges required.")

    log("INFO", module_name, function_name, "Fetching webhook logs for retry UI.", {"status_filter": status_filter})

    query_conditions = []
    if status_filter:
        query_conditions.append(app_tables.webhook_log.status == status_filter)
    else:  # "All Actionable"
        actionable_statuses = [
            "Pending Retry - Missing Link",
            "Max Retries Reached - Manual Review",
            "Forwarding Task Error",
            "MyBizz Processing Error",
            "R2Hub Forwarding Error",
            "Reprocess Error - R2Hub Fetch Failed", # Added this status
            "Reprocess Failed - MyBizz Logic",    # Added this status
            "Reprocess Error - JSON",             # Added this status
            "Reprocess Error - Unexpected",       # Added this status
            "Reprocess Error - Trigger Failed"    # Added this status
        ]
        query_conditions.append(app_tables.webhook_log.status.any_of(*actionable_statuses))

    try:
        log_rows = app_tables.webhook_log.search(
            *query_conditions,
            order_by=tables.order_by("received_at", ascending=False)
        )
        
        results = []
        for row in log_rows:
            results.append({
                'anvil_id': row.get_id(),
                'event_id': row['event_id'],
                'event_type': row['event_type'],
                'received_at': row['received_at'],
                'status': row['status'],
                'retry_count': row.get('retry_count', 0),
                'last_retry_timestamp': row.get('last_retry_timestamp'),
                'processing_details': row['processing_details']
            })
        log("INFO", module_name, function_name, f"Retrieved {len(results)} log entries.", {"status_filter": status_filter})
        return results
    except Exception as e:
        log("ERROR", module_name, function_name, "Error fetching webhook logs for retry UI.", {"error": str(e), "trace": traceback.format_exc()})
        raise anvil.server.AnvilWrappedError(f"Could not retrieve webhook logs: {str(e)}")


def _reprocess_single_webhook(log_row, raw_payload_string):
    """
    Internal helper to re-process a single webhook payload.
    Updates the log_row based on success/failure.
    """
    module_name = "payload_retry"
    function_name = "_reprocess_single_webhook"
    event_id = log_row['event_id']
    event_type = log_row['event_type']
    log_context = {"webhook_log_id": log_row.get_id(), "event_id": event_id, "event_type": event_type, "mode": "reprocessing"}
    log("INFO", module_name, function_name, "Starting reprocessing attempt.", log_context)

    try:
        payload = json.loads(raw_payload_string)
        data_payload = payload.get('data', {})

        processing_success = False
        processing_details_reprocess = "Event type not handled during reprocess."

        if event_type.startswith('transaction.'):
            processing_success, processing_details_reprocess = _process_transaction(data_payload)
        elif event_type.startswith('subscription.'):
            processing_success, processing_details_reprocess = _process_subscription(data_payload)
        elif event_type.startswith('product.'):
            processing_success, processing_details_reprocess = _process_product(data_payload)
        elif event_type.startswith('price.'):
            processing_success, processing_details_reprocess = _process_price(data_payload)
        elif event_type.startswith('customer.'):
            processing_success, processing_details_reprocess = _process_customer(data_payload)
        elif event_type.startswith('discount.'):
            processing_success, processing_details_reprocess = _process_discount(data_payload)
        # Add other _process_... functions if they exist in webhook_handler.py
        else:
            processing_success = True 
            processing_details_reprocess = f"No specific MyBizz reprocessing logic for event type: {event_type}"

        with anvil.server.Transaction():
            log_row_to_update = app_tables.webhook_log.get_by_id(log_row.get_id())
            if log_row_to_update:
                log_row_to_update['status'] = 'Processed via Retry' if processing_success else 'Reprocess Failed - MyBizz Logic'
                current_details = log_row_to_update['processing_details'] or ""
                separator = " | " if current_details else ""
                log_row_to_update['processing_details'] = f"{current_details}{separator}Reprocess attempt ({datetime.now(timezone.utc).isoformat()}): {processing_details_reprocess}"
                log_row_to_update['last_retry_timestamp'] = datetime.now(timezone.utc)
            else:
                log("CRITICAL", module_name, function_name, "Log row disappeared during reprocessing update.", log_context)
                return False, "Critical error: Log row missing during update."
        
        return processing_success, processing_details_reprocess

    except json.JSONDecodeError as e:
        error_msg = f"JSON parsing failed during reprocess: {str(e)}"
        log("ERROR", module_name, function_name, error_msg, log_context)
        try:
            with anvil.server.Transaction():
                log_row_to_update_err = app_tables.webhook_log.get_by_id(log_row.get_id())
                if log_row_to_update_err:
                    log_row_to_update_err['status'] = 'Reprocess Error - JSON'
                    log_row_to_update_err['processing_details'] = f"{log_row_to_update_err['processing_details'] or ''} | Reprocess JSON Error: {error_msg}"
                    log_row_to_update_err['last_retry_timestamp'] = datetime.now(timezone.utc)
        except Exception: 
          pass
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error in _reprocess_single_webhook: {str(e)}"
        log("ERROR", module_name, function_name, error_msg, {**log_context, "trace": traceback.format_exc()})
        try:
            with anvil.server.Transaction():
                log_row_to_update_err = app_tables.webhook_log.get_by_id(log_row.get_id())
                if log_row_to_update_err:
                    log_row_to_update_err['status'] = 'Reprocess Error - Unexpected'
                    log_row_to_update_err['processing_details'] = f"{log_row_to_update_err['processing_details'] or ''} | Reprocess Unexpected Error: {error_msg[:200]}"
                    log_row_to_update_err['last_retry_timestamp'] = datetime.now(timezone.utc)
        except Exception: 
          pass
        return False, error_msg


@anvil.server.callable(require_user=True)
def trigger_reprocess_webhook_log(webhook_log_anvil_id):
    """
    Manually triggers the reprocessing of a single webhook log entry.
    """
    module_name = "payload_retry"
    function_name = "trigger_reprocess_webhook_log"
    
    if not is_admin_user():
        log("WARNING", module_name, function_name, "Permission denied to trigger webhook reprocess.")
        raise anvil.server.PermissionDenied("Admin privileges required.")

    log_context = {"webhook_log_anvil_id": webhook_log_anvil_id, "triggered_by_user": anvil.users.get_user()['email']}
    log("INFO", module_name, function_name, "Manual trigger to reprocess webhook log.", log_context)

    if not webhook_log_anvil_id:
        log("WARNING", module_name, function_name, "No webhook_log_anvil_id provided.", log_context)
        return "Error: No log entry ID provided."

    log_row = app_tables.webhook_log.get_by_id(webhook_log_anvil_id)
    if not log_row:
        log("ERROR", module_name, function_name, "Webhook log entry not found.", log_context)
        return f"Error: Log entry with ID {webhook_log_anvil_id} not found."

    event_id = log_row['event_id']
    log_context['event_id'] = event_id

    try:
        raw_payload_string = request_payload_from_hub(event_id) 

        if raw_payload_string is None:
            log("ERROR", module_name, function_name, "Failed to fetch payload from R2Hub for reprocessing.", log_context)
            log_row.update(
                status="Reprocess Error - R2Hub Fetch Failed",
                processing_details=f"{log_row['processing_details'] or ''} | Manual Reprocess: R2Hub payload fetch failed at {datetime.now(timezone.utc).isoformat()}"
            )
            return "Error: Failed to fetch payload from R2Hub. Cannot reprocess."

        success, message = _reprocess_single_webhook(log_row, raw_payload_string)
        
        log("INFO", module_name, function_name, f"Manual reprocessing result: {success} - {message}", log_context)
        return message 

    except Exception as e:
        error_msg = f"Unexpected error during manual reprocess trigger: {str(e)}"
        log("ERROR", module_name, function_name, error_msg, {**log_context, "trace": traceback.format_exc()})
        try:
            if log_row: # Check if log_row was fetched before error
                log_row.update(
                    status="Reprocess Error - Trigger Failed",
                    processing_details=f"{log_row['processing_details'] or ''} | Manual Reprocess Trigger Error: {error_msg[:200]}"
                )
        except Exception: 
          pass 
        return f"Error: {error_msg}"


@anvil.server.callable(require_user=True)
def mark_webhook_log_resolved(webhook_log_anvil_id):
    """
    Marks a webhook log entry as resolved or ignored by an admin.
    """
    module_name = "payload_retry"
    function_name = "mark_webhook_log_resolved"

    if not is_admin_user():
        log("WARNING", module_name, function_name, "Permission denied to mark webhook log resolved.")
        raise anvil.server.PermissionDenied("Admin privileges required.")

    log_context = {"webhook_log_anvil_id": webhook_log_anvil_id, "resolved_by_user": anvil.users.get_user()['email']}
    log("INFO", module_name, function_name, "Attempting to mark webhook log as resolved.", log_context)

    if not webhook_log_anvil_id:
        log("WARNING", module_name, function_name, "No webhook_log_anvil_id provided.", log_context)
        return "Error: No log entry ID provided."

    log_row = app_tables.webhook_log.get_by_id(webhook_log_anvil_id)
    if not log_row:
        log("ERROR", module_name, function_name, "Webhook log entry not found.", log_context)
        return f"Error: Log entry with ID {webhook_log_anvil_id} not found."

    try:
        user_email = anvil.users.get_user()['email'] 
        new_status = "Resolved by Admin"
        log_row.update(
            status=new_status,
            processing_details=f"{log_row['processing_details'] or ''} | Marked as '{new_status}' by {user_email} at {datetime.now(timezone.utc).isoformat()}"
        )
        log("INFO", module_name, function_name, f"Webhook log {webhook_log_anvil_id} marked as '{new_status}'.", log_context)
        return f"Log entry {log_row['event_id']} marked as '{new_status}'."
    except Exception as e:
        error_msg = f"Error marking log as resolved: {str(e)}"
        log("ERROR", module_name, function_name, error_msg, {**log_context, "trace": traceback.format_exc()})
        return f"Error: {error_msg}"

@anvil.server.callable
@anvil.server.background_task
def reprocess_deferred_webhooks():
    """
    Scheduled task to attempt reprocessing of webhook logs that are pending retry.
    """
    module_name = "payload_retry"
    function_name = "reprocess_deferred_webhooks_task"
    log("INFO", module_name, function_name, "Scheduled task started: Reprocessing deferred webhooks.")

    MAX_RETRIES = 5 
    retry_statuses = [
        "Pending Retry - Missing Link", 
        "Reprocess Failed - MyBizz Logic", 
        "Reprocess Error - R2Hub Fetch Failed",
        "Reprocess Error - JSON",
        "Reprocess Error - Unexpected",
        "Reprocess Error - Trigger Failed" # If manual trigger failed, task might pick it up
    ] 

    logs_to_retry = app_tables.webhook_log.search(
        status=q.any_of(*retry_statuses),
        retry_count=q.less_than(MAX_RETRIES) # Ensure retry_count field exists in webhook_log
    )

    reprocessed_count = 0
    failed_reprocess_count = 0

    for log_row in logs_to_retry:
        event_id = log_row['event_id']
        current_retry_count = log_row.get('retry_count', 0)
        log_context_item = {"webhook_log_id": log_row.get_id(), "event_id": event_id, "current_retry_count": current_retry_count}

        # Max retries check already done by search query, but double check for safety
        if current_retry_count >= MAX_RETRIES:
            if log_row['status'] != "Max Retries Reached - Manual Review":
                log_row.update(status="Max Retries Reached - Manual Review", last_retry_timestamp=datetime.now(timezone.utc))
            continue

        log("INFO", module_name, function_name, "Attempting to reprocess item via scheduled task.", log_context_item)
        
        try:
            raw_payload_string = request_payload_from_hub(event_id)

            if raw_payload_string is None:
                log("WARNING", module_name, function_name, "Failed to fetch payload from R2Hub for scheduled reprocessing.", log_context_item)
                with anvil.server.Transaction():
                    log_row_to_update_fetch_fail = app_tables.webhook_log.get_by_id(log_row.get_id())
                    if log_row_to_update_fetch_fail:
                        log_row_to_update_fetch_fail['status'] = "Reprocess Error - R2Hub Fetch Failed"
                        log_row_to_update_fetch_fail['retry_count'] = current_retry_count + 1
                        log_row_to_update_fetch_fail['last_retry_timestamp'] = datetime.now(timezone.utc)
                        log_row_to_update_fetch_fail['processing_details'] = f"{log_row_to_update_fetch_fail['processing_details'] or ''} | Scheduled Reprocess: R2Hub payload fetch failed."
                        if log_row_to_update_fetch_fail['retry_count'] >= MAX_RETRIES:
                            log_row_to_update_fetch_fail['status'] = "Max Retries Reached - Manual Review"
                failed_reprocess_count += 1
                continue

            success, message = _reprocess_single_webhook(log_row, raw_payload_string)

            if success:
                reprocessed_count += 1
                log("INFO", module_name, function_name, f"Successfully reprocessed: {message}", log_context_item)
            else:
                failed_reprocess_count += 1
                log("WARNING", module_name, function_name, f"Failed to reprocess: {message}", log_context_item)
                with anvil.server.Transaction(): # Ensure retry count is updated even if _reprocess_single_webhook updated status
                    log_row_to_update_retry = app_tables.webhook_log.get_by_id(log_row.get_id())
                    if log_row_to_update_retry:
                        log_row_to_update_retry['retry_count'] = current_retry_count + 1
                        log_row_to_update_retry['last_retry_timestamp'] = datetime.now(timezone.utc)
                        if log_row_to_update_retry['retry_count'] >= MAX_RETRIES and "Error" in log_row_to_update_retry['status']: # Only set to Max Retries if still in an error state
                            log_row_to_update_retry['status'] = "Max Retries Reached - Manual Review"
                    else:
                        log("CRITICAL", module_name, function_name, "Log row disappeared during retry count update.", log_context_item)

        except Exception as e_task_item:
            failed_reprocess_count += 1
            log("ERROR", module_name, function_name, f"Unexpected error reprocessing item in scheduled task: {str(e_task_item)}", 
                {**log_context_item, "trace": traceback.format_exc()})
            try:
                with anvil.server.Transaction():
                    log_row_to_update_task_err = app_tables.webhook_log.get_by_id(log_row.get_id())
                    if log_row_to_update_task_err:
                        log_row_to_update_task_err['status'] = "Reprocess Error - Task Exception"
                        log_row_to_update_task_err['processing_details'] = f"{log_row_to_update_task_err['processing_details'] or ''} | Task Exception: {str(e_task_item)[:200]}"
                        log_row_to_update_task_err['retry_count'] = current_retry_count + 1
                        log_row_to_update_task_err['last_retry_timestamp'] = datetime.now(timezone.utc)
                        if log_row_to_update_task_err['retry_count'] >= MAX_RETRIES:
                             log_row_to_update_task_err['status'] = "Max Retries Reached - Manual Review"
            except Exception: 
              pass

    log("INFO", module_name, function_name, f"Scheduled task finished. Successfully reprocessed: {reprocessed_count}. Failed attempts: {failed_reprocess_count}.")

