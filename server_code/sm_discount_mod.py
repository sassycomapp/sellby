# Server Module: sm_discount_mod.py
from . import helper_functions 
from collections import defaultdict
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime, timezone, date
import traceback # For logging detailed errors
import json # For custom_data handling
import dateutil.parser #
from .sm_logs_mod import log # Assuming this path is correct
from .sessions_server import is_admin_user, is_owner_user # For permission checks
from .paddle_api_client import create_paddle_discount, update_paddle_discount # To be created/confirmed

# --- Constants ---
VALID_DISCOUNT_TYPES_PADDLE = ['percentage', 'flat'] # MyBizz types map to these
VALID_MYBIZZ_STATUSES = ['active', 'archived']

# --- Helper: Permission Check ---
def _ensure_admin():
  if not is_admin_user():
    raise anvil.server.PermissionDenied("Administrator privileges required for this action.")

# --- Helper: Validation ---
def _validate_discount_data_for_save(discount_data, is_update=False, existing_discount_row=None):
  """
    Validates discount_data from the client before saving to MyBizz DB and syncing to Paddle.
    Returns a dictionary of validated data suitable for DB and Paddle payload.
    Raises ValueError on validation failure.
    """
  module_name = "sm_discount_mod"
  function_name = "_validate_discount_data_for_save"
  log_context = {"is_update": is_update, "input_data_keys": list(discount_data.keys())}

  if not isinstance(discount_data, dict):
    raise ValueError("Discount data must be a dictionary.")

  validated_db_data = {}
  paddle_payload_parts = {}

  # 1. Target Item (MyBizz item_id - Anvil Row ID from dropdown)
  target_item_anvil_id = discount_data.get('target_item_anvil_id')
  if not is_update and not target_item_anvil_id: # Required for new discounts
    raise ValueError("Target Item (Product, Service, or Plan) is required.")
  if target_item_anvil_id:
    target_item_row = app_tables.items.get_by_id(target_item_anvil_id)
    if not target_item_row:
      raise ValueError(f"Selected Target Item with ID '{target_item_anvil_id}' not found.")
    validated_db_data['target_item_id'] = target_item_row
    # For Paddle sync, we'll need its paddle_product_id or paddle_price_id later
  elif is_update and existing_discount_row: # If updating, retain existing target if not changed
    validated_db_data['target_item_id'] = existing_discount_row['target_item_id']


    # 2. MyBizz Discount Name/Description (maps to Paddle 'description')
  discount_name = discount_data.get('discount_name', '').strip()
  if not discount_name:
    raise ValueError("MyBizz Discount Name/Description is required.")
  if len(discount_name) > 255: # Arbitrary limit, adjust as needed
    raise ValueError("MyBizz Discount Name/Description is too long (max 255 chars).")
  validated_db_data['discount_name'] = discount_name
  paddle_payload_parts['description'] = discount_name # Paddle field

  # 3. Coupon Code (maps to Paddle 'code')
  coupon_code = discount_data.get('coupon_code', '').strip()
  if coupon_code: # Optional, but if provided, validate
    if not is_update: # Check uniqueness for new codes against Paddle (via MyBizz cache)
      existing_by_code = app_tables.discount.get(coupon_code=coupon_code)
      if existing_by_code:
        raise ValueError(f"Coupon code '{coupon_code}' already exists.")
    elif is_update and existing_discount_row and existing_discount_row['coupon_code'] != coupon_code:
      # This case is prevented by UI (code field read-only on edit)
      pass # Should not happen with current UI design for edit
    if len(coupon_code) > 100: # Paddle limit might be different
      raise ValueError("Coupon Code is too long (max 100 chars).")
    paddle_payload_parts['code'] = coupon_code
  validated_db_data['coupon_code'] = coupon_code if coupon_code else None


  # 4. Type (MyBizz 'type' maps to Paddle 'type')
  discount_type = discount_data.get('type')
  if not discount_type or discount_type not in VALID_DISCOUNT_TYPES_PADDLE:
    raise ValueError(f"Invalid Discount Type. Must be one of: {', '.join(VALID_DISCOUNT_TYPES_PADDLE)}.")
  validated_db_data['type'] = discount_type
  if not is_update or (is_update and existing_discount_row and existing_discount_row['type'] != discount_type):
    paddle_payload_parts['type'] = discount_type # Type is usually immutable in Paddle after creation

    # 5. Amount/Rate based on Type
  if discount_type == 'percentage':
    rate_str = discount_data.get('amount_rate', '').strip()
    if not rate_str: 
      raise ValueError("Percentage Rate is required for percentage discount.")
    try:
      rate_float = float(rate_str)
      if not (0 < rate_float <= 100): # Assuming rate is like "10" for 10%
        raise ValueError("Percentage Rate must be between 0 (exclusive) and 100 (inclusive).")
      validated_db_data['amount_rate'] = rate_str # Store as "10.5"
      # Convert to Paddle format "0.105"
      if not is_update or (is_update and existing_discount_row and existing_discount_row.get('amount_rate') != rate_str):
        paddle_payload_parts['rate'] = str(rate_float / 100.0)
    except ValueError:
      raise ValueError("Invalid Percentage Rate. Must be a number (e.g., 10 or 10.5).")
    validated_db_data['amount_amount'] = None
    validated_db_data['amount_currency_code'] = None
  elif discount_type == 'flat':
    amount_str = discount_data.get('amount_amount', '').strip()
    currency_code = discount_data.get('amount_currency_code')
    if not amount_str or not amount_str.isdigit():
      raise ValueError("Flat Amount must be a whole number in minor units (e.g., 1000 for $10.00).")
    if not currency_code or len(currency_code) != 3 or not currency_code.isalpha():
      raise ValueError("Currency Code is required for flat amount discount (3 letters).")
    validated_db_data['amount_amount'] = amount_str
    validated_db_data['amount_currency_code'] = currency_code.upper()
    if not is_update or \
    (is_update and existing_discount_row and (existing_discount_row.get('amount_amount') != amount_str or existing_discount_row.get('amount_currency_code') != currency_code.upper())):
      paddle_payload_parts['amount'] = amount_str
      paddle_payload_parts['currency_code'] = currency_code.upper()
    validated_db_data['amount_rate'] = None
  else: # Should be caught by type validation, but defensive
    raise ValueError("Unsupported discount type for amount processing.")

    # 6. Recurring Settings (Paddle: 'recurring', 'maximum_recurring_intervals')
    # MyBizz: 'recurring' (bool), 'duration_in_months' (int)
  is_recurring = discount_data.get('recurring', False)
  validated_db_data['recurring'] = is_recurring # Store MyBizz 'recurring'
  paddle_payload_parts['recurring'] = is_recurring

  if is_recurring:
    duration_in_months_str = discount_data.get('duration_in_months', '').strip()
    if duration_in_months_str:
      try:
        duration_val = int(duration_in_months_str)
        if duration_val < 1: 
          raise ValueError("Must be > 0")
        validated_db_data['duration_in_months'] = duration_val
        paddle_payload_parts['maximum_recurring_intervals'] = duration_val
      except ValueError:
        raise ValueError("Max Recurring Intervals must be a whole number greater than 0.")
    else: # If recurring but no intervals specified, Paddle might treat as indefinite for recurring
      validated_db_data['duration_in_months'] = None
      # paddle_payload_parts['maximum_recurring_intervals'] = None # Let Paddle default
  else: # Not recurring
    validated_db_data['duration_in_months'] = None
    # paddle_payload_parts['maximum_recurring_intervals'] = None # Let Paddle default

    # 7. Usage Limit (Paddle: 'usage_limit')
  usage_limit_str = discount_data.get('usage_limit', '').strip()
  if usage_limit_str:
    try:
      usage_val = int(usage_limit_str)
      if usage_val < 1: 
        raise ValueError("Must be > 0")
      validated_db_data['usage_limit'] = usage_val
      paddle_payload_parts['usage_limit'] = usage_val
    except ValueError:
      raise ValueError("Usage Limit must be a whole number greater than 0, or blank.")
  else:
    validated_db_data['usage_limit'] = None
    # paddle_payload_parts['usage_limit'] = None # Let Paddle default (unlimited)

    # 8. Expires At (Paddle: 'expires_at' ISO 8601 datetime string)
  expires_at_date = discount_data.get('expires_at') # Anvil DatePicker returns datetime.date
  if expires_at_date:
    # Convert date to datetime at end of day for Paddle, or specific time if UI supports it
    # For simplicity, using end of day UTC.
    expires_dt = datetime(expires_at_date.year, expires_at_date.month, expires_at_date.day, 23, 59, 59, tzinfo=timezone.utc)
    validated_db_data['expires_at'] = expires_dt
    paddle_payload_parts['expires_at'] = expires_dt.isoformat()
  else:
    validated_db_data['expires_at'] = None
    # paddle_payload_parts['expires_at'] = None # Let Paddle default (no expiry)

    # 9. MyBizz Custom Data (Not directly synced to Paddle discount custom_data unless explicitly mapped)
  mybizz_custom_data_json_str = discount_data.get('custom_data_mybizz')
  if mybizz_custom_data_json_str:
    try:
      validated_db_data['custom_data'] = json.loads(mybizz_custom_data_json_str)
    except json.JSONDecodeError:
      raise ValueError("MyBizz Custom Data is not valid JSON.")
  else:
    validated_db_data['custom_data'] = None

    # Paddle Custom Data (Example: could include mybizz_discount_id)
    # For now, not adding specific MyBizz IDs to Paddle custom_data for discounts
    # paddle_payload_parts['custom_data'] = {"mybizz_discount_id": "to_be_filled_later"}


    # 10. Status (MyBizz 'status' drives Paddle 'status' and 'enabled_for_checkout')
    # For new discounts, MyBizz status is 'active' by default from client.
    # For updates, status is handled by a separate function 'set_mybizz_discount_status'.
    # Here, we just validate the status if provided for creation (though client sends 'active').
  mybizz_status = discount_data.get('status_mybizz', 'active').lower()
  if mybizz_status not in VALID_MYBIZZ_STATUSES:
    raise ValueError(f"Invalid MyBizz status: {mybizz_status}")
  validated_db_data['status'] = mybizz_status

  # For Paddle payload during CREATE:
  if not is_update:
    paddle_payload_parts['status'] = 'active' # New Paddle discounts are active
    paddle_payload_parts['enabled_for_checkout'] = True # And enabled

  log("DEBUG", module_name, function_name, "Discount data validated.", {**log_context, "validated_db_keys": list(validated_db_data.keys()), "paddle_payload_keys": list(paddle_payload_parts.keys())})
  return validated_db_data, paddle_payload_parts


# --- Helper: Trigger Paddle Discount Sync ---
def _trigger_paddle_discount_sync(mybizz_discount_row, paddle_payload_parts_for_creation_or_update):
  """
    Creates or updates a discount in Paddle based on MyBizz data.
    Updates mybizz_discount_row with paddle_id.
    `paddle_payload_parts_for_creation_or_update` contains fields for Paddle API,
    already validated and formatted (e.g., percentage rate).
    """
  module_name = "sm_discount_mod"
  function_name = "_trigger_paddle_discount_sync"
  log_context = {"mybizz_discount_id": mybizz_discount_row['discount_id']}

  if not mybizz_discount_row:
    log("ERROR", module_name, function_name, "MyBizz discount row not provided.", log_context)
    raise ValueError("MyBizz discount row is required for Paddle sync.")

  target_mybizz_item = mybizz_discount_row.get('target_item_id')
  if not target_mybizz_item:
    log("ERROR", module_name, function_name, "Discount is not linked to a target MyBizz item.", log_context)
    raise ValueError("Discount must be linked to a target MyBizz item for Paddle sync.")

    # Determine Paddle restriction type based on MyBizz item type
  paddle_restriction_payload = {}
  if target_mybizz_item['item_type'] in ['product', 'service']:
    if not target_mybizz_item['paddle_product_id']:
      raise ValueError(f"Target MyBizz item '{target_mybizz_item['name']}' is not synced to Paddle (missing paddle_product_id). Cannot create restricted discount.")
    paddle_restriction_payload['restrict_to_products'] = [target_mybizz_item['paddle_product_id']]
  elif target_mybizz_item['item_type'] == 'subscription_plan':
    # This item is a GLT plan. It links to a `prices` row, which has the `paddle_price_id`.
    price_row_for_plan = target_mybizz_item.get('default_price_id') # Link to prices table
    if not price_row_for_plan or not price_row_for_plan['paddle_price_id']:
      raise ValueError(f"Target MyBizz subscription plan '{target_mybizz_item['name']}' is not synced to a Paddle Price (missing paddle_price_id). Cannot create restricted discount.")
    paddle_restriction_payload['restrict_to_prices'] = [price_row_for_plan['paddle_price_id']]
  else:
    raise ValueError(f"Unsupported target item type '{target_mybizz_item['item_type']}' for discount restriction.")

    # Combine base payload with restrictions
  final_paddle_payload = {**paddle_payload_parts_for_creation_or_update, **paddle_restriction_payload}
  log_context['final_paddle_payload_keys'] = list(final_paddle_payload.keys())

  existing_paddle_id = mybizz_discount_row.get('paddle_id')

  try:
    if not existing_paddle_id:
      log("INFO", module_name, function_name, "Creating new discount in Paddle.", log_context)
      # Ensure all required fields for Paddle creation are in final_paddle_payload
      # (e.g., description, type, amount/rate, status, enabled_for_checkout)
      if 'description' not in final_paddle_payload: 
        final_paddle_payload['description'] = mybizz_discount_row['discount_name']
      if 'type' not in final_paddle_payload: 
        final_paddle_payload['type'] = mybizz_discount_row['type']
        # ... add other required fields if not already in paddle_payload_parts ...

      created_paddle_discount = create_paddle_discount(final_paddle_payload) # From paddle_api_client
      new_paddle_id = created_paddle_discount.get('id')
      if new_paddle_id:
        mybizz_discount_row.update(
          paddle_id=new_paddle_id,
          paddle_created_at=_parse_datetime_from_paddle(created_paddle_discount.get('created_at')), # Helper needed
          paddle_updated_at=_parse_datetime_from_paddle(created_paddle_discount.get('updated_at'))
        )
        log("INFO", module_name, function_name, f"Paddle discount created: {new_paddle_id}", log_context)
      else:
        raise Exception("Paddle discount creation failed to return an ID.")
    else:
      # Update existing Paddle discount (only mutable fields)
      # Paddle does not allow updating type, code, rate, amount, currency_code, restrictions easily.
      # Our UI prevents editing these for synced discounts.
      # So, update_payload should only contain fields like description, status, usage_limit, expires_at, recurring settings.
      log("INFO", module_name, function_name, f"Updating existing Paddle discount: {existing_paddle_id}", log_context)

      # Construct update payload carefully with only mutable fields
      paddle_update_payload = {}
      if 'description' in final_paddle_payload: 
        paddle_update_payload['description'] = final_paddle_payload['description']
      if 'status' in final_paddle_payload: 
        paddle_update_payload['status'] = final_paddle_payload['status'] # e.g. 'archived'
      if 'enabled_for_checkout' in final_paddle_payload: 
        paddle_update_payload['enabled_for_checkout'] = final_paddle_payload['enabled_for_checkout']
      if 'recurring' in final_paddle_payload: 
        paddle_update_payload['recurring'] = final_paddle_payload['recurring']
      if 'maximum_recurring_intervals' in final_paddle_payload: 
        paddle_update_payload['maximum_recurring_intervals'] = final_paddle_payload['maximum_recurring_intervals']
      if 'usage_limit' in final_paddle_payload: 
        paddle_update_payload['usage_limit'] = final_paddle_payload['usage_limit']
      if 'expires_at' in final_paddle_payload: 
        paddle_update_payload['expires_at'] = final_paddle_payload['expires_at']
        # custom_data can also be updated
        # if 'custom_data' in final_paddle_payload: paddle_update_payload['custom_data'] = final_paddle_payload['custom_data']


      if paddle_update_payload: # Only call update if there's something to update
        updated_paddle_discount = update_paddle_discount(existing_paddle_id, paddle_update_payload) # From paddle_api_client
        mybizz_discount_row.update(
          paddle_updated_at=_parse_datetime_from_paddle(updated_paddle_discount.get('updated_at'))
        )
        log("INFO", module_name, function_name, f"Paddle discount updated: {existing_paddle_id}", log_context)
      else:
        log("INFO", module_name, function_name, "No mutable fields to update in Paddle for existing discount.", log_context)


  except anvil.http.HttpError as http_err:
    log("ERROR", module_name, function_name, f"Paddle API Error during discount sync: {http_err.status}", {**log_context, "paddle_error": http_err.content})
    raise # Re-raise to be caught by calling function
  except Exception as e:
    log("ERROR", module_name, function_name, f"Unexpected error during Paddle discount sync: {str(e)}", {**log_context, "trace": traceback.format_exc()})
    raise

def _parse_datetime_from_paddle(datetime_str):
  """Safely parses ISO 8601 datetime string from Paddle."""
  if not datetime_str: 
    return None
  try:
    return dateutil.parser.isoparse(datetime_str)
  except (ValueError, TypeError) as e: # <<<--- MODIFIED: Catch specific exceptions
    # Log the error if desired, e.g., using your log function
    # log("WARNING", "sm_discount_mod", "_parse_datetime_from_paddle", f"Could not parse datetime string '{datetime_str}': {e}")
    print(f"Warning (sm_discount_mod._parse_datetime_from_paddle): Could not parse datetime string '{datetime_str}': {e}")
    return None

# --- Callable Functions for Client ---

@anvil.server.callable
def save_mybizz_discount(discount_data_from_client):
    """
    Main function to create/update a discount in MyBizz and sync to Paddle.
    Client sends a dictionary. If 'mybizz_discount_anvil_id' is present, it's an update.
    For Phase 7, "update" is conceptual (archive old, create new) due to UI model.
    This function will focus on CREATION for Phase 7.
    Archiving/status change will be handled by 'set_mybizz_discount_status'.
    """
    _ensure_admin()
    module_name = "sm_discount_mod"
    function_name = "save_mybizz_discount (Create New)"
    
    # For Phase 7, this function is only for CREATING new discounts.
    # The UI model is "archive and recreate" for changes to core fields.
    
    try:
        validated_db_data, paddle_payload_parts = _validate_discount_data_for_save(discount_data_from_client, is_update=False)
        
        # Generate MyBizz PK
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        mybizz_pk = f"DSC-{timestamp_str}"
        while app_tables.discount.get(discount_id=mybizz_pk): # Ensure uniqueness
            timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
            mybizz_pk = f"DSC-{timestamp_str}"
        validated_db_data['discount_id'] = mybizz_pk
        
        # Add Anvil timestamps
        now = datetime.now(timezone.utc)
        validated_db_data['created_at_anvil'] = now
        validated_db_data['updated_at_anvil'] = now
        
        # Add to MyBizz DB
        new_discount_row = app_tables.discount.add_row(**validated_db_data)
        log("INFO", module_name, function_name, f"New discount created in MyBizz DB: {mybizz_pk}", {"data": validated_db_data})
        
        # Trigger Paddle Sync
        _trigger_paddle_discount_sync(new_discount_row, paddle_payload_parts)
        
        # Return some details of the created discount
        return {
            "discount_anvil_id": new_discount_row.get_id(),
            "mybizz_discount_id": new_discount_row['discount_id'],
            "coupon_code": new_discount_row['coupon_code'],
            "discount_name": new_discount_row['discount_name'],
            "paddle_id": new_discount_row.get('paddle_id') # Will be populated by sync
        }
        
    except ValueError as ve: # Validation errors
        log("WARNING", module_name, function_name, f"Validation error: {str(ve)}", {"input_data": discount_data_from_client})
        raise anvil.server.ValidationError(str(ve)) # Send specific error to client
    except anvil.http.HttpError as http_err: # Paddle API errors
        log("ERROR", module_name, function_name, f"Paddle API error during save: {http_err.status}", {"input_data": discount_data_from_client, "paddle_error": http_err.content})
        # Discount is saved in MyBizz, but Paddle sync failed. Client needs to know.
        raise # Re-raise to client
    except Exception as e:
        log("CRITICAL", module_name, function_name, f"Unexpected error saving discount: {str(e)}", {"input_data": discount_data_from_client, "trace": traceback.format_exc()})
        raise anvil.server.AnvilWrappedError(f"An unexpected error occurred: {str(e)}")


@anvil.server.callable
def set_mybizz_discount_status(discount_anvil_id, new_mybizz_status):
    """
    Updates the status of a MyBizz discount and syncs this status to Paddle.
    (e.g., 'active' -> 'archived' in MyBizz and Paddle).
    """
    _ensure_admin()
    module_name = "sm_discount_mod"
    function_name = "set_mybizz_discount_status"
    log_context = {"discount_anvil_id": discount_anvil_id, "new_mybizz_status": new_mybizz_status}

    if new_mybizz_status not in VALID_MYBIZZ_STATUSES:
        raise ValueError(f"Invalid status. Must be one of {VALID_MYBIZZ_STATUSES}.")

    discount_row = app_tables.discount.get_by_id(discount_anvil_id)
    if not discount_row:
        raise ValueError("Discount not found.")

    if discount_row['status'] == new_mybizz_status:
        log("INFO", module_name, function_name, "Status is already set to the desired state.", log_context)
        return {"message": "Status already as requested.", "status": discount_row['status']}

    # Update MyBizz status
    discount_row.update(status=new_mybizz_status, updated_at_anvil=datetime.now(timezone.utc))
    log("INFO", module_name, function_name, f"MyBizz discount status updated to {new_mybizz_status}.", log_context)

    # Prepare Paddle update payload
    # Paddle status: 'active', 'archived', 'expired'
    # MyBizz 'active' -> Paddle 'active', 'enabled_for_checkout': True
    # MyBizz 'archived' -> Paddle 'archived', 'enabled_for_checkout': False
    paddle_update_payload = {}
    if new_mybizz_status == 'active':
        paddle_update_payload['status'] = 'active'
        paddle_update_payload['enabled_for_checkout'] = True
    elif new_mybizz_status == 'archived':
        paddle_update_payload['status'] = 'archived'
        paddle_update_payload['enabled_for_checkout'] = False
    
    # Trigger sync for status change (this will call update_paddle_discount)
    try:
        # _trigger_paddle_discount_sync expects the full row and the parts to update
        # We are only updating status-related fields in Paddle here.
        # The _trigger_paddle_discount_sync needs to be smart enough to handle this.
        # For now, let's assume it can take a minimal payload for update.
        # A more direct call to update_paddle_discount might be cleaner here.
        
        if discount_row.get('paddle_id') and paddle_update_payload:
            log("INFO", module_name, function_name, f"Syncing status to Paddle: {paddle_update_payload}", log_context)
            update_paddle_discount(discount_row['paddle_id'], paddle_update_payload)
            log("INFO", module_name, function_name, "Paddle status sync successful.", log_context)
        elif not discount_row.get('paddle_id'):
            log("WARNING", module_name, function_name, "No Paddle ID for this discount. Skipping Paddle status sync.", log_context)

    except anvil.http.HttpError as http_err:
        log("ERROR", module_name, function_name, f"Paddle API error during status sync: {http_err.status}", {**log_context, "paddle_error": http_err.content})
        # MyBizz status is updated, but Paddle failed.
        raise Exception(f"MyBizz status updated to '{new_mybizz_status}', but Paddle sync failed: {http_err.status}. Please check Paddle dashboard.")
    except Exception as e:
        log("ERROR", module_name, function_name, f"Unexpected error during Paddle status sync: {str(e)}", {**log_context, "trace": traceback.format_exc()})
        raise Exception(f"MyBizz status updated to '{new_mybizz_status}', but Paddle sync encountered an error: {str(e)}. Please check Paddle dashboard.")

    return {"message": f"Discount status set to {new_mybizz_status} and sync attempted.", "status": new_mybizz_status}


@anvil.server.callable
def get_mybizz_discount_details(discount_anvil_id):
    """Fetches full details for a single MyBizz discount for display."""
    _ensure_admin()
    discount_row = app_tables.discount.get_by_id(discount_anvil_id)
    if not discount_row:
        return None
    
    # Convert row to dict, handle linked target_item_id
    details = dict(discount_row)
    if discount_row['target_item_id']:
        details['target_item_id'] = discount_row['target_item_id'].get_id() # Send Anvil ID
        details['target_item_name_display'] = f"{discount_row['target_item_id']['name']} ({discount_row['target_item_id']['item_id']} - {discount_row['target_item_id']['item_type']})"
    
    # Convert custom_data SimpleObject to JSON string for TextArea if it exists
    if details.get('custom_data') is not None:
        try:
            details['custom_data_mybizz_json_str'] = json.dumps(details['custom_data'], indent=2)
        except TypeError:
            details['custom_data_mybizz_json_str'] = str(details['custom_data']) # Fallback
    else:
        details['custom_data_mybizz_json_str'] = ""
        
    return details

@anvil.server.callable
def list_mybizz_discounts_for_dropdown():
    """Fetches MyBizz discounts for populating a dropdown."""
    _ensure_admin()
    discounts = app_tables.discount.search(tables.order_by("coupon_code"))
    return [(f"{d['coupon_code'] or d['discount_name']} ({d['status']})", d.get_id()) for d in discounts]

@anvil.server.callable
def get_all_discounts_for_report_list(status_filter=None, type_filter=None, sort_by=None):
  """
    Fetches a list of all discounts from the 'discount' table,
    with filtering and sorting capabilities.
    Includes the name of the target item if specified.
    Admin access required.
    """
  _ensure_admin() # Assumes _ensure_admin is defined or imported in this module

  module_name = "sm_discount_mod"
  function_name = "get_all_discounts_for_report_list"
  log_context = {"status_filter": status_filter, "type_filter": type_filter, "sort_by": sort_by}

  query_conditions = []

  # Apply status filter
  if status_filter and status_filter.lower() != 'all':
    query_conditions.append(app_tables.discount.status == status_filter.lower())

    # Apply type filter
  if type_filter and type_filter.lower() != 'all':
    # Ensure type_filter matches values in discount.type (e.g., 'percentage', 'flat')
    query_conditions.append(app_tables.discount.type == type_filter.lower())

    # Determine sorting order
  order_by_clause = None
  if sort_by:
    if sort_by == "coupon_code_asc":
      order_by_clause = tables.order_by("coupon_code", ascending=True)
    elif sort_by == "coupon_code_desc":
      order_by_clause = tables.order_by("coupon_code", ascending=False)
    elif sort_by == "discount_name_asc":
      order_by_clause = tables.order_by("discount_name", ascending=True)
    elif sort_by == "discount_name_desc":
      order_by_clause = tables.order_by("discount_name", ascending=False)
    elif sort_by == "status_asc": # Simple string sort for status
      order_by_clause = tables.order_by("status", ascending=True)
    elif sort_by == "expires_at_desc":
      order_by_clause = tables.order_by("expires_at", ascending=False)
    elif sort_by == "expires_at_asc":
      order_by_clause = tables.order_by("expires_at", ascending=True)
    elif sort_by == "times_used_desc":
      order_by_clause = tables.order_by("times_used", ascending=False)
      # Add more sort options here if needed

  if not order_by_clause: # Default sort
    order_by_clause = tables.order_by("coupon_code", ascending=True)

    # Construct the final query
  if query_conditions:
    final_query = q.all_of(*query_conditions)
    discount_rows = app_tables.discount.search(final_query, order_by_clause)
  else: # No filters, search all
    discount_rows = app_tables.discount.search(order_by_clause)

  results = []
  for discount_row in discount_rows:
    discount_dict = dict(discount_row) # Convert row to dictionary

    # Fetch target item name if target_item_id exists
    target_item_name = "All Items" # Default if no specific target
    if discount_row['target_item_id']: # This is a link to the 'items' table
      try:
        # Accessing linked row directly. Ensure 'target_item_id' is correctly populated.
        linked_item_row = discount_row['target_item_id'] 
        if linked_item_row and linked_item_row['name']:
          target_item_name = linked_item_row['name']
        elif linked_item_row: # Linked row exists but name is missing
          target_item_name = f"Item ID: {linked_item_row['item_id']}" 
      except Exception as e:
        log("WARNING", module_name, function_name, 
            f"Could not fetch target item name for discount {discount_row['discount_id']}: {e}", 
            log_context)
        target_item_name = "Error fetching target"

    discount_dict['target_item_name'] = target_item_name

    # Ensure all fields expected by the client are present
    discount_dict.setdefault('coupon_code', None)
    discount_dict.setdefault('discount_name', None)
    discount_dict.setdefault('status', None)
    discount_dict.setdefault('type', None)
    discount_dict.setdefault('amount_rate', None)
    discount_dict.setdefault('amount_amount', None)
    discount_dict.setdefault('amount_currency_code', None)
    discount_dict.setdefault('times_used', 0)
    discount_dict.setdefault('usage_limit', None)
    discount_dict.setdefault('expires_at', None)
    discount_dict.setdefault('discount_id', discount_row.get_id()) # Add Anvil row ID as 'discount_id' if PK is different

    results.append(discount_dict)

  log("INFO", module_name, function_name, f"Fetched {len(results)} discounts for report list.", log_context)
  return results


# Discount Usage Analytics Report Function
@anvil.server.callable
def get_discount_usage_data(start_date=None, end_date=None, status_filter=None):
  """
    Fetches data for the Discount Usage Analytics report.
    Admin access required.
    Filters by date range (for transactions) and discount status.
    Only includes discounts with activity in the period if a date range is applied.
    """
  _ensure_admin() # Enforce admin-only access

  module_name = "sm_discount_mod"
  function_name = "get_discount_usage_data"
  log_context = {"start_date": start_date, "end_date": end_date, "status_filter": status_filter}

  system_currency_info = helper_functions.get_system_currency()
  system_currency_code = None

  if system_currency_info and system_currency_info.get('currency'):
    system_currency_code = system_currency_info['currency'].upper()
  else:
    log("CRITICAL", module_name, function_name, "System currency not configured or get_system_currency() returned None/invalid. Aborting report.", log_context)
    return [] # Abort if system currency is not properly configured

  discount_query_args = {}
  if status_filter and status_filter != "All":
    discount_query_args['status'] = status_filter.lower()

  all_relevant_discounts = app_tables.discount.search(**discount_query_args)

  results = []

  if start_date and isinstance(start_date, date) and not isinstance(start_date, datetime):
    start_date = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, 0, tzinfo=timezone.utc)
  elif start_date and isinstance(start_date, datetime) and start_date.tzinfo is None:
    start_date = start_date.replace(tzinfo=timezone.utc)

  if end_date and isinstance(end_date, date) and not isinstance(end_date, datetime):
    end_date = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
  elif end_date and isinstance(end_date, datetime) and end_date.tzinfo is None:
    end_date = end_date.replace(tzinfo=timezone.utc)

  for discount_row in all_relevant_discounts:
    transaction_query_parts = [
      q.status == 'paid',
      q.discount_id == discount_row
    ]

    if start_date and end_date:
      transaction_query_parts.append(q.billed_at.between(start_date, end_date, min_inclusive=True, max_inclusive=True))
    elif start_date:
      transaction_query_parts.append(q.billed_at >= start_date)
    elif end_date:
      transaction_query_parts.append(q.billed_at <= end_date)

    period_transactions = app_tables.transaction.search(*transaction_query_parts)

    current_period_revenue_minor_units = 0
    current_period_transactions_count = 0

    for txn in period_transactions:
      earnings_str = txn['details_totals_earnings']
      if earnings_str is not None:
        try:
          current_period_revenue_minor_units += int(str(earnings_str))
        except (ValueError, TypeError) as e:
          log("WARNING", module_name, function_name, 
              f"Could not convert earnings '{earnings_str}' to int for transaction {txn.get('paddle_id', 'N/A')}. Error: {e}", 
              log_context)
      current_period_transactions_count += 1

    date_filter_active = start_date is not None or end_date is not None

    if date_filter_active:
      if current_period_transactions_count == 0:
        continue 

    results.append({
      'anvil_discount_id': discount_row.get_id(),
      'coupon_code': discount_row['coupon_code'],
      'description': discount_row['description'],
      'status': discount_row['status'],
      'times_used': discount_row['times_used'] or 0,
      'total_associated_revenue_in_period': current_period_revenue_minor_units,
      'transactions_in_period': current_period_transactions_count,
      'system_currency_code': system_currency_code 
    })

  log("INFO", module_name, function_name, f"Fetched {len(results)} discount usage data entries.", log_context)
  return results


