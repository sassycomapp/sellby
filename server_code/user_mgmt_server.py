# Server Module: user_mgmt_server.py (NEW FILE)
import traceback

import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.server
from sm_logs_mod import log

# --- Define Role Representation and Names Locally ---
USER_ROLE_REPRESENTATION = None
OWNER_ROLE_NAME = "owner"
ADMIN_ROLE_NAME = "admin"


# --- User Management Operations ---

@anvil.server.callable
def get_all_users():
    """
    Returns a list of all users from the users table.
    Requires admin privileges (Owner or Admin) to view.
    """
    # --- Import inside function ---
    from sessions_server import is_admin_user

    log("DEBUG", "user_mgmt_server", "get_all_users", "Attempting to get all users")
    if not is_admin_user():
        log("WARNING", "user_mgmt_server", "get_all_users", "Permission denied", {"user_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None"})
        raise anvil.server.PermissionDenied("Admin privileges required to view users.")

    user = anvil.users.get_user()
    try:
        users_list = list(app_tables.users.search())
        log("INFO", "user_mgmt_server", "get_all_users", f"Retrieved {len(users_list)} users for viewer {user['email']}", {"viewer_user_id": user.get_id()})
        return users_list
    except Exception as e:
        log("ERROR", "user_mgmt_server", "get_all_users", f"Failed to retrieve users: {e}", {"viewer_user_id": user.get_id() if user else None})
        raise Exception(f"Failed to retrieve users: {e}")


@anvil.server.callable
def update_user_role(target_user_id, new_role):
    """
    Updates the role of a target user. Requires OWNER privileges.
    """
    # --- Import inside function ---
    from sessions_server import is_owner_user

    log("DEBUG", "user_mgmt_server", "update_user_role", f"Attempting update: user {target_user_id}, role {new_role}")
    if not is_owner_user():
        log("WARNING", "user_mgmt_server", "update_user_role", "Permission denied - Owner role required", {"requestor_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None", "target_user_id": target_user_id})
        raise anvil.server.PermissionDenied("Only the Owner can change user roles.")

    requestor_user = anvil.users.get_user()

    allowed_roles = [ADMIN_ROLE_NAME, USER_ROLE_REPRESENTATION]
    if new_role not in allowed_roles:
        log("ERROR", "user_mgmt_server", "update_user_role", f"Invalid target role '{new_role}' requested by {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
        raise ValueError(f"Invalid role specified. Allowed roles: '{ADMIN_ROLE_NAME}' or standard user.")

    try:
        target_user_row = app_tables.users.get_by_id(target_user_id)
        if not target_user_row:
            log("ERROR", "user_mgmt_server", "update_user_role", f"Target user not found by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
            raise Exception("Target user not found.")

        target_email = target_user_row['email']

        if requestor_user.get_id() == target_user_row.get_id():
             log("ERROR", "user_mgmt_server", "update_user_role", f"Owner {requestor_user['email']} attempted to change their own role", {"requestor_user_id": requestor_user.get_id()})
             raise anvil.server.PermissionDenied("The Owner cannot change their own role.")

        current_role = None
        try: 
          current_role = target_user_row['role']
        except KeyError: 
          pass

        if current_role == OWNER_ROLE_NAME:
             log("ERROR", "user_mgmt_server", "update_user_role", f"Owner {requestor_user['email']} attempted to change role of another owner {target_email}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
             raise anvil.server.PermissionDenied("Cannot change the role of an Owner.")

        target_user_row.update(role=new_role)
        log("INFO", "user_mgmt_server", "update_user_role", f"Owner {requestor_user['email']} updated role for user {target_email} from '{current_role}' to '{new_role}'", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
        return True

    except Exception as e:
        log("ERROR", "user_mgmt_server", "update_user_role", f"Failed to update role for user_id {target_user_id} by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "error": str(e)})
        if isinstance(e, (anvil.server.PermissionDenied, ValueError, KeyError)): 
          raise e
        raise Exception(f"Failed to update user role: {type(e).__name__}: {e}")


@anvil.server.callable
def toggle_user_enabled(target_user_id, is_enabled):
    """
    Updates the enabled status of a target user. Requires OWNER privileges.
    """
    # --- Import inside function ---
    from sessions_server import is_owner_user

    log("DEBUG", "user_mgmt_server", "toggle_user_enabled", f"Attempting update: user {target_user_id}, enabled {is_enabled}")
    if not is_owner_user():
        log("WARNING", "user_mgmt_server", "toggle_user_enabled", "Permission denied - Owner role required", {"requestor_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None", "target_user_id": target_user_id})
        raise anvil.server.PermissionDenied("Only the Owner can change user enabled status.")

    requestor_user = anvil.users.get_user()

    if not isinstance(is_enabled, bool):
        log("ERROR", "user_mgmt_server", "toggle_user_enabled", f"Invalid 'is_enabled' value '{is_enabled}' requested by {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
        raise ValueError("Enabled status must be True or False.")

    try:
        target_user_row = app_tables.users.get_by_id(target_user_id)
        if not target_user_row:
            log("ERROR", "user_mgmt_server", "toggle_user_enabled", f"Target user not found by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
            raise Exception("Target user not found.")

        target_email = target_user_row['email']

        if requestor_user.get_id() == target_user_row.get_id() and not is_enabled:
             log("ERROR", "user_mgmt_server", "toggle_user_enabled", f"Owner {requestor_user['email']} attempted to disable their own account", {"requestor_user_id": requestor_user.get_id()})
             raise anvil.server.PermissionDenied("The Owner cannot disable their own account.")

        current_status = None
        try: 
          current_status = target_user_row['enabled']
        except KeyError: 
          pass # Assume default if missing

        target_user_row.update(enabled=is_enabled)
        log("INFO", "user_mgmt_server", "toggle_user_enabled", f"Owner {requestor_user['email']} updated enabled status for user {target_email} from '{current_status}' to '{is_enabled}'", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
        return True

    except Exception as e:
        log("ERROR", "user_mgmt_server", "toggle_user_enabled", f"Failed to update enabled status for user_id {target_user_id} by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "error": str(e)})
        if isinstance(e, (anvil.server.PermissionDenied, ValueError)): 
          raise e
        raise Exception(f"Failed to update user enabled status: {e}")


@anvil.server.callable
def delete_user(target_user_id):
    """
    Deletes a target user from the users table. Requires OWNER privileges.
    """
    # --- Import inside function ---
    from sessions_server import is_owner_user

    log("DEBUG", "user_mgmt_server", "delete_user", f"Attempting to delete user_id: {target_user_id}")
    if not is_owner_user():
        log("WARNING", "user_mgmt_server", "delete_user", "Permission denied - Owner role required", {"requestor_email": anvil.users.get_user()['email'] if anvil.users.get_user() else "None", "target_user_id": target_user_id})
        raise anvil.server.PermissionDenied("Only the Owner can delete users.")

    requestor_user = anvil.users.get_user()

    try:
        target_user_row = app_tables.users.get_by_id(target_user_id)
        if not target_user_row:
            log("ERROR", "user_mgmt_server", "delete_user", f"Target user not found for deletion by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
            raise Exception("Target user not found.")

        target_email = target_user_row['email']

        if requestor_user.get_id() == target_user_row.get_id():
             log("ERROR", "user_mgmt_server", "delete_user", f"Owner {requestor_user['email']} attempted to delete their own account", {"requestor_user_id": requestor_user.get_id()})
             raise anvil.server.PermissionDenied("The Owner cannot delete their own account.")

        current_role = None
        try: 
          current_role = target_user_row['role']
        except KeyError: 
          pass

        if current_role == OWNER_ROLE_NAME:
             log("ERROR", "user_mgmt_server", "delete_user", f"Owner {requestor_user['email']} attempted to delete another owner {target_email}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
             raise anvil.server.PermissionDenied("Cannot delete an Owner account.")

        target_user_row.delete()
        log("INFO", "user_mgmt_server", "delete_user", f"Owner {requestor_user['email']} deleted user {target_email}", {"requestor_user_id": requestor_user.get_id(), "target_user_id": target_user_id})
        return True

    except Exception as e:
        log("ERROR", "user_mgmt_server", "delete_user", f"Failed to delete user_id {target_user_id} by owner {requestor_user['email']}", {"requestor_user_id": requestor_user.get_id(), "error": str(e)})
        if isinstance(e, (anvil.server.PermissionDenied, ValueError)): 
          raise e
        raise Exception(f"Failed to delete user: {e}")

@anvil.server.callable
def get_full_user_data(user_id):
    user_table = app_tables.users
    try:
        user_row = user_table.get_by_id(user_id)
        if user_row:
            # Instead of returning the Row object, create a dictionary with the values we need
            return {
                'email': user_row['email'],
                'role': user_row['role'],  # This should contain 'admin', 'owner', or None
                'enabled': user_row.get('enabled', True)
            }
        return None
    except Exception as e:
        print(f"ERROR getting user data: {e}")
        raise

@anvil.server.callable
def assign_role_to_user(target_user_anvil_id, new_role_anvil_id):
  module_name = "user_mgmt_server"
  function_name = "assign_role_to_user"

  from .sessions_server import is_owner_user 

  requesting_user = anvil.users.get_user()
  requesting_user_email_for_log = "Unknown (requesting_user is None)"
  if requesting_user and 'email' in requesting_user: # Check if user object and email key exist
    requesting_user_email_for_log = requesting_user['email']

  log_context = {
    "target_user_anvil_id": target_user_anvil_id, 
    "new_role_anvil_id": new_role_anvil_id,
    "requesting_user_email": requesting_user_email_for_log
  }
  log("INFO", module_name, function_name, "Attempting to assign role.", log_context)

  if not is_owner_user(): 
    log("WARNING", module_name, function_name, "Permission denied - Owner role required.", log_context)
    raise anvil.server.PermissionDenied("Only the Owner can assign user roles at this time.")

  if not target_user_anvil_id:
    log("ERROR", module_name, function_name, "Target user Anvil ID not provided.", log_context)
    raise ValueError("Target user ID must be provided.")

  try:
    log("DEBUG", module_name, function_name, f"Fetching target_user_row by ID: {target_user_anvil_id}", log_context)
    target_user_row = app_tables.users.get_by_id(target_user_anvil_id)
    if not target_user_row:
      log("ERROR", module_name, function_name, "Target user not found by Anvil ID.", log_context)
      raise anvil.tables.TableError(f"Target user with Anvil ID '{target_user_anvil_id}' not found.")
    log("DEBUG", module_name, function_name, f"Target user found: {target_user_row['email']}", log_context)

    role_to_assign_row = None
    new_role_name_for_log = "None (Unassigning/Clearing Role)"

    if new_role_anvil_id: 
      log("DEBUG", module_name, function_name, f"Fetching role_to_assign_row by ID: {new_role_anvil_id}", log_context)
      role_to_assign_row = app_tables.roles.get_by_id(new_role_anvil_id)
      if not role_to_assign_row:
        log("ERROR", module_name, function_name, f"Role to assign not found by Anvil ID '{new_role_anvil_id}'.", log_context)
        raise anvil.tables.TableError(f"Role with Anvil ID '{new_role_anvil_id}' not found.")
      new_role_name_for_log = role_to_assign_row['name']
      log("DEBUG", module_name, function_name, f"Role to assign found: {new_role_name_for_log}", log_context)

    current_user_role_link = None
    if 'role' in target_user_row: # Check if 'role' key exists
      current_user_role_link = target_user_row['role']
    current_user_role_name = current_user_role_link['name'] if current_user_role_link and 'name' in current_user_role_link else "None"
    log("DEBUG", module_name, function_name, f"Current role of target user ({target_user_row['email']}) is '{current_user_role_name}'.", log_context)

    requesting_user_id = requesting_user.get_id() # get_id() is a method
    target_user_id_from_row = target_user_row.get_id()

    if target_user_id_from_row == requesting_user_id:
      if role_to_assign_row is None or (('name' in role_to_assign_row) and role_to_assign_row['name'] != "Owner"):
        log("ERROR", module_name, function_name, f"Owner {requesting_user_email_for_log} attempted to change their own role to '{new_role_name_for_log}'.", log_context)
        raise anvil.server.PermissionDenied("The Owner cannot change their own role to a non-Owner role.")

    if current_user_role_name == "Owner" and target_user_id_from_row != requesting_user_id:
      log("ERROR", module_name, function_name, f"Attempt to change role of another Owner user ({target_user_row['email']}) by {requesting_user_email_for_log}.", log_context)
      raise anvil.server.PermissionDenied("Cannot change the role of another Owner.")

    if role_to_assign_row and ('name' in role_to_assign_row) and role_to_assign_row['name'] == "Owner" and target_user_id_from_row != requesting_user_id:
      log("ERROR", module_name, function_name, f"Attempt to assign 'Owner' role to user ({target_user_row['email']}) by {requesting_user_email_for_log}.", log_context)
      raise anvil.server.PermissionDenied("The 'Owner' role cannot be assigned to other users via this function.")

    log("DEBUG", module_name, function_name, f"Attempting to update user {target_user_row['email']}'s role to '{new_role_name_for_log}'.", log_context)
    target_user_row.update(role=role_to_assign_row) 

    log("INFO", module_name, function_name, f"User {requesting_user_email_for_log} successfully updated role for user {target_user_row['email']} from '{current_user_role_name}' to '{new_role_name_for_log}'.", log_context)
    return True

  except AttributeError as ae: # Catch AttributeError specifically
    log("CRITICAL", module_name, function_name, f"AttributeError during role assignment: {str(ae)}", {**log_context, "trace": traceback.format_exc()})
    raise Exception(f"An unexpected error occurred (AttributeError): {str(ae)}") # Re-raise with specific type
  except Exception as e:
    log("ERROR", module_name, function_name, f"Failed to assign role: {str(e)}", {**log_context, "trace": traceback.format_exc()})
    if isinstance(e, (anvil.server.PermissionDenied, ValueError, anvil.tables.TableError)): 
      raise e 
    if not isinstance(e, anvil.server.AnvilWrappedError): # Avoid double-wrapping
      raise Exception(f"An unexpected error occurred while assigning user role: {type(e).__name__}: {str(e)}")
    else:
      raise e # Re-raise if already an AnvilWrappedError