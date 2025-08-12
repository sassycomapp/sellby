from ._anvil_designer import clear_logsTemplate
from anvil import *
import anvil.server

# Import the client-side logging function
from ..cm_logs_helper import log  # Adjust path if needed

class clear_logs(clear_logsTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Log form initialization
        log("INFO", "clear_logs", "__init__", "Form opened")

        # Any code you write here will run when the form opens.
        self.lbl_clear_logs.text = "" # Clear label on init
        self.lbl_clear_logs.foreground = "" # Reset color
        self.lbl_print_concatenated.text = "" # Clear print status label
        self.rp_print_concatenated.items = [] # Clear repeating panel

    def btn_clear_logs_click(self, **event_args):
        """This method is called when btn_clear_logs is clicked"""
        log("INFO", "clear_logs", "btn_clear_logs_click", "Clear logs button clicked")

        # Add a confirmation dialog for safety
        if confirm("Are you sure you want to delete ALL log entries?\nThis action cannot be undone."):
            log("INFO", "clear_logs", "btn_clear_logs_click", "User confirmed log deletion")
            self.lbl_clear_logs.text = "Clearing logs..."
            self.lbl_clear_logs.foreground = ""
            self.lbl_print_concatenated.text = "" # Clear other status
            self.rp_print_concatenated.items = [] # Clear display
            try:
                # Call the existing server function
                log("DEBUG", "clear_logs", "btn_clear_logs_click", "Calling server function 'delete_all_logs'")
                success = anvil.server.call('delete_all_logs')

                if success:
                    self.lbl_clear_logs.text = "All logs cleared successfully."
                    self.lbl_clear_logs.foreground = "green"
                    log("INFO", "clear_logs", "btn_clear_logs_click", "Server reported logs cleared successfully")
                else:
                    self.lbl_clear_logs.text = "Log clearing operation completed but did not explicitly report success."
                    self.lbl_clear_logs.foreground = "orange"
                    log("WARNING", "clear_logs", "btn_clear_logs_click", "Server call 'delete_all_logs' returned non-True", {"return_value": success})

            except Exception as e:
                self.lbl_clear_logs.text = f"Error clearing logs: {e}"
                self.lbl_clear_logs.foreground = "red"
                log("ERROR", "clear_logs", "btn_clear_logs_click", "Exception during server call 'delete_all_logs'", {"error": str(e)})
        else:
            self.lbl_clear_logs.text = "Log clearing cancelled."
            self.lbl_clear_logs.foreground = ""
            log("INFO", "clear_logs", "btn_clear_logs_click", "User cancelled log deletion confirmation")


    def btn_home_click(self, **event_args):
        """This method is called when btn_home is clicked"""
        log("INFO", "clear_logs", "btn_home_click", "Home button clicked, navigating to paddle_home")
        open_form('paddle_home')

    def btn_print_concatenated_click(self, **event_args):
        """This method is called when btn_print_concatenated is clicked"""
        log("INFO", "clear_logs", "btn_print_concatenated_click", "Print logs button clicked")
        self.lbl_print_concatenated.text = "Loading logs..."
        self.lbl_print_concatenated.foreground = ""
        self.lbl_clear_logs.text = "" # Clear other status
        self.rp_print_concatenated.items = [] # Clear previous items

        try:
            log("DEBUG", "clear_logs", "btn_print_concatenated_click", "Calling server function 'get_all_logs_concatenated'")
            # Call the new server function
            log_data = anvil.server.call('get_all_logs_concatenated')

            # Set the items property of the repeating panel
            self.rp_print_concatenated.items = log_data

            count = len(log_data)
            self.lbl_print_concatenated.text = f"Loaded {count} log entries."
            self.lbl_print_concatenated.foreground = "green" if count > 0 else ""
            log("INFO", "clear_logs", "btn_print_concatenated_click", f"Successfully loaded {count} log entries into repeating panel")

        except anvil.server.PermissionDenied as e:
             self.lbl_print_concatenated.text = f"Permission Denied: {e}"
             self.lbl_print_concatenated.foreground = "red"
             log("WARNING", "clear_logs", "btn_print_concatenated_click", "Permission denied when calling 'get_all_logs_concatenated'", {"error": str(e)})
        except Exception as e:
            # Catch other errors (network, server function errors)
            self.lbl_print_concatenated.text = f"Error loading logs: {e}"
            self.lbl_print_concatenated.foreground = "red"
            log("ERROR", "clear_logs", "btn_print_concatenated_click", "Exception during server call 'get_all_logs_concatenated'", {"error": str(e)})