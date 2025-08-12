# Server Module: sm_logs_mod.py

import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables
from datetime import datetime
import json
import traceback



# --- Constants ---
DEFAULT_LOG_LEVEL = 'INFO'
LOG_LEVEL_SETTING_NAME = 'log_level'
DEBUG_MODE_SETTING_NAME = 'DEBUG_MODE'
LOG_LEVELS = {
    'DEBUG': 0, 'INFO': 1, 'WARNING': 2, 'ERROR': 3, 'CRITICAL': 4
}

# --- Core Logging Functions ---

def _get_min_log_level():
    """Retrieves the minimum log level setting from app_settings."""
    try:
        min_level_setting = app_tables.app_settings.get(setting_name=LOG_LEVEL_SETTING_NAME)
        level = min_level_setting['value_text'] if min_level_setting and min_level_setting['value_text'] else DEFAULT_LOG_LEVEL
        if level not in LOG_LEVELS:
            print(f"WARNING: Invalid log level '{level}' found in settings. Defaulting to {DEFAULT_LOG_LEVEL}.")
            return DEFAULT_LOG_LEVEL
        return level
    except Exception as e:
        print(f"ERROR: Failed to retrieve log level setting: {e}. Defaulting to {DEFAULT_LOG_LEVEL}.")
        return DEFAULT_LOG_LEVEL

def _should_log(level):
    """Determines if a message at a given level should be logged based on settings."""
    min_level = _get_min_log_level()
    if level not in LOG_LEVELS:
        print(f"ERROR: Invalid log level specified: {level}")
        return False # Don't log invalid levels
    return LOG_LEVELS[level] >= LOG_LEVELS[min_level]

def _get_debug_mode():
    """Checks if debug mode (console logging) is enabled in settings."""
    try:
        debug_setting = app_tables.app_settings.get(setting_name=DEBUG_MODE_SETTING_NAME)
        # Ensure we check the boolean field correctly
        return debug_setting['value_bool'] if debug_setting and debug_setting['value_bool'] is not None else False
    except Exception as e:
        print(f"ERROR: Failed to retrieve debug mode setting: {e}. Defaulting to False.")
        return False

def _create_log_entry_string(level, module, process, message, context_str):
    """Creates a formatted log entry string."""
    timestamp = datetime.now().isoformat() # Use ISO format for better parsing
    return f"{timestamp} - {level} - {module} - {process} - {message} - Context: {context_str}"

def _write_to_log_table(level, module, process, message, context_str, concatenated_str):
    """Writes the prepared log entry to the database table."""
    try:
        app_tables.logs.add_row(
            timestamp=datetime.now(), # Use consistent timestamp
            level=level,
            module=module,
            process=process,
            message=message, # Store potentially long message with traceback here
            context=context_str, # Store JSON context string
            concatenated=concatenated_str # Store the formatted string
        )
    except Exception as e:
        # Log failure to console - critical if logging itself fails
        print("CRITICAL: Failed to write log entry to database!")
        print(f"Log Details: Level={level}, Module={module}, Process={process}")
        print(f"Error: {e}")
        # Avoid infinite loop if DB is down - don't try to log this failure to DB

@anvil.server.callable
def log(level, module, process, message, context=None):
    """
    Main server-side logging function.
    Orchestrates level checking, formatting, console output (if debug), and DB writing.
    Includes traceback information automatically in the message if an exception is active.
    """
    level = level.upper() # Ensure level is uppercase for consistency

    # Check if we should log this level before doing any work
    if not _should_log(level):
        return # Don't log if below minimum level

    # Capture traceback if an exception is being handled
    tb = traceback.format_exc()
    message_with_tb = f"{message}\nTraceback:\n{tb}" if tb != 'NoneType: None\n' else message

    # Safely serialize context to JSON string
    context_str = "None"
    if context is not None:
        try:
            context_str = json.dumps(context)
        except TypeError as e:
            context_str = f"Error serializing context: {e}"

    # Create the formatted string entry
    log_entry_str = _create_log_entry_string(level, module, process, message_with_tb, context_str)

    # Write to console if debug mode is enabled
    if _get_debug_mode():
        print(log_entry_str)

    # Write to the database table
    _write_to_log_table(level, module, process, message_with_tb, context_str, log_entry_str)


@anvil.server.callable
def client_log(level, module, process, message, context=None):
    """
    Callable endpoint for client-side code to trigger server-side logging.
    Simply forwards the arguments to the main log function.
    """
    # Basic validation on client input? Optional.
    if not all(isinstance(arg, str) for arg in [level, module, process, message]):
         print(f"WARNING: Invalid type received in client_log: {level}, {module}, {process}, {message}")
         # Decide whether to reject or attempt logging
         # For robustness, attempt logging but maybe log a warning about types
         log("WARNING", "sm_logs_mod", "client_log", "Potential type mismatch from client",
             {"level": level, "module": module, "process": process, "message": message, "context": context})
         return # Or proceed to log below

    log(level, module, process, message, context)


# --- Log Management Callables ---

@anvil.server.callable
def delete_all_logs():
    """
    Deletes all records from the logs table.
    Requires appropriate permissions (consider adding owner/admin check if needed).
    """
    # TODO: Add permission check if necessary
    # if not is_owner_user(): raise anvil.server.PermissionDenied("Owner required")
    log("WARNING", "sm_logs_mod", "delete_all_logs", "Attempting to delete all logs",
        {"user": anvil.users.get_user()['email'] if anvil.users.get_user() else "N/A"})
    try:
        num_deleted = len(app_tables.logs.search()) # Get count before deleting
        app_tables.logs.delete_all_rows()
        log("INFO", "sm_logs_mod", "delete_all_logs", f"Successfully deleted {num_deleted} log entries.",
            {"user": anvil.users.get_user()['email'] if anvil.users.get_user() else "N/A"})
        return True
    except Exception as e:
        log("ERROR", "sm_logs_mod", "delete_all_logs", "Failed to delete all logs", {"error": str(e)})
        raise Exception(f"Failed to delete logs: {e}")


@anvil.server.callable
def get_latest_log():
    """Retrieves the most recent log entry."""
    # TODO: Add permission check if necessary
    # if not is_admin_user(): raise anvil.server.PermissionDenied("Admin required")
    try:
        latest = app_tables.logs.search(tables.order_by("timestamp", ascending=False))
        if latest:
            return latest[0]
        else:
            return None
    except Exception as e:
        log("ERROR", "sm_logs_mod", "get_latest_log", "Failed to retrieve latest log", {"error": str(e)})
        raise Exception(f"Failed to get latest log: {e}")


# --- Settings Management Callables (Consider moving to dedicated module later) ---

@anvil.server.callable
def get_current_log_level():
    """Gets the currently configured minimum log level."""
    # TODO: Add permission check if necessary
    return _get_min_log_level()

@anvil.server.callable
def get_bool_setting_value(setting_name):
    """Gets the boolean value of a specific setting."""
    # TODO: Add permission check if necessary
    if not isinstance(setting_name, str):
        log("ERROR", "sm_logs_mod", "get_bool_setting_value", f"Invalid setting_name type: {type(setting_name)}")
        return None # Or raise error

    try:
        setting = app_tables.app_settings.get(setting_name=setting_name)
        # Ensure we check the boolean field correctly and handle missing setting
        return setting['value_bool'] if setting and setting['value_bool'] is not None else None
    except Exception as e:
        log("ERROR", "sm_logs_mod", "get_bool_setting_value", f"Failed to retrieve setting '{setting_name}'", {"error": str(e)})
        return None # Return None on error

@anvil.server.callable
def update_setting_value(setting_name, value):
    """
    Updates the value of an existing setting in the app_settings table.
    Determines the correct column (value_text, value_number, value_bool) based on value type.
    Requires appropriate permissions (consider adding owner/admin check).
    """
    # TODO: Add permission check if necessary
    # if not is_owner_user(): raise anvil.server.PermissionDenied("Owner required")

    log("DEBUG", "sm_logs_mod", "update_setting_value", f"Attempting to update setting '{setting_name}'",
        {"user": anvil.users.get_user()['email'] if anvil.users.get_user() else "N/A"})

    if not isinstance(setting_name, str):
        log("ERROR", "sm_logs_mod", "update_setting_value", f"Invalid setting_name type: {type(setting_name)}")
        raise TypeError("setting_name must be a string.")

    try:
        setting = app_tables.app_settings.get(setting_name=setting_name)
        if not setting:
            log("ERROR", "sm_logs_mod", "update_setting_value", f"Setting '{setting_name}' not found.")
            raise Exception(f"Setting '{setting_name}' not found.")

        update_dict = {}
        log_value_type = ""
        # Determine type and prepare update dictionary
        if isinstance(value, bool):
            update_dict = {'value_bool': value, 'value_text': None, 'value_number': None}
            log_value_type = "boolean"
        elif isinstance(value, (int, float)):
            update_dict = {'value_number': value, 'value_text': None, 'value_bool': None}
            log_value_type = "numeric"
        elif isinstance(value, str):
            update_dict = {'value_text': value, 'value_number': None, 'value_bool': None}
            log_value_type = "text"
        else:
            log("ERROR", "sm_logs_mod", "update_setting_value", f"Unsupported value type '{type(value)}' for setting '{setting_name}'")
            raise TypeError(f"Unsupported value type for setting: {type(value)}")

        setting.update(**update_dict)
        log("INFO", "sm_logs_mod", "update_setting_value", f"Successfully updated setting '{setting_name}' to {log_value_type} value.",
            {"user": anvil.users.get_user()['email'] if anvil.users.get_user() else "N/A", "new_value": value})
        return True

    except Exception as e:
        log("ERROR", "sm_logs_mod", "update_setting_value", f"Failed to update setting '{setting_name}'", {"error": str(e)})
        # Re-raise specific errors if needed
        if isinstance(e, (TypeError, Exception)): # Catch specific expected errors or generic ones
             raise e
        raise Exception(f"Failed to update setting '{setting_name}': {e}")


# --- Test Function ---
@anvil.server.callable
def test_server_logging():
    """Callable function to test the logging mechanism."""
    log("INFO", "sm_logs_mod", "test_server_logging",
        "Server logging test executed successfully",
        {"test_timestamp": datetime.now().isoformat()})
    try:
        # Test logging an error with traceback
        raise ValueError("This is a test error for traceback logging.")
    except ValueError as e:
        log("ERROR", "sm_logs_mod", "test_server_logging", f"Caught test error: {e}", {"context_info": "Testing traceback"})

    log("DEBUG", "sm_logs_mod", "test_server_logging", "Debug test message.")
    log("CRITICAL", "sm_logs_mod", "test_server_logging", "Critical test message.")
    return True

@anvil.server.callable
def get_all_logs_concatenated():
    # ... (import and permission check as before) ...
    user = anvil.users.get_user()
    user_id_for_log = user.get_id() if user else None # Get ID safely
    user_email_for_log = user['email'] if user else "N/A" # Get email safely

    try:
        log_rows = app_tables.logs.search(tables.order_by("timestamp", ascending=True))
        concatenated_logs = [{"log_line": row['concatenated']} for row in log_rows]

        # --- Simplified Context ---
        log("INFO", "sm_logs_mod", "get_all_logs_concatenated",
            f"Retrieved {len(concatenated_logs)} log entries for user {user_email_for_log}",
            {"user_id": user_id_for_log}) # Pass only serializable data
        # --- End Simplified Context ---

        return concatenated_logs
    except Exception as e:
        # --- Simplified Context ---
        log("ERROR", "sm_logs_mod", "get_all_logs_concatenated",
            f"Failed to retrieve logs for user {user_email_for_log}",
            {"user_id": user_id_for_log, "error": str(e)}) # Ensure error is string
        # --- End Simplified Context ---
        raise Exception(f"Failed to retrieve logs: {e}")

@anvil.server.callable
def set_log_level(new_level):
    """
    Sets or creates the application's minimum log level in app_settings.
    Validates the input level.
    """
    # TODO: Add permission check if needed (e.g., require Owner)
    # from sessions_server import is_owner_user # Import inside if needed
    # if not is_owner_user(): raise anvil.server.PermissionDenied("Owner required to change log level.")

    requesting_user_email = anvil.users.get_user()['email'] if anvil.users.get_user() else "N/A"
    log("INFO", "sm_logs_mod", "set_log_level", f"Attempting to set log level to {new_level}",
        {"user": requesting_user_email})

    # Validate the input level against known levels
    valid_levels = list(LOG_LEVELS.keys()) # Use keys from the LOG_LEVELS dict
    if new_level not in valid_levels:
        log("ERROR", "sm_logs_mod", "set_log_level", f"Invalid log level specified: {new_level}", {"user": requesting_user_email})
        raise ValueError(f"Invalid log level. Must be one of: {', '.join(valid_levels)}")

    try:
        # --- Check if the setting already exists ---
        setting_row = app_tables.app_settings.get(setting_name=LOG_LEVEL_SETTING_NAME)

        if setting_row:
            # --- Setting exists: Update it ---
            log("DEBUG", "sm_logs_mod", "set_log_level", f"Found existing setting '{LOG_LEVEL_SETTING_NAME}', updating value.", {"user": requesting_user_email})
            setting_row.update(
                value_text=new_level,
                value_number=None, # Clear other potential value types
                value_bool=None
            )
            log("INFO", "sm_logs_mod", "set_log_level", f"Log level successfully updated to {new_level}", {"user": requesting_user_email})
        else:
            # --- Setting does not exist: Create it ---
            log("DEBUG", "sm_logs_mod", "set_log_level", f"Setting '{LOG_LEVEL_SETTING_NAME}' not found, creating new row.", {"user": requesting_user_email})
            app_tables.app_settings.add_row(
                setting_name=LOG_LEVEL_SETTING_NAME,
                value_text=new_level
                # Other value columns will default to None/null
            )
            log("INFO", "sm_logs_mod", "set_log_level", f"Log level successfully created and set to {new_level}", {"user": requesting_user_email})

        return True # Indicate success in either case

    except Exception as e:
        # Catch errors during get, update, or add
        log("ERROR", "sm_logs_mod", "set_log_level", f"Failed to set/create log level '{new_level}'", {"error": str(e), "user": requesting_user_email})
        # Re-raise the exception so the client knows about the failure
        raise Exception(f"Failed to set log level: {e}")