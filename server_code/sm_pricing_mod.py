# Server Module: sm_pricing_mod.py
# Manages Prices and Price Overrides, aligned with Paddle structure.
# Includes Paddle Price sync logic and validation.

import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime, timezone
import traceback

# Import RBAC functions (adjust path if necessary)
from .sessions_server import is_admin_user, is_owner_user

# Import Paddle API client functions (adjust path if necessary)
from .paddle_api_client import create_paddle_price, update_paddle_price
# Placeholder for future Paddle Price archival function
# from .paddle_api_client import archive_paddle_price

# --- Constants ---
VALID_PRICE_TYPES = ['one_time', 'recurring']
VALID_BILLING_INTERVALS = ['day', 'week', 'month', 'year']
VALID_TAX_MODES = ['account_setting', 'internal', 'external']
VALID_PRICE_STATUSES = ['active', 'archived'] # Paddle uses these text statuses

# --- Helper to check admin permissions ---
def _ensure_admin():
  """Raises PermissionDenied if the current user is not an admin."""
  if not is_admin_user():
    raise anvil.server.PermissionDenied("Administrator privileges required.")

# --- Validation Helper: Price Data ---
def _validate_price_data(price_data, is_update=False):
  """Validates input data for creating/updating a price."""
  if not isinstance(price_data, dict):
    raise TypeError("Price data must be a dictionary.")

    validated_data = {}
  # Define fields and their expected types/constraints
  field_definitions = {
    'item_id': {'type': app_tables.items, 'required_create': True, 'updatable': False},
    'description': {'type': str, 'required_create': True, 'updatable': True, 'max_len': 255}, # Example max_len
    'price_type': {'type': str, 'required_create': True, 'updatable': False, 'valid_values': VALID_PRICE_TYPES},
    'unit_price_amount': {'type': str, 'required_create': True, 'updatable': True, 'is_digit': True},
    'unit_price_currency_code': {'type': str, 'required_create': True, 'updatable': True, 'len': 3, 'is_alpha': True},
    'tax_mode': {'type': str, 'required_create': True, 'updatable': True, 'valid_values': VALID_TAX_MODES},
    'status': {'type': str, 'required_create': False, 'updatable': True, 'valid_values': VALID_PRICE_STATUSES, 'default': 'active'},
    'billing_cycle_interval': {'type': str, 'required_create': False, 'updatable': True, 'valid_values': VALID_BILLING_INTERVALS},
    'billing_cycle_frequency': {'type': int, 'required_create': False, 'updatable': True, 'min_val': 1},
    'trial_period_interval': {'type': str, 'required_create': False, 'updatable': True, 'valid_values': VALID_BILLING_INTERVALS},
    'trial_period_frequency': {'type': int, 'required_create': False, 'updatable': True, 'min_val': 1},
    'quantity_minimum': {'type': int, 'required_create': False, 'updatable': True, 'min_val': 1, 'default': 1},
    'quantity_maximum': {'type': int, 'required_create': False, 'updatable': True, 'min_val': 1, 'default': 1},
    'custom_data': {'type': dict, 'required_create': False, 'updatable': True}
  }

  # --- Check Required Fields (Create) ---
  if not is_update:
    for field, definition in field_definitions.items():
      if definition.get('required_create'):
        if field not in price_data or price_data[field] is None or price_data[field] == "":
          raise ValueError(f"Missing required field: '{field}'.")

    # --- Validate All Provided Fields ---
    data_to_validate = price_data if is_update else validated_data # Use validated for create required fields
  for field, value in price_data.items():
    if field not in field_definitions:
      # Allow extra fields if needed, or raise error for unknown fields
      # print(f"Warning: Unknown field '{field}' provided in price_data.")
      continue # Skip validation for unknown fields for now

      definition = field_definitions[field]

    # Check if field is updatable
    if is_update and not definition.get('updatable', True):
      raise ValueError(f"Field '{field}' cannot be updated.")

      # Add to validated_data if present in input (even if None for optional fields)
      validated_data[field] = value

    # Perform checks only if value is not None
    if value is not None:
      expected_type = definition.get('type')
      if expected_type and not isinstance(value, expected_type):
        # Special check for Link types (allow Row objects)
        if expected_type in [app_tables.items, app_tables.prices]: # Add other Link types if needed
          if not hasattr(value, 'get_id'):
            raise TypeError(f"Field '{field}' must be a valid Anvil Data Table Row object.")
        else:
          raise TypeError(f"Field '{field}' has incorrect type. Expected {expected_type.__name__}.")

          if 'valid_values' in definition and value not in definition['valid_values']:
            raise ValueError(f"Field '{field}' has invalid value '{value}'. Must be one of {definition['valid_values']}.")

            if definition.get('is_digit') and not value.isdigit():
              raise ValueError(f"Field '{field}' must be a string containing only digits.")

      if 'len' in definition and len(value) != definition['len']:
        raise ValueError(f"Field '{field}' must have a length of {definition['len']}.")

        if definition.get('is_alpha') and not value.isalpha():
          raise ValueError(f"Field '{field}' must contain only letters.")

          if 'min_val' in definition and value < definition['min_val']:
            raise ValueError(f"Field '{field}' must be at least {definition['min_val']}.")

            if 'max_len' in definition and len(value) > definition['max_len']:
              raise ValueError(f"Field '{field}' cannot exceed {definition['max_len']} characters.")

    # --- Cross-Field / Type-Specific Validation ---
    current_price_type = validated_data.get('price_type') if not is_update else price_data.get('price_type_from_db')

  if current_price_type == 'recurring':
    # Check if required recurring fields are present and valid
    billing_interval = validated_data.get('billing_cycle_interval')
    billing_frequency = validated_data.get('billing_cycle_frequency')
    if billing_interval is None or billing_frequency is None:
      # Only raise error if creating, or if explicitly trying to set one without the other during update
      if not is_update or ('billing_cycle_interval' in price_data or 'billing_cycle_frequency' in price_data):
        raise ValueError("Fields 'billing_cycle_interval' and 'billing_cycle_frequency' are required for recurring prices.")
  elif current_price_type == 'one_time':
    # Check if recurring fields are incorrectly set
    if validated_data.get('billing_cycle_interval') is not None or validated_data.get('billing_cycle_frequency') is not None:
      raise ValueError("Billing cycle fields are not applicable for one_time prices.")
      if validated_data.get('trial_period_interval') is not None or validated_data.get('trial_period_frequency') is not None:
        raise ValueError("Trial period fields are not applicable for one_time prices.")

    # Set defaults for optional fields if not provided during creation
    if not is_update:
      for field, definition in field_definitions.items():
        if field not in validated_data and 'default' in definition:
          validated_data[field] = definition['default']

  return validated_data


# --- Validation Helper: Price Override Data ---
def _validate_override_data(override_data, is_update=False):
  """Validates input data for creating/updating a price override."""
  if not isinstance(override_data, dict):
    raise TypeError("Override data must be a dictionary.")

    validated_data = {}
  # Field definitions
  field_definitions = {
    'price_id': {'type': app_tables.prices, 'required_create': True, 'updatable': False},
    'country_codes': {'type': list, 'required_create': True, 'updatable': True}, # Stored in Simple Object
    'currency_code': {'type': str, 'required_create': True, 'updatable': True, 'len': 3, 'is_alpha': True},
    'amount': {'type': str, 'required_create': True, 'updatable': True, 'is_digit': True}
  }

  # Check required fields for creation
  if not is_update:
    for field, definition in field_definitions.items():
      if definition.get('required_create'):
        if field not in override_data or override_data[field] is None or override_data[field] == "":
          raise ValueError(f"Missing required field: '{field}'.")

    # Validate all provided fields
    for field, value in override_data.items():
      if field not in field_definitions:
        continue # Ignore unknown fields

        definition = field_definitions[field]

      if is_update and not definition.get('updatable', True):
        raise ValueError(f"Field '{field}' cannot be updated.")

        validated_data[field] = value

      if value is not None:
        expected_type = definition.get('type')
        if expected_type and not isinstance(value, expected_type):
          if expected_type == app_tables.prices: # Link type check
            if not hasattr(value, 'get_id'): 
              raise TypeError(f"Field '{field}' must be a valid Anvil Data Table Row object.")
          else: 
            raise TypeError(f"Field '{field}' has incorrect type. Expected {expected_type.__name__}.")

            if field == 'country_codes':
              if not all(isinstance(c, str) and len(c) == 2 and c.isupper() for c in value):
                raise TypeError("Field 'country_codes' must be a list of 2-letter uppercase country codes.")
            elif field == 'currency_code':
              if definition.get('len') and len(value) != definition['len']: 
                raise ValueError(f"Field '{field}' must have a length of {definition['len']}.")
                if definition.get('is_alpha') and not value.isalpha(): 
                  raise ValueError(f"Field '{field}' must contain only letters.")
            elif field == 'amount':
              if definition.get('is_digit') and not value.isdigit(): 
                raise ValueError(f"Field '{field}' must be a string containing only digits (minor units).")

  return validated_data


# --- Helper: Trigger Paddle Price Sync ---
# --- Helper: Trigger Paddle Price Sync ---
def _trigger_paddle_price_sync(price_row):
  """
    Creates or updates the corresponding Paddle Price for a MyBizz price row.
    Updates the paddle_price_id on the price row.
    """
  if not price_row:
    print("Error: Cannot sync Paddle Price, invalid price_row provided.")
    return

    item_row = price_row.get('item_id')
  if not item_row:
    print(f"WARNING: Price record {price_row['price_id']} is not linked to a valid item. Skipping Paddle sync.")
    return

    # --- Get Parent Paddle Product ID ---
    parent_paddle_product_id = item_row.get('paddle_product_id')
  if not parent_paddle_product_id:
    print(f"Warning: Cannot sync Paddle Price {price_row['price_id']} yet. Parent item {item_row['item_id']} has no paddle_product_id. Skipping Paddle sync.")
    return # Skip sync for now

    # --- Fetch Overrides ---
    overrides = app_tables.price_unit_price_overrides.search(price_id=price_row)
  paddle_overrides = []
  for ovr in overrides:
    country_codes_list = ovr['country_codes'] if isinstance(ovr['country_codes'], list) else []
    if not country_codes_list: # Skip overrides with no countries
      print(f"Warning: Skipping override {ovr['id']} for price {price_row['price_id']} due to empty country_codes list.")
      continue
      paddle_overrides.append({
        "country_codes": country_codes_list,
        "unit_price": {
          "amount": ovr['amount'],
          "currency_code": ovr['currency_code']
        }
      })

    # --- Prepare Paddle Price Data ---
    paddle_price_data = {
      "product_id": parent_paddle_product_id,
      "description": price_row['description'],
      "unit_price": {
        "amount": price_row['unit_price_amount'],
        "currency_code": price_row['unit_price_currency_code']
      },
      "name": price_row['description'], # Paddle API v1 often uses 'name' for Price too
      "tax_mode": price_row['tax_mode'],
      "status": price_row['status'], # Assumes MyBizz uses 'active'/'archived'
      "quantity": {
        "minimum": price_row.get('quantity_minimum', 1),
        "maximum": price_row.get('quantity_maximum', 1)
      },
      "custom_data": {
        "mybizz_price_id": price_row['price_id'],
        "mybizz_item_id": item_row['item_id'],
        **(price_row.get('custom_data') or {})
      }
    }

  if price_row['price_type'] == 'recurring':
    if price_row.get('billing_cycle_interval') and price_row.get('billing_cycle_frequency'):
      paddle_price_data["billing_cycle"] = {
        "interval": price_row['billing_cycle_interval'],
        "frequency": price_row['billing_cycle_frequency']
      }
      if price_row.get('trial_period_interval') and price_row.get('trial_period_frequency'):
        paddle_price_data["trial_period"] = {
          "interval": price_row['trial_period_interval'],
          "frequency": price_row['trial_period_frequency']
        }

    if paddle_overrides:
      paddle_price_data["unit_price_overrides"] = paddle_overrides

  # --- PADDLE API VALIDATION ---
  if not paddle_price_data.get('product_id'):
    raise ValueError("Internal Error: Cannot sync Price, missing parent paddle_product_id.")
    if not paddle_price_data.get('description'):
      raise ValueError("Paddle API Error: Price 'description' is required.")
  if not paddle_price_data.get('unit_price'):
    raise ValueError("Paddle API Error: Price 'unit_price' is required.")
    if not paddle_price_data['unit_price'].get('amount') or not paddle_price_data['unit_price'].get('currency_code'):
      raise ValueError("Paddle API Error: Price 'unit_price' requires 'amount' (string digits) and 'currency_code' (3 letters).")
  if price_row['price_type'] == 'recurring' and not paddle_price_data.get('billing_cycle'):
    # Check if interval/frequency were actually provided in the source row before raising
    if price_row.get('billing_cycle_interval') or price_row.get('billing_cycle_frequency'):
      raise ValueError("Paddle API Error: Price 'billing_cycle' requires both interval and frequency for recurring prices.")
      # If neither was provided, maybe it's an incomplete definition? Or allow saving without cycle? For now, require both if type is recurring.
    elif not price_row.get('billing_cycle_interval') or not price_row.get('billing_cycle_frequency'):
      raise ValueError("Paddle API Error: Price 'billing_cycle' (interval and frequency) is required for recurring prices.")

    # Validate override structure if present
    if 'unit_price_overrides' in paddle_price_data:
      if not isinstance(paddle_price_data['unit_price_overrides'], list):
        raise ValueError("Paddle API Error: 'unit_price_overrides' must be a list.")
        for ovr in paddle_price_data['unit_price_overrides']:
          if not isinstance(ovr.get('country_codes'), list) or not ovr.get('unit_price') or not isinstance(ovr['country_codes'], list) or len(ovr['country_codes']) == 0:
            raise ValueError("Paddle API Error: Each override requires 'country_codes' (non-empty list) and 'unit_price' (object).")
            if not ovr['unit_price'].get('amount') or not ovr['unit_price'].get('currency_code'):
              raise ValueError("Paddle API Error: Override 'unit_price' requires 'amount' and 'currency_code'.")
  # --- END PADDLE API VALIDATION ---

  # --- Call Paddle API ---
  existing_paddle_price_id = price_row.get('paddle_price_id')

  try:
    if not existing_paddle_price_id:
      # Create New Paddle Price
      print(f"Creating Paddle Price for MyBizz price: {price_row['price_id']}")
      # Ensure paddle_api_client functions are imported
      created_paddle_price = create_paddle_price(paddle_price_data)
      new_paddle_price_id = created_paddle_price.get('id')

      if new_paddle_price_id:
        print(f"Paddle Price created: {new_paddle_price_id}")
        # Update the price row with the new Paddle Price ID
        price_row.update(paddle_price_id=new_paddle_price_id)
      else:
        print("Error: Paddle API did not return an ID for the new price.")
        raise Exception("Paddle Price creation failed (no ID returned).")
    else:
      # Update Existing Paddle Price
      print(f"Updating Paddle Price {existing_paddle_price_id} for MyBizz price: {price_row['price_id']}")
      # Prepare update payload
      update_payload = paddle_price_data.copy()
      # Remove fields not allowed/recommended in PATCH
      update_payload.pop('product_id', None)

      # --- PADDLE API VALIDATION (for update specific rules if any) ---
      # Example: Check if description is empty if trying to update it
      # if 'description' in update_payload and not update_payload['description']:
      #     raise ValueError("Paddle API Error: Price 'description' cannot be empty on update.")
      # --- END PADDLE API VALIDATION ---

      updated_paddle_price = update_paddle_price(existing_paddle_price_id, update_payload)
      print(f"Paddle Price updated: {updated_paddle_price.get('id')}")

  except anvil.http.HttpError as e:
    print(f"Paddle API Error syncing price {price_row['price_id']}: {e.status} - {e.content}")
    raise Exception(f"Paddle API sync failed: {e.status}") # Re-raise
  except Exception as e:
    print(f"Error during Paddle Price sync for price {price_row['price_id']}: {e}")
    traceback.print_exc() # Assumes traceback is imported
    raise Exception(f"Paddle sync failed: {e}")


# --- Create Price ---
@anvil.server.callable
def create_price(price_data):
    """ Creates a new price linked to an item, triggers Paddle Price sync. """
    _ensure_admin()
    try:
        validated_data = _validate_price_data(price_data, is_update=False)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid input data: {e}")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    price_id = f"PRC-{timestamp_str}"
    if app_tables.prices.get(price_id=price_id):
         raise Exception("Failed to generate unique price ID.")

    new_price = None
    try:
        # Prepare row data using validated fields and defaults
        row_data = {
            'price_id': price_id,
            'item_id': validated_data['item_id'],
            'description': validated_data['description'],
            'price_type': validated_data['price_type'],
            'unit_price_amount': validated_data['unit_price_amount'],
            'unit_price_currency_code': validated_data['unit_price_currency_code'],
            'tax_mode': validated_data['tax_mode'],
            'status': validated_data.get('status', 'active'),
            'billing_cycle_interval': validated_data.get('billing_cycle_interval'),
            'billing_cycle_frequency': validated_data.get('billing_cycle_frequency'),
            'trial_period_interval': validated_data.get('trial_period_interval'),
            'trial_period_frequency': validated_data.get('trial_period_frequency'),
            'quantity_minimum': validated_data.get('quantity_minimum', 1),
            'quantity_maximum': validated_data.get('quantity_maximum', 1),
            'custom_data': validated_data.get('custom_data'),
            'created_at_anvil': datetime.now(timezone.utc),
            'updated_at_anvil': datetime.now(timezone.utc)
        }
        new_price = app_tables.prices.add_row(**row_data)
        item_id_str = validated_data['item_id']['item_id'] # Get string ID for logging
        print(f"Price created in MyBizz DB: {price_id} for item {item_id_str}")

        # Trigger Paddle Price Sync
        try:
            _trigger_paddle_price_sync(new_price)
        except Exception as sync_err:
            print(f"WARNING: Paddle Price sync failed after creating price {price_id}: {sync_err}")
            pass # Log only for now

        return new_price
    except Exception as e:
        item_id_str = validated_data.get('item_id', {}).get('item_id', 'UNKNOWN')
        print(f"Error creating price for item '{item_id_str}': {e}")
        traceback.print_exc()
        raise Exception(f"Could not create price. Error: {e}")

# --- Update Price ---
@anvil.server.callable
def update_price(price_id, update_data):
    """ Updates an existing price, triggers Paddle Price sync. """
    _ensure_admin()
    if not isinstance(price_id, str) or not price_id: 
      raise ValueError("Invalid price_id provided.")
    price_row = app_tables.prices.get(price_id=price_id)
    if not price_row: 
      raise ValueError(f"Price with ID '{price_id}' not found.")

    update_data['price_type_from_db'] = price_row['price_type'] # Add context for validation
    try:
        validated_updates = _validate_price_data(update_data, is_update=True)
    except (ValueError, TypeError) as e: 
      raise ValueError(f"Invalid update data: {e}")

    # Remove fields that cannot be updated or were only for context
    validated_updates.pop('item_id', None)
    validated_updates.pop('price_type', None)
    validated_updates.pop('price_type_from_db', None)

    updates_to_apply = {k: v for k, v in validated_updates.items() if k in update_data}
    if not updates_to_apply:
        print(f"No valid fields provided to update for price '{price_id}'.")
        return price_row

    updates_to_apply['updated_at_anvil'] = datetime.now(timezone.utc)

    try:
        price_row.update(**updates_to_apply)
        print(f"Price updated in MyBizz DB: {price_id}")

        # Trigger Paddle Price Sync
        try:
            _trigger_paddle_price_sync(price_row)
        except Exception as sync_err:
            print(f"WARNING: Paddle Price sync failed after updating price {price_id}: {sync_err}")
            pass # Log only for now

        return price_row
    except Exception as e:
        print(f"Error updating price '{price_id}': {e}")
        traceback.print_exc()
        raise Exception(f"Could not update price. Error: {e}")


# --- Delete Price (Use with Caution) ---
@anvil.server.callable
def delete_price(price_id):
    """ Deletes a price and its associated overrides. """
    if not is_owner_user(): 
      raise anvil.server.PermissionDenied("Owner privileges required.")
    if not isinstance(price_id, str) or not price_id: 
      raise ValueError("Invalid price_id provided.")
    price_row = app_tables.prices.get(price_id=price_id)
    if not price_row: 
      raise ValueError(f"Price with ID '{price_id}' not found.")

    # Check active subscriptions
    try:
        active_subs = app_tables.customer_subscriptions.search(mybizz_price_id=price_row, status='active')
        if len(active_subs) > 0: 
          raise Exception(f"Cannot delete price '{price_row['description']}'. Used by {len(active_subs)} active subscription(s).")
    except tables.TableError as e:
        print(f"Warning: Could not check customer_subscriptions: {e}")
        # Decide if deletion should proceed - safer to block if check fails
        raise Exception("Cannot confirm dependencies (subscriptions). Deletion aborted.")


    # --- Placeholder for Paddle Price Archival ---
    # if price_row['paddle_price_id']:
    #     try: archive_paddle_price(price_row['paddle_price_id']) # Func in paddle_api_client
    #     except Exception as paddle_err: raise Exception(f"Failed to archive Paddle Price: {paddle_err}")

    try:
        # Delete associated overrides first
        overrides = app_tables.price_unit_price_overrides.search(price_id=price_row)
        for override in overrides: 
          override.delete()
        print(f"Deleted {len(overrides)} overrides for price {price_id}")

        price_desc_deleted = price_row['description']
        price_row.delete()
        print(f"Price deleted: {price_id} - {price_desc_deleted}")
        return True
    except Exception as e:
        print(f"Error deleting price '{price_id}': {e}")
        traceback.print_exc()
        raise Exception(f"Could not delete price. Error: {e}")


# === Price Override Functions ===

@anvil.server.callable
def create_price_override(override_data):
    """ Creates a new price override, triggers parent Price sync. """
    _ensure_admin()
    try:
        validated_data = _validate_override_data(override_data, is_update=False)
    except (ValueError, TypeError) as e: 
      raise ValueError(f"Invalid input data: {e}")

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    override_id = f"OVR-{timestamp_str}"
    if app_tables.price_unit_price_overrides.get(id=override_id): 
      raise Exception("Failed to generate unique override ID.")

    new_override = None
    parent_price_row = validated_data['price_id']

    try:
        new_override = app_tables.price_unit_price_overrides.add_row(
            id=override_id,
            price_id=parent_price_row,
            country_codes=validated_data['country_codes'], # List stored in Simple Object
            currency_code=validated_data['currency_code'],
            amount=validated_data['amount'],
            created_at_anvil=datetime.now(timezone.utc),
            updated_at_anvil=datetime.now(timezone.utc)
        )
        parent_price_id_str = parent_price_row['price_id']
        print(f"Price override created: {override_id} for price {parent_price_id_str}")

        # Trigger Parent Paddle Price Sync
        try: 
          _trigger_paddle_price_sync(parent_price_row)
        except Exception as sync_err: 
          print(f"WARNING: Paddle Price sync failed after creating override {override_id}: {sync_err}")

        return new_override
    except Exception as e:
        parent_price_id_str = parent_price_row['price_id'] if parent_price_row else 'UNKNOWN'
        print(f"Error creating price override for price '{parent_price_id_str}': {e}")
        traceback.print_exc()
        raise Exception(f"Could not create price override. Error: {e}")


@anvil.server.callable
def update_price_override(override_id, update_data):
    """ Updates an existing price override, triggers parent Price sync. """
    _ensure_admin()
    if not isinstance(override_id, str) or not override_id: 
      raise ValueError("Invalid override_id provided.")
    override_row = app_tables.price_unit_price_overrides.get(id=override_id)
    if not override_row: 
      raise ValueError(f"Price override with ID '{override_id}' not found.")

    try: 
      validated_updates = _validate_override_data(update_data, is_update=True)
    except (ValueError, TypeError) as e: 
      raise ValueError(f"Invalid update data: {e}")

    validated_updates.pop('price_id', None) # Cannot update parent link
    updates_to_apply = {k: v for k, v in validated_updates.items() if k in update_data}
    if not updates_to_apply:
         print(f"No valid fields provided to update for override '{override_id}'.")
         return override_row

    updates_to_apply['updated_at_anvil'] = datetime.now(timezone.utc)
    parent_price_row = override_row['price_id']

    try:
         override_row.update(**updates_to_apply)
         print(f"Price override updated: {override_id}")

         # Trigger Parent Paddle Price Sync
         try: 
           _trigger_paddle_price_sync(parent_price_row)
         except Exception as sync_err: 
           print(f"WARNING: Paddle Price sync failed after updating override {override_id}: {sync_err}")

         return override_row
    except Exception as e:
         print(f"Error updating price override '{override_id}': {e}")
         traceback.print_exc()
         raise Exception(f"Could not update price override. Error: {e}")


@anvil.server.callable
def delete_price_override(override_id):
    """ Deletes a specific price override, triggers parent Price sync. """
    _ensure_admin()
    if not isinstance(override_id, str) or not override_id: 
      raise ValueError("Invalid override_id provided.")
    override_row = app_tables.price_unit_price_overrides.get(id=override_id)
    if not override_row: 
      raise ValueError(f"Price override with ID '{override_id}' not found.")

    parent_price_row = override_row['price_id']

    try:
         override_row.delete()
         print(f"Price override deleted: {override_id}")

         # Trigger Parent Paddle Price Sync
         try: 
           _trigger_paddle_price_sync(parent_price_row)
         except Exception as sync_err: 
           print(f"WARNING: Paddle Price sync failed after deleting override {override_id}: {sync_err}")

         return True
    except Exception as e:
         print(f"Error deleting price override '{override_id}': {e}")
         traceback.print_exc()
         raise Exception(f"Could not delete price override. Error: {e}")


# --- Get/List Functions ---

@anvil.server.callable
def get_price(price_id):
    """ Retrieves a specific price by its price_id. """
    _ensure_admin()
    if not isinstance(price_id, str) or not price_id: 
      raise ValueError("Invalid price_id provided.")
    return app_tables.prices.get(price_id=price_id)

@anvil.server.callable
def list_prices_for_item(item_id_str):
    """ Retrieves all prices linked to a specific item_id. """
    _ensure_admin()
    if not isinstance(item_id_str, str) or not item_id_str: 
      raise ValueError("Invalid item_id provided.")
    item_row = app_tables.items.get(item_id=item_id_str)
    if not item_row: 
      raise ValueError(f"Item with ID '{item_id_str}' not found.")
    prices = app_tables.prices.search(item_id=item_row, order_by=tables.order_by('description'))
    return list(prices)

@anvil.server.callable
def list_overrides_for_price(price_id_str):
    """ Lists all overrides for a given price_id. """
    _ensure_admin()
    if not isinstance(price_id_str, str) or not price_id_str: 
      raise ValueError("Invalid price_id provided.")
    price_row = app_tables.prices.get(price_id=price_id_str)
    if not price_row: 
      raise ValueError(f"Price with ID '{price_id_str}' not found.")
    overrides = app_tables.price_unit_price_overrides.search(price_id=price_row)
    return list(overrides)

@anvil.server.callable
def set_mybizz_price_status(price_id, new_status):
  """
    Sets the status of a MyBizz price and attempts to sync it to Paddle.
    Allowed new_status values: 'active', 'archived'.
    Requires Admin privileges.
    """
  _ensure_admin() # Assumes _ensure_admin() helper exists

  if not isinstance(price_id, str) or not price_id:
    raise ValueError("Invalid price_id provided.")
    if new_status not in VALID_PRICE_STATUSES: # VALID_PRICE_STATUSES = ['active', 'archived']
      raise ValueError(f"Invalid new_status '{new_status}'. Must be 'active' or 'archived'.")

  price_row = app_tables.prices.get(price_id=price_id)
  if not price_row:
    raise ValueError(f"Price with ID '{price_id}' not found.")

    # If current status is already the new status, do nothing.
    if price_row['status'] == new_status:
      print(f"Price {price_id} is already in '{new_status}' state.")
      return price_row # Or return a message indicating no change

  # Update MyBizz database first
  try:
    price_row.update(status=new_status, updated_at_anvil=datetime.now(timezone.utc))
    print(f"MyBizz Price {price_id} status updated to '{new_status}'.")
  except Exception as db_err:
    print(f"Error updating MyBizz price {price_id} status in DB: {db_err}")
    traceback.print_exc()
    raise Exception(f"Failed to update price status locally: {db_err}")

    # Attempt to sync status to Paddle if paddle_price_id exists
    if price_row['paddle_price_id']:
      try:
        print(f"Attempting to update Paddle Price {price_row['paddle_price_id']} status to '{new_status}'.")
        # Paddle's update price endpoint typically takes a payload.
        # The status is usually part of the main price object attributes.
        update_payload = {"status": new_status}

        # Ensure update_paddle_price is imported from paddle_api_client
        updated_paddle_price = update_paddle_price(price_row['paddle_price_id'], update_payload)

        print(f"Paddle Price {price_row['paddle_price_id']} status successfully updated to '{updated_paddle_price.get('status')}'.")
      except anvil.http.HttpError as e:
        print(f"Paddle API Error updating status for price {price_row['paddle_price_id']}: {e.status} - {e.content}")
        # CRITICAL: MyBizz DB is updated, but Paddle sync failed.
        # This requires a reconciliation strategy or clear error to user.
        # For now, raise an error indicating partial success.
        raise Exception(f"MyBizz status updated, but Paddle sync failed ({e.status}). Please check Paddle dashboard. Error: {e.content}")
      except Exception as sync_err:
        print(f"Unexpected error syncing status for Paddle Price {price_row['paddle_price_id']}: {sync_err}")
        traceback.print_exc()
        raise Exception(f"MyBizz status updated, but Paddle sync encountered an unexpected error. Please check Paddle dashboard. Error: {sync_err}")
    else:
      print(f"Price {price_id} has no paddle_price_id. Skipping Paddle status sync.")

  return price_row


# In helper_functions.py (or sm_pricing_mod.py)
# Ensure necessary imports are at the top of the file:
# import anvil.server
# import anvil.tables as tables
# from anvil.tables import app_tables
# from sm_logs_mod import log # Optional, if you want to log this activity

@anvil.server.callable
def get_currency_options_for_dropdown():
  """
    Fetches all active currencies from the 'currency' table and formats them
    as a list of (display_text, value) tuples suitable for a DropDown component.
    Example: [("USD - US Dollar", "USD"), ("EUR - Euro", "EUR")]
    Sorts the list by currency code.
    """

  # Optional: Add permission check if needed, though typically currency lists are public.
  # user = anvil.users.get_user()
  # if not user:
  #     log("WARNING", module_name, function_name, "Attempt to get currency options by non-logged-in user.")
  #     # Depending on policy, either raise PermissionDenied or allow for public forms.
  #     # For now, assuming it's generally accessible if called.

  try:
    # Fetch all rows from the currency table.
    # Assuming 'currency' column holds the code (e.g., "USD")
    # and 'country' column holds the descriptive name (e.g., "US Dollar")
    # You might have a 'is_active' column if you want to filter only active currencies.
    # For now, fetching all and sorting by currency code.

    currency_rows = app_tables.currency.search(
      tables.order_by("currency") 
      # Add q.fetch_only("currency", "country") if you want to optimize by fetching only needed columns
    )

    options = []
    for row in currency_rows:
      code = row['currency']
      # The 'country' column in your schema seems to store the currency name (e.g., "US Dollar")
      # If it stores the country name, you might need a different field for currency description.
      # Assuming 'country' field is the currency's descriptive name for the display text.
      name = row['country'] 

      if code and name: # Ensure both code and name are present
        display_text = f"{code} - {name}"
        options.append((display_text, code))
      elif code: # Fallback if name is missing
        options.append((code, code))

        # log("INFO", module_name, function_name, f"Retrieved {len(options)} currency options for dropdown.")
    return options

  except Exception as e:
    # log("ERROR", module_name, function_name, "Error fetching currency options.", {"error": str(e)})
    # Depending on how critical this is, either raise the error or return an empty list/error indicator
    # For a dropdown, returning an empty list or a list with an error message might be preferable
    # to crashing the form that tries to populate it.
    print(f"SERVER ERROR in get_currency_options_for_dropdown: {e}") # Print to server logs
    # Consider returning a specific error indicator if the client needs to handle it differently
    # For now, re-raising to make the error visible during development.
    raise anvil.server.AnvilWrappedError(f"Failed to load currency options: {str(e)}")