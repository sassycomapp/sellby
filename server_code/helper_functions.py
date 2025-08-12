import anvil.email
import anvil.users
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.files
from anvil.files import data_files
import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import csv
import io
import datetime as datetime
from sm_logs_mod import log
import anvil.media
from anvil import server  # ✅ Required import
import traceback # <<< --- ADD THIS IMPORT
import re


#Manage App Secrets
@anvil.server.callable
def store_secret(secret_name, secret_value):
    """Store secrets securely in Anvil's Secrets Service."""
    try:
        anvil.secrets.put(secret_name, secret_value)
        return f"Secret '{secret_name}' saved successfully."
    except Exception as e:
        raise RuntimeError(f"Error storing secret: {str(e)}")

# Manage App Settings
@anvil.server.callable
def get_settings():
    """Retrieve all settings from the app_settings table."""
    return [(row['setting_name'], row.get_id()) for row in app_tables.app_settings.search()]
  
# Manage App Settings
@anvil.server.callable
def get_setting_by_id(row_id):
    """Retrieve a setting's details by its row ID."""
    row = app_tables.app_settings.get_by_id(row_id)
    if row:
        return {
            "setting_name": row['setting_name'],
            "value_text": row['value_text'],
            "value_number": row['value_number'],
            "value_bool": row['value_bool']
        }
    return None
  
# Manage App Settings
@anvil.server.callable
def save_new_setting(setting_name, setting_value, is_boolean, bool_value):
    """Save a new setting with appropriate type."""
    if app_tables.app_settings.get(setting_name=setting_name):
        return "Setting already exists. Use update instead."

    if is_boolean:
        app_tables.app_settings.add_row(setting_name=setting_name, value_bool=bool_value)
    else:
        if setting_value.isnumeric():
            app_tables.app_settings.add_row(setting_name=setting_name, value_number=float(setting_value))
        else:
            app_tables.app_settings.add_row(setting_name=setting_name, value_text=setting_value)

    return "New setting saved successfully!"
  
# Manage App Settings
@anvil.server.callable
def update_setting(row_id, new_value, is_boolean, bool_value):
    """Update an existing setting with a new value."""
    row = app_tables.app_settings.get_by_id(row_id)
    if row:
        if is_boolean:
            row.update(value_bool=bool_value)
        else:
            if new_value.isnumeric():
                row.update(value_number=float(new_value), value_text=None)
            else:
                row.update(value_text=new_value, value_number=None)
        return "Setting updated successfully!"
    return "Setting not found."

@anvil.server.callable
def import_currency_from_lists(currency_list, country_list):
    """Import currencies from two lists into the currency table."""
    module = "currency_import_server"
    process = "import_currency_from_lists"
    log("INFO", module, process, f"Starting import from lists with {len(currency_list)} items")
    
    try:
        # Clear existing non-system records
        try:
            rows_to_delete = app_tables.currency.search(is_system=False)
            delete_count = len(rows_to_delete)
            for row in rows_to_delete:
                row.delete()
            log("INFO", module, process, f"Cleared {delete_count} existing non-system currency records")
        except Exception as del_err:
            log("ERROR", module, process, "Error clearing existing records", {"error": str(del_err)})
            return f"Error clearing existing records: {del_err}"
        
        # Process lists and add new records
        inserted = 0
        
        # Make sure both lists have the same length
        if len(currency_list) != len(country_list):
            log("ERROR", module, process, "Currency and country lists have different lengths")
            return "Error: Currency and country lists must have the same length"
        
        for idx, (currency, country) in enumerate(zip(currency_list, country_list), start=1):
            # Skip empty values
            if not currency or not country:
                log("WARNING", module, process, f"Skipping row {idx} due to missing fields")
                continue
                
            # Clean up values
            currency = currency.strip()
            country = country.strip()
            
            try:
                # All records initially set to is_system=False
                app_tables.currency.add_row(currency=currency, country=country, is_system=False)
                inserted += 1
                log("DEBUG", module, process, f"Inserted row {idx}", {"currency": currency, "country": country})
            except Exception as db_err:
                log("ERROR", module, process, f"Insert failed at row {idx}", {"error": str(db_err)})
                return f"Error inserting row {idx}: {db_err}"
        
        # After importing, set a specific row as system record
        if inserted > 0:
            try:
                # Set USD as the system currency
                system_row = app_tables.currency.get(currency="USD")
                if system_row:
                    system_row["is_system"] = True
                    log("INFO", module, process, "Set USD as system currency")
            except Exception as sys_err:
                log("WARNING", module, process, "Could not set system currency", {"error": str(sys_err)})
                
        result = f"Success - {inserted} rows imported."
        log("INFO", module, process, result)
        return result
        
    except Exception as e:
        log("ERROR", module, process, "Unexpected error", {"error": str(e)})
        return f"Server-side error during import: {type(e).__name__}: {e}"
      
@anvil.server.callable
def get_currencies():
    """Return all currencies from the currency table."""
    return [
        {
            'currency': row['currency'],
            'country': row['country'],
            'is_system': row['is_system']
        }
        for row in app_tables.currency.search()
    ]

@anvil.server.callable
def set_system_currency(currency_data):
    """Set the system currency to the provided currency and country.
       Returns True on success, False on failure.
    """
    currency_code = currency_data.get('currency')
    currency_country = currency_data.get('country')

    if not currency_code or not currency_country:
        return False

    # Find the existing system currency (if any) and unset it
    existing_system_currency = app_tables.currency.get(is_system=True)
    if existing_system_currency:
        existing_system_currency.update(is_system=False)

    # Find the new currency row and set is_system=True
    new_system_currencies = app_tables.currency.search(currency=currency_code, country=currency_country)

    if not new_system_currencies:
        return False  # Currency not found

    new_system_currency = new_system_currencies[0]
    new_system_currency.update(is_system=True)

    return True  # Success

# In helper_functions.py

@anvil.server.callable
def get_system_currency():
  """Return the current system currency (currency and country), or None if one does not exist."""
  system_currency = app_tables.currency.get(is_system=True)
  if system_currency:
    return {
      'currency': system_currency['currency'],
      'country': system_currency['country']
    }
  return None

@anvil.server.callable
def get_is_system_currency_set():
    """Return True if any currency is set as is_system=True, False otherwise."""
    system_currency = app_tables.currency.get(is_system=True)
    return system_currency is not None #Returns True if System currency is set

@anvil.server.callable
def get_currency_options():
    currencies = app_tables.currency.search()
    return [f"{c['currency']} ({c['country']})" for c in currencies]

@anvil.server.callable
def get_tax_included_setting():
    setting = app_tables.app_settings.get(setting_name="tax_included")
    return setting['value_bool']

@anvil.server.callable # Or remove if only called by other server code
def save_prod_image_to_db(file, zone, name):
    """Saves the uploaded file to the 'files' table and returns the img_url."""
    if not file:
        return None # Return None if no file provided

    file_name = name if name else getattr(file, "name", "Unknown")
    size = file.length if hasattr(file, "length") else 0
    file_type = file.content_type if hasattr(file, "content_type") else "Unknown"
    created_at = datetime.datetime.now()

    new_file_row = app_tables.files.add_row(
        file=file,
        name=file_name,
        size=size,
        file_type=file_type,
        created_at=created_at,
        zone=zone
    )
    print(f"DEBUG: Returning type from save_prod_image_to_db: {type(new_file_row)}")
    # Optional: Update the stored img_url if needed, but getting it on demand is often better.
    try:
        img_url = new_file_row['file'].get_url(download=False)
        new_file_row.update(img_url=img_url)
    except Exception as e:
        print(f"Warning: Could not generate/update img_url for file {new_file_row['name']}: {e}")
  
    # Return the img_url string
    return new_file_row['img_url']
    

def _row_to_dict_deep(row):
    """
    Converts an Anvil Row to a dict, ensuring linked rows are also
    converted to dicts or set to None if conversion fails.
    Handles 'subscription_group', 'currency', and 'media' links specifically.
    Removes warnings previously printed for non-Row link conversions.
    """
    if not row:
        return None
    # Start with a basic dictionary conversion
    row_dict = dict(row)

    # --- Process 'subscription_group' Link ---
    group_link = row_dict.get('subscription_group')
    if isinstance(group_link, tables.Row):
        row_dict['subscription_group'] = dict(group_link)
    elif group_link is not None:
        # If it's not a Row but not None (e.g., unexpected proxy), try converting, else None
        try:
            # Attempt conversion (works for Row and Proxy)
            row_dict['subscription_group'] = dict(group_link)
            # REMOVED: print(f"Warning: Converted non-Row 'subscription_group' link of type {type(group_link)}.")
        except TypeError:
            print(f"Warning: Could not convert 'subscription_group' link of type {type(group_link)} to dict. Setting to None.")
            row_dict['subscription_group'] = None
    # If group_link was None initially, it remains None

    # --- Process 'currency' Link ---
    currency_link = row_dict.get('currency')
    if isinstance(currency_link, tables.Row):
        row_dict['currency'] = dict(currency_link)
    elif currency_link is not None:
        try:
            # Attempt conversion (works for Row and Proxy)
            row_dict['currency'] = dict(currency_link)
            # REMOVED: print(f"Warning: Converted non-Row 'currency' link of type {type(currency_link)}.")
        except TypeError:
            print(f"Warning: Could not convert 'currency' link of type {type(currency_link)} to dict. Setting to None.")
            row_dict['currency'] = None
    # If currency_link was None initially, it remains None

    # --- Process 'media' Link ---
    media_link = row_dict.get('media')
    if isinstance(media_link, tables.Row):
        # Convert media row and attempt to add img_url
        media_dict = dict(media_link)
        # Access file object from original row passed to this function
        media_row_obj = row.get('media') # Use original row for reliable access
        media_file = media_row_obj.get('file') if media_row_obj else None

        if media_file and hasattr(media_file, 'get_url'):
            try:
                media_dict['img_url'] = media_file.get_url(download=False)
            except Exception as e: # Catch potential errors during get_url
                print(f"Warning: Could not get URL for media file: {e}")
                media_dict['img_url'] = None
        else:
            media_dict['img_url'] = None
        row_dict['media'] = media_dict # Replace row proxy with dict
    elif media_link is not None:
        # If it's not a Row but not None (e.g., unexpected proxy), try converting, else None
        try:
            media_dict = dict(media_link)
            # Cannot reliably get img_url here without original file object
            media_dict.setdefault('img_url', None)
            row_dict['media'] = media_dict
            # REMOVED: print(f"Warning: Converted non-Row 'media' link of type {type(media_link)}.")
        except TypeError:
            print(f"Warning: Could not convert 'media' link of type {type(media_link)} to dict. Setting to None.")
            row_dict['media'] = None # Ensure it's None if conversion fails
    # If media_link was None initially, it remains None

    return row_dict

@anvil.server.callable
def add_message(name, email, message):
  app_tables.contact.add_row(name=name, email=email, message=message, date=datetime.now())
  anvil.email.send(from_name="Contact Form", 
                   subject="New Web Contact",
                   text=f"New web contact from {name} ({email})\nMessage: {message}")
  
@anvil.server.callable
def add_subscriber(email):
  app_tables.subscribers.add_row(email=email)


@anvil.server.callable
def list_target_items_for_discount_dropdown():
  """
    Fetches MyBizz items (Products, Services, and priced Subscription Plans)
    suitable for being targeted by a discount.
    Returns a list of (display_text, item_anvil_id) tuples.
    """
  # Optional: Add permission check if needed
  # from .sessions_server import is_admin_user
  # if not is_admin_user():
  #     raise anvil.server.PermissionDenied("Admin access required.")

  items_for_dropdown = []

  # Fetch Products and Services
  prod_serv_items = app_tables.items.search(
    item_type=q.any_of('product', 'service'),
    status='active' # Only active items can have new discounts
  )
  for item in prod_serv_items:
    display_text = f"{item['name']} ({item['item_id']} - {item['item_type'].title()})"
    items_for_dropdown.append((display_text, item.get_id()))

    # Fetch Priced Subscription Plans (GLT items)
    # A GLT item is discountable if it has a default_price_id that links to a
    # 'prices' row which, in turn, has a paddle_price_id (meaning it's synced and priced in Paddle).
    # Tier 1 (Free) plans typically wouldn't have a paddle_price_id.

    # This query is a bit more complex due to the join-like nature.
    # One way: Iterate through subscription_plan items and check their price.
  sub_plan_items = app_tables.items.search(item_type='subscription_plan', status='active')
  for plan_item in sub_plan_items:
    price_link = plan_item.get('default_price_id') # This is a Link to the 'prices' table
    if price_link and price_link.get('paddle_price_id'): # Check if linked price exists and has a paddle_price_id
      # Further check if this plan is not a "Free" tier if that's a strict rule
      # For example, if GLT naming implies tier (e.g., item_id "G1L1T1" is free)
      # For now, any sub plan with a synced Paddle Price is considered.
      display_text = f"{plan_item['name']} ({plan_item['item_id']} - Subscription Plan)"
      items_for_dropdown.append((display_text, plan_item.get_id()))

    # Sort the final list
  items_for_dropdown.sort(key=lambda x: x[0]) # Sort by display_text

  return items_for_dropdown