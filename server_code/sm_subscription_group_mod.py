# Server Module: sm_subscription_group_mod.py
# Contains functions for managing Subscription Groups with validation and Paddle sync

import anvil.server
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from datetime import datetime, timezone
import traceback
from sm_logs_mod import log
# Import RBAC functions (adjust path if necessary)
from .sessions_server import is_admin_user, is_owner_user

# Import Paddle API client functions <<<--- ADDED IMPORT
from .paddle_api_client import create_paddle_product, update_paddle_product

# --- Constants ---
# (Keep existing constants if any)

# --- Validation Helper Function ---
# (_validate_group_data remains the same as previous version)
# --- Validation Helper Function ---
def _validate_group_data(group_data, is_update=False):
  """
    Validates input data for creating/updating a subscription group.
    Includes validation for the new 'tax_category' field.
    """
  if not isinstance(group_data, dict):
    raise TypeError("Input data must be a dictionary.")

  validated_data = {}
  # --- MODIFIED: Added 'tax_category' to optional_fields and required_fields_create ---
  required_fields_create = ['group_name', 'tax_category'] # Tax category is now required on create
  optional_fields = [
    'group_name', 'group_description', 'tax_category', # Added tax_category
    'group_level1_name', 'group_level2_name', 'group_level3_name',
    'group_tier1_name', 'group_tier2_name', 'group_tier3_name'
    # Note: 'media' link is handled separately via file upload logic, not direct validation here.
  ]
  # --- END MODIFICATION ---

  # Check required fields for creation
  if not is_update:
    for field in required_fields_create:
      if field not in group_data or not group_data[field]:
        raise ValueError(f"Missing required field: '{field}'.")
      # Basic type check for required fields
      if field == 'tax_category' and not isinstance(group_data[field], str):
        raise TypeError(f"Field '{field}' must be a string.")
      elif field == 'group_name' and not isinstance(group_data[field], str):
        raise TypeError(f"Field '{field}' must be a string.")
      validated_data[field] = group_data[field] # Add required field to validated data

  # Validate all provided optional fields (or all fields if updating)
  data_source = group_data # Check all provided fields in the input dict

  for field in optional_fields:
    if field in data_source:
      value = data_source[field]
      # Allow None for optional fields, but check type if not None
      if value is not None and not isinstance(value, str):
        raise TypeError(f"Field '{field}' must be a string or None.")
      # Add to validated_data if it was present in the input, even if None
      # Only add if it wasn't already added as a required field
      if field not in validated_data:
        validated_data[field] = value

  # Length checks (apply to validated data)
  if 'group_name' in validated_data and len(validated_data['group_name']) > 100:
    raise ValueError("Group Name cannot exceed 100 characters.")
  if 'group_description' in validated_data and validated_data.get('group_description') is not None and len(validated_data['group_description']) > 500:
    raise ValueError("Group Description cannot exceed 500 characters.")
  # --- MODIFIED: Added length check for tax_category (adjust max_len if needed) ---
  if 'tax_category' in validated_data and validated_data.get('tax_category') is not None and len(validated_data['tax_category']) > 50: # Example max length
    raise ValueError("Tax Category cannot exceed 50 characters.")
  # --- END MODIFICATION ---

  # Add specific validation for tax_category values if needed (e.g., check against a list from Paddle)
  # if 'tax_category' in validated_data and validated_data['tax_category'] not in PADDLE_VALID_TAX_CATEGORIES:
  #    raise ValueError(f"Invalid tax category: {validated_data['tax_category']}")

  return validated_data


# --- Helper to check admin permissions ---
def _ensure_admin():
  """Raises PermissionDenied if the current user is not an admin."""
  if not is_admin_user():
    raise anvil.server.PermissionDenied("Administrator privileges required.")

# --- Helper: Trigger Paddle Product Sync ---
def _trigger_paddle_product_sync_for_group(group_row):
  """
    Creates or updates the corresponding Paddle Product for a subscription group.
    Updates the paddle_product_id on associated items rows.
    Uses the actual tax_category from the group_row.
    """
  if not group_row:
    print("Error: Cannot sync Paddle Product, invalid group_row provided.")
    return

  # Find associated items rows (should represent the group concept)
  items_to_update = list(app_tables.items.search(subscription_group_id=group_row, item_type='subscription_plan'))
  if not items_to_update:
    print(f"Warning: No 'subscription_plan' items found linked to group {group_row['group_number']} during Paddle sync trigger.")
    return

  # Use the first item found to check for existing paddle_product_id
  existing_paddle_product_id = items_to_update[0]['paddle_product_id']

  # --- Prepare Paddle Product Data ---
  # --- MODIFIED: Fetch TAX CATEGORY from group_row ---
  tax_category = group_row.get('tax_category')
  if not tax_category:
    # Fallback or raise error if tax_category is mandatory for Paddle Product
    print(f"CRITICAL WARNING: tax_category is missing for group {group_row['group_number']}. Using 'standard' as fallback for Paddle sync.")
    tax_category = 'standard' # Fallback - consider raising error instead?
  # --- END MODIFICATION ---

  # --- MODIFIED: Get image_url from group's media link ---
  image_url = None
  media_link = group_row.get('media')
  if media_link and isinstance(media_link, tables.Row) and media_link.get('file') and hasattr(media_link['file'], 'url'):
    try:
      image_url = media_link['file'].url
    except Exception as url_err:
      print(f"Warning: Could not get URL for group media file: {url_err}")
  # --- END MODIFICATION ---


  paddle_product_data = {
    "name": group_row['group_name'],
    "tax_category": tax_category, # Use actual value
    "description": group_row.get('group_description'),
    "image_url": image_url, # Use image_url from group media
    "custom_data": {
      "mybizz_group_number": group_row['group_number'],
      "mybizz_item_ids": [i['item_id'] for i in items_to_update]
    }
    # "status": 'active' # Default for Paddle Product
  }

  # --- PADDLE API VALIDATION ---
  if not paddle_product_data.get('name'):
    raise ValueError("Paddle API Error: Product 'name' is required for sync.")
  if not paddle_product_data.get('tax_category'):
    raise ValueError("Paddle API Error: Product 'tax_category' is required for sync.")
  # --- END PADDLE API VALIDATION ---

  try:
    if not existing_paddle_product_id:
      # --- Create New Paddle Product ---
      print(f"Creating Paddle Product for group: {group_row['group_number']}")
      created_paddle_product = create_paddle_product(paddle_product_data)
      new_paddle_product_id = created_paddle_product.get('id')

      if new_paddle_product_id:
        print(f"Paddle Product created: {new_paddle_product_id}")
        # Update all associated items rows
        updated_count = 0
        for item_row in items_to_update:
          try:
            item_row.update(paddle_product_id=new_paddle_product_id)
            updated_count += 1
          except Exception as e:
            print(f"Error updating paddle_product_id for item {item_row['item_id']}: {e}")
        print(f"Updated {updated_count}/{len(items_to_update)} items rows with paddle_product_id.")
      else:
        print("Error: Paddle API did not return an ID for the new product.")
        raise Exception("Paddle Product creation failed (no ID returned).")

    else:
      # --- Update Existing Paddle Product ---
      print(f"Updating Paddle Product {existing_paddle_product_id} for group: {group_row['group_number']}")
      update_payload = paddle_product_data.copy()
      update_payload.pop('tax_category', None)

      # --- PADDLE API VALIDATION (for update specific rules if any) ---
      # --- END PADDLE API VALIDATION ---

      updated_paddle_product = update_paddle_product(existing_paddle_product_id, update_payload)
      print(f"Paddle Product updated: {updated_paddle_product.get('id')}")

  except anvil.http.HttpError as e:
    print(f"Paddle API Error syncing product for group {group_row['group_number']}: {e.status} - {e.content}")
    raise Exception(f"Paddle API sync failed: {e.status}")
  except Exception as e:
    print(f"Error during Paddle Product sync for group {group_row['group_number']}: {e}")
    traceback.print_exc()
    raise Exception(f"Paddle sync failed: {e}")


# --- Create Subscription Group ---
@anvil.server.callable
def create_subscription_group(group_data):
  """
    Creates a new subscription group, including tax_category,
    and triggers Paddle Product sync.
    Handles file upload for media link.
    """
  _ensure_admin()
  try:
    # --- MODIFIED: Validation now includes tax_category ---
    validated_data = _validate_group_data(group_data, is_update=False)
    # --- END MODIFICATION ---
  except (ValueError, TypeError) as e:
    raise ValueError(f"Invalid input data: {e}")

  timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
  group_number = f"GRP-{timestamp_str}"
  if app_tables.subscription_group.get(group_number=group_number):
    raise Exception("Failed to generate unique group number.")

  # --- Handle File Upload ---
  media_link_row = None
  uploaded_file = group_data.get('file_upload')
  if uploaded_file:
    try:
      # Assuming helper_functions.save_prod_image_to_db exists and works
      # It should save the file to 'files' table and return the 'files' row
      # We need the row itself to link it.
      # Let's assume a helper that returns the row:
      # media_link_row = _save_media_file_and_get_row(uploaded_file, group_data.get('file_upload_name'), 'group_image')
      # For now, let's simulate getting the row if a file is present.
      # This part needs refinement based on the actual file saving helper.
      # Placeholder: If a file is passed, assume it's saved and we get a link.
      # In a real scenario, call the function that saves to 'files' table and returns the row.
      print(f"Placeholder: File '{group_data.get('file_upload_name')}' provided. Need actual save logic.")
      # media_link_row = app_tables.files.get(...) # Get the row after saving
      pass # Replace with actual file saving call returning the 'files' row object
    except Exception as file_err:
      print(f"Error saving group image: {file_err}")
      # Decide if creation should fail or continue without image
      # raise Exception(f"Failed to save group image: {file_err}")
  # --- End File Upload Handling ---


  new_group = None # Define before try block
  try:
    new_group = app_tables.subscription_group.add_row(
      group_number=group_number,
      group_name=validated_data['group_name'],
      group_description=validated_data.get('group_description'),
      # --- MODIFIED: Added tax_category ---
      tax_category=validated_data['tax_category'],
      # --- END MODIFICATION ---
      group_level1_name=validated_data.get('group_level1_name'),
      group_level2_name=validated_data.get('group_level2_name'),
      group_level3_name=validated_data.get('group_level3_name'),
      group_tier1_name=validated_data.get('group_tier1_name'),
      group_tier2_name=validated_data.get('group_tier2_name'),
      group_tier3_name=validated_data.get('group_tier3_name'),
      media=media_link_row, # Link to the 'files' row if image was saved
      created_at_anvil=datetime.now(timezone.utc),
      updated_at_anvil=datetime.now(timezone.utc)
    )
    print(f"Subscription Group created in MyBizz DB: {group_number} - {validated_data['group_name']}")

    # --- Trigger Paddle Product Sync ---
    # Assumes associated 'items' rows are created elsewhere or handled robustly
    # For now, trigger sync immediately after group creation
    try:
      # Sync function now uses the tax_category from the new_group row
      _trigger_paddle_product_sync_for_group(new_group)
    except Exception as sync_err:
      print(f"WARNING: Paddle Product sync failed after creating group {group_number}: {sync_err}")
      pass # Log only for now

    return new_group
  except Exception as e:
    print(f"Error creating subscription group '{validated_data.get('group_name')}': {e}")
    traceback.print_exc()
    raise Exception(f"Could not create subscription group. Error: {e}")



# --- Update Subscription Group ---
@anvil.server.callable
def update_subscription_group(group_number, update_data):
  """
    Updates an existing subscription group, including tax_category,
    and triggers Paddle Product sync. Handles file upload/linking.
    """
  _ensure_admin()
  if not isinstance(group_number, str) or not group_number:
    raise ValueError("Invalid group_number provided.")
  group_row = app_tables.subscription_group.get(group_number=group_number)
  if not group_row:
    raise ValueError(f"Subscription Group with number '{group_number}' not found.")

  try:
    # --- MODIFIED: Validation now includes tax_category ---
    validated_updates = _validate_group_data(update_data, is_update=True)
    # --- END MODIFICATION ---
  except (ValueError, TypeError) as e:
    raise ValueError(f"Invalid update data: {e}")

  # Prepare updates, excluding fields not directly in validated_updates (like file uploads)
  updates_to_apply = {k: v for k, v in validated_updates.items() if k in update_data}

  # --- Handle File Upload/Update ---
  uploaded_file = update_data.get('file_upload')
  existing_media_link = update_data.get('existing_media_link') # Passed from client if no new file

  if uploaded_file:
    # New file uploaded, save it and get the link row
    try:
      # media_link_row = _save_media_file_and_get_row(uploaded_file, update_data.get('file_upload_name'), 'group_image')
      # Placeholder: Assume save successful, get the new row object
      print(f"Placeholder: New file '{update_data.get('file_upload_name')}' provided for update. Need actual save logic.")
      # updates_to_apply['media'] = media_link_row # Add/replace media link
      pass # Replace with actual file saving call returning the 'files' row object
    except Exception as file_err:
      print(f"Error saving updated group image: {file_err}")
      # Decide if update should fail or continue without image update
      # raise Exception(f"Failed to save updated group image: {file_err}")
  elif 'file_upload' in update_data and uploaded_file is None:
    # Explicitly clearing the image (if file_upload key exists but is None)
    updates_to_apply['media'] = None
    print(f"Clearing media link for group {group_number}.")
  elif existing_media_link:
    # No new file, retain existing link (already on group_row, no change needed in updates_to_apply unless explicitly clearing)
    # If 'media' key is accidentally included in updates_to_apply from validation, remove it
    updates_to_apply.pop('media', None)
    print(f"Retaining existing media link for group {group_number}.")
  # If no file info provided, 'media' link remains unchanged.

  # --- End File Upload Handling ---


  if not updates_to_apply and 'media' not in updates_to_apply: # Check if any actual field changed besides timestamp
    print(f"No valid fields provided to update for group '{group_number}'.")
    # Still trigger sync in case underlying items changed? Or return early?
    # Let's return early if no data fields changed.
    return group_row

  updates_to_apply['updated_at_anvil'] = datetime.now(timezone.utc)

  try:
    group_row.update(**updates_to_apply)
    print(f"Subscription Group updated in MyBizz DB: {group_number}")

    # --- Trigger Paddle Product Sync ---
    try:
      # Sync function now uses the potentially updated tax_category from the group_row
      _trigger_paddle_product_sync_for_group(group_row)
    except Exception as sync_err:
      print(f"WARNING: Paddle Product sync failed after updating group {group_number}: {sync_err}")
      pass # Log only for now

    return group_row
  except Exception as e:
    print(f"Error updating subscription group '{group_number}': {e}")
    traceback.print_exc()
    raise Exception(f"Could not update subscription group. Error: {e}")


# --- Get/List/Delete Functions (remain the same as previous version, ensure imports/helpers are correct) ---

@anvil.server.callable
def get_subscription_group(group_number):
  """ Retrieves a specific subscription group by its group_number. """
  _ensure_admin()
  if not isinstance(group_number, str) or not group_number:
    raise ValueError("Invalid group_number provided (must be a non-empty string).")
    return app_tables.subscription_group.get(group_number=group_number)

@anvil.server.callable
def list_subscription_groups():
  """ Retrieves a list of all subscription groups (basic info). """
  _ensure_admin()
  return [
    {'group_name': g['group_name'], 'group_number': g['group_number']}
    for g in app_tables.subscription_group.search(tables.order_by('group_name'))
  ]

@anvil.server.callable
def delete_subscription_group(group_number):
  """ Deletes a subscription group. Requires Owner privileges. """
  if not is_owner_user():
    raise anvil.server.PermissionDenied("Owner privileges required to delete subscription groups.")
    if not isinstance(group_number, str) or not group_number:
      raise ValueError("Invalid group_number provided.")
  group_row = app_tables.subscription_group.get(group_number=group_number)
  if not group_row:
    raise ValueError(f"Subscription Group with number '{group_number}' not found.")
    # Dependency checks...
    try:
      linked_items = app_tables.items.search(subscription_group_id=group_row)
      if len(linked_items) > 0:
        raise Exception(f"Cannot delete group '{group_row['group_name']}'. It still has associated plan definitions (items).")
    except tables.TableError as e:
      print(f"Warning: Could not check for linked items during group deletion: {e}")
      raise Exception("Cannot confirm dependencies. Deletion aborted.")
  # Placeholder for Paddle Product Archival...
    try:
      group_name_deleted = group_row['group_name']
      group_row.delete()
      print(f"Subscription Group deleted: {group_number} - {group_name_deleted}")
      return True
    except Exception as e: # Corrected indentation for except block
      print(f"Error deleting subscription group '{group_number}': {e}")
      traceback.print_exc() # Make sure traceback is imported
      raise Exception(f"Could not delete subscription group. Error: {e}")

@anvil.server.callable
def get_subscription_plan_matrix_data(group_number):
  """
    Fetches and structures the data for the 3x3 subscription plan price matrix
    for a given subscription_group_number. Includes descriptive level names.

    Args:
        group_number (str): The 'group_number' of the subscription_group.

    Returns:
        list: A list of 3 dictionaries, one for each Tier (T1, T2, T3).
              Each dictionary contains:
                'tier_name_display': (str) The descriptive name for the tier.
                'tier_num_identifier': (str) e.g., "T1", "T2", "T3"
                'l1_level_name_display': (str) Descriptive name for Level 1.
                'l1_price_display': (str) Formatted price or "Free" / "Not Set".
                'l1_item_id': (str) The item_id of the 'items' row for Level 1 / Current Tier.
                'l1_is_paid': (bool) True if this plan variation is paid.
                'l2_level_name_display': (str)
                'l2_price_display': (str)
                'l2_item_id': (str)
                'l2_is_paid': (bool)
                'l3_level_name_display': (str)
                'l3_price_display': (str)
                'l3_item_id': (str)
                'l3_is_paid': (bool)
              Returns None if the group is not found or an error occurs.
    """
  module_name = "sm_subscription_group_mod" # Or actual module name
  function_name = "get_subscription_plan_matrix_data"
  log("INFO", module_name, function_name, f"Fetching matrix data for G#: {group_number}")
  # Optional: Permission Check
  if not is_admin_user():
    log("WARNING", module_name, function_name, "Permission denied.", {"group_number": group_number})
    raise anvil.server.PermissionDenied("Admin privileges required.")

    if not group_number:
      log("WARNING", module_name, function_name, "No group_number provided.")
      return None

  group_row = app_tables.subscription_group.get(group_number=group_number)
  if not group_row:
    log("WARNING", module_name, function_name, f"Subscription group G#: {group_number} not found.")
    return None

    matrix_result = []
  tier_identifiers = ["T1", "T2", "T3"]
  level_identifiers = ["L1", "L2", "L3"]

  # Get the descriptive names for levels and tiers from the group
  group_level_names = {
    "L1": group_row.get('group_level1_name') or "Level 1",
    "L2": group_row.get('group_level2_name') or "Level 2",
    "L3": group_row.get('group_level3_name') or "Level 3",
  }
  group_tier_names = {
    "T1": group_row.get('group_tier1_name') or "Tier 1 (Free)",
    "T2": group_row.get('group_tier2_name') or "Tier 2 (Monthly)",
    "T3": group_row.get('group_tier3_name') or "Tier 3 (Yearly)",
  }

  try:
    for tier_num_id in tier_identifiers: # e.g., "T1", "T2", "T3"
      tier_data = {
        'tier_name_display': group_tier_names.get(tier_num_id, f"Tier {tier_num_id[-1]}"),
        'tier_num_identifier': tier_num_id
      }
      # Determine if the current tier is considered a "paid" tier
      # T1 is Free, T2 and T3 are considered paid for pricing purposes
      is_paid_tier_for_pricing = (tier_num_id != "T1") 

      for level_num_id in level_identifiers: # e.g., "L1", "L2", "L3"
        price_display = "Not Defined" # Default if no price/plan found
        item_id_for_plan = None

        # Find the 'subs' row for this specific G/L/T combination
        subs_row = app_tables.subs.get(
          subscription_group=group_row,
          level_num=level_num_id,
          tier_num=tier_num_id
        )

        if subs_row:
          item_row = subs_row.get('item_id') # This is a link to the 'items' table
          if item_row:
            item_id_for_plan = item_row['item_id']
            if not is_paid_tier_for_pricing: # For T1 (Free tier)
              price_display = "$0.00" # Or "Free"
            else:
              # For paid tiers, find the linked price in the 'prices' table
              price_link_row = item_row.get('default_price_id') # Link to 'prices' table
              if price_link_row: # price_link_row is the actual 'prices' row
                amount = price_link_row.get('unit_price_amount', "N/A")
                currency = price_link_row.get('unit_price_currency_code', "")
                try:
                  # Ensure amount is a string before int conversion
                  amount_val = int(str(amount)) / 100
                  price_display = f"{currency} {amount_val:,.2f}"
                except (ValueError, TypeError):
                  price_display = f"{currency} {amount} (raw)"
              else:
                price_display = "Price Not Set" # Paid tier, but no price defined yet
          else: # item_row not found for subs_row
            price_display = "Plan Item Missing"
            log("WARNING", module_name, function_name, f"Missing item_row for subs_id {subs_row['subs_id']} (G:{group_number} L:{level_num_id} T:{tier_num_id})")
        else: # subs_row not found for G/L/T
          price_display = "Plan Def. Missing"
          log("WARNING", module_name, function_name, f"Missing subs_row for G:{group_number} L:{level_num_id} T:{tier_num_id}")

          # Key for the dictionary, e.g., 'l1_price_display', 'l1_item_id', 'l1_is_paid'
          level_key_prefix = level_num_id.lower() # l1, l2, l3

        tier_data[f'{level_key_prefix}_level_name_display'] = group_level_names.get(level_num_id) # <<<--- ADDED
        tier_data[f'{level_key_prefix}_price_display'] = price_display
        tier_data[f'{level_key_prefix}_item_id'] = item_id_for_plan
        # 'is_paid' here refers to whether a price should be set/edited, not if the plan itself costs money.
        # T1 is "free" so no price editing, T2/T3 are "paid" meaning they have editable prices.
        tier_data[f'{level_key_prefix}_is_paid'] = is_paid_tier_for_pricing 

        matrix_result.append(tier_data)

      log("INFO", module_name, function_name, f"Successfully fetched matrix data for G#: {group_number}", {"result_count": len(matrix_result)})
    return matrix_result

  except Exception as e:
    log("ERROR", module_name, function_name, f"Error fetching matrix data for G#: {group_number} - {e}", {"trace": traceback.format_exc()})
    print(f"SERVER ERROR in get_subscription_plan_matrix_data for G#: {group_number} - {e}")
    traceback.print_exc()
    return None # Return None on error
