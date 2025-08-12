# sessions_server.py (Using hashlib)
from datetime import datetime, timedelta, timezone
from anvil.tables import app_tables
import anvil.server
import anvil.users
import anvil.tables.query as q
import anvil.secrets
from sm_logs_mod import log
import hashlib # <-- Import hashlib
import os # <-- Import os for salt generation
import hmac # <-- Import hmac (though not directly used here, good practice)
import traceback
import anvil.tables as tables


# --- Constants ---
TEMP_ADMIN_TIMEOUT_MINUTES = 10
SESSION_EXPIRY_CLEANUP_HOURS = 24
OWNER_ROLE_NAME = "Owner" # MODIFIED - Changed to uppercase "Owner"
ADMIN_ROLE_NAME = "Admin" # MODIFIED - Changed to uppercase "Admin"
OWNER_PASSWORD_VAULT_KEY = "owner_password"
HASH_ITERATIONS = 260000 # Recommended iterations for PBKDF2_HMAC SHA256
TEMP_SETUP_ROLE_NAME = "owner" # Lowercase as per your plan
# --- Core Session Logic ---

@anvil.server.callable
def grant_temp_admin_session():
  """
    Grants a time-limited temporary admin session to the currently logged-in user.
    Requires the user to have successfully validated the owner password beforehand.
    """
  log("DEBUG", "sessions_server", "grant_temp_admin_session", "Attempting to grant temp admin session")
  user = anvil.users.get_user()
  if not user:
    log("ERROR", "sessions_server", "grant_temp_admin_session", "User not logged in")
    raise anvil.server.PermissionDenied("User must be logged in to grant a temporary session.")

  expiry = datetime.utcnow() + timedelta(minutes=TEMP_ADMIN_TIMEOUT_MINUTES)
  now = datetime.utcnow()

  try:
    # Use get() and update() or add_row() for atomicity
    session_row = app_tables.sessions.get(user=user)
    if session_row:
      session_row.update(
        is_temp_admin=True,
        expires_at=expiry,
        created_at=now # Update creation time to reflect new session grant
      )
      log("INFO", "sessions_server", "grant_temp_admin_session", f"Updated existing session row for user {user['email']} as temp admin", {"user_id": user.get_id(), "expiry": expiry.isoformat()})
    else:
      app_tables.sessions.add_row(
        user=user,
        is_temp_admin=True,
        expires_at=expiry,
        created_at=now
      )
      log("INFO", "sessions_server", "grant_temp_admin_session", f"Created new session row for user {user['email']} as temp admin", {"user_id": user.get_id(), "expiry": expiry.isoformat()})
    return True # Indicate success
  except Exception as e:
    log("ERROR", "sessions_server", "grant_temp_admin_session", f"Failed to grant/update session for user {user['email']}", {"user_id": user.get_id(), "error": str(e)})
    raise Exception(f"Failed to grant temporary admin session: {e}")


@anvil.server.callable
def is_temp_admin_session_active():
  """
    Checks if the currently logged-in user has an active (non-expired)
    temporary admin session record in the sessions table.
    Returns True if active, False otherwise.
    """
  # No initial log here to avoid spamming on frequent checks

  user = anvil.users.get_user()
  if user is None:
    # log("DEBUG", "sessions_server", "is_temp_admin_session_active", "No user logged in")
    return False # Not logged in, so no session

  try:
    session = app_tables.sessions.get(user=user)
    if session and session['is_temp_admin']:
      now = datetime.utcnow()
      if session['expires_at'] and session['expires_at'] > now:
        # log("DEBUG", "sessions_server", "is_temp_admin_session_active", f"User {user['email']} has active temp session", {"user_id": user.get_id()})
        return True # Session exists, is temp admin, and not expired
      elif session['expires_at'] and session['expires_at'] <= now:
        # Session expired, update the flag for clarity
        log("INFO", "sessions_server", "is_temp_admin_session_active", f"Temp session expired for user {user['email']}, updating flag", {"user_id": user.get_id()})
        session.update(is_temp_admin=False)
        return False # Expired
      else:
        # Should not happen if expires_at is always set, but handle defensively
        log("WARNING", "sessions_server", "is_temp_admin_session_active", f"Temp session found for user {user['email']} but has no expiry date", {"user_id": user.get_id()})
        session.update(is_temp_admin=False) # Mark as inactive if expiry is missing
        return False
  except Exception as e:
    # Log error but return False for safety
    log("ERROR", "sessions_server", "is_temp_admin_session_active", f"Error checking temp session for user {user['email'] if user else 'None'}", {"error": str(e)})

    # log("DEBUG", "sessions_server", "is_temp_admin_session_active", f"User {user['email']} has no active temp session", {"user_id": user.get_id()})
  return False # No session found or not temp admin


# --- Role-Based Access Control (RBAC) Checks ---

@anvil.server.callable
def is_admin_user():
  user = anvil.users.get_user()
  log("DEBUG", "sessions_server", "is_admin_user", f"Entry. User object type: {type(user)}, User: {user}")
  if user is None:
    log("DEBUG", "sessions_server", "is_admin_user", "No user logged in, returning False.")
    return False
  try:
    user_role_name = None
    role_link_obj = None 

    try:
      # MODIFIED: Attempt direct dictionary access for 'role'
      role_link_obj = user['role'] 
      log("DEBUG", "sessions_server", "is_admin_user", f"Value of user['role']: {role_link_obj}, Type: {type(role_link_obj)}")
    except TypeError: 
      log("ERROR", "sessions_server", "is_admin_user", f"TypeError accessing user['role']. User object not subscriptable. User: {user}", {"trace": traceback.format_exc()})
      return False 
    except KeyError: 
      log("DEBUG", "sessions_server", "is_admin_user", f"User {user['email']} has no 'role' key in user object.")
      # No role assigned, will proceed to check temp session
    except Exception as e_user_role_access: 
      log("ERROR", "sessions_server", "is_admin_user", f"Unexpected error accessing user['role'] for {user['email']}. Error: {str(e_user_role_access)}", {"trace": traceback.format_exc()})
      return False

    if role_link_obj:
      try:
        # Now that we have role_link_obj, try to get its 'name'
        user_role_name = role_link_obj['name']
        log("DEBUG", "sessions_server", "is_admin_user", f"Fetched role name '{user_role_name}' from role_link_obj for user {user['email']}.")
      except TypeError:
        log("WARNING", "sessions_server", "is_admin_user", f"role_link_obj for user {user['email']} is not subscriptable. Role Link: {role_link_obj}")
      except KeyError:
        log("WARNING", "sessions_server", "is_admin_user", f"role_link_obj for user {user['email']} does not have a 'name' key. Role Link: {role_link_obj}")
      except Exception as e_role_name_fetch:
        log("ERROR", "sessions_server", "is_admin_user", f"Error fetching 'name' from role_link_obj for user {user['email']}. Role Link: {role_link_obj}. Error: {str(e_role_name_fetch)}", {"trace": traceback.format_exc()})
    else:
      log("DEBUG", "sessions_server", "is_admin_user", f"User {user['email']} has no role linked (user['role'] was None or evaluated to False).")

    if user_role_name == OWNER_ROLE_NAME or user_role_name == ADMIN_ROLE_NAME:
      log("INFO", "sessions_server", "is_admin_user", f"User {user['email']} has role '{user_role_name}' and is considered admin.")
      return True

    if is_temp_admin_session_active():
      log("INFO", "sessions_server", "is_admin_user", f"User {user['email']} has active temp admin session.")
      return True

  except Exception as e: 
    log("ERROR", "sessions_server", "is_admin_user", f"Outer error checking admin status for user {user['email'] if user else 'N/A'}: {type(e).__name__}: {e}",
        {"user_id": user.get_id() if user and hasattr(user, 'get_id') else "N/A", "error": str(e), "trace": traceback.format_exc()})
    return False 

  log("INFO", "sessions_server", "is_admin_user", f"User {user['email'] if user else 'N/A'} is not an admin.")
  return False

@anvil.server.callable
def is_owner_user():
  user = anvil.users.get_user()
  log("DEBUG", "sessions_server", "is_owner_user", f"Entry. User object type: {type(user)}, User: {user}")
  if user is None:
    log("DEBUG", "sessions_server", "is_owner_user", "No user logged in, returning False.")
    return False
  try:
    user_role_name = None
    role_link_obj = None

    try:
      # MODIFIED: Attempt direct dictionary access for 'role'
      role_link_obj = user['role']
      log("DEBUG", "sessions_server", "is_owner_user", f"Value of user['role'] for owner check: {role_link_obj}, Type: {type(role_link_obj)}")
    except TypeError:
      log("ERROR", "sessions_server", "is_owner_user", f"TypeError accessing user['role'] for owner check. User object not subscriptable. User: {user}", {"trace": traceback.format_exc()})
      return False
    except KeyError:
      log("DEBUG", "sessions_server", "is_owner_user", f"User {user['email']} has no 'role' key for owner check.")
    except Exception as e_user_role_access:
      log("ERROR", "sessions_server", "is_owner_user", f"Unexpected error accessing user['role'] for owner check for {user['email']}. Error: {str(e_user_role_access)}", {"trace": traceback.format_exc()})
      return False

    if role_link_obj:
      try:
        user_role_name = role_link_obj['name']
      except TypeError:
        log("WARNING", "sessions_server", "is_owner_user", f"role_link_obj for user {user['email']} for owner check is not subscriptable. Role Link: {role_link_obj}")
      except KeyError:
        log("WARNING", "sessions_server", "is_owner_user", f"role_link_obj for user {user['email']} for owner check does not have a 'name' key. Role Link: {role_link_obj}")
      except Exception as e_role_name_fetch:
        log("ERROR", "sessions_server", "is_owner_user", f"Error fetching 'name' from role_link_obj for owner check for user {user['email']}. Role Link: {role_link_obj}. Error: {str(e_role_name_fetch)}", {"trace": traceback.format_exc()})
    else:
      log("DEBUG", "sessions_server", "is_owner_user", f"User {user['email']} has no role linked for owner check (user['role'] was None or evaluated to False).")

    is_owner = (user_role_name == OWNER_ROLE_NAME)
    if is_owner:
      log("INFO", "sessions_server", "is_owner_user", f"User {user['email']} is Owner.")
    else:
      log("INFO", "sessions_server", "is_owner_user", f"User {user['email']} is NOT Owner (Role name found: {user_role_name}).")
    return is_owner
  except Exception as e:
    log("ERROR", "sessions_server", "is_owner_user", f"Outer error checking owner status for user {user['email'] if user else 'N/A'}: {type(e).__name__}: {e}",
        {"user_id": user.get_id() if user and hasattr(user, 'get_id') else "N/A", "error": str(e), "trace": traceback.format_exc()})
    return False

# --- Owner Bootstrap Logic ---

@anvil.server.callable
def check_or_init_owner():
  """
    Checks if an 'Owner' user exists in the system.
    Intended to be called on application startup/first login.
    Returns a dictionary: {'setup_needed': True/False}.
    """
  module_name = "sessions_server" 
  function_name = "check_or_init_owner"
  log("INFO", module_name, function_name, "Checking if owner setup is needed")
  try:
    # First, get the 'Owner' role row object from the 'roles' table
    # OWNER_ROLE_NAME is now "Owner" (uppercase)
    owner_role_row = app_tables.roles.get(name=OWNER_ROLE_NAME) 

    if not owner_role_row:
      log("CRITICAL", module_name, function_name, f"The '{OWNER_ROLE_NAME}' role definition does not exist in the 'roles' table. RBAC seeding might be required.")
      # If the "Owner" role itself doesn't exist, setup is definitely needed, 
      # but RBAC initialization (seeding roles) is a prerequisite.
      return {'setup_needed': True, 'error': "Owner role definition missing."}

      # Now search the users table using the owner_role_row object
    owner_user_exists = app_tables.users.get(role=owner_role_row) # Use the role row object

    if owner_user_exists:
      log("INFO", module_name, function_name, "Owner user found.", {"owner_email": owner_user_exists['email']})
      return {'setup_needed': False}
    else:
      log("INFO", module_name, function_name, "No owner user found. Setup is needed.")
      return {'setup_needed': True}
  except Exception as e:
    log("CRITICAL", module_name, function_name, "Error checking for owner user", {"error": str(e), "trace": traceback.format_exc()})
    return {'setup_needed': True, 'error': f"Error during owner check: {str(e)}"}

# sessions_server.py (Corrected Owner Check)

@anvil.server.callable
def set_initial_owner_password(password):
  """
    Sets the initial owner password in the vault and assigns the temporary 'owner' (lowercase)
    role to the currently logged-in user.
    """
  module_name = "sessions_server"
  function_name = "set_initial_owner_password"
  user = anvil.users.get_user()
  log_context = {"user_email": user['email'] if user else "Unknown"}
  log("INFO", module_name, function_name, "Attempting to set initial owner password and assign temporary role.", log_context)

  if not user:
    log("ERROR", module_name, function_name, "No user logged in for setup.", log_context)
    raise anvil.server.PermissionDenied("You must be logged in to set the initial owner password.")

    # Get the temporary 'owner' (lowercase) role row
  temp_owner_role_row = app_tables.roles.get(name=TEMP_SETUP_ROLE_NAME) # Uses "owner"
  if not temp_owner_role_row:
    log("CRITICAL", module_name, function_name, f"The temporary setup role '{TEMP_SETUP_ROLE_NAME}' is missing. This should have been created by owner_setup_form calling ensure_temporary_owner_role_exists.", log_context)
    raise Exception(f"Critical setup error: Temporary setup role '{TEMP_SETUP_ROLE_NAME}' missing.")

    # Check if any user is already assigned the *permanent* "Owner" (uppercase) role
    # This is a safeguard against unexpected states.
  permanent_owner_role = app_tables.roles.get(name=OWNER_ROLE_NAME) # OWNER_ROLE_NAME = "Owner" (uppercase)
  if permanent_owner_role:
    existing_permanent_owners = list(app_tables.users.search(role=permanent_owner_role))
    if existing_permanent_owners:
      log("ERROR", module_name, function_name, "Owner setup attempted, but a user is already assigned the permanent 'Owner' role.", {**log_context, "found_owners": [o['email'] for o in existing_permanent_owners]})
      raise anvil.server.PermissionDenied("Owner setup appears to have already been fully completed for another user.")

    # Check if owner password already exists in vault
  password_entry = app_tables.vault.get(key=OWNER_PASSWORD_VAULT_KEY)
  if password_entry:
    log("ERROR", module_name, function_name, "Owner password entry already exists in vault.", log_context)
    raise anvil.server.PermissionDenied("Owner password entry already exists.")

  MIN_PASSWORD_LENGTH = 8 
  if not password or len(password) < MIN_PASSWORD_LENGTH:
    log("WARNING", module_name, function_name, "Password too short.", log_context)
    raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.")

  try:
    salt = os.urandom(16) 
    password_bytes = password.encode('utf-8')
    hashed_password_bytes = hashlib.pbkdf2_hmac(
      'sha256',
      password_bytes,
      salt,
      HASH_ITERATIONS
    )
    now = datetime.now(timezone.utc)
    app_tables.vault.add_row(
      key=OWNER_PASSWORD_VAULT_KEY,
      value=hashed_password_bytes.hex(), 
      salt=salt.hex(), 
      description="Hashed password (PBKDF2-HMAC-SHA256) for the application Owner role.",
      scope="System",
      owner=user,
      created_at=now,
      updated_at=now
    )

    # Assign the temporary 'owner' (lowercase) role to the current user
    user.update(role=temp_owner_role_row) 

    log("INFO", module_name, function_name, f"Successfully set initial owner password and assigned temporary role '{TEMP_SETUP_ROLE_NAME}'.", log_context)
    return True 

  except Exception as e:
    log("CRITICAL", module_name, function_name, "Failed during owner password setup.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise Exception(f"Owner password setup failed: {e}")


# --- Utility Functions ---

@anvil.server.callable
@anvil.server.background_task
def cleanup_expired_sessions():
  """
    Background task to delete expired session rows older than a defined threshold.
    """
  log("INFO", "sessions_server", "cleanup_expired_sessions", "Starting background task to clean up expired sessions")
  threshold = datetime.utcnow() - timedelta(hours=SESSION_EXPIRY_CLEANUP_HOURS)
  count = 0
  try:
    # Find sessions that are marked as temporary admin but have expired
    expired_temp_admin = app_tables.sessions.search(
      is_temp_admin=True,
      expires_at=q.less_than(datetime.utcnow()) # Expired right now
    )
    for row in expired_temp_admin:
      log("INFO", "sessions_server", "cleanup_expired_sessions", "Marking expired temp admin session as inactive", {"user_email": row['user']['email'] if row['user'] else 'Unknown', "session_id": row.get_id()})
      row.update(is_temp_admin=False) # Mark as inactive instead of deleting immediately

      # Find old, non-temporary sessions (or sessions where expiry is very old)
    old_sessions_to_delete = app_tables.sessions.search(
      q.any_of(
        # Non-temp sessions older than threshold (based on creation/update?)
        # Let's use expires_at for deletion threshold for simplicity, assuming it's set even for non-temp?
        # If expires_at is only for temp, this needs adjustment.
        # Assuming we only want to delete *very* old records regardless of temp status:
        expires_at=q.less_than(threshold)
        # Or maybe based on created_at if expires_at is often null?
        # created_at=q.less_than(threshold)
      )
    )

    for row in old_sessions_to_delete:
      user_email = row['user']['email'] if row['user'] else 'Unknown User'
      log("DEBUG", "sessions_server", "cleanup_expired_sessions", "Deleting old session row", {"user_email": user_email, "session_id": row.get_id(), "expires_at": row['expires_at']})
      row.delete()
      count += 1

    log("INFO", "sessions_server", "cleanup_expired_sessions", f"Finished cleanup task. Marked expired temp sessions inactive. Deleted {count} old session rows.")
  except Exception as e:
    log("ERROR", "sessions_server", "cleanup_expired_sessions", "Error during session cleanup task", {"error": str(e)})

# Consider scheduling the cleanup task if not already done elsewhere
# anvil.server.schedule(cleanup_expired_sessions, interval=3600*SESSION_EXPIRY_CLEANUP_HOURS)

@anvil.server.callable
def ensure_temporary_owner_role_exists():
  """
    Checks if the temporary 'owner' (lowercase) role exists. 
    If not, creates a basic entry for initial setup.
    Called by owner_setup_form.py.
    """
  module_name = "sessions_server"
  function_name = "ensure_temporary_owner_role_exists"

  try:
    temp_role = app_tables.roles.get(name=TEMP_SETUP_ROLE_NAME)
    if not temp_role:
      log("INFO", module_name, function_name, f"Temporary setup role '{TEMP_SETUP_ROLE_NAME}' not found. Creating it.")
      app_tables.roles.add_row(
        name=TEMP_SETUP_ROLE_NAME,
        is_system_role=False, # This is a temporary, non-system role
        description="Temporary role solely for initial owner password setup.",
        # role_id (MyBizz PK) can be left blank; it's temporary and will be deleted.
        created_at_anvil=datetime.now(timezone.utc),
        updated_at_anvil=datetime.now(timezone.utc)
      )
      log("INFO", module_name, function_name, f"Temporary setup role '{TEMP_SETUP_ROLE_NAME}' created.")
      # else:
      # log("DEBUG", module_name, function_name, f"Temporary setup role '{TEMP_SETUP_ROLE_NAME}' already exists.")
    return True
  except Exception as e:
    log("ERROR", module_name, function_name, f"Error ensuring temporary setup role '{TEMP_SETUP_ROLE_NAME}' exists: {str(e)}", {"trace": traceback.format_exc()})
    return False