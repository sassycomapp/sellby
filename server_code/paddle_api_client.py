# Server Module: paddle_api_client.py
# Handles communication with the Paddle API v1 using Tenant's credentials.

import anvil.server
import anvil.http
import anvil.tables as tables
from anvil.tables import app_tables
import json
import traceback

# Import function to get secrets from vault (adjust path if necessary)
# Assuming vault_server has a function like get_decrypted_secret(key)
# that requires appropriate permissions (e.g., internal server call)
from .vault_server import _get_decrypted_secret_value # NEW - Correct name

# --- Constants ---
PADDLE_API_BASE_URL = "https://api.paddle.com/" # Use sandbox URL for testing: "https://sandbox-api.paddle.com/"
PADDLE_API_KEY_VAULT_KEY = "PADDLE_API_KEY" # The key used by Tenants to store their key in the vault

# --- Helper Function: Get Tenant's Paddle API Key ---
def _get_tenant_paddle_api_key():
  """
    Retrieves and decrypts the Tenant's Paddle API Key from the vault.
    This function assumes it's called within a context where the relevant
    Tenant's vault is accessible (e.g., called by other server functions
    within the same Tenant's app instance).
    Raises Exception if key is not found or cannot be decrypted.
    """
  try:
    # Assuming get_decrypted_secret handles permissions appropriately
    # or is called internally by authorized functions.
    api_key = _get_decrypted_secret_value(PADDLE_API_KEY_VAULT_KEY)
    if not api_key:
      raise ValueError(f"Paddle API Key not found in vault under key '{PADDLE_API_KEY_VAULT_KEY}'.")
      return api_key
  except Exception as e:
    print(f"Error retrieving Paddle API Key from vault: {e}")
    # Re-raise or raise a more specific error
    raise Exception("Could not retrieve necessary Paddle API credentials.")

# --- Helper Function: Make Authenticated Paddle API Request ---
def _make_paddle_request(method, endpoint, payload=None, params=None):
  """
    Makes an authenticated request to the Paddle API v1.

    Args:
        method (str): HTTP method ('GET', 'POST', 'PATCH', 'DELETE').
        endpoint (str): API endpoint path (e.g., 'products', 'prices').
        payload (dict, optional): Data payload for POST/PATCH requests.
        params (dict, optional): URL parameters for GET requests.

    Returns:
        dict: The JSON response data from Paddle.

    Raises:
        anvil.http.HttpError: If the API call fails or returns an error status.
        Exception: For configuration errors (like missing API key).
    """
  api_key = _get_tenant_paddle_api_key()
  headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
  }
  url = PADDLE_API_BASE_URL + endpoint

  try:
    print(f"Making Paddle API Request: {method} {url}") # Basic logging
    response = anvil.http.request(
      url=url,
      method=method.upper(),
      headers=headers,
      data=payload, # Anvil handles JSON encoding if data is dict
      params=params,
      json=True # Expect JSON response
    )
    # Paddle API v1 typically returns the data directly under a 'data' key
    # Errors might be structured differently - check Paddle docs for error format
    # For simplicity now, we assume success returns the desired object under 'data'
    # A more robust implementation would check response status codes and error structures
    if isinstance(response, dict) and 'data' in response:
      print(f"Paddle API Success: {method} {url}")
      return response['data']
    else:
      # Handle unexpected successful response format
      print(f"Warning: Paddle API response format unexpected for {method} {url}. Response: {response}")
      return response # Return raw response for inspection

  except anvil.http.HttpError as e:
    # Log details of the HTTP error
    error_content = "No content"
    try:
      # Try to parse error details from Paddle if available (often JSON)
      error_content = json.dumps(e.content) if e.content else "No content"
    except Exception:
      error_content = str(e.content) # Fallback to string representation

      print(f"Paddle API Error: {method} {url} failed with status {e.status}. Error: {error_content}")
    # Re-raise the error so calling functions know it failed
    raise e
  except Exception as e:
    # Catch other errors like failure to get API key
    print(f"Error during Paddle API request ({method} {url}): {e}")
    traceback.print_exc()
    raise e # Re-raise

# --- Product Functions ---

# @anvil.server.callable # Maybe not directly callable? Called by other server funcs.
def create_paddle_product(product_data):
  """
    Creates a Product in the Tenant's Paddle account.

    Args:
        product_data (dict): Data matching Paddle's Create Product API structure.
                             Must include 'name', 'tax_category'.
                             Should include 'custom_data' with MyBizz IDs.

    Returns:
        dict: The created Paddle Product object.
    """
  # Basic Validation (More specific validation should happen *before* calling this)
  if not product_data.get('name') or not product_data.get('tax_category'):
    raise ValueError("Product name and tax_category are required to create a Paddle Product.")

    endpoint = "products"
  return _make_paddle_request('POST', endpoint, payload=product_data)

# @anvil.server.callable # Maybe not directly callable?
def update_paddle_product(paddle_product_id, product_update_data):
  """
    Updates a Product in the Tenant's Paddle account.

    Args:
        paddle_product_id (str): The ID of the Paddle Product to update.
        product_update_data (dict): Data matching Paddle's Update Product API structure.
                                    Can include fields like 'name', 'description', 'status', etc.

    Returns:
        dict: The updated Paddle Product object.
    """
  if not paddle_product_id:
    raise ValueError("paddle_product_id is required to update a Paddle Product.")
    if not product_update_data:
      print("Warning: update_paddle_product called with empty update data.")
      # Optionally fetch and return the current product data? Or raise error?
      # For now, let Paddle handle empty patch if it allows it.
      # return get_paddle_product(paddle_product_id) # Example fetch
      pass # Proceed with potentially empty patch

  endpoint = f"products/{paddle_product_id}"
  return _make_paddle_request('PATCH', endpoint, payload=product_update_data)

# --- Price Functions ---

# @anvil.server.callable # Maybe not directly callable?
def create_paddle_price(price_data):
  """
    Creates a Price in the Tenant's Paddle account.

    Args:
        price_data (dict): Data matching Paddle's Create Price API structure.
                           Must include 'product_id', 'description', 'unit_price'.
                           Should include 'custom_data' with MyBizz IDs.

    Returns:
        dict: The created Paddle Price object.
    """
  # Basic Validation
  if not price_data.get('product_id') or not price_data.get('description') or not price_data.get('unit_price'):
    raise ValueError("product_id, description, and unit_price are required to create a Paddle Price.")

    endpoint = "prices"
  return _make_paddle_request('POST', endpoint, payload=price_data)

# @anvil.server.callable # Maybe not directly callable?
def update_paddle_price(paddle_price_id, price_update_data):
  """
    Updates a Price in the Tenant's Paddle account.

    Args:
        paddle_price_id (str): The ID of the Paddle Price to update.
        price_update_data (dict): Data matching Paddle's Update Price API structure.

    Returns:
        dict: The updated Paddle Price object.
    """
  if not paddle_price_id:
    raise ValueError("paddle_price_id is required to update a Paddle Price.")
    if not price_update_data:
      print("Warning: update_paddle_price called with empty update data.")
      pass # Proceed with potentially empty patch

  endpoint = f"prices/{paddle_price_id}"
  return _make_paddle_request('PATCH', endpoint, payload=price_update_data)

# --- Discount Functions (Placeholder for Phase 7) ---

# def create_paddle_discount(discount_data): ...
# def update_paddle_discount(paddle_discount_id, discount_update_data): ...
# In Server Module (e.g., helper_functions.py)
# ... (other imports) ...

@anvil.server.callable
def get_tax_use_cases(mybizz_sector_filter):
  """
    Retrieves a list of use case descriptions and their corresponding
    Paddle tax categories for a given MyBizz sector.
    Filters for active mappings and orders them.
    """
  if not mybizz_sector_filter:
    return []

    # Ensure user has permission to access this data if needed (e.g., logged in)
    # user = anvil.users.get_user(allow_remembered=True)
    # if not user:
    #     raise anvil.server.PermissionDenied("You must be logged in.")

    try:
      mappings = app_tables.tax_category_mapping.search(
        mybizz_sector=mybizz_sector_filter,
        is_active_for_mybizz=True, # Only show active mappings
        order_by="order_in_dropdown" # Use this if you populated it, else remove or use 'use_case_description'
      )

      # Format for DropDown: list of tuples (display_text, value_to_be_stored)
      # Here, display_text is use_case_description, value is paddle_tax_category
      use_cases_for_dropdown = [
        (row['use_case_description'], row['paddle_tax_category'])
        for row in mappings
      ]
      return use_cases_for_dropdown
    except Exception as e:
      print(f"Error fetching tax use cases for sector '{mybizz_sector_filter}': {e}")
      # Consider logging this error with your sm_logs_mod.log
      return [] # Return empty list on error

# --- Discount Functions ---

def create_paddle_discount(discount_data_payload):
  """
    Creates a Discount in the Tenant's Paddle account.
    Args:
        discount_data_payload (dict): Data matching Paddle's Create Discount API structure.
                                      (e.g., description, type, code, amount/rate, restrictions)
    Returns:
        dict: The created Paddle Discount object.
    """
  # Basic validation (more specific validation should happen in sm_discount_mod.py)
  if not discount_data_payload.get('description') or not discount_data_payload.get('type'):
    raise ValueError("Paddle Discount 'description' and 'type' are required.")
  if discount_data_payload['type'] == 'flat' and (not discount_data_payload.get('amount') or not discount_data_payload.get('currency_code')):
    raise ValueError("For 'flat' discount, 'amount' and 'currency_code' are required.")
  if discount_data_payload['type'] == 'percentage' and not discount_data_payload.get('rate'):
    raise ValueError("For 'percentage' discount, 'rate' is required.")

  endpoint = "discounts"
  # Paddle API v1 returns the created object directly in the 'data' field of the response
  return _make_paddle_request('POST', endpoint, payload=discount_data_payload)


def update_paddle_discount(paddle_discount_id, discount_update_payload):
  """
    Updates a Discount in the Tenant's Paddle account.
    Args:
        paddle_discount_id (str): The ID of the Paddle Discount to update.
        discount_update_payload (dict): Data matching Paddle's Update Discount API structure.
                                        Should only contain fields that are mutable.
    Returns:
        dict: The updated Paddle Discount object.
    """
  if not paddle_discount_id:
    raise ValueError("paddle_discount_id is required to update a Paddle Discount.")
  if not discount_update_payload: # If payload is empty, Paddle might error or do nothing.
    print(f"Warning: update_paddle_discount called for {paddle_discount_id} with empty payload.")
    # Optionally, one could fetch and return the current discount if no update is to be made.
    # For now, proceed and let Paddle handle it.
    pass

  endpoint = f"discounts/{paddle_discount_id}"
  # Paddle API v1 returns the updated object directly in the 'data' field of the response
  return _make_paddle_request('PATCH', endpoint, payload=discount_update_payload)