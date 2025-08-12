# Server Module: sm_item_mod.py
# Contains functions for managing the unified 'items' table (products, services, subscription plans)
# Includes Paddle Product sync for item_type 'product' and 'service', and validation.
from .sm_rbac_mod import user_has_permission
import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime, timezone
import re # For potential regex validation if needed later
import traceback # For detailed error logging

# Import RBAC functions (adjust path if necessary)
from .sessions_server import is_admin_user, is_owner_user

# Import Paddle API client functions (adjust path if necessary)
from .paddle_api_client import create_paddle_product, update_paddle_product
# Placeholder for future Paddle Product archival function
# from .paddle_api_client import archive_paddle_product

# --- Constants ---
VALID_ITEM_TYPES = ['product', 'service', 'subscription_plan']

# --- Validation Helper Function ---
def _validate_item_data(item_data, is_update=False):
  """
    Validates the input dictionary for creating or updating an item.
    Raises ValueError or TypeError on failure. Returns the validated data.
    Handles 'status' as a string ('active' or 'archived').
    """
  if not isinstance(item_data, dict):
    raise TypeError("Input data must be a dictionary.")

  validated_data = {}
  # Define fields and their expected types/constraints
  field_definitions = {
    'name': {'type': str, 'required_create': True, 'updatable': True, 'max_len': 150},
    'item_type': {'type': str, 'required_create': True, 'updatable': False, 'valid_values': VALID_ITEM_TYPES},
    'tax_category': {'type': str, 'required_create': True, 'updatable': True}, # Add validation if specific categories exist
    'description': {'type': str, 'required_create': False, 'updatable': True, 'max_len': 1000},
    # --- MODIFIED status definition ---
    'status': {'type': str, 'required_create': False, 'updatable': True, 'valid_values': ['active', 'archived'], 'default': 'active'}, # MyBizz status (string)
    # --- END MODIFICATION ---
    'media': {'type': tables.Media, 'required_create': False, 'updatable': True},
    'custom_data': {'type': dict, 'required_create': False, 'updatable': True},
    'subscription_group_id': {'type': app_tables.subscription_group, 'required_create': False, 'updatable': True}, # Required if item_type is sub plan
    'glt': {'type': str, 'required_create': False, 'updatable': True}, # Required if item_type is sub plan
    'default_price_id': {'type': app_tables.prices, 'required_create': False, 'updatable': True}
    # Note: paddle_product_id is managed internally by sync, not directly validated here.
  }

  # --- Check Required Fields (Create) ---
  if not is_update:
    for field, definition in field_definitions.items():
      if definition.get('required_create'):
        if field not in item_data or item_data[field] is None or item_data[field] == "":
          raise ValueError(f"Missing required field: '{field}'.")

  # --- Validate All Provided Fields ---
  for field, value in item_data.items():
    # Skip internal context field used for updates
    if field == 'item_type_from_db':
      continue

    if field not in field_definitions:
      # print(f"Warning: Unknown field '{field}' provided in item_data.")
      continue # Ignore unknown fields

    definition = field_definitions[field]

    # Check if field is updatable
    if is_update and not definition.get('updatable', True):
      # Special case: allow item_type check here even if not updatable
      if field == 'item_type' and value != item_data.get('item_type_from_db'):
        raise ValueError(f"Field '{field}' cannot be updated.")
      elif field != 'item_type':
        raise ValueError(f"Field '{field}' cannot be updated.")

    # Add to validated_data if present in input (even if None for optional fields)
    validated_data[field] = value

    # Perform checks only if value is not None
    if value is not None:
      expected_type = definition.get('type')
      if expected_type and not isinstance(value, expected_type):
        # Special check for Link types (allow Row objects)
        if expected_type in [app_tables.items, app_tables.prices, app_tables.subscription_group, tables.Media]:
          if not hasattr(value, 'get_id'):
            raise TypeError(f"Field '{field}' must be a valid Anvil Data Table Row or Media object.")
        else:
          raise TypeError(f"Field '{field}' has incorrect type. Expected {expected_type.__name__}.")

      if 'valid_values' in definition and value not in definition['valid_values']:
        raise ValueError(f"Field '{field}' has invalid value '{value}'. Must be one of {definition['valid_values']}.")

      if 'max_len' in definition and isinstance(value, str) and len(value) > definition['max_len']:
        raise ValueError(f"Field '{field}' cannot exceed {definition['max_len']} characters.")

  # --- Type-Specific Validation ---
  current_item_type = validated_data.get('item_type') if not is_update else item_data.get('item_type_from_db')

  if current_item_type == 'subscription_plan':
    # Check required links/fields for subscription plans
    if not validated_data.get('subscription_group_id'):
      if not is_update or ('subscription_group_id' in validated_data and validated_data['subscription_group_id'] is None):
        raise ValueError("Field 'subscription_group_id' is required when item_type is 'subscription_plan'.")
    if not validated_data.get('glt'):
      if not is_update or ('glt' in validated_data and validated_data['glt'] is None):
        raise ValueError("Field 'glt' is required when item_type is 'subscription_plan'.")
  elif current_item_type in ['product', 'service']:
    # Ensure subscription-specific fields are not set for product/service
    if validated_data.get('subscription_group_id') is not None:
      raise ValueError("Field 'subscription_group_id' is only applicable for item_type 'subscription_plan'.")
    if validated_data.get('glt') is not None:
      raise ValueError("Field 'glt' is only applicable for item_type 'subscription_plan'.")

  # Set defaults for optional fields if not provided during creation
  if not is_update:
    for field, definition in field_definitions.items():
      if field not in validated_data and 'default' in definition:
        validated_data[field] = definition['default']

  return validated_data


# --- Helper: Trigger Paddle Product Sync for Product/Service Items ---
# --- Helper: Trigger Paddle Product Sync for Product/Service Items ---
def _trigger_paddle_product_sync_for_item(item_row):
  """
    Creates or updates the corresponding Paddle Product for an item
    of type 'product' or 'service'. Updates paddle_product_id on the item row.
    Uses string status ('active'/'archived').
    """
  if not item_row or item_row['item_type'] not in ['product', 'service']:
    return # Only sync products and services here

  existing_paddle_product_id = item_row.get('paddle_product_id')

  # Prepare Paddle Product Data
  # --- MODIFIED status mapping ---
  # Directly use the string status from the item row, default to 'active' if missing
  paddle_status = item_row.get('status', 'active')
  # --- END MODIFICATION ---
  tax_category = item_row.get('tax_category')
  if not tax_category:
    print(f"Warning: Missing 'tax_category' for item {item_row['item_id']}. Defaulting to 'standard'.")
    tax_category = 'standard'

  image_url = None
  media_link = item_row.get('media')
  # Check if media_link is a valid Media object with a URL
  if media_link and isinstance(media_link, tables.Media) and getattr(media_link, 'url', None):
    image_url = media_link.url

  paddle_product_data = {
    "name": item_row['name'],
    "tax_category": tax_category,
    "description": item_row.get('description'),
    "image_url": image_url, # Include if available
    "custom_data": {
      "mybizz_item_id": item_row['item_id'],
      "mybizz_item_type": item_row['item_type'],
      **(item_row.get('custom_data') or {})
    },
    "status": paddle_status # Use the string status directly
  }

  # --- PADDLE API VALIDATION ---
  if not paddle_product_data.get('name'):
    raise ValueError("Paddle API Error: Product 'name' is required for sync.")
  if not paddle_product_data.get('tax_category'):
    raise ValueError("Paddle API Error: Product 'tax_category' is required for sync.")
  # --- END PADDLE API VALIDATION ---

  try:
    if not existing_paddle_product_id:
      # Create New Paddle Product
      print(f"Creating Paddle Product for item: {item_row['item_id']}")
      created_paddle_product = create_paddle_product(paddle_product_data)
      new_paddle_product_id = created_paddle_product.get('id')
      if new_paddle_product_id:
        print(f"Paddle Product created: {new_paddle_product_id}")
        item_row.update(paddle_product_id=new_paddle_product_id)
      else:
        print("Error: Paddle API did not return an ID for the new product.")
        raise Exception("Paddle Product creation failed (no ID returned).")
    else:
      # Update Existing Paddle Product
      print(f"Updating Paddle Product {existing_paddle_product_id} for item: {item_row['item_id']}")
      update_payload = paddle_product_data.copy()
      update_payload.pop('tax_category', None) # Cannot update tax_category

      # --- PADDLE API VALIDATION (for update specific rules if any) ---
      # Add checks if needed
      # --- END PADDLE API VALIDATION ---

      updated_paddle_product = update_paddle_product(existing_paddle_product_id, update_payload)
      print(f"Paddle Product updated: {updated_paddle_product.get('id')}")

  except anvil.http.HttpError as e:
    print(f"Paddle API Error syncing product for item {item_row['item_id']}: {e.status} - {e.content}")
    raise Exception(f"Paddle API sync failed: {e.status}")
  except Exception as e:
    print(f"Error during Paddle Product sync for item {item_row['item_id']}: {e}")
    traceback.print_exc()
    raise Exception(f"Paddle sync failed: {e}")


# --- Create Item ---
@anvil.server.callable
def create_item(item_data):
  """ Creates a new item, triggers Paddle Product sync if product/service. """
  if not user_has_permission("create_edit_items"):
    raise anvil.server.PermissionDenied("You do not have permission to create items.")

  try:
    validated_data = _validate_item_data(item_data, is_update=False)
  except (ValueError, TypeError) as e:
    raise ValueError(f"Invalid input data: {e}")

  timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
  item_id = f"ITM-{timestamp_str}"
  if app_tables.items.get(item_id=item_id):
    raise Exception("Failed to generate unique item ID.")

  new_item = None
  try:
    row_data = {
      'item_id': item_id,
      'name': validated_data['name'],
      'item_type': validated_data['item_type'],
      'tax_category': validated_data['tax_category'],
      'description': validated_data.get('description'),
      'status': validated_data.get('status', 'active'), # Ensure default is string 'active'
      'media': validated_data.get('media'),
      'custom_data': validated_data.get('custom_data'),
      'subscription_group_id': validated_data.get('subscription_group_id'),
      'glt': validated_data.get('glt'),
      'default_price_id': validated_data.get('default_price_id'),
      'created_at_anvil': datetime.now(timezone.utc),
      'updated_at_anvil': datetime.now(timezone.utc)
    }
    new_item = app_tables.items.add_row(**row_data)
    print(f"Item created in MyBizz DB: {item_id} - {validated_data['name']} ({validated_data['item_type']})")

    if new_item['item_type'] in ['product', 'service']:
      try:
        _trigger_paddle_product_sync_for_item(new_item)
      except Exception as sync_err:
        print(f"WARNING: Paddle Product sync failed after creating item {item_id}: {sync_err}")
        pass 

    return new_item
  except Exception as e:
    print(f"Error creating item '{validated_data.get('name')}': {e}")
    traceback.print_exc()
    raise Exception(f"Could not create item. Error: {e}")


# --- Update Item ---
@anvil.server.callable
def update_item(item_id, update_data):
  """ Updates an existing item, triggers Paddle Product sync if product/service. """
  if not user_has_permission("create_edit_items"):
    raise anvil.server.PermissionDenied("You do not have permission to update items.")

  if not isinstance(item_id, str) or not item_id: 
    raise ValueError("Invalid item_id provided.")
  item_row = app_tables.items.get(item_id=item_id)
  if not item_row: 
    raise ValueError(f"Item with ID '{item_id}' not found.")

  update_data_with_context = update_data.copy()
  update_data_with_context['item_type_from_db'] = item_row['item_type']
  try:
    validated_updates = _validate_item_data(update_data_with_context, is_update=True)
  except (ValueError, TypeError) as e: 
    raise ValueError(f"Invalid update data: {e}")

  validated_updates.pop('item_type', None) 
  validated_updates.pop('item_type_from_db', None)

  updates_to_apply = {k: v for k, v in validated_updates.items() if k in update_data}
  if not updates_to_apply:
    print(f"No valid fields provided to update for item '{item_id}'.")
    return item_row

  updates_to_apply['updated_at_anvil'] = datetime.now(timezone.utc)

  try:
    item_row.update(**updates_to_apply)
    print(f"Item updated in MyBizz DB: {item_id}")

    if item_row['item_type'] in ['product', 'service']:
      try:
        _trigger_paddle_product_sync_for_item(item_row)
      except Exception as sync_err:
        print(f"WARNING: Paddle Product sync failed after updating item {item_id}: {sync_err}")
        pass 

    return item_row
  except Exception as e:
    print(f"Error updating item '{item_id}': {e}")
    traceback.print_exc()
    raise Exception(f"Could not update item. Error: {e}")


# --- Get/List/Delete Functions ---

@anvil.server.callable
def get_item(item_id):
  """ Retrieves a specific item by its item_id. Requires 'view_all_items' permission. """
  if not user_has_permission("view_all_items"):
    raise anvil.server.PermissionDenied("You do not have permission to view items.")

  if not isinstance(item_id, str) or not item_id: 
    raise ValueError("Invalid item_id provided.")
  item = app_tables.items.get(item_id=item_id)
  return item

@anvil.server.callable
def list_items(item_type_filter=None):
  """ Retrieves a list of items, optionally filtered by item_type. Requires 'view_all_items' permission. """
  if not user_has_permission("view_all_items"):
    raise anvil.server.PermissionDenied("You do not have permission to view items list.")

  search_args = {}
  if item_type_filter:
    if item_type_filter not in VALID_ITEM_TYPES: 
      raise ValueError(f"Invalid item_type_filter: '{item_type_filter}'.")
    search_args['item_type'] = item_type_filter

  items_query = app_tables.items.search(tables.order_by('name'), **search_args)
  # Returning a list of dictionaries as per the original function's structure.
  # Add more fields to the dictionary if clients calling this function require them.
  return [
    {'name': i['name'], 
     'item_id': i['item_id'], 
     'item_type': i['item_type']
    }
    for i in items_query
  ]

@anvil.server.callable
def delete_item(item_id):
  """ Deletes an item. Checks dependencies. Requires 'delete_items' permission. """
  if not user_has_permission("delete_items"):
    raise anvil.server.PermissionDenied("You do not have permission to delete items.")

  if not isinstance(item_id, str) or not item_id: 
    raise ValueError("Invalid item_id provided.")
  item_row = app_tables.items.get(item_id=item_id)
  if not item_row: 
    raise ValueError(f"Item with ID '{item_id}' not found.")

  try:
    linked_prices = app_tables.prices.search(item_id=item_row)
    if len(list(linked_prices)) > 0: # Convert iterator to list for len
      raise Exception(f"Cannot delete item '{item_row['name']}'. It still has associated prices.")
  except tables.TableError as e:
    print(f"Warning: Could not check for linked prices during item deletion: {e}")
    raise Exception("Cannot confirm dependencies (prices). Deletion aborted.")

  if item_row['item_type'] == 'subscription_plan':
    try:
      linked_subs = app_tables.subs.search(item_id=item_row)
      if len(list(linked_subs)) > 0: # Convert iterator to list for len
        raise Exception(f"Cannot delete item '{item_row['name']}'. It still has associated 'subs' definitions.")
    except tables.TableError as e:
      print(f"Warning: Could not check for linked subs definitions: {e}")
      raise Exception("Cannot confirm dependencies (subs). Deletion aborted.")

    # Placeholder for Paddle Product Archival
    # if item_row['paddle_product_id'] and item_row['item_type'] in ['product', 'service']:
    #    try: archive_paddle_product(item_row['paddle_product_id'])
    #    except Exception as paddle_err: print(f"Warning: Failed to archive Paddle Product...")

  try:
    item_name_deleted = item_row['name']
    item_row.delete()
    print(f"Item deleted: {item_id} - {item_name_deleted}")
    return True
  except Exception as e:
    print(f"Error deleting item '{item_id}': {e}")
    traceback.print_exc()
    raise Exception(f"Could not delete item. Error: {e}")

