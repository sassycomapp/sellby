# Server Module: webhook_handler.py (Tenant App)
from sm_logs_mod import log
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.secrets
import hmac
import hashlib
import json
from datetime import datetime, timezone
import dateutil.parser # For parsing ISO 8601 dates from Paddle
from .vault_server import get_secret_for_server_use # Ensure this import is present
from datetime import timedelta # Ensure timedelta is imported
# Import the actual forwarding function
from .payload_forwarder import forward_payload_to_hub
import anvil.users as users
import traceback


# --- Constants (if not already defined at the top of your file, add/verify them) ---
# Key used by Tenants to store their Paddle Webhook Signing Secret in the vault
PADDLE_WEBHOOK_SECRET_VAULT_KEY = "paddle_webhook_secret"
# Tolerance for webhook timestamp verification (e.g., 5 minutes)
WEBHOOK_TIMESTAMP_TOLERANCE = timedelta(minutes=5)


# --- Helper Function: Get Linked Row ---
def _get_linked_row(target_table_name, paddle_id):
    """Fetches a row from a target table based on paddle_id. Returns None if not found."""
    if not paddle_id:
        return None
    try:
        target_table = getattr(app_tables, target_table_name)
        return target_table.get(paddle_id=paddle_id)
    except AttributeError:
        print(f"Warning: Linked table '{target_table_name}' not found.")
        return None
    except Exception as e:
        print(f"Warning: Error fetching linked row from '{target_table_name}' for id '{paddle_id}': {e}")
        return None

# --- Helper Function: Parse Datetime ---
def _parse_datetime(datetime_string):
    """Parses ISO 8601 datetime strings, returns None if invalid or empty."""
    if not datetime_string:
        return None
    try:
        # Use dateutil.parser for robust ISO 8601 parsing
        return dateutil.parser.isoparse(datetime_string)
    except (ValueError, TypeError) as e:
        print(f"Warning: Could not parse datetime string '{datetime_string}': {e}")
        return None

# --- Processing Functions for Specific Resources ---

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file) ...

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file, including)
# from .sm_logs_mod import log
# from anvil import tables
# from datetime import datetime, timezone
# import dateutil.parser # If not already imported for _parse_datetime

def _process_transaction(data):
  """
    Processes transaction.* webhooks.
    Creates/updates the 'transaction' table row in MyBizz.
    Crucially, now also creates/updates related 'transaction_items' rows.
    Includes logic to populate the 'failed_transactions' table if applicable.
    """
  module_name = "webhook_handler"
  function_name = "_process_transaction"
  paddle_transaction_id = data.get('id')
  event_type_from_payload = data.get("event_type", "transaction_event") # For logging
  transaction_status_from_payload = data.get('status', '').lower()

  log_context = {
    "paddle_transaction_id": paddle_transaction_id,
    "event_type_from_payload": event_type_from_payload,
    "transaction_status_from_payload": transaction_status_from_payload
  }

  if not paddle_transaction_id:
    log("ERROR", module_name, function_name, "Missing data.id (paddle_transaction_id) in transaction payload.", log_context)
    return False, "Missing paddle_transaction_id in transaction payload"

  log("INFO", module_name, function_name, "Processing transaction payload.", log_context)

  try: # Main try block for the function's core logic
    # Ensure parent transaction row exists or is created first
    transaction_table = app_tables.transaction
    mybizz_transaction_row = transaction_table.get(paddle_id=paddle_transaction_id)
    current_time_anvil = datetime.now(timezone.utc)

    # Prepare data for the main transaction record
    details_data = data.get('details', {})
    totals_data = details_data.get('totals', {})

    update_data_main_txn = {
      'paddle_id': paddle_transaction_id,
      'status': data.get('status'),
      'customer_id': _get_linked_row('customer', data.get('customer_id')),
      'subscription_id': _get_linked_row('subs', data.get('subscription_id')), 
      'invoice_id': data.get('invoice_id'),
      'invoice_number': data.get('invoice_number'),
      'currency_code': data.get('currency_code'),
      'origin': data.get('origin'),
      'collection_mode': data.get('collection_mode'),
      'billed_at': _parse_datetime(data.get('billed_at')),
      'paddle_created_at': _parse_datetime(data.get('created_at')),
      'paddle_updated_at': _parse_datetime(data.get('updated_at')),
      'custom_data': data.get('custom_data'), 
      'checkout_url': data.get('checkout', {}).get('url'),
      'details_totals_subtotal': totals_data.get('subtotal'),
      'details_totals_tax': totals_data.get('tax'),
      'details_totals_discount': totals_data.get('discount'),
      'details_totals_total': totals_data.get('total'),
      'details_totals_credit': totals_data.get('credit'),
      'details_totals_balance': totals_data.get('balance'),
      'details_totals_grand_total': totals_data.get('grand_total'),
      'details_totals_fee': totals_data.get('fee'),
      'details_totals_earnings': totals_data.get('earnings'),
      'discount_id': _get_linked_row('discount', data.get('discount', {}).get('id')), 
      'address_id': _get_linked_row('address', data.get('billing_details', {}).get('address', {}).get('id')), 
      'occurred_at': _parse_datetime(data.get('occurred_at') or data.get('created_at')),
    }
    if update_data_main_txn.get('customer_id') and update_data_main_txn['customer_id'].get('user_id'):
      update_data_main_txn['user_id'] = update_data_main_txn['customer_id']['user_id'] 
    else:
      update_data_main_txn['user_id'] = None

    update_data_main_txn['business_id'] = _get_linked_row('business', data.get('business_id')) 

    final_update_data_main_txn = {'paddle_id': paddle_transaction_id}
    nullable_fields_main_txn = [
      'subscription_id', 'invoice_id', 'invoice_number', 'discount_id',
      'address_id', 'business_id', 'checkout_url', 'billed_at', 'occurred_at',
      'user_id', 'custom_data', 'collection_mode', 'origin', 'currency_code',
      'details_totals_subtotal', 'details_totals_tax', 'details_totals_discount',
      'details_totals_total', 'details_totals_credit', 'details_totals_balance',
      'details_totals_grand_total', 'details_totals_fee', 'details_totals_earnings'
    ]
    for k, v in update_data_main_txn.items():
      if k == 'paddle_id': 
        continue
      if v is not None:
        final_update_data_main_txn[k] = v
      elif k in nullable_fields_main_txn:
        final_update_data_main_txn[k] = None

    mybizz_transaction_anvil_pk = None 

    if mybizz_transaction_row:
      mybizz_transaction_anvil_pk = mybizz_transaction_row['transaction_id']
      log("INFO", module_name, function_name, f"Updating existing MyBizz transaction: {mybizz_transaction_anvil_pk}", log_context)
      final_update_data_main_txn['updated_at_anvil'] = current_time_anvil
      mybizz_transaction_row.update(**final_update_data_main_txn)
    else:
      log("INFO", module_name, function_name, "Creating new MyBizz transaction.", log_context)
      final_update_data_main_txn['created_at_anvil'] = current_time_anvil
      final_update_data_main_txn['updated_at_anvil'] = current_time_anvil
      timestamp_str = current_time_anvil.strftime("%Y%m%d%H%M%S%f")
      anvil_transaction_id_pk = f"TRN-{timestamp_str}-{paddle_transaction_id[:8]}"
      while app_tables.transaction.get(transaction_id=anvil_transaction_id_pk):
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") 
        anvil_transaction_id_pk = f"TRN-{timestamp_str}-{paddle_transaction_id[:8]}"
      final_update_data_main_txn['transaction_id'] = anvil_transaction_id_pk
      mybizz_transaction_anvil_pk = anvil_transaction_id_pk

      mybizz_transaction_row = transaction_table.add_row(**final_update_data_main_txn) 

    log_context['mybizz_transaction_id'] = mybizz_transaction_anvil_pk

    # --- Process Transaction Line Items ---
    paddle_line_items_data = data.get('items', []) 
    if not paddle_line_items_data and details_data: 
      paddle_line_items_data = details_data.get('line_items', [])

    if paddle_line_items_data:
      log("INFO", module_name, function_name, f"Processing {len(paddle_line_items_data)} line item(s) for transaction {paddle_transaction_id}.", log_context)
      transaction_items_table = app_tables.transaction_items

      for line_item_payload in paddle_line_items_data:
        paddle_line_item_id = line_item_payload.get('id') 

        if not paddle_line_item_id:
          log("WARNING", module_name, function_name, "Skipping a line item due to missing Paddle Line Item ID.", {**log_context, "line_item_payload": line_item_payload})
          continue

        line_item_log_context = {**log_context, "paddle_line_item_id": paddle_line_item_id}

        paddle_price_id_from_line = line_item_payload.get('price', {}).get('id')
        mybizz_price_row = None
        if paddle_price_id_from_line:
          mybizz_price_row = app_tables.prices.get(paddle_price_id=paddle_price_id_from_line)
          if not mybizz_price_row:
            log("WARNING", module_name, function_name, f"MyBizz 'prices' row not found for paddle_price_id '{paddle_price_id_from_line}' from line item. Line item will not be linked to a MyBizz price.", line_item_log_context)
        else:
          log("WARNING", module_name, function_name, "Paddle Price ID missing from line item payload. Cannot link to MyBizz price.", line_item_log_context)

        proration_data = line_item_payload.get('proration', {})
        line_item_totals_data = line_item_payload.get('totals', {})

        update_data_line_item = {
          'paddle_id': paddle_line_item_id, 
          'transaction_id': mybizz_transaction_row, 
          'price_id': mybizz_price_row, 
          'quantity': line_item_payload.get('quantity'),
          'proration_rate': proration_data.get('rate'),
          'proration_billing_period_starts_at': _parse_datetime(proration_data.get('billing_period', {}).get('starts_at')),
          'proration_billing_period_ends_at': _parse_datetime(proration_data.get('billing_period', {}).get('ends_at')),
          'totals_subtotal': line_item_totals_data.get('subtotal'),
          'totals_tax': line_item_totals_data.get('tax'),
          'totals_discount': line_item_totals_data.get('discount'),
          'totals_total': line_item_totals_data.get('total'),
        }

        final_update_data_line_item = {'paddle_id': paddle_line_item_id}
        nullable_fields_line_item = list(update_data_line_item.keys()) 
        for k, v in update_data_line_item.items():
          if k == 'paddle_id': 
            continue
          if v is not None:
            final_update_data_line_item[k] = v
          elif k in nullable_fields_line_item:
            final_update_data_line_item[k] = None

        existing_txn_item_row = transaction_items_table.get(paddle_id=paddle_line_item_id, transaction_id=mybizz_transaction_row)

        if existing_txn_item_row:
          log("INFO", module_name, function_name, f"Updating existing transaction_item: {paddle_line_item_id}", line_item_log_context)
          final_update_data_line_item['updated_at_anvil'] = current_time_anvil
          existing_txn_item_row.update(**final_update_data_line_item)
        else:
          log("INFO", module_name, function_name, f"Creating new transaction_item: {paddle_line_item_id}", line_item_log_context)
          final_update_data_line_item['created_at_anvil'] = current_time_anvil
          final_update_data_line_item['updated_at_anvil'] = current_time_anvil
          transaction_items_table.add_row(**final_update_data_line_item)
    else:
      log("INFO", module_name, function_name, f"No line items found in payload for transaction {paddle_transaction_id}.", log_context)

      # --- Logic for Failed Transactions ---
    if transaction_status_from_payload in ['failed', 'payment_failed', 'declined']:
      log("INFO", module_name, function_name, f"Transaction status '{transaction_status_from_payload}' indicates failure. Logging to failed_transactions table.", log_context)
      failed_tx_table = app_tables.failed_transactions
      existing_failed_entry = failed_tx_table.get(paddle_transaction_id=paddle_transaction_id)

      paddle_failure_reason = data.get('payment_attempt', {}).get('error_code') or \
      data.get('decline_reason') or \
      data.get('error', {}).get('detail') or \
      data.get('error_message') or \
      "Reason not specified in webhook"

      customer_linked_row = final_update_data_main_txn.get('customer_id')

      failed_data = {
        'paddle_transaction_id': paddle_transaction_id,
        'failure_reason_paddle': str(paddle_failure_reason)[:990] if paddle_failure_reason else "N/A",
        'mybizz_failure_reason': str(paddle_failure_reason)[:990] if paddle_failure_reason else "N/A",
        'failed_at': final_update_data_main_txn.get('occurred_at') or final_update_data_main_txn.get('paddle_updated_at') or current_time_anvil,
        'email': customer_linked_row['email'] if customer_linked_row else data.get('customer',{}).get('email'),
        'first_name': customer_linked_row['first_name'] if customer_linked_row else None,
        'last_name': customer_linked_row['last_name'] if customer_linked_row else None,
        'paddle_customer_id': customer_linked_row['paddle_id'] if customer_linked_row else data.get('customer_id'),
        'status': 'Logged', 
        'created_at_anvil': current_time_anvil 
      }

      if paddle_line_items_data:
        summary_parts = [f"{item.get('quantity',1)} x {item.get('price',{}).get('description','Unknown Item')}" for item in paddle_line_items_data]
        failed_data['attempted_items_summary'] = "; ".join(summary_parts)[:990]
      else:
        failed_data['attempted_items_summary'] = "No items detailed in webhook"

      if existing_failed_entry:
        log("INFO", module_name, function_name, "Updating existing entry in failed_transactions.", log_context)
        existing_failed_entry.update(**failed_data)
      else:
        log("INFO", module_name, function_name, "Creating new entry in failed_transactions.", log_context)
        timestamp_ft_str = current_time_anvil.strftime("%Y%m%d%H%M%S%f")
        failed_transaction_pk = f"FTX-{timestamp_ft_str}-{paddle_transaction_id[:8]}"
        while failed_tx_table.get(failed_transaction_id=failed_transaction_pk):
          timestamp_ft_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") 
          failed_transaction_pk = f"FTX-{timestamp_ft_str}-{paddle_transaction_id[:8]}"
        failed_data['failed_transaction_id'] = failed_transaction_pk
        failed_tx_table.add_row(**failed_data)

    log("INFO", module_name, function_name, "Transaction and its items processed successfully.", log_context)
    return True, "Transaction and its items processed successfully."

  except Exception as e:
    error_msg = f"Error processing transaction: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg

def _process_subscription(data):
  """
    Processes subscription.created/updated/paused/resumed/canceled webhooks.
    Creates/updates the 'subs' table row in MyBizz.
    Assumes 'glt' is in the custom_data of the primary Paddle Price in the webhook.
    """
  module_name = "webhook_handler"
  function_name = "_process_subscription"
  paddle_subscription_id = data.get('id')
  log_context = {"paddle_subscription_id": paddle_subscription_id, "event_type": data.get("event_type", "subscription_event")}

  if not paddle_subscription_id:
    log("ERROR", module_name, function_name, "Missing data.id in subscription payload.", log_context)
    return False, "Missing data.id in subscription payload"

    log("INFO", module_name, function_name, "Processing subscription payload.", log_context)

  try:
    # 1. Identify the core MyBizz Plan (items row)
    mybizz_item_row = None
    subscription_group_row = None
    glt_value = None
    level_num_parsed = None
    tier_num_parsed = None

    if data.get('items') and isinstance(data['items'], list) and len(data['items']) > 0:
      # Assume the first item in the array represents the primary plan
      primary_line_item = data['items'][0]
      price_data = primary_line_item.get('price', {})
      paddle_price_id = price_data.get('id')
      log_context['primary_paddle_price_id'] = paddle_price_id

      if paddle_price_id:
        # Attempt to get 'glt' from custom_data of the price in the webhook
        # Paddle's webhook structure for subscription items:
        # "items": [ { "price": { "id": "pri_...", "custom_data": {"glt": "G1L1T1"} }, ... } ]
        price_custom_data = price_data.get('custom_data', {})
        glt_value = price_custom_data.get('glt')
        log_context['glt_from_price_custom_data'] = glt_value

        if glt_value:
          mybizz_item_row = tables.app_tables.items.get(glt=glt_value, item_type='subscription_plan')
          if mybizz_item_row:
            log("INFO", module_name, function_name, f"Found MyBizz item row by GLT '{glt_value}'.", log_context)
            subscription_group_row = mybizz_item_row.get('subscription_group_id')
            # Parse G, L, T from GLT string (e.g., G1L2T3)
            try:
              if 'L' in glt_value and 'T' in glt_value:
                level_part = glt_value.split('L')[1].split('T')[0]
                tier_part = glt_value.split('T')[1]
                level_num_parsed = f"L{level_part}" # Store as L1, L2, L3
                tier_num_parsed = f"T{tier_part}"   # Store as T1, T2, T3
            except IndexError:
              log("WARNING", module_name, function_name, f"Could not parse Level/Tier from GLT '{glt_value}'.", log_context)
          else:
            log("ERROR", module_name, function_name, f"MyBizz item (plan definition) not found for GLT '{glt_value}'. Critical data mismatch.", log_context)
            # This is a significant issue, implies a plan subscribed to in Paddle doesn't exist in MyBizz.
            # Depending on policy, could return False or try to proceed with limited data.
            # For now, we'll proceed but item_id link will be None.
        else:
          log("WARNING", module_name, function_name, "GLT not found in custom_data of primary price in webhook. Cannot link to MyBizz item.", log_context)
          # TODO: Optional: Implement fallback to call Paddle GET /prices/{price_id} if GLT not in webhook
      else:
        log("WARNING", module_name, function_name, "Primary line item in subscription webhook does not contain a price ID.", log_context)
    else:
      log("WARNING", module_name, function_name, "Subscription webhook payload does not contain 'items' array or it's empty.", log_context)

      # 2. Prepare data for 'subs' table
      subs_table = tables.app_tables.subs
    subs_row = subs_table.get(paddle_id=paddle_subscription_id)

    # Map data from Paddle payload to subs table columns
    update_data = {
      'paddle_id': paddle_subscription_id,
      'status': data.get('status'), # This is Paddle's subscription status
      'customer_id': _get_linked_row('customer', data.get('customer_id')),
      'address_id': _get_linked_row('address', data.get('address_id')),
      'discount_id': _get_linked_row('discount', data.get('discount_id')),
      # 'currency_code': data.get('currency_code'), # Currency is usually on price/transaction, not sub directly
      'collection_mode': data.get('collection_mode'),
      'billing_cycle_interval': data.get('billing_cycle', {}).get('interval'),
      'billing_cycle_frequency': data.get('billing_cycle', {}).get('frequency'),
      'next_billed_at': _parse_datetime(data.get('next_billed_at')),
      'started_at': _parse_datetime(data.get('started_at')),
      'first_billed_at': _parse_datetime(data.get('first_billed_at')),
      'paused_at': _parse_datetime(data.get('paused_at')),
      'canceled_at': _parse_datetime(data.get('canceled_at')),
      'paddle_created_at': _parse_datetime(data.get('created_at')), # Paddle's created_at for the subscription
      'paddle_updated_at': _parse_datetime(data.get('updated_at')), # Paddle's updated_at for the subscription
      'custom_data': data.get('custom_data'), # Custom data from the Paddle subscription object
      'management_urls_customer_portal': data.get('management_urls', {}).get('customer_portal'),
      'management_urls_update_payment_method': data.get('management_urls', {}).get('update_payment_method'),
      'management_urls_cancel': data.get('management_urls', {}).get('cancel'),
      'scheduled_change_action': data.get('scheduled_change', {}).get('action'),
      'scheduled_change_effective_at': _parse_datetime(data.get('scheduled_change', {}).get('effective_at')),
      'scheduled_change_resume_at': _parse_datetime(data.get('scheduled_change', {}).get('resume_at')),
      # MyBizz specific plan definition fields
      'item_id': mybizz_item_row, # Link to the items table (plan definition)
      'subscription_group': subscription_group_row, # Link to subscription_group table
      'glt': glt_value,
      'level_num': level_num_parsed,
      'tier_num': tier_num_parsed,
      # 'level_name' and 'tier_name' can be derived from subscription_group_row and level/tier numbers if needed for display
      # or stored denormalized if frequently accessed without joins. For now, keep lean.
    }
    # Remove keys where value is None to avoid overwriting existing data with None unnecessarily,
    # but ensure 'paddle_id' is always present for the get/add logic.
    # Also ensure fields that can be legitimately nullified (like paused_at, canceled_at) are handled.
    # A more nuanced approach for None:
    final_update_data = {'paddle_id': paddle_subscription_id}
    for k, v in update_data.items():
      if k == 'paddle_id': 
        continue
        if v is not None:
          final_update_data[k] = v
        elif k in ['paused_at', 'canceled_at', 'discount_id', 'address_id', 'scheduled_change_action', 'scheduled_change_effective_at', 'scheduled_change_resume_at']: # Fields that can be nulled
          final_update_data[k] = None


      current_time_anvil = datetime.now(timezone.utc)
    if subs_row:
      log("INFO", module_name, function_name, "Updating existing MyBizz subscription.", {**log_context, "mybizz_subs_id": subs_row['subs_id']})
      final_update_data['updated_at_anvil'] = current_time_anvil
      subs_row.update(**final_update_data)
    else:
      log("INFO", module_name, function_name, "Creating new MyBizz subscription.", log_context)
      final_update_data['created_at_anvil'] = current_time_anvil
      final_update_data['updated_at_anvil'] = current_time_anvil
      # Ensure all required fields for add_row are present if subs_table has constraints
      # For example, if 'item_id' is NOT NULL in 'subs' table and mybizz_item_row is None, this will fail.
      if not mybizz_item_row:
        log("ERROR", module_name, function_name, "Cannot create new subscription instance in MyBizz as the corresponding plan definition (item) was not found.", log_context)
        return False, "Cannot create subscription, MyBizz plan definition missing."
        subs_row = subs_table.add_row(**final_update_data) # Capture the newly created row

      log("DEBUG", module_name, function_name, "MyBizz 'subs' table processed.", log_context)

    # 3. Process subscription line items
    # Pass the MyBizz subs_row (which is now guaranteed to exist)
    items_data_from_payload = data.get('items', [])
    items_processed, items_msg = _process_subscription_items(subs_row, items_data_from_payload, log_context)
    if not items_processed:
      # Log or append warning, but don't necessarily fail the whole sub processing
      log("WARNING", module_name, function_name, f"Issues processing subscription line items: {items_msg}", log_context)
      # The main subscription record was still processed.

      log("INFO", module_name, function_name, "Subscription processed successfully.", log_context)
    return True, "Subscription processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing subscription: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file) ...

def _process_subscription_items(mybizz_subs_row, paddle_line_items_data, parent_log_context):
  """
    Processes the 'items' array from a Paddle subscription webhook.
    Creates/updates/inactivates rows in the 'subscription_items' table.

    Args:
        mybizz_subs_row (anvil.tables.Row): The parent subscription row from MyBizz 'subs' table.
        paddle_line_items_data (list): The 'items' array from the Paddle webhook payload.
        parent_log_context (dict): Logging context from the calling function.
    """
  module_name = "webhook_handler"
  function_name = "_process_subscription_items"
  log_context = {**parent_log_context, "mybizz_subs_id": mybizz_subs_row['subs_id']}

  if not isinstance(paddle_line_items_data, list):
    log("ERROR", module_name, function_name, "Paddle line items data is not a list.", log_context)
    return False, "Paddle line items data is not a list."

    if not mybizz_subs_row: # Should not happen if called correctly
      log("CRITICAL", module_name, function_name, "Parent MyBizz subscription row (mybizz_subs_row) is missing.", log_context)
      return False, "Parent MyBizz subscription row missing."

  log("INFO", module_name, function_name, f"Processing {len(paddle_line_items_data)} line item(s) for subscription.", log_context)

  processed_paddle_item_ids = set() # To track Paddle Subscription Line Item IDs (sli_...) from the webhook

  try:
    subscription_items_table = tables.app_tables.subscription_items
    current_time_anvil = datetime.now(timezone.utc)

    for paddle_item_data in paddle_line_items_data:
      item_log_context = {**log_context} # Copy for item-specific logging

      paddle_subscription_line_item_id = paddle_item_data.get('id') # This is the sli_...
      item_log_context['paddle_subscription_line_item_id'] = paddle_subscription_line_item_id

      price_info = paddle_item_data.get('price', {})
      paddle_price_id = price_info.get('id') # This is the pri_...
      item_log_context['paddle_price_id'] = paddle_price_id

      if not paddle_subscription_line_item_id:
        log("WARNING", module_name, function_name, "Skipping subscription line item due to missing Paddle Subscription Line Item ID (sli_...).", item_log_context)
        continue
        if not paddle_price_id:
          log("WARNING", module_name, function_name, "Skipping subscription line item due to missing Paddle Price ID (pri_...).", item_log_context)
          continue

          processed_paddle_item_ids.add(paddle_subscription_line_item_id)

      # Find the corresponding MyBizz 'prices' row
      mybizz_price_row = tables.app_tables.prices.get(paddle_price_id=paddle_price_id)
      if not mybizz_price_row:
        log("ERROR", module_name, function_name, f"MyBizz 'prices' row not found for paddle_price_id '{paddle_price_id}'. Cannot link line item.", item_log_context)
        # Decide if this should be a partial failure or stop all item processing.
        # For now, skip this item and continue with others.
        continue
        item_log_context['mybizz_price_id'] = mybizz_price_row['price_id']

      # Get existing subscription_items row or prepare for new one
      sub_item_row = subscription_items_table.get(paddle_id=paddle_subscription_line_item_id)

      update_data = {
        'paddle_id': paddle_subscription_line_item_id,
        'subscription_id': mybizz_subs_row,
        'price_id': mybizz_price_row,
        'quantity': paddle_item_data.get('quantity'),
        # 'status': paddle_item_data.get('status'), # Paddle API v1 subscription items don't typically have their own status distinct from the sub.
        # If Paddle API v2 or specific events provide it, map it here. Default to 'active' or derive.
        'status': 'active', # Assuming line items are active if the subscription is. Adjust if Paddle provides item-level status.
        'paddle_created_at': _parse_datetime(paddle_item_data.get('created_at')), # Timestamps for the line item itself
        'paddle_updated_at': _parse_datetime(paddle_item_data.get('updated_at')),
        'custom_data': paddle_item_data.get('custom_data'), # Custom data on the subscription line item
        'proration_billing_mode': paddle_item_data.get('proration', {}).get('billing_mode'), # Example path, adjust to actual Paddle payload
        'next_billed_at': _parse_datetime(paddle_item_data.get('next_billed_at')), # If available per line item
      }

      final_update_data = {'paddle_id': paddle_subscription_line_item_id}
      for k, v in update_data.items():
        if k == 'paddle_id': 
          continue
          if v is not None:
            final_update_data[k] = v

            if sub_item_row:
              log("INFO", module_name, function_name, "Updating existing MyBizz subscription line item.", item_log_context)
              final_update_data['updated_at_anvil'] = current_time_anvil
              sub_item_row.update(**final_update_data)
            else:
              log("INFO", module_name, function_name, "Creating new MyBizz subscription line item.", item_log_context)
              final_update_data['created_at_anvil'] = current_time_anvil
              final_update_data['updated_at_anvil'] = current_time_anvil
              # Generate a unique Anvil ID for sub_item_id
              timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
              anvil_sub_item_id = f"SLI-{timestamp_str}-{paddle_subscription_line_item_id[:8]}" # Example unique ID
              # Ensure it's truly unique if high concurrency is expected
              while subscription_items_table.get(sub_item_id=anvil_sub_item_id):
                timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f") # Regen
                anvil_sub_item_id = f"SLI-{timestamp_str}-{paddle_subscription_line_item_id[:8]}"

                final_update_data['sub_item_id'] = anvil_sub_item_id
              subscription_items_table.add_row(**final_update_data)

      # Reconciliation: Mark local items not in the webhook as 'inactive'
      existing_db_items = subscription_items_table.search(subscription_id=mybizz_subs_row, status='active') # Only check active ones
    for db_item in existing_db_items:
      if db_item['paddle_id'] not in processed_paddle_item_ids:
        log("INFO", module_name, function_name, "Marking MyBizz subscription line item as inactive (not in webhook).", 
            {**log_context, "mybizz_sub_item_id": db_item['sub_item_id'], "paddle_subscription_line_item_id": db_item['paddle_id']})
        db_item.update(status='inactive', updated_at_anvil=current_time_anvil)

        log("INFO", module_name, function_name, "Subscription line items processed.", log_context)
    return True, "Subscription items processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing subscription line items: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg


# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file) ...

def _process_product(data):
  """
    Processes product.created/updated webhooks from Paddle.
    Updates the corresponding 'items' row in MyBizz.
    """
  module_name = "webhook_handler"
  function_name = "_process_product"
  paddle_product_id = data.get('id')
  log_context = {"paddle_product_id": paddle_product_id, "event_type": data.get("event_type", "product_event")}

  if not paddle_product_id:
    log("ERROR", module_name, function_name, "Missing data.id (paddle_product_id) in product payload.", log_context)
    return False, "Missing paddle_product_id in product payload"

    log("INFO", module_name, function_name, "Processing product payload.", log_context)

  try:
    # Find the corresponding MyBizz 'items' row.
    # Products in Paddle can correspond to item_type 'product', 'service',
    # or even 'subscription_plan' (as groups are synced as Paddle Products).
    # We need to be careful here. If MyBizz created it, it should have the paddle_product_id.
    item_row = tables.app_tables.items.get(paddle_product_id=paddle_product_id)

    if not item_row:
      # If the item doesn't exist in MyBizz with this paddle_product_id,
      # it might be a product created directly in Paddle, or a group.
      # For now, we will only update items that MyBizz already knows about and has synced.
      # If MyBizz needs to create items based on Paddle webhooks, that's a separate design decision.
      log("WARNING", module_name, function_name, f"MyBizz item with paddle_product_id '{paddle_product_id}' not found. No update performed. This might be a product created directly in Paddle or a subscription group's product.", log_context)
      # We return True because the webhook itself was valid, but no action was taken for this specific product.
      # Or, return False if this scenario should be treated as an error/unhandled case.
      # For now, let's consider it a valid scenario where no MyBizz item needs updating.
      return True, f"MyBizz item for paddle_product_id '{paddle_product_id}' not found. No update action taken."

      log_context['mybizz_item_id'] = item_row['item_id']
    log_context['mybizz_item_type'] = item_row['item_type']

    # Prepare update data for the 'items' table
    # Map Paddle product fields to MyBizz 'items' table columns
    # Note: MyBizz 'status' is string ('active'/'archived'), Paddle 'status' is string.
    mybizz_status = data.get('status', item_row['status']) # Default to existing if not in payload

    # Handle image_url: If Paddle provides an image_url, we might want to
    # update our 'media' link or 'image_url' field. This is complex because
    # MyBizz stores images in the 'files' table and links via the 'media' column.
    # A simple approach is to store Paddle's image_url in items.image_url if it exists.
    # A more complex one would be to download the image and create/update a 'files' row.
    # For now, let's just update the items.image_url string field if it exists in your schema.
    paddle_image_url = data.get('image_url')

    update_data = {
      'name': data.get('name', item_row['name']), # Default to existing if not in payload
      'description': data.get('description', item_row['description']),
      'status': mybizz_status,
      'tax_category': data.get('tax_category', item_row['tax_category']),
      # 'image_url': paddle_image_url if paddle_image_url is not None else item_row.get('image_url'), # Update if provided
      # 'custom_data': data.get('custom_data', item_row['custom_data']), # Merge or overwrite?
      'paddle_updated_at': _parse_datetime(data.get('updated_at')), # Reflect Paddle's update time
      'updated_at_anvil': datetime.now(timezone.utc)
    }

    # Handle custom_data: Overwrite or merge?
    # For simplicity, let's overwrite if present in webhook, but ensure MyBizz IDs are preserved if possible.
    # The custom_data from Paddle product webhook might not contain our internal MyBizz IDs.
    # The custom_data on the item_row in MyBizz *should* contain mybizz_item_id etc.
    # It's safer not to blindly overwrite custom_data from a generic product webhook
    # unless we are sure about its content.
    # Let's only update it if the webhook explicitly provides it and we decide to overwrite.
    if 'custom_data' in data: # Only update if Paddle sends it
      # Be cautious here. If MyBizz adds its own IDs to custom_data sent to Paddle,
      # and Paddle returns it, then it's fine. Otherwise, this might wipe MyBizz specific custom_data.
      # A safer merge strategy might be needed if MyBizz adds distinct custom_data.
      update_data['custom_data'] = data.get('custom_data')


      # If items.image_url exists in your schema and you want to store Paddle's direct image URL:
      if 'image_url' in tables.app_tables.items.list_columns() and paddle_image_url is not None:
        update_data['image_url'] = paddle_image_url
      elif 'image_url' in tables.app_tables.items.list_columns() and paddle_image_url is None and 'image_url' in data: # Explicitly nulled
        update_data['image_url'] = None


        log("INFO", module_name, function_name, f"Updating MyBizz item '{item_row['item_id']}'.", {**log_context, "update_payload": update_data})
    item_row.update(**update_data)

    log("INFO", module_name, function_name, "Product (item) processed successfully.", log_context)
    return True, "Product (item) processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing product: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file) ...

def _process_price(data):
  """
    Processes price.created/updated webhooks from Paddle.
    Updates the corresponding 'prices' row in MyBizz.
    """
  module_name = "webhook_handler"
  function_name = "_process_price"
  paddle_price_id = data.get('id')
  paddle_product_id_from_price = data.get('product_id') # This is Paddle's Product ID

  log_context = {
    "paddle_price_id": paddle_price_id,
    "paddle_product_id_from_price_payload": paddle_product_id_from_price,
    "event_type": data.get("event_type", "price_event")
  }

  if not paddle_price_id:
    log("ERROR", module_name, function_name, "Missing data.id (paddle_price_id) in price payload.", log_context)
    return False, "Missing paddle_price_id in price payload"
    if not paddle_product_id_from_price:
      log("ERROR", module_name, function_name, "Missing data.product_id (parent paddle_product_id) in price payload.", log_context)
      return False, "Missing parent paddle_product_id in price payload"

  log("INFO", module_name, function_name, "Processing price payload.", log_context)

  try:
    # 1. Find the parent MyBizz 'items' row using the paddle_product_id from the price payload
    parent_item_row = tables.app_tables.items.get(paddle_product_id=paddle_product_id_from_price)
    if not parent_item_row:
      log("WARNING", module_name, function_name, f"Parent MyBizz item with paddle_product_id '{paddle_product_id_from_price}' not found. Cannot process price '{paddle_price_id}'.", log_context)
      # If the parent product doesn't exist in MyBizz, we can't link this price.
      # This might be a price for a product created directly in Paddle and not known to MyBizz.
      return False, f"Parent item for price '{paddle_price_id}' not found in MyBizz."
      log_context['mybizz_parent_item_id'] = parent_item_row['item_id']

    # 2. Find or (optionally) create the MyBizz 'prices' row
    price_row = tables.app_tables.prices.get(paddle_price_id=paddle_price_id)

    # Prepare update data for the 'prices' table
    # Paddle 'type' for price ('standard', 'package') vs MyBizz 'price_type' ('one_time', 'recurring')
    # This mapping needs to be robust. Paddle's price 'type' might not directly map.
    # The 'billing_cycle' presence determines if it's recurring.
    mybizz_price_type = 'one_time'
    if data.get('billing_cycle') and data['billing_cycle'].get('interval'):
      mybizz_price_type = 'recurring'
      log_context['determined_mybizz_price_type'] = mybizz_price_type

    # MyBizz 'status' is string ('active'/'archived'), Paddle 'status' is string.
    mybizz_status = data.get('status', price_row['status'] if price_row else 'active')


    update_data = {
      'paddle_price_id': paddle_price_id, # Ensure this is set for new rows if we decide to create
      'item_id': parent_item_row, # Link to the parent MyBizz item
      'description': data.get('description'), # Paddle Price description
      # 'name': data.get('name'), # Paddle Price also has a 'name', map if you have a corresponding field
      'price_type': mybizz_price_type,
      'status': mybizz_status,
      'tax_mode': data.get('tax_mode'),
      'billing_cycle_interval': data.get('billing_cycle', {}).get('interval'),
      'billing_cycle_frequency': data.get('billing_cycle', {}).get('frequency'),
      'trial_period_interval': data.get('trial_period', {}).get('interval'), # Check Paddle payload structure
      'trial_period_frequency': data.get('trial_period', {}).get('frequency'), # Check Paddle payload structure
      'unit_price_amount': data.get('unit_price', {}).get('amount'), # Stored as string
      'unit_price_currency_code': data.get('unit_price', {}).get('currency_code'),
      'quantity_minimum': data.get('quantity', {}).get('minimum', 1), # Default to 1 if not present
      'quantity_maximum': data.get('quantity', {}).get('maximum', 1), # Default to 1 if not present
      # 'custom_data': data.get('custom_data'), # Be cautious with overwriting custom_data
      'paddle_created_at': _parse_datetime(data.get('created_at')),
      'paddle_updated_at': _parse_datetime(data.get('updated_at')),
      'updated_at_anvil': datetime.now(timezone.utc)
    }

    # Handle custom_data carefully (similar to _process_product)
    if 'custom_data' in data:
      # Ensure MyBizz internal IDs (like mybizz_price_id if we put it there) are preserved
      # or that Paddle echoes back the custom_data MyBizz sent.
      # For now, direct overwrite if present in webhook.
      update_data['custom_data'] = data.get('custom_data')

      # Remove None values unless they are meant to explicitly nullify a field
      # For price, most fields are defining characteristics.
      final_update_data = {k: v for k, v in update_data.items() if v is not None}
    final_update_data['paddle_price_id'] = paddle_price_id # Ensure this is present
    final_update_data['item_id'] = parent_item_row # Ensure link is present

    if price_row:
      log("INFO", module_name, function_name, f"Updating MyBizz price '{price_row['price_id']}'.", {**log_context, "mybizz_price_id": price_row['price_id']})
      # Ensure all fields from final_update_data are applied
      price_row.update(**final_update_data)
    else:
      # Price with this paddle_price_id doesn't exist in MyBizz.
      # This could happen if a price is created directly in Paddle for a MyBizz-known product.
      # Decision: Create a new MyBizz price record.
      log("INFO", module_name, function_name, f"Creating new MyBizz price for paddle_price_id '{paddle_price_id}'.", log_context)
      final_update_data['created_at_anvil'] = datetime.now(timezone.utc)

      # Generate a unique Anvil ID for price_id
      timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
      anvil_price_id = f"PRC-{timestamp_str}-{paddle_price_id[:8]}"
      while tables.app_tables.prices.get(price_id=anvil_price_id): # Ensure uniqueness
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        anvil_price_id = f"PRC-{timestamp_str}-{paddle_price_id[:8]}"
        final_update_data['price_id'] = anvil_price_id

      # Ensure all required fields for add_row are present
      if not final_update_data.get('description'): # Description is usually key
        final_update_data['description'] = f"Paddle Price {paddle_price_id}" # Default description
        if not final_update_data.get('unit_price_amount') or not final_update_data.get('unit_price_currency_code'):
          log("ERROR", module_name, function_name, "Cannot create new price, unit_price amount or currency_code missing from Paddle payload.", log_context)
          return False, "Cannot create price, missing unit price details from payload."

          tables.app_tables.prices.add_row(**final_update_data)
      log("INFO", module_name, function_name, f"New MyBizz price '{anvil_price_id}' created.", log_context)

      # TODO: Handle price.unit_price_overrides if Paddle sends them in this webhook
      # The current `sm_pricing_mod.py` handles overrides when MyBizz creates/updates them.
      # If Paddle sends override updates with the main price update, that logic would go here.
      # For now, assuming overrides are managed separately or via different events.

      log("INFO", module_name, function_name, "Price processed successfully.", log_context)
    return True, "Price processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing price: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file, including)
# from .sm_logs_mod import log
# from anvil import tables, users # anvil.users for add_user
# from datetime import datetime, timezone
# import dateutil.parser

def _parse_full_name(full_name_str):
  """Helper to attempt parsing first and last name from a full name string."""
  if not full_name_str or not isinstance(full_name_str, str):
    return None, None
    parts = full_name_str.strip().split(maxsplit=1)
  first_name = parts[0] if parts else None
  last_name = parts[1] if len(parts) > 1 else None
  return first_name, last_name

def _process_customer(data):
  """
    Processes customer.created/updated webhooks from Paddle.
    Creates/updates the 'customer' table row in MyBizz.
    Creates a corresponding Anvil user in app_tables.users if one doesn't exist
    for the customer's email and links it.
    Attempts to parse first_name and last_name from full_name.
    """
  module_name = "webhook_handler"
  function_name = "_process_customer"
  paddle_customer_id = data.get('id')
  log_context = {"paddle_customer_id": paddle_customer_id, "event_type": data.get("event_type", "customer_event")}

  if not paddle_customer_id:
    log("ERROR", module_name, function_name, "Missing data.id (paddle_customer_id) in customer payload.", log_context)
    return False, "Missing paddle_customer_id in customer payload"

    log("INFO", module_name, function_name, "Processing customer payload.", log_context)

  try:
    customer_table = tables.app_tables.customer
    customer_row = customer_table.get(paddle_id=paddle_customer_id)

    email_from_payload = data.get('email')
    log_context['email_from_payload'] = email_from_payload

    anvil_user_link = None
    if email_from_payload:
      try:
        # Check if an Anvil user already exists with this email
        existing_anvil_user = users.get_user(email_from_payload) # Uses Anvil's user service
        if existing_anvil_user:
          anvil_user_link = existing_anvil_user
          log("INFO", module_name, function_name, "Found existing Anvil user by email.", {**log_context, "anvil_user_email": email_from_payload})
        else:
          # Auto-create Anvil user if not found
          log("INFO", module_name, function_name, f"No existing Anvil user for email '{email_from_payload}'. Creating new Anvil user.", log_context)
          # Create user without a password; they would set it via a reset flow or invitation.
          # Ensure 'enabled' and 'rememberable' are appropriate for your user flow.
          new_anvil_user = users.add_user(email=email_from_payload, password_hash=None, enabled=True, rememberable=False)
          if new_anvil_user:
            anvil_user_link = new_anvil_user
            log("INFO", module_name, function_name, "Successfully created new Anvil user for customer.", {**log_context, "new_anvil_user_email": email_from_payload})
          else:
            log("ERROR", module_name, function_name, f"Failed to create new Anvil user for email '{email_from_payload}'.", log_context)
      except Exception as e_user_mgmt:
        log("ERROR", module_name, function_name, f"Error during Anvil user lookup/creation for email '{email_from_payload}': {str(e_user_mgmt)}", log_context)

        full_name_from_payload = data.get('name')
    first_name_parsed, last_name_parsed = _parse_full_name(full_name_from_payload)

    update_data = {
      'paddle_id': paddle_customer_id,
      'email': email_from_payload,
      'status': data.get('status'),
      'marketing_consent': data.get('marketing_consent', {}).get('granted'),
      'full_name': full_name_from_payload,
      'first_name': first_name_parsed,
      'last_name': last_name_parsed,
      'locale': data.get('locale'),
      'paddle_created_at': _parse_datetime(data.get('created_at')),
      'paddle_updated_at': _parse_datetime(data.get('updated_at')),
      'custom_data': data.get('custom_data'),
      'user_id': anvil_user_link, # Link to Anvil 'users' table row
      'country': data.get('country_code'), # Assuming Paddle sends 'country_code' directly
    }

    final_update_data = {'paddle_id': paddle_customer_id}
    nullable_fields = ['email', 'status', 'marketing_consent', 'full_name', 'first_name', 'last_name', 'locale', 'custom_data', 'user_id', 'country']
    for k, v in update_data.items():
      if k == 'paddle_id': 
        continue
        if v is not None:
          final_update_data[k] = v
        elif k in nullable_fields:
          final_update_data[k] = None

      current_time_anvil = datetime.now(timezone.utc)
    if customer_row:
      mybizz_customer_id = customer_row['customer_id']
      log_context_update = {**log_context, "mybizz_customer_id": mybizz_customer_id}
      log("INFO", module_name, function_name, "Updating existing MyBizz customer.", log_context_update)

      final_update_data['updated_at_anvil'] = current_time_anvil
      customer_row.update(**final_update_data)
    else:
      log("INFO", module_name, function_name, "Creating new MyBizz customer.", log_context)
      final_update_data['created_at_anvil'] = current_time_anvil
      final_update_data['updated_at_anvil'] = current_time_anvil

      timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
      anvil_customer_id = f"CUS-{timestamp_str}-{paddle_customer_id[:8]}"
      while tables.app_tables.customer.get(customer_id=anvil_customer_id):
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        anvil_customer_id = f"CUS-{timestamp_str}-{paddle_customer_id[:8]}"
        final_update_data['customer_id'] = anvil_customer_id

      customer_table.add_row(**final_update_data)

      log("INFO", module_name, function_name, "Customer processed successfully.", log_context)
    return True, "Customer processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing customer: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg

# Server Module: webhook_handler.py (Tenant App)

# ... (ensure all necessary imports are at the top of the file) ...

def _process_discount(data):
  """
    Processes discount.created/updated webhooks from Paddle.
    Creates/updates the 'discount' table row in MyBizz.
    """
  module_name = "webhook_handler"
  function_name = "_process_discount"
  paddle_discount_id = data.get('id')
  log_context = {"paddle_discount_id": paddle_discount_id, "event_type": data.get("event_type", "discount_event")}

  if not paddle_discount_id:
    log("ERROR", module_name, function_name, "Missing data.id (paddle_discount_id) in discount payload.", log_context)
    return False, "Missing paddle_discount_id in discount payload"

    log("INFO", module_name, function_name, "Processing discount payload.", log_context)

  try:
    discount_table = tables.app_tables.discount
    discount_row = discount_table.get(paddle_id=paddle_discount_id)

    # Prepare data dictionary for Anvil 'discount' table
    # Your 'discount' schema includes: discount_id (Anvil PK), paddle_id, discount_name, coupon_code,
    # type, description, status, usage_limit, times_used, duration_type, duration_in_months,
    # currency_restrictions (SimpleObject), location_restrictions (SimpleObject), custom_data (SimpleObject),
    # paddle_created_at, paddle_updated_at, amount_type, amount_rate, amount_amount, amount_currency_code, expires_at.

    # Paddle's discount 'code' is the coupon code. 'description' is also usually present.
    # 'name' field in your schema: Paddle's discount object doesn't have a separate 'name' distinct from 'description' or 'code'.
    # We can map Paddle's 'description' to 'discount_name' or use 'code' if 'description' is empty.
    discount_name_from_payload = data.get('description') or data.get('code') # Use description, fallback to code for name

    update_data = {
      'paddle_id': paddle_discount_id,
      'status': data.get('status'), # e.g., 'active', 'expired', 'archived'
      'description': data.get('description'), # Detailed description
      'discount_name': discount_name_from_payload, # For your schema's 'discount_name'
      'coupon_code': data.get('code'), # The actual coupon code
      'type': data.get('type'), # e.g., 'percentage', 'flat', 'free_trial'

      # Amount details (often nested under 'amount' in Paddle v1, but varies by discount type)
      # The schema has flat amount_type, amount_rate, amount_amount, amount_currency_code
      # This needs careful mapping based on Paddle's discount object structure for different types.
      # For a 'percentage' discount, 'rate' is key. For 'flat', 'amount' and 'currency_code'.
      'amount_type': data.get('type'), # Often the main 'type' also indicates amount type
      'amount_rate': data.get('rate') if data.get('type') == 'percentage' else None, # Paddle often has 'rate' for percentage
      'amount_amount': data.get('amount') if data.get('type') == 'flat' else None, # Paddle often has 'amount' for flat
      'amount_currency_code': data.get('currency_code') if data.get('type') == 'flat' else None, # Currency for flat discounts

      'usage_limit': data.get('usage_limit'),
      'times_used': data.get('times_used', 0), # Default to 0 if not present

      # Duration details (often nested under 'duration' in Paddle v1)
      'duration_type': data.get('duration_type'), # e.g., 'repeating', 'forever', 'one_time'
      'duration_in_months': data.get('duration_in_months') if data.get('duration_type') == 'repeating' else None,

      'expires_at': _parse_datetime(data.get('expires_at')),
      'paddle_created_at': _parse_datetime(data.get('created_at')),
      'paddle_updated_at': _parse_datetime(data.get('updated_at')),
      'custom_data': data.get('custom_data'),

      # Restrictions - these are often complex objects in Paddle.
      # Storing them as SimpleObjects is a good approach.
      'currency_restrictions': data.get('restrict_to_currency') or data.get('currency_restrictions'), # Check actual payload key
      'location_restrictions': data.get('restrict_to_location') or data.get('location_restrictions'), # Check actual payload key
    }

    # Refined amount mapping based on common Paddle structures
    if data.get('type') == 'percentage' and 'rate' in data:
      update_data['amount_rate'] = str(data['rate']) # Ensure string if schema is string
      update_data['amount_amount'] = None
      update_data['amount_currency_code'] = None
    elif data.get('type') == 'flat' and 'amount' in data:
      update_data['amount_amount'] = str(data['amount']) # Ensure string if schema is string
      update_data['amount_currency_code'] = data.get('currency_code')
      update_data['amount_rate'] = None

      # Clean update_data
      final_update_data = {'paddle_id': paddle_discount_id}
    # Define fields that can be legitimately nulled if Paddle sends them as such
    nullable_fields = [
      'description', 'status', 'coupon_code', 'type', 'amount_type', 'amount_rate', 
      'amount_amount', 'amount_currency_code', 'usage_limit', 'duration_type', 
      'duration_in_months', 'expires_at', 'custom_data', 
      'currency_restrictions', 'location_restrictions', 'discount_name'
    ]
    for k, v in update_data.items():
      if k == 'paddle_id': 
        continue
        if v is not None:
          final_update_data[k] = v
        elif k in nullable_fields:
          final_update_data[k] = None

      current_time_anvil = datetime.now(timezone.utc)
    if discount_row:
      mybizz_discount_id = discount_row['discount_id']
      log_context_update = {**log_context, "mybizz_discount_id": mybizz_discount_id}
      log("INFO", module_name, function_name, "Updating existing MyBizz discount.", log_context_update)

      final_update_data['updated_at_anvil'] = current_time_anvil
      discount_row.update(**final_update_data)
    else:
      log("INFO", module_name, function_name, "Creating new MyBizz discount.", log_context)
      final_update_data['created_at_anvil'] = current_time_anvil
      final_update_data['updated_at_anvil'] = current_time_anvil

      timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
      anvil_discount_id = f"DSC-{timestamp_str}-{paddle_discount_id[:8]}"
      while tables.app_tables.discount.get(discount_id=anvil_discount_id):
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        anvil_discount_id = f"DSC-{timestamp_str}-{paddle_discount_id[:8]}"
        final_update_data['discount_id'] = anvil_discount_id

      # Ensure essential fields for a new discount are present
      if not final_update_data.get('coupon_code') and not final_update_data.get('description'):
        log("WARNING", module_name, function_name, "Cannot create new discount, code or description missing from Paddle payload.", log_context)
        # Return False if a code/description is absolutely essential for a new discount record
        # For now, allow creation if Paddle sends it.

        discount_table.add_row(**final_update_data)

      log("INFO", module_name, function_name, "Discount processed successfully.", log_context)
    return True, "Discount processed successfully."

  except Exception as e:
    import traceback
    error_msg = f"Error processing discount: {str(e)}"
    log("CRITICAL", module_name, function_name, error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return False, error_msg


# --- Helper Function: Paddle Signature Verification ---
def verify_paddle_signature(request):
  """
    Verifies the signature of an incoming Paddle webhook request using
    the secret stored in the MyBizz Vault and checks timestamp tolerance.
    Raises anvil.server.HttpError on failure.
    Logs events using sm_logs_mod.
    """
  module_name = "webhook_handler"
  function_name = "verify_paddle_signature"
  log_context = {} # Initialize context for logging

  try:
    # 1. Get Signature Header
    signature_header = request.headers.get('paddle-signature')
    log_context['signature_header_present'] = bool(signature_header)
    if not signature_header:
      log("WARNING", module_name, function_name, "Missing 'Paddle-Signature' header.", log_context)
      raise anvil.server.HttpError(400, "Missing 'Paddle-Signature' header.")
      log_context['raw_signature_header'] = signature_header

    # 2. Parse Signature Header (Format: "ts=<timestamp>,h1=<signature>")
    parsed_header_parts = {}
    try:
      for part in signature_header.split(','):
        key_value_pair = part.split('=', 1)
        if len(key_value_pair) == 2:
          parsed_header_parts[key_value_pair[0].strip()] = key_value_pair[1].strip()
    except ValueError as ve: # Catch potential errors from split
      log("ERROR", module_name, function_name, "Malformed 'Paddle-Signature' header structure during parsing.", {"header": signature_header, "error": str(ve)})
      raise anvil.server.HttpError(400, "Malformed 'Paddle-Signature' header structure.")

      timestamp_str = parsed_header_parts.get('ts')
    signature_h1 = parsed_header_parts.get('h1')
    log_context['parsed_timestamp_str'] = timestamp_str
    log_context['parsed_signature_h1_present'] = bool(signature_h1)

    if not timestamp_str or not signature_h1:
      log("ERROR", module_name, function_name, "Could not parse ts or h1 from Paddle-Signature header.", log_context)
      raise anvil.server.HttpError(400, "Malformed 'Paddle-Signature' header (missing ts or h1).")

      # 3. Retrieve Tenant's Webhook Secret Key from MyBizz Vault
      secret_key = get_secret_for_server_use(PADDLE_WEBHOOK_SECRET_VAULT_KEY)
    if not secret_key:
      log("CRITICAL", module_name, function_name, f"Secret key '{PADDLE_WEBHOOK_SECRET_VAULT_KEY}' not found in MyBizz Vault.", log_context)
      raise anvil.server.HttpError(500, "Webhook secret configuration error.")
      log("DEBUG", module_name, function_name, f"Successfully retrieved '{PADDLE_WEBHOOK_SECRET_VAULT_KEY}' from vault.", log_context)

    # 4. Construct Signed Payload (timestamp_string + ":" + raw_request_body_bytes)
    signed_payload_prefix = f"{timestamp_str}:".encode('utf-8')
    signed_payload = signed_payload_prefix + request.body_bytes
    log("DEBUG", module_name, function_name, "Constructed signed payload for hashing.", log_context)

    # 5. Calculate Expected Signature
    computed_signature_h1 = hmac.new(
      key=secret_key.encode('utf-8'),
      msg=signed_payload,
      digestmod=hashlib.sha256
    ).hexdigest()
    log("DEBUG", module_name, function_name, "Computed expected HMAC-SHA256 signature.", {"computed_signature": computed_signature_h1})

    # 6. Compare Signatures Securely
    if not hmac.compare_digest(signature_h1, computed_signature_h1):
      log("WARNING", module_name, function_name, "Invalid webhook signature.", {"received_signature": signature_h1, "computed_signature": computed_signature_h1})
      raise anvil.server.HttpError(403, "Invalid webhook signature.")
      log("INFO", module_name, function_name, "Webhook signature digest matches.", log_context)

    # 7. Verify Timestamp
    try:
      event_timestamp_int = int(timestamp_str)
      event_datetime = datetime.fromtimestamp(event_timestamp_int, timezone.utc)
      current_datetime = datetime.now(timezone.utc)
      log_context['event_datetime_utc'] = str(event_datetime)
      log_context['current_datetime_utc'] = str(current_datetime)
      log_context['tolerance_minutes'] = WEBHOOK_TIMESTAMP_TOLERANCE.total_seconds() / 60

      if abs(current_datetime - event_datetime) > WEBHOOK_TIMESTAMP_TOLERANCE:
        log("WARNING", module_name, function_name, "Webhook timestamp outside tolerance window.", log_context)
        raise anvil.server.HttpError(403, "Webhook timestamp outside tolerance window.")
        log("INFO", module_name, function_name, "Webhook timestamp is within tolerance.", log_context)

    except ValueError:
      log("ERROR", module_name, function_name, "Invalid timestamp format in Paddle-Signature header (cannot convert to int).", {"timestamp_str": timestamp_str})
      raise anvil.server.HttpError(400, "Invalid timestamp format in signature.")

      log("INFO", module_name, function_name, "Webhook signature and timestamp verified successfully.", log_context)
    return True

  except anvil.server.HttpError as e:
    # Log HttpErrors before re-raising if not already logged with sufficient detail
    if not log_context.get('http_error_logged'): # Avoid double logging if error originated here
      log("ERROR", module_name, function_name, f"HTTPError during signature verification: Status {e.status}, Message: {e.message}", {"http_status": e.status, **log_context})
      raise e
  except Exception as e:
    import traceback
    log("CRITICAL", module_name, function_name, "Unexpected error during signature verification.", {"error": str(e), "trace": traceback.format_exc(), **log_context})
    raise anvil.server.HttpError(500, "Internal server error during signature verification.")


# Placeholder for payment_method events
def _process_payment_method(data):
  module_name = "webhook_handler"
  function_name = "_process_payment_method"
  paddle_id = data.get('id')
  event_type = data.get("event_type", "payment_method_event")
  log_context = {"paddle_resource_id": paddle_id, "event_type": event_type}

  log("INFO", module_name, function_name, "Received payment_method event. No specific MyBizz processing implemented for this event type at this time.", log_context)
  # For now, consider it successfully handled as the webhook was valid,
  # even if no specific data processing occurs in MyBizz tables.
  return True, "Payment method event received; no specific MyBizz processing."

# Placeholder for payout events
def _process_payout(data):
  module_name = "webhook_handler"
  function_name = "_process_payout"
  paddle_id = data.get('id')
  event_type = data.get("event_type", "payout_event")
  log_context = {"paddle_resource_id": paddle_id, "event_type": event_type}

  log("INFO", module_name, function_name, "Received payout event. No specific MyBizz processing implemented for this event type at this time.", log_context)
  return True, "Payout event received; no specific MyBizz processing."

# Placeholder for report events
def _process_report(data):
  module_name = "webhook_handler"
  function_name = "_process_report"
  # Reports might not have a simple 'id' in data; adjust logging context as needed
  report_type = data.get('report_type') # Example field
  event_type = data.get("event_type", "report_event")
  log_context = {"report_type": report_type, "event_type": event_type}

  log("INFO", module_name, function_name, "Received report event. No specific MyBizz processing implemented for this event type at this time.", log_context)
  return True, "Report event received; no specific MyBizz processing."


# --- Main Webhook Handler HTTP Endpoint ---
@anvil.server.http_endpoint('/_/api/paddle_webhook', methods=['POST'])
def paddle_webhook_handler(**kwargs):
  module_name = "webhook_handler"
  function_name = "paddle_webhook_handler"

  request = anvil.server.request
  raw_payload_bytes = request.body_bytes
  raw_payload_string = "" 
  received_time = datetime.now(timezone.utc)

  event_id = "unknown_event_id" 
  event_type = "unknown_event_type" 
  resource_id = "unknown_resource_id" 
  log_row = None 

  log_context = {
    "remote_address": request.remote_address,
    "headers": dict(request.headers), 
    "received_at_iso": received_time.isoformat()
  }
  log("INFO", module_name, function_name, "Webhook request received.", log_context)

  try: # Main try block for the entire handler
    if not verify_paddle_signature(request):
      log("CRITICAL", module_name, function_name, "Signature verification failed but did not raise HttpError.", log_context)
      return anvil.server.HttpResponse(403, "Invalid Signature (Internal Check Failure)")

    try:
      raw_payload_string = raw_payload_bytes.decode('utf-8')
    except UnicodeDecodeError as ude:
      # ... (logging and return HttpResponse(400) as before) ...
      log("ERROR", module_name, function_name, "Failed to decode request body to UTF-8.", {**log_context, "decode_error": str(ude)})
      # Minimal logging to webhook_log here as event_id might be unknown
      try:
        app_tables.webhook_log.add_row(
          event_id="decode_error", received_at=received_time, event_type="decode_error",
          status='Decoding Error', forwarded_to_hub=False,
          processing_details=f"UTF-8 Decoding Failed: {str(ude)}"
        )
      except Exception as db_log_err:
        log("CRITICAL", module_name, function_name, "Failed to log UTF-8 decoding error.", {"db_log_error": str(db_log_err)})
      return anvil.server.HttpResponse(400, "Invalid request body encoding.")


    try:
      payload = json.loads(raw_payload_string)
    except json.JSONDecodeError as e:
      # ... (logging and raise HttpError(400) as before) ...
      log("ERROR", module_name, function_name, "Failed to parse JSON payload.", {**log_context, "json_error": str(e), "raw_payload_preview": raw_payload_string[:200]})
      try:
        app_tables.webhook_log.add_row(
          event_id="json_error", received_at=received_time, event_type="json_error",
          status='JSON Error', forwarded_to_hub=False,
          processing_details=f"JSON Parsing Failed: {str(e)}"
        )
      except Exception as db_log_err:
        log("CRITICAL", module_name, function_name, "Failed to log JSON parsing error.", {"db_log_error": str(db_log_err)})
      raise anvil.server.HttpError(400, "Invalid JSON payload.")


    event_id = payload.get('event_id', event_id) 
    event_type = payload.get('event_type', event_type) 
    data_payload = payload.get('data', {}) 
    resource_id = data_payload.get('id', resource_id) 

    log_context.update({"event_id": event_id, "event_type": event_type, "resource_id": resource_id})
    log("INFO", module_name, function_name, "Webhook signature verified, payload parsed.", log_context)

    if event_id == "unknown_event_id" or event_type == "unknown_event_type":
      # ... (logging and raise HttpError(400) as before) ...
      log("WARNING", module_name, function_name, "Payload missing 'event_id' or 'event_type'.", log_context)
      try:
        app_tables.webhook_log.add_row(
          event_id=event_id, received_at=received_time, event_type=event_type,
          resource_id=resource_id, status='Payload Error', forwarded_to_hub=False,
          processing_details="Payload missing 'event_id' or 'event_type'."
        )
      except Exception as db_log_err:
        log("CRITICAL", module_name, function_name, "Failed to log missing event_id/type error.", {"db_log_error": str(db_log_err)})
      raise anvil.server.HttpError(400, "Payload missing required fields (event_id or event_type).")

    log_row = app_tables.webhook_log.add_row(
      event_id=event_id,
      received_at=received_time,
      event_type=event_type,
      resource_id=resource_id or 'N/A', 
      status='Received', 
      forwarded_to_hub=False, 
      processing_details="Webhook received. Awaiting MyBizz processing."
    )
    log_context['webhook_log_id'] = log_row.get_id()
    log("INFO", module_name, function_name, "Initial entry created in webhook_log.", log_context)

    # ... (MyBizz internal data processing logic as before) ...
    processing_success = False
    processing_details_mybizz = "Event type not handled by MyBizz."
    try:
      # ... (if/elif for event_type and calling _process_... functions) ...
      if event_type.startswith('transaction.'):
        processing_success, processing_details_mybizz = _process_transaction(data_payload)
      elif event_type.startswith('subscription.'):
        processing_success, processing_details_mybizz = _process_subscription(data_payload)
        # ... (etc.) ...
      else:
        processing_success = True 
        processing_details_mybizz = f"No specific MyBizz data processing for event type: {event_type}"

      with anvil.server.Transaction():
        log_row_to_update_mybizz = app_tables.webhook_log.get_by_id(log_row.get_id())
        if log_row_to_update_mybizz:
          log_row_to_update_mybizz['status'] = 'Processed by MyBizz' if processing_success else 'MyBizz Processing Error'
          # ... (update processing_details carefully as before) ...
          current_details = log_row_to_update_mybizz['processing_details'] or ""
          separator = " | " if current_details and "Awaiting MyBizz processing" not in current_details else ""
          if "Awaiting MyBizz processing" in current_details: 
            current_details = ""
            separator = ""
          log_row_to_update_mybizz['processing_details'] = f"{current_details}{separator}MyBizz: {processing_details_mybizz}"

    except Exception as e_mybizz_process:
      # ... (log critical error and update log_row for MyBizz processing failure as before) ...
      processing_success = False # Ensure this is set
      processing_details_mybizz = f"Unexpected error during MyBizz data processing: {str(e_mybizz_process)}"
      log("CRITICAL", module_name, function_name, processing_details_mybizz, {**log_context, "error": str(e_mybizz_process), "trace": traceback.format_exc()})
      try:
        with anvil.server.Transaction():
          log_row_to_update_mybizz_err = app_tables.webhook_log.get_by_id(log_row.get_id())
          if log_row_to_update_mybizz_err:
            log_row_to_update_mybizz_err['status'] = 'MyBizz Processing Error'
            # ... (update processing_details carefully) ...
      except Exception as db_err_mybizz:
        log("CRITICAL", module_name, function_name, f"Failed to update log_row with MyBizz processing error: {db_err_mybizz}", log_context)


        # Launch Background Task for R2Hub Forwarding
    if raw_payload_string and log_row and log_row.get_id():
      # ... (launch background task and update log_row status to "Forwarding Initiated" as before) ...
      try:
        log("INFO", module_name, function_name, "Initiating background task to forward payload to R2Hub.", log_context)
        anvil.server.launch_background_task(
          'forward_payload_to_hub_background', 
          log_row_id=log_row.get_id(),
          raw_payload_string=raw_payload_string
        )
        with anvil.server.Transaction(): 
          log_row_to_update_fwd_init = app_tables.webhook_log.get_by_id(log_row.get_id())
          if log_row_to_update_fwd_init:
            if 'Error' not in (log_row_to_update_fwd_init['status'] or ""): 
              log_row_to_update_fwd_init['status'] = 'Forwarding Initiated'
      except Exception as e_bgtask:
        # ... (log error and update log_row for background task launch failure as before) ...
        log("ERROR", module_name, function_name, "Failed to launch forwarding background task.", {**log_context, "error": str(e_bgtask), "trace": traceback.format_exc()})
        # ... (update log_row with failure details) ...
        # ... (handling for empty raw_payload_string or missing log_row as before) ...

    log("INFO", module_name, function_name, "Webhook handling complete. Returning 200 OK to Paddle.", log_context)
    return anvil.server.HttpResponse(200, "Webhook received.")

    # CORRECTED INDENTATION for these except blocks
  except anvil.server.HttpError as e: 
    log("ERROR", module_name, function_name, f"Terminating with HTTPError: Status={e.status}, Message={e.message}", {**log_context, "http_status": e.status})
    # ... (attempt to log to webhook_log as before) ...
    return anvil.server.HttpResponse(e.status, e.message) 

  except Exception as e:
    final_error_msg = f"Unexpected critical failure processing webhook: {str(e)}"
    log("CRITICAL", module_name, function_name, final_error_msg, {**log_context, "error": str(e), "trace": traceback.format_exc()})
    # ... (attempt to log to webhook_log as before) ...
    return anvil.server.HttpResponse(500, "Internal Server Error")