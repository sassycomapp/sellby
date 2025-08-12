# Server Module: vault_server.py (Using hashlib)

import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from datetime import datetime
from sm_logs_mod import log
import hashlib # <-- Import hashlib
import hmac # <-- Import hmac for compare_digest
import os # <-- Import os (though not directly used here, good practice)
from cryptography.fernet import Fernet, InvalidToken # Keep for other secrets
# Import the centralized authorization functions and logging
from .sessions_server import is_admin_user, OWNER_PASSWORD_VAULT_KEY, HASH_ITERATIONS # Import HASH_ITERATIONS

# --- Vault Operations ---
@anvil.server.callable
def validate_owner_password(password_attempt):
    """
    Validates the provided password attempt against the hashed owner password
    stored in the vault. Uses hashlib.pbkdf2_hmac and hmac.compare_digest.
    """
    log("DEBUG", "vault_server", "validate_owner_password", "Attempting to validate owner password using hashlib")

    # --- Get user information for logging ---
    user = anvil.users.get_user()
    user_email = user.get('email', 'Email Missing') if user else "No user logged in"
    # --- End user info retrieval ---

    if not password_attempt:
        log("WARNING", "vault_server", "validate_owner_password", f"Empty password attempt received from user {user_email}")
        return False

    try:
        secret_row = app_tables.vault.get(key=OWNER_PASSWORD_VAULT_KEY)

        if secret_row:
            stored_hash_hex = secret_row['value'] # Hash stored in 'value'
            stored_salt_hex = secret_row['salt'] # Salt stored in 'salt'

            if not stored_hash_hex or not stored_salt_hex:
                 log("CRITICAL", "vault_server", "validate_owner_password", f"Owner password vault entry exists but hash ('value') or 'salt' is empty! User: {user_email}")
                 return False

            # --- Securely check the password against the hash using hashlib ---
            try:
                # Decode hex salt and hash back to bytes
                salt_bytes = bytes.fromhex(stored_salt_hex)
                stored_hash_bytes = bytes.fromhex(stored_hash_hex)

                # Hash the password attempt using the stored salt
                password_attempt_bytes = password_attempt.encode('utf-8')
                password_attempt_hash_bytes = hashlib.pbkdf2_hmac(
                    'sha256',
                    password_attempt_bytes,
                    salt_bytes,
                    HASH_ITERATIONS # Use the same iterations as when hashing
                )

                # Compare the generated hash with the stored hash securely
                is_valid = hmac.compare_digest(stored_hash_bytes, password_attempt_hash_bytes)

            except (ValueError, TypeError) as ve:
                # Handle potential errors if the stored hash/salt hex is invalid
                log("ERROR", "vault_server", "validate_owner_password", f"Invalid stored hash/salt format for owner password. User: {user_email}", {"error": str(ve)})
                return False
            # --- End hashlib check ---

            if is_valid:
                log("INFO", "vault_server", "validate_owner_password", f"Owner password validation successful (hashlib) for user {user_email}")
                return True
            else:
                log("INFO", "vault_server", "validate_owner_password", f"Owner password validation failed (hashlib) for user {user_email}")
                return False
        else:
            log("CRITICAL", "vault_server", "validate_owner_password", f"Secret '{OWNER_PASSWORD_VAULT_KEY}' not found in vault table. Cannot validate. User: {user_email}")
            return False

    except Exception as e:
        log("ERROR", "vault_server", "validate_owner_password", f"Error during owner password validation (hashlib) for user {user_email}", {"error": str(e)})
        return False # Return False on any error during validation

# Make sure is_admin_user() is defined or imported in this server module
# (It is imported from sessions_server)

@anvil.server.callable
def get_all_secrets():
    """
    Returns a list of dictionaries containing secret details (key, scope, description, id).
    Requires admin privileges (Owner, Admin, or active Temp Admin).
    Excludes the owner password entry for security.
    """
    log("DEBUG", "vault_server", "get_all_secrets", "Attempting to get all secrets")

    if not is_admin_user():
        user_email = anvil.users.get_user()['email'] if anvil.users.get_user() else "None"
        log("WARNING", "vault_server", "get_all_secrets", "Permission denied", {"user_email": user_email})
        raise anvil.server.PermissionDenied("Admin privileges required to view secrets.")

    user = anvil.users.get_user()
    try:
        # Fetch all rows using server permissions, excluding the owner password row
        all_secret_rows = app_tables.vault.search(key=q.not_(OWNER_PASSWORD_VAULT_KEY))

        secrets_list_for_client = []
        for row in all_secret_rows:
            secrets_list_for_client.append({
                'key': row['key'],
                'scope': row['scope'],
                'description': row['description'],
                'row_id': row.get_id() # Include the row ID for deletion
            })

        log("INFO", "vault_server", "get_all_secrets", f"Returning {len(secrets_list_for_client)} non-owner secrets as dicts for user {user['email']}", {"user_id": user.get_id()})
        return secrets_list_for_client

    except Exception as e:
        user_email = user['email'] if user else "None"
        user_id_val = user.get_id() if user else "None"
        log("ERROR", "vault_server", "get_all_secrets", f"Failed to retrieve secrets for user {user_email}", {"user_id": user_id_val, "error": str(e)})
        raise Exception(f"Failed to retrieve secrets: {e}")


@anvil.server.callable
def save_secret(key, value, scope, description):
    """
    Saves (adds or updates) a secret in the vault. Encrypts the value using Fernet.
    Requires admin privileges. Prevents owner password modification.
    Uses 'encrypted_value' column.
    """
    log("DEBUG", "vault_server", "save_secret", f"Attempting to save secret with key: {key}")
    if not is_admin_user():
        log("WARNING", "vault_server", "save_secret", f"Permission denied for key '{key}'", {"user_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None"})
        raise anvil.server.PermissionDenied("Admin privileges required to save secrets.")

    user = anvil.users.get_user()

    if key == OWNER_PASSWORD_VAULT_KEY: # Prevent modification of owner password hash/salt via this function
        log("ERROR", "vault_server", "save_secret", f"Attempt to modify owner password via save_secret blocked for user {user['email']}", {"user_id": user.get_id(), "key": key})
        raise anvil.server.PermissionDenied(f"The '{OWNER_PASSWORD_VAULT_KEY}' secret cannot be modified directly.")

    if not key or value is None: # Basic validation
        log("WARNING", "vault_server", "save_secret", f"Save attempt failed for user {user['email']} due to missing key or None value", {"user_id": user.get_id(), "key": key})
        raise ValueError("Secret key cannot be empty and value cannot be None.")

    try:
        # --- Encryption Step (Fernet) ---
        encryption_key_str = anvil.secrets.get_secret("VAULT_ENCRYPTION_KEY")
        if not encryption_key_str:
             log("CRITICAL", "vault_server", "save_secret", "VAULT_ENCRYPTION_KEY not found in Anvil Secrets. Cannot save secret.")
             raise Exception("FATAL: VAULT_ENCRYPTION_KEY not found in Anvil Secrets.")
        encryption_key = encryption_key_str.encode('utf-8')
        f = Fernet(encryption_key)
        encrypted_value_bytes = f.encrypt(value.encode('utf-8'))
        encrypted_value_str = encrypted_value_bytes.decode('utf-8')
        # --- End Encryption Step ---

        now = datetime.utcnow()
        existing = app_tables.vault.get(key=key)

        if existing:
            log("INFO", "vault_server", "save_secret", f"Updating existing secret '{key}' by user {user['email']}", {"user_id": user.get_id()})
            existing.update(
                encrypted_value=encrypted_value_str, # Store ENCRYPTED value
                scope=scope,
                description=description,
                updated_at=now
                # Note: 'value' and 'salt' columns are NOT used for general secrets
            )
        else:
            log("INFO", "vault_server", "save_secret", f"Adding new secret '{key}' by user {user['email']}", {"user_id": user.get_id()})
            app_tables.vault.add_row(
                key=key,
                encrypted_value=encrypted_value_str, # Store ENCRYPTED value
                scope=scope,
                description=description,
                created_at=now,
                updated_at=now,
                owner=user
                # Note: 'value' and 'salt' columns are NOT used for general secrets
            )
        return True
    except Exception as e:
        log("ERROR", "vault_server", "save_secret", f"Failed to save secret '{key}' for user {user['email']}", {"user_id": user.get_id(), "error": str(e)})
        raise Exception(f"Failed to save secret '{key}': {e}")

@anvil.server.callable
def test_decryption(secret_key_to_test):
    """
    Callable function to test decryption of a secret (uses Fernet).
    Takes the secret key name, attempts decryption using the internal helper,
    and returns a status message. Does NOT return the secret itself.
    Requires admin privileges. Cannot test owner password.
    """
    log("INFO", "vault_server", "test_decryption", f"Attempting to test decryption for key: {secret_key_to_test}")

    if not is_admin_user():
        log("WARNING", "vault_server", "test_decryption", f"Permission denied for key '{secret_key_to_test}'", {"user_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None"})
        raise anvil.server.PermissionDenied("Admin privileges required to test decryption.")

    if not secret_key_to_test:
        return "Error: No secret key provided for testing."

    if secret_key_to_test == OWNER_PASSWORD_VAULT_KEY:
        return f"Error: Cannot test decryption for the '{OWNER_PASSWORD_VAULT_KEY}' entry."

    # Call the internal helper function to attempt decryption
    decrypted_value = _get_decrypted_secret_value(secret_key_to_test)

    if decrypted_value is not None:
        log("INFO", "vault_server", "test_decryption", f"Decryption test SUCCESSFUL for key: {secret_key_to_test}")
        return f"Success: Decryption for key '{secret_key_to_test}' worked."
    else:
        log("WARNING", "vault_server", "test_decryption", f"Decryption test FAILED for key: {secret_key_to_test}")
        return f"Failed: Could not decrypt key '{secret_key_to_test}'. Check logs for details (key not found, bad key, etc.)."

# NOTE: This function is NOT decorated with @anvil.server.callable
# It should ONLY be called by other functions within the SAME server module.
def _get_decrypted_secret_value(key):
    """
    Retrieves and decrypts the value for a given secret key from the vault table
    using Fernet and the 'encrypted_value' column.
    Returns the decrypted string value, or None if not found or decryption fails.
    Should only be called by other server functions. Does not handle owner password.
    """
    log("DEBUG", "vault_server", "_get_decrypted_secret_value", f"Internal request to decrypt secret with key: {key}")
    if not key:
        log("WARNING", "vault_server", "_get_decrypted_secret_value", "Attempt to decrypt with empty key.")
        return None
    if key == OWNER_PASSWORD_VAULT_KEY:
        log("ERROR", "vault_server", "_get_decrypted_secret_value", f"Attempt to decrypt owner password entry '{key}' using Fernet logic.")
        return None # Owner password is not encrypted with Fernet

    try:
        secret_row = app_tables.vault.get(key=key)
        if not secret_row:
            log("WARNING", "vault_server", "_get_decrypted_secret_value", f"Secret '{key}' not found in vault.")
            return None

        encrypted_value_str = secret_row['encrypted_value'] # Use 'encrypted_value' column
        if not encrypted_value_str:
             log("WARNING", "vault_server", "_get_decrypted_secret_value", f"Secret '{key}' found but encrypted value is empty.")
             return None

        # --- Decryption Step (Fernet) ---
        encryption_key_str = anvil.secrets.get_secret("VAULT_ENCRYPTION_KEY")
        if not encryption_key_str:
             log("CRITICAL", "vault_server", "_get_decrypted_secret_value", "VAULT_ENCRYPTION_KEY not found in Anvil Secrets. Cannot decrypt.")
             raise Exception("FATAL: VAULT_ENCRYPTION_KEY not found in Anvil Secrets.")
        encryption_key = encryption_key_str.encode('utf-8')
        f = Fernet(encryption_key)
        decrypted_value_bytes = f.decrypt(encrypted_value_str.encode('utf-8'))
        decrypted_value_str = decrypted_value_bytes.decode('utf-8')
        # --- End Decryption Step ---

        log("DEBUG", "vault_server", "_get_decrypted_secret_value", f"Successfully decrypted secret '{key}'.")
        return decrypted_value_str

    except InvalidToken:
         log("ERROR", "vault_server", "_get_decrypted_secret_value", f"DECRYPTION FAILED (InvalidToken) for secret '{key}'. Key mismatch or data corruption?")
         return None
    except Exception as e:
        log("ERROR", "vault_server", "_get_decrypted_secret_value", f"Failed to decrypt secret '{key}'", {"error": str(e)})
        return None

@anvil.server.callable
def delete_secret(row_id):
    """Deletes a secret by its row ID. Requires admin. Prevents owner password deletion."""
    log("DEBUG", "vault_server", "delete_secret", f"Attempting to delete secret with row_id: {row_id}")
    if not is_admin_user():
         user_email = anvil.users.get_user()['email'] if anvil.users.get_user() else "None"
         log("WARNING", "vault_server", "delete_secret", "Permission denied", {"user_email": user_email, "row_id": row_id})
         raise anvil.server.PermissionDenied("Admin privileges required to delete secrets.")

    user = anvil.users.get_user()
    try:
        secret_row = app_tables.vault.get_by_id(row_id)
        if secret_row:
            # Prevent deletion of owner password entry
            if secret_row['key'] == OWNER_PASSWORD_VAULT_KEY:
                log("WARNING", "vault_server", "delete_secret", "Attempt denied to delete protected owner password key", {"user_email": user['email'], "row_id": row_id, "key": secret_row['key']})
                raise anvil.server.PermissionDenied(f"The '{OWNER_PASSWORD_VAULT_KEY}' secret cannot be deleted.")

            key_deleted = secret_row['key']
            secret_row.delete()
            log("INFO", "vault_server", "delete_secret", f"Secret '{key_deleted}' (ID: {row_id}) deleted by user {user['email']}", {"user_id": user.get_id()})
        else:
            log("WARNING", "vault_server", "delete_secret", f"Secret with ID {row_id} not found for deletion.", {"user_email": user['email']})
            # raise Exception("Secret not found.") # Optional: raise error if not found
    except Exception as e:
        log("ERROR", "vault_server", "delete_secret", f"Failed to delete secret ID {row_id} for user {user['email']}", {"user_id": user.get_id(), "error": str(e)})
        raise Exception(f"Failed to delete secret: {e}")

# NOTE: This function is NOT decorated with @anvil.server.callable
# It is intended to be called ONLY by other functions within the SAME server module or other server modules.
def get_secret_for_server_use(secret_key_name):
    """
    Retrieves the decrypted value for a given secret key (uses Fernet).
    This is the primary function other server code should call to get general secrets.
    Returns the decrypted string value, or None if not found/decryption fails.
    Does NOT handle the owner password entry.
    """
    log("DEBUG", "vault_server", "get_secret_for_server_use", f"Server request for secret key: {secret_key_name}")

    if not secret_key_name:
        log("WARNING", "vault_server", "get_secret_for_server_use", "Called with empty secret_key_name.")
        return None

    if secret_key_name == OWNER_PASSWORD_VAULT_KEY:
        log("ERROR", "vault_server", "get_secret_for_server_use", f"Attempt to retrieve owner password entry '{secret_key_name}' using general secret retrieval function.")
        return None # Use validate_owner_password for owner password checks

    # Call the internal helper function that handles Fernet decryption
    decrypted_value = _get_decrypted_secret_value(secret_key_name)

    if decrypted_value is None:
        log("WARNING", "vault_server", "get_secret_for_server_use", f"Failed to get/decrypt secret '{secret_key_name}' for server use.")
        return None
    else:
        # log("DEBUG", "vault_server", "get_secret_for_server_use", f"Successfully retrieved secret '{secret_key_name}' for server use.")
        return decrypted_value


# Add this function to vault_server.py

@anvil.server.callable
def save_multiple_secrets(secrets_list):
  """
    Saves a list of secrets to the vault.
    Each item in secrets_list should be a dictionary:
    {'key': 'SECRET_KEY_NAME', 'value': 'secret_value', 'scope': 'ScopeName', 'description': 'Description'}
    Requires admin privileges. Uses the existing save_secret logic for individual saves.
    """
  log("DEBUG", "vault_server", "save_multiple_secrets", f"Attempting to save {len(secrets_list)} secrets.")

  # is_admin_user() is already imported and used by save_secret,
  # so individual calls to save_secret will enforce permissions.
  # We can add an upfront check here too if desired for the batch operation.
  if not is_admin_user(): # is_admin_user is from sessions_server.py
    user_email = anvil.users.get_user()['email'] if anvil.users.get_user() else "None"
    log("WARNING", "vault_server", "save_multiple_secrets", "Permission denied for batch save.", {"user_email": user_email})
    raise anvil.server.PermissionDenied("Admin privileges required to save secrets.")

  user = anvil.users.get_user()
  saved_count = 0
  errors = []

  if not isinstance(secrets_list, list):
    log("ERROR", "vault_server", "save_multiple_secrets", "Input is not a list.", {"user_email": user['email'] if user else "None"})
    raise ValueError("Input must be a list of secret dictionaries.")

  for secret_item in secrets_list:
    if not isinstance(secret_item, dict):
      errors.append(f"Invalid item format: {secret_item}. Each item must be a dictionary.")
      continue

    key = secret_item.get('key')
    value = secret_item.get('value')
    scope = secret_item.get('scope')
    description = secret_item.get('description')

    if not key or value is None: # Value can be an empty string, but not None
      errors.append(f"Missing key or value for item: {secret_item}.")
      continue

      # Scope and description can be optional for save_secret, will default if None
    scope = scope if scope is not None else "Default" 
    description = description if description is not None else ""

    try:
      # Call the existing save_secret function which handles encryption and DB write
      # save_secret already logs its own success/failure internally
      save_secret(key, value, scope, description)
      saved_count += 1
    except Exception as e:
      error_message = f"Failed to save secret '{key}': {str(e)}"
      errors.append(error_message)
      log("ERROR", "vault_server", "save_multiple_secrets", error_message, {"user_email": user['email'] if user else "None", "key": key})
      # Continue to try saving other secrets in the list

  if errors:
    # If there were any errors, raise an exception with a summary
    # The client can then decide how to display this.
    # Individual errors were already logged by save_secret or this loop.
    summary_error_message = f"Completed saving secrets with {len(errors)} error(s): {'; '.join(errors)}"
    log("WARNING", "vault_server", "save_multiple_secrets", summary_error_message, {"user_email": user['email'] if user else "None"})
    # Raise a general exception. Client-side will catch this.
    raise Exception(f"Encountered {len(errors)} error(s) while saving credentials. Please check details. First error: {errors[0]}")

  log("INFO", "vault_server", "save_multiple_secrets", f"Successfully saved {saved_count} secrets out of {len(secrets_list)} provided.", {"user_email": user['email'] if user else "None"})
  return {"message": f"Successfully saved {saved_count} secrets.", "saved_count": saved_count, "total_provided": len(secrets_list)}

# Add this function to vault_server.py

@anvil.server.callable
def get_essential_credentials_status():
  """
    Checks the MyBizz Vault for the presence of essential credential keys.
    Returns a dictionary with the status (True if set, False if not set) for each key.
    Requires admin privileges.
    """
  module_name = "vault_server"
  function_name = "get_essential_credentials_status"
  log("INFO", module_name, function_name, "Request received to get essential credentials status.")

  if not is_admin_user(): # is_admin_user is from sessions_server.py
    user_email = anvil.users.get_user()['email'] if anvil.users.get_user() else "None"
    log("WARNING", module_name, function_name, "Permission denied.", {"user_email": user_email})
    raise anvil.server.PermissionDenied("Admin privileges required to view credential statuses.")

  user = anvil.users.get_user() # Get user for logging context
  log_context = {"user_email": user['email'] if user else "None"}

  # Define the list of essential credential keys to check in the vault
  # These keys must match exactly what is stored in the vault table
  # and what essential_credentials_form.py expects.
  essential_keys = [
    "PADDLE_API_KEY",
    "paddle_webhook_secret",
    "paddle_client_token",
    "paddle_seller_id",
    "paddle_webhook_url", 
    "paddle_customer_portal_url",
    "r2hub_api_endpoint",
    "r2hub_tenant_id",
    "r2hub_api_key",
    OWNER_PASSWORD_VAULT_KEY # Check owner password status as well
  ]

  statuses = {}

  try:
    for key_name in essential_keys:
      vault_entry = app_tables.vault.get(key=key_name)
      is_set = False
      if vault_entry:
        if key_name == OWNER_PASSWORD_VAULT_KEY:
          # Owner password uses the 'value' for the hash and 'salt'
          if vault_entry['value'] and vault_entry['salt']:
            is_set = True
        else:
          # General secrets use 'encrypted_value'
          if vault_entry['encrypted_value']:
            is_set = True
      statuses[key_name] = is_set
      log("DEBUG", module_name, function_name, f"Status for '{key_name}': {'Set' if is_set else 'Not Set'}", log_context)

    log("INFO", module_name, function_name, "Successfully retrieved essential credential statuses.", log_context)
    return statuses

  except Exception as e:
    log("ERROR", module_name, function_name, "Error retrieving credential statuses.", {**log_context, "error": str(e)})
    # Raise the exception to inform the client of a failure.
    # The client-side will handle displaying an error message.
    raise Exception(f"An error occurred while checking credential statuses: {e}")