# Client Module: cm_logs_helper.py

# This module provides a simple client-side interface for logging.
# It forwards log messages to a server function for centralized processing and storage.

import anvil.server
import anvil.users # Not strictly needed here, but often useful in client modules
import json # For attempting to serialize context if needed client-side (optional)

# Define the server function name once
_SERVER_LOG_FUNCTION = 'client_log'

def log(level, module, process, message, context=None):
    """
    Client-side logging function.

    Forwards log details to the server-side 'client_log' function.

    Args:
        level (str): The severity level (e.g., "DEBUG", "INFO", "WARNING", "ERROR").
        module (str): The name of the client-side module/form logging the event.
        process (str): The specific function or process within the module.
        message (str): The log message.
        context (dict, optional): Additional context data (will be JSON serialized). Defaults to None.
    """
    try:
        # Optional: Basic type checking on client before sending?
        if not all(isinstance(arg, str) for arg in [level, module, process, message]):
             print(f"WARNING (cm_logs_helper): Potential non-string type passed to log(): {level}, {module}, {process}, {message}")
             # Convert to string to ensure server call doesn't fail immediately on type
             level = str(level)
             module = str(module)
             process = str(process)
             message = str(message)

        # Optional: Serialize context client-side? Usually better handled server-side.
        # context_to_send = None
        # if context is not None:
        #     try:
        #         context_to_send = json.dumps(context)
        #     except TypeError:
        #         context_to_send = f"Error serializing context client-side: {type(context)}"

        # Call the server function asynchronously (fire-and-forget)
        # This prevents logging calls from blocking the UI thread.
        anvil.server.call_s(_SERVER_LOG_FUNCTION, level, module, process, message, context)

    except Exception as e:
        # If logging itself fails, print an error to the browser console.
        # Avoid calling log() here to prevent potential infinite loops.
        print("CRITICAL (cm_logs_helper): Failed to send log to server!")
        print(f"Log Details: Level={level}, Module={module}, Process={process}, Message={message}")
        print(f"Error: {e}")

# Example Usage (within another client module/form):
# from ..cm_logs_helper import log # Adjust import path as needed
#
# log("INFO", "MyForm", "button_click", "User clicked the submit button", {"user_input": self.textbox.text})
# try:
#    anvil.server.call('do_something')
# except Exception as e:
#    log("ERROR", "MyForm", "button_click", f"Server call failed: {e}", {"details": "..."})