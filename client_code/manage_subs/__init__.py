from ._anvil_designer import manage_subsTemplate
from anvil import *
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import datetime as datetime
from .manage_price_form import manage_price_form

class manage_subs(manage_subsTemplate):
  def __init__(self, **properties):
    # --- Initialize State Variables ---
    self.current_group_row = None # Will store the loaded 'subscription_group' Anvil Row
    self.is_edit_group_mode = False # True if editing an existing group
    # self.uploaded_group_image_file = None # If using a FileLoader, store the file object here before save

    self.init_components(**properties) # Initialize components from Anvil designer FIRST
    print("CLIENT manage_subs: __init__ called") # Using print for client-side logs

    # --- Configure Price Matrix RepeatingPanel ---
    if hasattr(self, 'rp_subs_matrix'):
      from ..template_rp_subs_matrix import template_rp_subs_matrix # Ensure correct import path
      self.rp_subs_matrix.item_template = template_rp_subs_matrix
      # Event handler for when 'Edit Price' is clicked within a matrix cell
      self.rp_subs_matrix.set_event_handler('x_edit_plan_price', self.edit_plan_price_handler)
      print("CLIENT manage_subs: rp_subs_matrix configured.")
    else:
      print("CLIENT manage_subs: WARNING - rp_subs_matrix RepeatingPanel not found on form design.")

      # --- Populate Dropdowns ---
      self.populate_group_tax_category_use_case_dropdown() # New method
    self.initialize_group_lookup_dropdown() # Refactored method

    # --- Set Event Handlers ---
    # Group Management Section
    if hasattr(self, 'sw_group_action'):
      self.sw_group_action.set_event_handler('change', self.sw_group_action_change)
      if hasattr(self, 'dd_group'):
        self.dd_group.set_event_handler('change', self.dd_group_change)
        self.btn_group_save.set_event_handler('click', self.btn_group_save_click)
    if hasattr(self, 'btn_delete_group'):
      self.btn_delete_group.set_event_handler('click', self.btn_delete_group_click)

      # New Group Tax Category Dropdown
      if hasattr(self, 'dd_subs_group_use_case'):
        self.dd_subs_group_use_case.set_event_handler('change', self.dd_subs_group_use_case_change)

        # Group Image (Assuming FileLoader named fl_group_image)
        if hasattr(self, 'fl_group_image'):
          self.fl_group_image.set_event_handler('change', self.fl_group_image_change)

    # General Buttons
    self.btn_reset.set_event_handler('click', self.btn_reset_click)
    if hasattr(self, 'btn_update_page'):
      self.btn_update_page.set_event_handler('click', self.btn_update_page_click)
      self.btn_home.set_event_handler('click', self.btn_home_click)

    # --- Initial UI State ---
    self.reset_group_form_ui() # Call new/refactored reset function
    print("CLIENT manage_subs: __init__ completed.")


  # 1. _reset_form 
    # Method #1 (Refactored from _reset_form)
    def reset_group_form_ui(self):
      """Resets the group management part of the form and price matrix to initial state."""
      print("CLIENT manage_subs: reset_group_form_ui called") # Using print for client-side logs

      # Reset top-level form title and group action switch
      self.lbl_group_form_title.text = "Manage Subscription Groups & Plans" # Default title
      if hasattr(self, 'sw_group_action'):
        self.sw_group_action.checked = False # Default to "Update Group" mode visually

        # Clear current group state variables
        self.current_group_row = None
      self.is_edit_group_mode = False
      # if hasattr(self, 'uploaded_group_image_file'): # If you use this state variable
      #     self.uploaded_group_image_file = None

      # Clear Group Detail Fields
      self.tb_group_name.text = ""
      self.ta_group_description.text = "" # Assuming this is a TextArea
      self.lbl_group_number_display.text = "(New Group)"
      if hasattr(self, 'dd_group'):
        self.dd_group.selected_value = None # Clear selection in lookup
        self.dd_group.enabled = True # Ensure lookup is enabled in reset state

        # Clear Group Tax Category Use Case Dropdown
        if hasattr(self, 'dd_subs_group_use_case'):
          self.dd_subs_group_use_case.selected_value = None
      if hasattr(self, 'lbl_group_selected_paddle_tax_category'):
        self.lbl_group_selected_paddle_tax_category.visible = False
        self.lbl_group_selected_paddle_tax_category.text = "Paddle Tax Category: "

        # Clear Descriptive Level/Tier Name Fields
        self.tb_group_level1_name.text = ""
      self.tb_group_level2_name.text = ""
      self.tb_group_level3_name.text = ""
      self.tb_group_tier1_name.text = ""
      self.tb_group_tier2_name.text = ""
      self.tb_group_tier3_name.text = ""

      # Clear Group Image Fields
      if hasattr(self, 'fl_group_image'):
        self.fl_group_image.clear()
        if hasattr(self, 'img_group_preview'):
          self.img_group_preview.source = None
      if hasattr(self, 'tb_group_img_name'):
        self.tb_group_img_name.text = ""
        if hasattr(self, 'tb_group_image_url'): # This is usually read-only
          self.tb_group_image_url.text = ""

      # Clear Price Matrix Section Titles and RepeatingPanel
      if hasattr(self, 'lbl_matrix_group_name'):
        self.lbl_matrix_group_name.text = "Plans for: (No Group Selected)"
        if hasattr(self, 'lbl_matrix_group_num'):
          self.lbl_matrix_group_num.text = "G#: "

      # Reset matrix header labels (Level names) to defaults
      if hasattr(self, 'lbl_level1_header'):
        self.lbl_level1_header.text = "Level 1"
        if hasattr(self, 'lbl_level2_header'):
          self.lbl_level2_header.text = "Level 2"
      if hasattr(self, 'lbl_level3_header'):
        self.lbl_level3_header.text = "Level 3"

        if hasattr(self, 'rp_subs_matrix'):
          self.rp_subs_matrix.items = []

      # Disable delete button as no group is loaded
      if hasattr(self, 'btn_delete_group'):
        self.btn_delete_group.enabled = False

        print("CLIENT manage_subs: reset_group_form_ui completed.")

  # 2. (NEW) populate_group_tax_category_use_case_dropdown
  # Method #2 (NEW)
  def populate_group_tax_category_use_case_dropdown(self):
    """Populates the use case dropdown for the group's tax category."""
    # Using print for client-side logs, replace with your client log call if available
    print("CLIENT manage_subs: populate_group_tax_category_use_case_dropdown called")
    if hasattr(self, 'dd_subs_group_use_case'):
      try:
        # Server function 'get_tax_use_cases' returns list of (display_text, value) tuples
        use_cases = anvil.server.call('get_tax_use_cases', mybizz_sector_filter='subscription_group')
        # Add a placeholder item at the beginning of the list
        self.dd_subs_group_use_case.items = [("Select Use Case for Tax Category...", None)] + sorted(use_cases)
        print(f"CLIENT manage_subs: Loaded {len(use_cases)} tax use cases for subscription_group into dropdown.")
      except Exception as e:
        print(f"CLIENT manage_subs: Error loading subscription group use cases: {e}")
        # In case of error, provide a fallback item
        self.dd_subs_group_use_case.items = [("Error loading categories...", None)]
        # Optionally, alert the user
        # alert(f"Could not load subscription type categories: {e}", role="warning", title="Data Load Error")
    else:
      print("CLIENT manage_subs: WARNING - dd_subs_group_use_case DropDown not found on form design.")

  # 3. initialize_group_dropdown
    # Method #3 (Refactored from initialize_group_dropdown)
    def initialize_group_lookup_dropdown(self):
      """Populates the subscription group lookup dropdown."""
      # Using print for client-side logs
      print("CLIENT manage_subs: initialize_group_lookup_dropdown called")
      if hasattr(self, 'dd_group'):
        try:
          # Server function 'list_subscription_groups' returns list of {'group_name': ..., 'group_number': ...}
          group_list = anvil.server.call('list_subscription_groups')
          # Format for DropDown: list of (display_text, value_to_be_stored)
          self.dd_group.items = [("Select Group to Manage...", None)] + sorted([(g['group_name'], g['group_number']) for g in group_list])
          print(f"CLIENT manage_subs: Loaded {len(group_list)} groups into lookup dropdown.")
        except Exception as e:
          print(f"CLIENT manage_subs: Error loading subscription groups for lookup: {e}")
          self.dd_group.items = [("Error loading groups...", None)]
          # Optionally, alert the user
          # alert(f"Could not load subscription groups: {e}", role="warning", title="Data Load Error")
      else:
        print("CLIENT manage_subs: WARNING - dd_group DropDown not found on form design.")

  # 4. _load_initial_data
  # Method #4 (Refactored from _load_initial_data)
  def _load_initial_data(self):
    """
        Loads initial data required for the form, specifically populating dropdowns.
        This method is typically called from __init__.
        """
    print("CLIENT manage_subs: _load_initial_data called") # Using print for client-side logs

    # Populate the group lookup dropdown
    self.initialize_group_lookup_dropdown()

    # Populate the tax category use case dropdown for groups
    self.populate_group_tax_category_use_case_dropdown()

    # Any other initial data loading specific to this form can be added here.
    # For example, if you had global settings or other lists to fetch.

    # Note: The original _load_initial_data also called initialize_plan_selector_dropdown().
    # This is no longer needed as individual plan selection and direct editing
    # from a dropdown is removed in the new design. Plan interaction will be via the matrix.
    print("CLIENT manage_subs: _load_initial_data completed.")

  # 5. _clear_group_fields
    # Method #5 (Carried over, may need minor adjustments based on final UI)
    def _clear_group_fields(self):
      """Clears group-specific input fields on the form."""
      print("CLIENT manage_subs: _clear_group_fields called") # Using print for client-side logs

      self.tb_group_name.text = ""
      self.ta_group_description.text = "" # Assuming this is a TextArea
      self.lbl_group_number_display.text = "(New Group)" # Default text for new group

        # Clear new Tax Category Use Case Dropdown for the group
      if hasattr(self, 'dd_subs_group_use_case'):
            self.dd_subs_group_use_case.selected_value = None
      if hasattr(self, 'lbl_group_selected_paddle_tax_category'):
            self.lbl_group_selected_paddle_tax_category.visible = False
            self.lbl_group_selected_paddle_tax_category.text = "Paddle Tax Category: "
            
        # Clear Descriptive Level/Tier Name Fields for the group
      self.tb_group_level1_name.text = ""
      self.tb_group_level2_name.text = ""
      self.tb_group_level3_name.text = ""
      self.tb_group_tier1_name.text = ""
      self.tb_group_tier2_name.text = ""
      self.tb_group_tier3_name.text = ""

        # Clear Group Image Fields
      if hasattr(self, 'fl_group_image'):
            self.fl_group_image.clear()
      if hasattr(self, 'img_group_preview'):
            self.img_group_preview.source = None
      if hasattr(self, 'tb_group_img_name'):
            self.tb_group_img_name.text = ""
      if hasattr(self, 'tb_group_image_url'): # This is usually read-only
            self.tb_group_image_url.text = ""
            
        # self.uploaded_group_image_file = None # If you use this state variable

      print("CLIENT manage_subs: _clear_group_fields completed.")

#6 (Refactored from _populate_group_fields)
def _populate_group_fields(self, group_row):
  """
    Populates group-specific input fields on the form from a loaded group_row.
    Includes populating the tax category dropdown.
    Args:
        group_row (anvil.tables.Row): The subscription_group row object.
    """
  print(f"CLIENT manage_subs: _populate_group_fields called for G#: {group_row['group_number'] if group_row else 'None'}")

  if not group_row:
    print("CLIENT manage_subs: _populate_group_fields - group_row is None. Clearing fields.")
    self._clear_group_fields() # Fallback to clearing if no valid row
    return

    self.tb_group_name.text = group_row.get('group_name', "")
  self.ta_group_description.text = group_row.get('group_description', "") # Assuming TextArea
  self.lbl_group_number_display.text = group_row.get('group_number', "(Error: No G#)")

  # --- MODIFIED: Populate Tax Category Use Case Dropdown ---
  if hasattr(self, 'dd_subs_group_use_case'):
    # Get the tax_category stored on the subscription_group row
    group_tax_cat = group_row.get('tax_category')
    self.dd_subs_group_use_case.selected_value = group_tax_cat
    # Trigger change handler to update optional display label
    self.dd_subs_group_use_case_change()
    # Check if the value actually got set (i.e., was in the dropdown items)
    if self.dd_subs_group_use_case.selected_value != group_tax_cat and group_tax_cat is not None:
      print(f"CLIENT manage_subs: Warning - Loaded group tax category '{group_tax_cat}' not found in use case dropdown items.")
      # Optionally alert user or add the item dynamically if needed
    # --- END MODIFICATION ---

    # Populate Descriptive Level/Tier Name Fields
    self.tb_group_level1_name.text = group_row.get('group_level1_name', "")
  self.tb_group_level2_name.text = group_row.get('group_level2_name', "")
  self.tb_group_level3_name.text = group_row.get('group_level3_name', "")
  self.tb_group_tier1_name.text = group_row.get('group_tier1_name', "")
  self.tb_group_tier2_name.text = group_row.get('group_tier2_name', "")
  self.tb_group_tier3_name.text = group_row.get('group_tier3_name', "")

  # Populate Group Image Fields
  if hasattr(self, 'fl_group_image'):
    self.fl_group_image.clear() # Clear any pending file in loader

    media_row = group_row.get('media') # 'media' is a Link to 'files' table row
  if hasattr(self, 'img_group_preview'):
    self.img_group_preview.source = media_row['file'] if media_row and media_row.get('file') else None
    if hasattr(self, 'tb_group_img_name'):
      self.tb_group_img_name.text = media_row['name'] if media_row else ""
  if hasattr(self, 'tb_group_image_url'):
    img_url_val = ""
    if media_row and media_row.get('file') and hasattr(media_row['file'], 'url'):
      try:
        img_url_val = media_row['file'].url
      except Exception as e:
        print(f"CLIENT manage_subs: Could not get URL for media file: {e}")
    elif media_row and media_row.get('img_url'): # Fallback if img_url is stored directly
      img_url_val = media_row.get('img_url')
      self.tb_group_image_url.text = img_url_val

    print(f"CLIENT manage_subs: _populate_group_fields completed for G#: {group_row['group_number']}")

# 7. (NEW) load_group_details_and_matrix
    # Method #7 (NEW - Incorporates logic from old dd_group_change and parts of old _populate_group_fields)
    def load_group_details_and_matrix(self, group_number):
        """
        Loads details for a specific subscription group, populates the group form fields,
        and then triggers the population of the price matrix for that group.
        This is the primary method called when a group is selected or needs to be displayed.
        """
        print(f"CLIENT manage_subs: load_group_details_and_matrix called for G#: {group_number}")

        if not group_number:
            print("CLIENT manage_subs: No group_number provided to load_group_details_and_matrix. Resetting UI.")
            self.reset_group_form_ui() # Reset if no group number
            return

        try:
            # This server call should return the subscription_group row
            # Ensure 'get_subscription_group' returns all necessary fields, including 'media' link and 'tax_category'
            group_row_data = anvil.server.call('get_subscription_group', group_number)

            if group_row_data:
                self.current_group_row = group_row_data # Store the loaded Anvil Row object
                self.is_edit_group_mode = True # Now in edit mode for this loaded group
                if hasattr(self, 'sw_group_action'):
                    self.sw_group_action.checked = False # Set switch to "Update Group" mode

                # Populate the group detail fields using the helper
                self._populate_group_fields(self.current_group_row)

                # Populate Matrix Section Titles based on loaded group data
                if hasattr(self, 'lbl_matrix_group_name'):
                    self.lbl_matrix_group_name.text = f"Plans for: {self.current_group_row.get('group_name', 'N/A')}"
                if hasattr(self, 'lbl_matrix_group_num'):
                    self.lbl_matrix_group_num.text = f"G#: {self.current_group_row.get('group_number', 'N/A')}"
                
                # Set dynamic headers for the price matrix based on group's L/T names
                if hasattr(self, 'lbl_level1_header'):
                    self.lbl_level1_header.text = self.current_group_row.get('group_level1_name') or "Level 1"
                if hasattr(self, 'lbl_level2_header'):
                    self.lbl_level2_header.text = self.current_group_row.get('group_level2_name') or "Level 2"
                if hasattr(self, 'lbl_level3_header'):
                    self.lbl_level3_header.text = self.current_group_row.get('group_level3_name') or "Level 3"

                # Now, populate the price matrix (this will be implemented in Stage 2 of manage_subs refactor)
                self.populate_price_matrix() # Call to the (new/refactored) method

                if hasattr(self, 'btn_delete_group'):
                    self.btn_delete_group.enabled = True # Enable delete for a loaded group
                
                print(f"CLIENT manage_subs: Group details and matrix trigger for G#: {group_number} completed.")
            else:
                alert(f"Subscription Group with number '{group_number}' not found by server.")
                print(f"CLIENT manage_subs: Group G#: {group_number} not found by server.")
                self.reset_group_form_ui() # Reset if group not found
        except Exception as e:
            alert(f"Error loading subscription group details: {e}")
            print(f"CLIENT manage_subs: Exception in load_group_details_and_matrix for G#: {group_number} - {e}")
            # Consider using traceback.print_exc() here for more detail in browser console if needed
            # import traceback
            # traceback.print_exc()
            self.reset_group_form_ui() # Reset on any error

# 8. dd_group_change 
    # Method #8 (Refactored from dd_group_change)
    def dd_group_change(self, **event_args):
        """
        Handles selection changes in the 'dd_group' (group lookup) DropDown.
        Loads the selected group's details and associated plan/price matrix.
        """
        selected_group_number = None
        if hasattr(self, 'dd_group'): # Ensure component exists
            selected_group_number = self.dd_group.selected_value
        
        print(f"CLIENT manage_subs: dd_group_change - selected group_number: {selected_group_number}")

        if selected_group_number:
            # A group is selected from the dropdown, load its details
            self.load_group_details_and_matrix(selected_group_number)
            if hasattr(self, 'sw_group_action'):
                self.sw_group_action.checked = False # Switch to "Update Group" mode
        else:
            # "Select Group to Manage..." or equivalent placeholder was chosen
            # This typically means the user wants to clear the selection or start creating a new group
            # If sw_group_action is not in "New Group" mode, reset.
            # If it IS in "New Group" mode, reset_group_form_ui was likely already called by sw_group_action_change.
            if hasattr(self, 'sw_group_action') and not self.sw_group_action.checked:
                self.reset_group_form_ui()
            # If sw_group_action is already true (New mode), reset_group_form_ui would have been called by its change handler.
            # No further action needed here if already in "New Group" mode.
            print("CLIENT manage_subs: dd_group_change - No group selected or 'Select Group...' chosen.")

# 9. _update_group_ui_mode
    # Method #9 (Carried Over - _update_group_ui_mode)
    def _update_group_ui_mode(self):
        """
        Sets UI elements' enabled/disabled state based on whether the form
        is in 'Create New Group' mode or 'Update Existing Group' mode,
        primarily driven by self.sw_group_action.checked.
        """
        # Using print for client-side logs
        print("CLIENT manage_subs: _update_group_ui_mode called")

        is_create_mode = False # Default to update mode if switch doesn't exist
        if hasattr(self, 'sw_group_action'):
            is_create_mode = self.sw_group_action.checked
        
        print(f"CLIENT manage_subs: UI mode determined as Create = {is_create_mode}")

        # Enable/disable the group selection dropdown
        if hasattr(self, 'dd_group'):
            self.dd_group.enabled = not is_create_mode

        # Group name and description textboxes are generally always enabled for input
        # Their content is cleared or populated based on the mode.
        self.tb_group_name.enabled = True
        self.ta_group_description.enabled = True # Assuming TextArea

        # Enable/disable other group-specific fields based on mode
        # For example, descriptive level/tier names, tax category dropdown, image uploader
        # These are typically part of the group definition, so enabled in both modes.
        if hasattr(self, 'dd_subs_group_use_case'):
            self.dd_subs_group_use_case.enabled = True
        
        self.tb_group_level1_name.enabled = True
        self.tb_group_level2_name.enabled = True
        self.tb_group_level3_name.enabled = True
        self.tb_group_tier1_name.enabled = True
        self.tb_group_tier2_name.enabled = True
        self.tb_group_tier3_name.enabled = True

        if hasattr(self, 'fl_group_image'):
            self.fl_group_image.enabled = True
        
        # The "Delete Group" button should only be enabled if a group is loaded (i.e., not create mode AND a group is selected)
        if hasattr(self, 'btn_delete_group'):
            self.btn_delete_group.enabled = not is_create_mode and bool(self.current_group_row)

        # The "Save Group" button is always enabled as it serves both create and update
        self.btn_group_save.enabled = True

        # The price matrix and "Add Price" button for individual plans are typically
        # only relevant when a group is loaded (i.e., in update mode and a group is selected).
        # However, their direct enabled state might be better controlled by load_group_details_and_matrix.
        # For now, this function focuses on the group definition part of the UI.

        print("CLIENT manage_subs: _update_group_ui_mode completed.")

# 10. sw_group_action_change
    # Method #10 (Refactored from sw_group_action_change)
    def sw_group_action_change(self, **event_args):
        """
        Handles the change event of the 'sw_group_action' (New/Update Group) Switch.
        Updates the UI mode and resets or loads group data accordingly.
        """
        is_new_group_mode = False # Default
        if hasattr(self, 'sw_group_action'): # Ensure component exists
            is_new_group_mode = self.sw_group_action.checked
        
        print(f"CLIENT manage_subs: sw_group_action_change - New Group Mode: {is_new_group_mode}")

        if is_new_group_mode:
            # Switched to "New Group" mode
            self.reset_group_form_ui() # Clear all fields for new group entry
            self.lbl_group_form_title.text = "Create New Subscription Group"
            if hasattr(self, 'dd_group'):
                self.dd_group.enabled = False # Disable group lookup dropdown
            self.is_edit_group_mode = False # Explicitly set state
            self.current_group_row = None # No current group when creating new
            # Price matrix should be clear, which reset_group_form_ui handles
        else:
            # Switched to "Update Group" mode
            self.lbl_group_form_title.text = "Manage Subscription Groups & Plans"
            if hasattr(self, 'dd_group'):
                self.dd_group.enabled = True # Enable group lookup dropdown
                # If a group was previously selected in the dropdown, reload it.
                # Otherwise, the form remains in a state ready to select a group.
                if self.dd_group.selected_value:
                    self.load_group_details_and_matrix(self.dd_group.selected_value)
                else:
                    # No group selected yet in "Update" mode, so reset to a clean "select group" state
                    self.reset_group_form_ui() 
                    # Ensure switch is correctly set back if reset_group_form_ui changed it
                    if hasattr(self, 'sw_group_action'): 
                      self.sw_group_action.checked = False
            # self.is_edit_group_mode will be set by load_group_details_and_matrix
            # or remains False if no group is loaded yet.

        # Call the UI mode updater to ensure all component enabled/disabled states are correct
        self._update_group_ui_mode()
        print("CLIENT manage_subs: sw_group_action_change processing complete.")

# 11. (NEW) dd_subs_group_use_case_change
    # Method #11 (NEW)
    def dd_subs_group_use_case_change(self, **event_args):
        """
        Handles the change event of the 'dd_subs_group_use_case' DropDown.
        Updates an optional label to display the selected raw Paddle tax category.
        """
        # Using print for client-side logs
        print("CLIENT manage_subs: dd_subs_group_use_case_change called")

        if hasattr(self, 'lbl_group_selected_paddle_tax_category'): # Check if the display label exists
            selected_paddle_category_value = None
            if hasattr(self, 'dd_subs_group_use_case'): # Check if the dropdown exists
                selected_paddle_category_value = self.dd_subs_group_use_case.selected_value
            
            if selected_paddle_category_value:
                self.lbl_group_selected_paddle_tax_category.text = f"Paddle Tax Category: {selected_paddle_category_value}"
                self.lbl_group_selected_paddle_tax_category.visible = True
                print(f"CLIENT manage_subs: Selected Paddle Tax Category for group display: {selected_paddle_category_value}")
            else:
                self.lbl_group_selected_paddle_tax_category.text = "Paddle Tax Category: "
                self.lbl_group_selected_paddle_tax_category.visible = False
                print("CLIENT manage_subs: No Paddle Tax Category selected for group display.")
        else:
            print("CLIENT manage_subs: WARNING - lbl_group_selected_paddle_tax_category Label not found on form design.")

# 12. fl_group_image_change
    # Method #12 (Refactored from fl_group_image_change)
    def fl_group_image_change(self, file, **event_args):
        """
        Handles the 'change' event of the 'fl_group_image' FileLoader.
        Updates the image preview and stores the file object if one is selected.
        If the file is cleared by the user, it attempts to revert to the saved image if editing.
        """
        # Using print for client-side logs
        print(f"CLIENT manage_subs: fl_group_image_change - file: {file.name if file else 'None'}")

        # Ensure the image preview and name textbox components exist
        has_img_preview = hasattr(self, 'img_group_preview')
        has_img_name_tb = hasattr(self, 'tb_group_img_name')

        if file:
            # A new file has been selected by the user
            if has_img_preview:
                self.img_group_preview.source = file
            if has_img_name_tb:
                self.tb_group_img_name.text = file.name if hasattr(file, "name") else "Unknown File"
            
            # Store the file object. It will be passed to the server during save.
            # self.uploaded_group_image_file = file # If you use a state variable for this
            print(f"CLIENT manage_subs: New group image '{file.name if file else ''}' selected for preview.")
        else:
            # The FileLoader was cleared (e.g., user clicked 'x' or selected no file)
            # self.uploaded_group_image_file = None # Clear any stored file object

            # If in edit mode and a group with an existing image is loaded,
            # revert the preview to the currently saved image.
            if self.is_edit_group_mode and self.current_group_row and self.current_group_row.get('media'):
                media_row = self.current_group_row['media'] # 'media' is a Link to 'files' table
                if has_img_preview:
                    self.img_group_preview.source = media_row['file'] if media_row and media_row.get('file') else None
                if has_img_name_tb:
                    self.tb_group_img_name.text = media_row['name'] if media_row else ""
                print("CLIENT manage_subs: Group image FileLoader cleared, reverted to saved image preview (if any).")
            else:
                # Not in edit mode, or no saved image, so clear preview.
                if has_img_preview:
                    self.img_group_preview.source = None
                if has_img_name_tb:
                    self.tb_group_img_name.text = ""
                print("CLIENT manage_subs: Group image FileLoader cleared, preview is empty.")

# 13. btn_group_save_click
# Method #13 (Refactored from btn_group_save_click)
def btn_group_save_click(self, **event_args):
  """
    Saves the Subscription Group details to the MyBizz database and triggers
    syncing the corresponding Product to the Tenant's Paddle account.
    Includes sending the selected tax category.
    """
  print("CLIENT manage_subs: btn_group_save_click called")

  # --- Client-Side Validation ---
  group_name = self.tb_group_name.text.strip()
  if not group_name:
    alert("Subscription Group Name is required.")
    return

    # --- MODIFIED: Get selected tax category ---
    group_tax_category = None
  if hasattr(self, 'dd_subs_group_use_case'):
    group_tax_category = self.dd_subs_group_use_case.selected_value
    if not group_tax_category:
      alert("Please select a 'Use Case' for this subscription offering (this sets the tax category for the Paddle Product).")
      return
  else:
    alert("Error: Group Tax Category selection component (dd_subs_group_use_case) is missing from the form design.")
    return
    # --- END MODIFICATION ---

    # --- Prepare Group Data for Server ---
    group_data = {
      'group_name': group_name,
      'group_description': self.ta_group_description.text.strip(), # Assuming TextArea
      # --- MODIFIED: Include tax_category in data sent to server ---
      'tax_category': group_tax_category,
      # --- END MODIFICATION ---
      'group_level1_name': self.tb_group_level1_name.text.strip(),
      'group_level2_name': self.tb_group_level2_name.text.strip(),
      'group_level3_name': self.tb_group_level3_name.text.strip(),
      'group_tier1_name': self.tb_group_tier1_name.text.strip(),
      'group_tier2_name': self.tb_group_tier2_name.text.strip(),
      'group_tier3_name': self.tb_group_tier3_name.text.strip(),
      'file_upload': None, # Initialize, will be set if file is present
      'file_upload_name': None
    }

  # Add image file to group_data if a FileLoader is used and has a file
  if hasattr(self, 'fl_group_image') and self.fl_group_image.file:
    group_data['file_upload'] = self.fl_group_image.file
    img_name_to_use = self.tb_group_img_name.text.strip() if hasattr(self, 'tb_group_img_name') and self.tb_group_img_name.text.strip() else None
    group_data['file_upload_name'] = img_name_to_use or self.fl_group_image.file.name
  elif self.is_edit_group_mode and self.current_group_row and self.current_group_row.get('media'):
    group_data['existing_media_link'] = self.current_group_row.get('media')

    # --- Call Server ---
    try:
      print(f"CLIENT manage_subs: Calling server to save group. Edit mode: {self.is_edit_group_mode}")
      if self.is_edit_group_mode and self.current_group_row:
        group_number_to_update = self.current_group_row['group_number']
        # Server function 'update_subscription_group' now expects 'tax_category' in group_data
        updated_group = anvil.server.call('update_subscription_group', group_number_to_update, group_data)
        self.current_group_row = updated_group
        Notification("Subscription Group updated successfully.", style="success", timeout=3).show()
        print(f"CLIENT manage_subs: Group {group_number_to_update} updated.")
      else: # Creating a new group
        # Server function 'create_subscription_group' now expects 'tax_category' in group_data
        new_group = anvil.server.call('create_subscription_group', group_data)
        self.current_group_row = new_group
        self.is_edit_group_mode = True
        if hasattr(self, 'sw_group_action'):
          self.sw_group_action.checked = False
          self.lbl_group_number_display.text = new_group['group_number']
        if hasattr(self, 'btn_delete_group'):
          self.btn_delete_group.enabled = True

          self.initialize_group_lookup_dropdown()
        if hasattr(self, 'dd_group'):
          self.dd_group.selected_value = new_group['group_number']

          Notification("Subscription Group created. You can now define prices for its plans.", style="success", timeout=3).show()
        print(f"CLIENT manage_subs: Group {new_group['group_number']} created.")

        # After save (create or update), reload details and matrix
        if self.current_group_row:
          self.load_group_details_and_matrix(self.current_group_row['group_number'])

      if hasattr(self, 'fl_group_image'):
        self.fl_group_image.clear()

    except anvil.server.ValidationError as e:
      alert(f"Validation Error: {e.err_obj if hasattr(e, 'err_obj') and e.err_obj else str(e)}", title="Save Failed")
      print(f"CLIENT manage_subs: Validation error saving group: {e}")
    except anvil.http.HttpError as e_http:
      alert(f"Paddle API Error: {e_http.status} - {e_http.content}. The group was saved in MyBizz, but syncing to Paddle failed. Please try saving again or check Paddle dashboard.", title="Paddle Sync Error")
      print(f"CLIENT manage_subs: Paddle API HttpError saving group: {e_http}")
    except Exception as e:
      alert(f"An error occurred while saving the subscription group: {e}", title="Save Error")
      print(f"CLIENT manage_subs: General error saving group: {e}")
      # import traceback
      # traceback.print_exc()

# 14. btn_delete_group_click
    # Method #14 (Refactored from btn_delete_group_click)
    def btn_delete_group_click(self, **event_args):
        """
        Handles the click event of the 'btn_delete_group' button.
        Confirms with the user and calls the server to delete the current subscription group.
        """
        print("CLIENT manage_subs: btn_delete_group_click called") # Using print for client-side logs

        if self.current_group_row and self.current_group_row.get('group_number'):
            group_name_for_confirm = self.current_group_row.get('group_name', 'this group')
            group_number_for_confirm = self.current_group_row['group_number']
            
            confirmation_message = (
                f"Are you sure you want to delete the subscription group '{group_name_for_confirm}' (G#: {group_number_for_confirm})?\n\n"
                "This action will also attempt to:\n"
                "  - Delete all its 9 defined plan variations (from MyBizz).\n"
                "  - Delete any associated prices for these plans (from MyBizz).\n"
                "  - Archive the corresponding Product in Paddle (if synced).\n\n"
                "This action CANNOT be undone if there are no active customer subscriptions linked to its plans. "
                "If active subscriptions exist, deletion will be prevented."
            )

            if confirm(confirmation_message, title="Confirm Group Deletion", buttons=["Cancel", "DELETE GROUP"]):
                print(f"CLIENT manage_subs: User confirmed deletion for group G#: {group_number_for_confirm}")
                try:
                    # Server function 'delete_subscription_group' handles dependency checks
                    # (items, prices, active subscriptions) and Paddle archival attempt.
                    success = anvil.server.call('delete_subscription_group', group_number_for_confirm)
                    
                    if success: # Assuming server returns True on successful deletion
                        Notification("Subscription Group and its associated plans/prices deleted from MyBizz.", style="success", timeout=4).show()
                        print(f"CLIENT manage_subs: Group G#: {group_number_for_confirm} reported as deleted by server.")
                        self.reset_group_form_ui() # Reset the form to a clean state
                        self.initialize_group_lookup_dropdown() # Refresh the group list
                    else:
                        # This case might occur if server-side checks prevent deletion but don't raise an exception
                        # (though raising an exception is usually better for clear error feedback).
                        alert("Group deletion was not fully completed by the server. Please check server logs.", title="Deletion Issue")
                        print(f"CLIENT manage_subs: Server call to delete group G#: {group_number_for_confirm} returned non-True.")
                        # Optionally, refresh the view to see the current state
                        self.load_group_details_and_matrix(group_number_for_confirm)


                except anvil.server.PermissionDenied as e:
                    alert(f"Permission Denied: {e}", title="Deletion Failed")
                    print(f"CLIENT manage_subs: Permission denied deleting group G#: {group_number_for_confirm} - {e}")
                except Exception as e:
                    alert(f"Error deleting subscription group: {e}", title="Deletion Failed")
                    print(f"CLIENT manage_subs: Error deleting group G#: {group_number_for_confirm} - {e}")
                    # Consider logging client-side traceback for dev if needed
                    # import traceback
                    # traceback.print_exc()
            else:
                print(f"CLIENT manage_subs: User cancelled deletion for group G#: {group_number_for_confirm}")
        else:
            alert("No subscription group is currently loaded to delete.")
            print("CLIENT manage_subs: btn_delete_group_click - No current_group_row or group_number to delete.")

# 15. btn_reset_click 
    # Method #15 (Refactored from btn_reset_click)
    def btn_reset_click(self, **event_args):
        """
        Handles the click event of the main 'btn_reset' (Clear & Reset) button for the form.
        Resets the group form UI to its initial state and re-populates the group lookup dropdown.
        """
        print("CLIENT manage_subs: btn_reset_click called") # Using print for client-side logs
        
        # Call the main UI reset function for the group section and matrix
        self.reset_group_form_ui()
        
        # Re-initialize/refresh the group lookup dropdown
        self.initialize_group_lookup_dropdown()

        # Ensure the group action switch (if present) is set to "Update" mode
        # as reset_group_form_ui defaults it to "Update" (checked=False)
        # and initialize_group_lookup_dropdown makes it ready for selection.
        if hasattr(self, 'sw_group_action'):
            self.sw_group_action.checked = False 
            # Call _update_group_ui_mode to ensure dependent component states are correct
            self._update_group_ui_mode() 

        print("CLIENT manage_subs: Form reset and group lookup dropdown refreshed.")

# 16. btn_update_page_click 
    # Method #16 (Carried Over - btn_update_page_click)
    def btn_update_page_click(self, **event_args):
        """
        Refreshes the data displayed on the form for the currently selected
        subscription group, including its details and the price matrix.
        """
        print("CLIENT manage_subs: btn_update_page_click called") # Using print for client-side logs

        group_to_refresh_number = None

        if self.current_group_row and self.current_group_row.get('group_number'):
            # If a group is already loaded in self.current_group_row, refresh that one
            group_to_refresh_number = self.current_group_row['group_number']
            print(f"CLIENT manage_subs: Refreshing currently loaded group: G# {group_to_refresh_number}")
        elif hasattr(self, 'dd_group') and self.dd_group.selected_value:
            # If no group is fully loaded in current_group_row, but one is selected in the dropdown
            group_to_refresh_number = self.dd_group.selected_value
            print(f"CLIENT manage_subs: Refreshing group selected in dropdown: G# {group_to_refresh_number}")
        
        if group_to_refresh_number:
            # Call the main loading function for the group and its matrix
            self.load_group_details_and_matrix(group_to_refresh_number)
            Notification("Page data refreshed.", style="info", timeout=2).show()
            print(f"CLIENT manage_subs: Page data refreshed for G#: {group_to_refresh_number}")
        else:
            alert("No group selected to refresh. Please select a group or create a new one.", title="Refresh Information")
            print("CLIENT manage_subs: No group selected to refresh.")

# 17. _clear_subs_matrix
    # Method #17 (Carried Over - _clear_subs_matrix)
    def _clear_subs_matrix(self):
        """
        Clears the subscription price matrix display (rp_subs_matrix)
        and resets the matrix header labels.
        """
        print("CLIENT manage_subs: _clear_subs_matrix called") # Using print for client-side logs

        # Clear the RepeatingPanel items
        if hasattr(self, 'rp_subs_matrix'):
            self.rp_subs_matrix.items = []
        else:
            print("CLIENT manage_subs: WARNING - rp_subs_matrix not found on form to clear.")

        # Reset matrix header labels (Level names) to generic defaults
        # These are populated with group-specific names when a group is loaded.
        if hasattr(self, 'lbl_level1_header'):
            self.lbl_level1_header.text = "Level 1"
        if hasattr(self, 'lbl_level2_header'):
            self.lbl_level2_header.text = "Level 2"
        if hasattr(self, 'lbl_level3_header'):
            self.lbl_level3_header.text = "Level 3"
            
        # Also clear the group name/number display specific to the matrix section
        if hasattr(self, 'lbl_matrix_group_name'):
            self.lbl_matrix_group_name.text = "Plans for: (No Group Selected)"
        if hasattr(self, 'lbl_matrix_group_num'):
            self.lbl_matrix_group_num.text = "G#: "
            
        print("CLIENT manage_subs: Subscription matrix display cleared.")

# 18. _update_subs_matrix 
    #Point 18. Obsolete - to be removed

# 19. (NEW) populate_price_matrix
    #Server Function get_subscription_plan_matrix_data:
    # >This client-side populate_price_matrix method depends entirely on a new #server function #named get_subscription_plan_matrix_data(group_number).
    #>This server function (which we will need to create, likely #in sm_item_mod.py or sm_subscription_group_mod.py) is responsible for the #complex task of:
    #   >>Finding the 9 subs rows for the given group_number.
    #   >>For each subs row, finding its corresponding items row.
    #   >>For each items row, finding its linked default_price_id and then #fetching the actual prices row.
    #   >>Structuring this information into a list of 3 dictionaries (one per Tier). #Each dictionary will contain the tier name #(from #subscription_group.group_tierX_name) and the price display #string + item_id + is_paid flag for each of the 3 Levels within that Tier.
    #   >>"Free" tiers (T1) should have a price display like "$0.00" or "Free", #and is_paid as False.
    #   >>Paid tiers (T2, T3) will get their price from #the prices.unit_price_amount and 
    #prices.unit_price_currency_code, and is_paid as True.
    #template_rp_subs_matrix.py Adaptation: The item template for rp_subs_matrix will #need to be updated to correctly bind to the data structure returned 

    # Method #19 (NEW - Replaces functionality of old _update_subs_matrix)
    def populate_price_matrix(self, **event_args): # Added **event_args to allow use as refresh handler
        """
        Fetches the 3x3 subscription plan matrix data (plan definitions and their
        associated prices) for the self.current_group_row from the server
        and populates the self.rp_subs_matrix RepeatingPanel.
        """
        # Using print for client-side logs
        print("CLIENT manage_subs: populate_price_matrix called")

        if not self.current_group_row or not self.current_group_row.get('group_number'):
            print("CLIENT manage_subs: populate_price_matrix - No current_group_row or group_number. Clearing matrix.")
            if hasattr(self, 'rp_subs_matrix'):
                self.rp_subs_matrix.items = []
            return

        if not hasattr(self, 'rp_subs_matrix'):
            print("CLIENT manage_subs: WARNING - rp_subs_matrix RepeatingPanel not found on form. Cannot populate.")
            return

        try:
            group_number = self.current_group_row['group_number']
            print(f"CLIENT manage_subs: Fetching matrix data for G#: {group_number}")

            # This new server function needs to be created.
            # It will query 'subs', 'items', and 'prices' tables to build the matrix data.
            # Expected return: A list of 3 dictionaries, one for each Tier (T1, T2, T3).
            # Each dictionary should contain:
            #   'tier_name_display': (e.g., self.current_group_row['group_tier1_name'])
            #   'l1_price_display': (Formatted price string or "Free" or "Not Set")
            #   'l1_item_id': (The item_id of the 'items' row for L1/T_current)
            #   'l1_is_paid': (Boolean, False for T1, True for T2/T3)
            #   'l2_price_display': ...
            #   'l2_item_id': ...
            #   'l2_is_paid': ...
            #   'l3_price_display': ...
            #   'l3_item_id': ...
            #   'l3_is_paid': ...
            matrix_data_from_server = anvil.server.call('get_subscription_plan_matrix_data', group_number)
            
            if matrix_data_from_server is not None: # Server might return None on error or if group has no plans
                self.rp_subs_matrix.items = matrix_data_from_server
                print(f"CLIENT manage_subs: Price matrix populated with {len(matrix_data_from_server)} tier rows.")
            else:
                self.rp_subs_matrix.items = []
                print("CLIENT manage_subs: Server returned no data for price matrix.")
                # alert("Could not load plan prices for this group.", title="Matrix Error")

        except Exception as e:
            alert(f"Error loading subscription plan price matrix: {e}", title="Matrix Load Error")
            print(f"CLIENT manage_subs: Exception in populate_price_matrix for G#: {self.current_group_row.get('group_number', 'UNKNOWN')} - {e}")
            # import traceback # For more detailed client-side error during development
            # traceback.print_exc()
            self.rp_subs_matrix.items = [] # Clear matrix on error

# 20. (NEW) edit_plan_price_handler
    # Method #20 (NEW)
    def edit_plan_price_handler(self, plan_item_data, **event_args):
        """
        Handles the 'x_edit_plan_price' event raised by template_rp_subs_matrix
        when an "Edit Price" button (or similar interaction) is clicked for a specific plan variation.

        Args:
            plan_item_data (dict): A dictionary passed from the item template.
                                   Expected to contain at least 'item_id' (the item_id
                                   of the 'items' table row for the specific G/L/T plan definition)
                                   and 'is_paid' (boolean).
            **event_args: Standard Anvil event arguments.
        """
        # Using print for client-side logs
        print(f"CLIENT manage_subs: edit_plan_price_handler called with plan_item_data: {plan_item_data}")

        if not self.current_group_row:
            alert("Cannot edit plan price: No parent subscription group is currently loaded.", title="Action Error")
            print("CLIENT manage_subs: edit_plan_price_handler - current_group_row is None.")
            return

        if not plan_item_data or not isinstance(plan_item_data, dict):
            alert("Error: Invalid data received for plan price editing.", title="Internal Error")
            print("CLIENT manage_subs: edit_plan_price_handler - plan_item_data is invalid or not a dict.")
            return

        item_id_for_price_edit = plan_item_data.get('item_id')
        is_plan_paid_tier = plan_item_data.get('is_paid') # From matrix data, indicates if it's T2/T3

        if not item_id_for_price_edit:
            alert("Error: Plan item identifier (item_id) is missing. Cannot edit price.", title="Internal Error")
            print("CLIENT manage_subs: edit_plan_price_handler - item_id missing in plan_item_data.")
            return

        if not is_plan_paid_tier:
            # This should ideally be prevented by the UI in template_rp_subs_matrix
            # (i.e., no "Edit Price" button for free tiers), but good to double-check.
            alert("Free plans (Tier 1) do not have editable prices in this manner.", title="Information")
            print(f"CLIENT manage_subs: edit_plan_price_handler - Attempt to edit price for a non-paid tier (item_id: {item_id_for_price_edit}).")
            return

        # Fetch the full 'items' row for the specific plan definition (G/L/T combo)
        # This item_row will be passed as the parent 'item_row' to manage_price_form
        try:
            print(f"CLIENT manage_subs: Fetching item details for item_id: {item_id_for_price_edit}")
            item_row_for_price_form = anvil.server.call('get_item', item_id_for_price_edit)
            if not item_row_for_price_form:
                alert(f"Could not load the specific plan definition (ID: {item_id_for_price_edit}) to edit its price.", title="Error")
                print(f"CLIENT manage_subs: edit_plan_price_handler - get_item returned None for item_id: {item_id_for_price_edit}")
                return
        except Exception as e:
            alert(f"Error fetching plan definition details: {e}", title="Server Error")
            print(f"CLIENT manage_subs: edit_plan_price_handler - Exception fetching item: {e}")
            return

        # Fetch the existing 'prices' row linked to this item, if it exists
        # The 'default_price_id' on the item_row_for_price_form is a Link to the 'prices' table
        price_to_edit_row = None
        if item_row_for_price_form.get('default_price_id'):
            price_to_edit_row = item_row_for_price_form['default_price_id']
            # Ensure it's a full row object if it was just an ID (though Link column should give row)
            # No, default_price_id IS the price row itself if it's a Link column.
            print(f"CLIENT manage_subs: Existing price found for item {item_id_for_price_edit}: Price ID {price_to_edit_row['price_id'] if price_to_edit_row else 'None'}")
        else:
            print(f"CLIENT manage_subs: No existing default_price_id found for item {item_id_for_price_edit}. Creating new price.")


        # Open manage_price_form.py as a modal dialog (alert)
        # Pass:
        #   item_row: The 'items' row for this specific plan definition (G/L/T combo).
        #   price_to_edit: The existing 'prices' row (if any), or None to create a new one.
        #   price_type_context: Always 'recurring' for subscription plans.
        print(f"CLIENT manage_subs: Opening manage_price_form for item_id: {item_row_for_price_form['item_id']}")
        result = alert(
            content=manage_price_form(
                item_row=item_row_for_price_form, 
                price_to_edit=price_to_edit_row, 
                price_type_context='recurring'
            ),
            title=f"Set/Edit Price for Plan: {item_row_for_price_form.get('name', item_id_for_price_edit)}",
            large=True,
            buttons=[] # Buttons are on manage_price_form itself
        )

        if result is True: # manage_price_form raises x-close-alert with value=True on successful save
            print("CLIENT manage_subs: manage_price_form reported successful save. Refreshing price matrix.")
            # Refresh the price matrix to show the new/updated price
            self.populate_price_matrix()
        else:
            print(f"CLIENT manage_subs: manage_price_form closed without saving (result: {result}).")

# 21. btn_home_click
    # Method #21 (Carried Over - btn_home_click)
    def btn_home_click(self, **event_args):
        """
        Handles the click event of the 'btn_home' button.
        Navigates the user back to the main dashboard or home form.
        """
        # Using print for client-side logs
        print("CLIENT manage_subs: btn_home_click called - Navigating to paddle_home")
        
        open_form("paddle_home") # Assuming 'paddle_home' is your main landing/dashboard form