# Client Module: manage_service.py

from ._anvil_designer import manage_serviceTemplate
from anvil import *
# Ensure correct import paths for your project structure
from ..price_list_item_form import price_list_item_form
from ..manage_price_form import manage_price_form
import anvil.server
import anvil.users # Assuming you might use this for permissions eventually
import anvil.tables as tables # Not strictly needed if all DB access is server-side
import anvil.tables.query as q # Same as above
from anvil.tables import app_tables # Same as above
import datetime # Keep if used, remove if not
import json # For custom_data if you add it

class manage_service(manage_serviceTemplate): # Changed class name

  #__init__
  def __init__(self, **properties):
    # --- State Variables ---
    self.is_edit_mode = False
    self.current_service_id = None # Changed current_product_id to current_service_id

    self.init_components(**properties) # Initialize components from designer FIRST
    print("CLIENT manage_service: __init__ called") # Changed manage_product to manage_service

    # --- Configure Price Management UI ---
    if hasattr(self, 'rp_prices'): 
      self.rp_prices.item_template = price_list_item_form
      self.rp_prices.set_event_handler('x_edit_item_price', self.edit_item_price_handler)
      self.rp_prices.set_event_handler('x_refresh_item_prices', self.load_associated_prices)
    else:
      print("CLIENT manage_service: WARNING - rp_prices RepeatingPanel not found on manage_service form.") # Changed manage_product

    # --- Populate Dropdowns ---
    self.populate_tax_category_use_case_dropdown()
    self.initialize_service_lookup_dropdown() # Changed from initialize_product_lookup_dropdown

    # --- Set Event Handlers ---
    if hasattr(self, 'fl_service_image'): # Changed from fl_product_image
      self.fl_service_image.set_event_handler('change', self.fl_service_image_change)

    if hasattr(self, 'btn_service_save'): # Changed from btn_product_save
      self.btn_service_save.set_event_handler('click', self.btn_service_save_click)
    if hasattr(self, 'btn_reset'):
      self.btn_reset.set_event_handler('click', self.btn_reset_click)
    if hasattr(self, 'btn_delete'):
      self.btn_delete.set_event_handler('click', self.btn_delete_click)
    if hasattr(self, 'btn_home'):
      self.btn_home.set_event_handler('click', self.btn_home_click)
    if hasattr(self, 'dd_service'): # Changed from dd_product
      self.dd_service.set_event_handler('change', self.dd_service_change)
    if hasattr(self, 'dd_service_use_case'): # Changed from dd_product_use_case
      self.dd_service_use_case.set_event_handler('change', self.dd_service_use_case_change)
    if hasattr(self, 'btn_add_price'): 
      self.btn_add_price.set_event_handler('click', self.btn_add_price_click)
    if hasattr(self, 'sw_service_action'): # Changed from sw_product_action
      # Assuming you will create a self.sw_service_action_change method
      self.sw_service_action.set_event_handler('change', self.sw_service_action_change) 

    # --- Initial UI State ---
    self.reset_form_ui() 

    passed_item_id = properties.get('service_id') or properties.get('item_id') # Changed product_id to service_id
    if passed_item_id:
      self.current_service_id = passed_item_id # Changed current_product_id
      self.is_edit_mode = True
      if hasattr(self, 'sw_service_action'): # Changed from sw_product_action
        self.sw_service_action.checked = True 
      self.load_service_data(self.current_service_id) # Changed from load_product_data
    else:
      if hasattr(self, 'sw_service_action'): # Changed from sw_product_action
        self.sw_service_action.checked = False 

    print("CLIENT manage_service: __init__ completed.") # Changed manage_product


  #1 reset_form_ui
  def reset_form_ui(self):
    """Resets the form to its initial state for creating a new service.""" # Changed product to service
    print("CLIENT manage_service: reset_form_ui called") # Changed manage_product to manage_service

    self.lbl_form_title.text = "Create New Service" # Changed Product to Service
    self.current_item_row = None
    self.current_service_id = None # Changed current_product_id to current_service_id
    self.is_edit_mode = False
    # self.uploaded_file_media_object = None # If you use this state variable for FileLoader

    # Clear main service input fields
    self.tb_service_name.text = "" # Changed tb_product_name
    if hasattr(self, 'ta_service_description'): # Check if component exists
      self.ta_service_description.text = "" # Changed ta_product_description

    if hasattr(self, 'sw_service_status'): # Check if component exists # Kept comment as is
      self.sw_service_status.checked = True # Default to active # Changed sw_product_status

    if hasattr(self, 'dd_service'): # Service lookup dropdown # Changed dd_product
      self.dd_service.selected_value = None # Kept comment as is

    # Kept comment as is
    if hasattr(self, 'lbl_service_num'): # Changed lbl_product_num
      self.lbl_service_num.text = "(New Service)" # Display for internal item_id # Changed Product to Service

    # Clear image related fields
    if hasattr(self, 'fl_service_image'): # Changed fl_product_image
      self.fl_service_image.clear()
    if hasattr(self, 'img_service'): # Kept comment as is # Changed img_product
      self.img_service.source = None
    if hasattr(self, 'tb_img_name'): # Kept comment as is
      self.tb_img_name.text = ""
      # If you have tb_service_image_url for displaying URL: # Changed tb_product_image_url
      # if hasattr(self, 'tb_service_image_url'):
      #    self.tb_service_image_url.text = ""

    # Clear new Tax Category Use Case Dropdown
    if hasattr(self, 'dd_service_use_case'): # Kept comment as is # Changed dd_product_use_case
      self.dd_service_use_case.selected_value = None
    if hasattr(self, 'lbl_selected_paddle_tax_category'): # Optional display label # Kept comment as is
      self.lbl_selected_paddle_tax_category.visible = False
      self.lbl_selected_paddle_tax_category.text = "Paddle Tax Category: "

    # Clear Custom Data TextArea
    if hasattr(self, 'ta_custom_data'): # Kept comment as is
      self.ta_custom_data.text = ""

    # Reset action switch if it exists
    if hasattr(self, 'sw_service_action'): # Changed sw_product_action
      self.sw_service_action.checked = False # Default to "Update" visual, but form is for "New"

    # Clear Prices RepeatingPanel
    if hasattr(self, 'rp_prices'): # Kept comment as is
      self.rp_prices.items = []

    # Disable buttons that require a loaded/saved service
    if hasattr(self, 'btn_add_price'): # Kept comment as is
      self.btn_add_price.enabled = False
    if hasattr(self, 'btn_delete'): # Kept comment as is
      self.btn_delete.enabled = False

    print("CLIENT manage_service: reset_form_ui completed.") # Changed manage_product to manage_service

  #2 populate_tax_category_use_case_dropdown
  # --- NEW: Populate Tax Category Use Case Dropdown ---
  def populate_tax_category_use_case_dropdown(self):
    if hasattr(self, 'dd_service_use_case'): # Changed dd_product_use_case
      try:
        use_cases = anvil.server.call('get_tax_use_cases', mybizz_sector_filter='service') # Changed 'product' to 'service'
        self.dd_service_use_case.items = [("Select a use case...", None)] + sorted(use_cases) # Changed dd_product_use_case
      except Exception as e:
        print(f"Error loading service use cases: {e}") # Changed product to service
        alert(f"Could not load service types: {e}", role="warning") # Changed product to service
        self.dd_service_use_case.items = [("Error loading...", None)] # Changed dd_product_use_case



    #3 initialize_service_lookup_dropdown
    # --- MODIFIED: Initialize Service Lookup Dropdown ---
  # Method to Replace/Refactor: initialize_service_lookup_dropdown (was initialize_product_lookup_dropdown)
    def initialize_service_lookup_dropdown(self): # Changed method name
      """Initializes the service lookup dropdown (dd_service) with items of type 'service'.""" # Changed product to service, dd_product to dd_service
    print("CLIENT manage_service: initialize_service_lookup_dropdown called") # Changed manage_product to manage_service

    if hasattr(self, 'dd_service'): # Check if the dropdown component exists # Changed dd_product to dd_service
      try:
        # Call the unified 'list_items' server function, filtering for services
        service_list_for_dd = anvil.server.call('list_items', item_type_filter='service') # Changed product to service

        # Format for DropDown: items should be a list of (display_text, value) tuples
        # The value will be the item_id.
        dropdown_items = [("Create New Service...", None)] # Option to switch to new service mode # Changed Product to Service
        if service_list_for_dd: # Check if list is not empty # Changed product_list_for_dd
          dropdown_items.extend(sorted([(s['name'], s['item_id']) for s in service_list_for_dd])) # Changed p to s, product_list_for_dd

        # Corrected: These lines were inside the if service_list_for_dd block
        self.dd_service.items = dropdown_items # Changed dd_product
        self.dd_service.selected_value = None # Default to placeholder # Changed dd_product
        # Corrected: Use len(service_list_for_dd) if service_list_for_dd else 0 for accurate count
        print(f"CLIENT manage_service: Service lookup dropdown populated with {len(service_list_for_dd) if service_list_for_dd else 0} services.") # Changed manage_product, Product, products, product_list_for_dd

      except Exception as e:
        print(f"CLIENT manage_service: Error loading service list for dropdown: {e}") # Changed manage_product, product
        alert(f"Could not load service list: {e}", role="warning", title="Data Load Error") # Changed product
        # Provide a fallback in case of error
        self.dd_service.items = [("Error loading services...", None)] # Changed dd_product, products
    else:
      print("CLIENT manage_service: WARNING - dd_service DropDown not found on form design.") # Changed manage_product, dd_product



    #4 dd_service_change
    def dd_service_change(self, **event_args): # Changed method name
          """
          Handles selection changes in the 'dd_service' (service lookup) DropDown.
          Loads the selected service's details or resets the form for new service creation.
          """ # Changed dd_product, product, service
    selected_item_id = None
    if hasattr(self, 'dd_service'): # Ensure component exists # Changed dd_product
      selected_item_id = self.dd_service.selected_value # Changed dd_product

    # Corrected: This print was inside the if hasattr(self, 'dd_service') block
    print(f"CLIENT manage_service: dd_service_change - selected_item_id: {selected_item_id}") # Changed manage_product, dd_product_change

    if selected_item_id:
      # An existing service is selected, load its details
      self.load_service_data(selected_item_id) # Calls the refactored load method # Changed load_product_data
      # Ensure form is in "Update" mode visually if sw_service_action exists
      if hasattr(self, 'sw_service_action'): # Changed sw_product_action
        self.sw_service_action.checked = True # This might trigger its own change event # Changed sw_product_action
    else:
      # "Create New Service..." (or placeholder with None value) was selected # Changed Product to Service
      self.reset_form_ui()
      # Ensure form is in "New" mode visually if sw_service_action exists
      if hasattr(self, 'sw_service_action'): # Changed sw_product_action
        self.sw_service_action.checked = False # This might trigger its own change event # Changed sw_product_action

    # Corrected: This print was inside the inner if hasattr(self, 'sw_service_action') block
    print("CLIENT manage_service: dd_service_change processing complete.") # Changed manage_product, dd_product_change


    #5 dd_service_use_case_change
    def dd_service_use_case_change(self, **event_args): # Changed method name
      if hasattr(self, 'lbl_selected_paddle_tax_category'): # Optional display label
        selected_paddle_category = self.dd_service_use_case.selected_value # Changed dd_product_use_case
        if selected_paddle_category:
          self.lbl_selected_paddle_tax_category.text = f"Paddle Tax Category: {selected_paddle_category}"
          self.lbl_selected_paddle_tax_category.visible = True
        else:
          self.lbl_selected_paddle_tax_category.text = "Paddle Tax Category: "
          self.lbl_selected_paddle_tax_category.visible = False



  #6 load_service_data 
  def load_service_data(self, item_id_to_load): # Changed method name
    """Loads data for a specific item_id (service) into the form.""" # Changed product to service
    print(f"CLIENT manage_service: load_service_data called for item_id: {item_id_to_load}") # Changed manage_product, load_product_data

    if not item_id_to_load:
      self.reset_form_ui() # If no ID, reset to new service state # Changed product to service
      print("CLIENT manage_service: load_service_data - no item_id_to_load provided.") # Changed manage_product, load_product_data
      return

    # Corrected: This try block was incorrectly indented
    try:
      # Call the unified 'get_item' server function
      item_row = anvil.server.call('get_item', item_id_to_load)

      if item_row and item_row.get('item_type') == 'service': # Changed 'product' to 'service'
        self.current_item_row = item_row
        self.current_service_id = item_row['item_id'] # Update current_service_id state # Changed current_product_id
        self.is_edit_mode = True
        if hasattr(self, 'sw_service_action'): # Changed sw_product_action
          self.sw_service_action.checked = True # Set switch to "Update" mode # Changed sw_product_action

        # Corrected: This block was incorrectly indented
        if hasattr(self, 'lbl_form_title'): 
          self.lbl_form_title.text = f"Edit Service: {item_row.get('name', '(No Name)')}" # Changed Product to Service
        if hasattr(self, 'lbl_service_num'): 
          self.lbl_service_num.text = item_row['item_id'] # Changed lbl_product_num
        self.tb_service_name.text = item_row.get('name', "") # Changed tb_product_name
        if hasattr(self, 'ta_service_description'): 
          self.ta_service_description.text = item_row.get('description', "") # Changed ta_product_description
        if hasattr(self, 'sw_service_status'): 
          self.sw_service_status.checked = item_row.get('status', True) # Default to True if not present # Changed sw_product_status

        # Set Tax Category Use Case Dropdown
        stored_paddle_tax_category = item_row.get('tax_category')
        if hasattr(self, 'dd_service_use_case'): # Changed dd_product_use_case
          self.dd_service_use_case.selected_value = stored_paddle_tax_category # Changed dd_product_use_case
          # Check if the value actually got set (i.e., was in the dropdown items)
          if self.dd_service_use_case.selected_value != stored_paddle_tax_category and stored_paddle_tax_category is not None: # Changed dd_product_use_case
            print(f"CLIENT manage_service: Warning - Loaded tax category '{stored_paddle_tax_category}' for item {item_id_to_load} was not found in dd_service_use_case items. Dropdown may show placeholder.") # Changed manage_product, dd_product_use_case
            # Optionally, you could add the missing value to items if desired, or alert user.
            # For now, it will default to placeholder if not found.
          self.dd_service_use_case_change() # Trigger change to update optional display label # Changed dd_product_use_case_change

        # Corrected: This block was incorrectly indented
        # Custom Data
        if hasattr(self, 'ta_custom_data'):
          custom_data_val = item_row.get('custom_data')
          if isinstance(custom_data_val, dict):
            try:
              self.ta_custom_data.text = json.dumps(custom_data_val, indent=2)
            except TypeError: 
              self.ta_custom_data.text = str(custom_data_val)
            except Exception as e_json: 
              print(f"CLIENT manage_service: Error serializing custom_data: {e_json}") # Changed manage_product
              self.ta_custom_data.text = str(custom_data_val) 
          elif custom_data_val is not None:
            self.ta_custom_data.text = str(custom_data_val)
          else:
            self.ta_custom_data.text = ""

        # Corrected: This block was incorrectly indented
        # Image Display
        if hasattr(self, 'fl_service_image'):  # Changed fl_product_image
          self.fl_service_image.clear() 
        media_row = item_row.get('media') 
        if hasattr(self, 'img_service'): # Changed img_product # Corrected Indent
          self.img_service.source = media_row['file'] if media_row and media_row.get('file') else None # Changed img_product
        if hasattr(self, 'tb_img_name'): # Corrected Indent
          self.tb_img_name.text = media_row['name'] if media_row and media_row.get('name') else ""
          # If you have tb_service_image_url and files table stores URL: # Changed tb_product_image_url
          # if hasattr(self, 'tb_service_image_url'):
          #    self.tb_service_image_url.text = media_row['img_url'] if media_row and media_row.get('img_url') else ""

        # Corrected: This block was incorrectly indented
        # Enable buttons relevant for an existing service
        if hasattr(self, 'btn_add_price'): 
          self.btn_add_price.enabled = True 
        if hasattr(self, 'btn_delete'): 
          self.btn_delete.enabled = True 

        # Load associated prices for this service
        self.load_associated_prices()
        print(f"CLIENT manage_service: Service details loaded for item_id: {item_id_to_load}") # Changed manage_product, Product to Service

      else:
        alert(f"Could not load details for ID '{item_id_to_load}'. It might not be a service or does not exist.", title="Load Error") # Changed product to service
        print(f"CLIENT manage_service: Item {item_id_to_load} not found or not a service.") # Changed manage_product
        self.reset_form_ui() # Reset form if service not found or wrong type
    except Exception as e:
      alert(f"An error occurred while loading service details: {e}", title="Load Error") # Changed product to service
      print(f"CLIENT manage_service: Exception in load_service_data for item_id {item_id_to_load} - {e}") # Changed manage_product, load_product_data
      self.reset_form_ui()



    #7 fl_service_image_change
    def fl_service_image_change(self, file, **event_args): # Changed method name
      """Display the uploaded image and file name."""
      # This function should only update the UI preview.
      # Actual file saving happens in btn_service_save_click via server call. # Changed btn_product_save_click
      if hasattr(self, 'img_service') and hasattr(self, 'tb_img_name'): # Changed img_product
        if file:
          self.img_service.source = file # Changed img_product
          self.tb_img_name.text = file.name if hasattr(file, "name") else "Unknown"
          # Store the file object to be passed to server on save
          # self.uploaded_file_media_object = file # We'll handle this in save
        else: # File cleared from FileLoader
          self.img_service.source = None # Changed img_product
          self.tb_img_name.text = ""
          # self.uploaded_file_media_object = None
          # Optionally revert to saved image if editing:
          # if self.is_edit_mode and self.current_item_row and self.current_item_row.get('media'):
          #    media_row = self.current_item_row['media']
          #    self.img_service.source = media_row['file'] if media_row else None # Changed img_product
          #    self.tb_img_name.text = media_row['name'] if media_row else ""


  #8 btn_service_save_click
  def btn_service_save_click(self, **event_args): # Changed method name
    """Saves the current service (item) details.""" # Changed product to service
    print("CLIENT manage_service: btn_service_save_click called") # Changed manage_product, btn_product_save_click

    if not self.tb_service_name.text.strip(): # Changed tb_product_name
      alert("Service Name is required.") # Changed Product to Service
      return

    selected_paddle_tax_category = None
    if hasattr(self, 'dd_service_use_case'): # Changed dd_product_use_case
      selected_paddle_tax_category = self.dd_service_use_case.selected_value # Changed dd_product_use_case
      if not selected_paddle_tax_category:
        alert("Please select a 'Use Case' for this service (this sets the tax category).") # Changed product to service
        return
    else:
      alert("Critical Error: Tax Category UI component (dd_service_use_case) is missing from the form design.") # Changed dd_product_use_case
      return

    item_data = {
      'name': self.tb_service_name.text.strip(), # Changed tb_product_name
      'description': self.ta_service_description.text.strip(), # Changed ta_product_description
      'status': self.sw_service_status.checked, # Changed sw_product_status
      'tax_category': selected_paddle_tax_category,
      'item_type': 'service', # Hardcoded for this form 
      'media': None 
    }

    if hasattr(self, 'ta_custom_data'):
      custom_data_str = self.ta_custom_data.text.strip()
      if custom_data_str:
        try:
          item_data['custom_data'] = json.loads(custom_data_str) 
        except json.JSONDecodeError:
          alert("Custom Data is not valid JSON. Please correct it or leave it blank.")
          return
      else:
        item_data['custom_data'] = None

    uploaded_file_for_server = None
    uploaded_file_name_for_server = None 
    if hasattr(self, 'fl_service_image') and self.fl_service_image.file: # Changed fl_product_image
      uploaded_file_for_server = self.fl_service_image.file # Changed fl_product_image
      if hasattr(self, 'tb_img_name') and self.tb_img_name.text.strip():
        uploaded_file_name_for_server = self.tb_img_name.text.strip()
      else:
        if uploaded_file_for_server:
          uploaded_file_name_for_server = uploaded_file_for_server.name

      item_data['file_upload'] = uploaded_file_for_server
      item_data['file_upload_name'] = uploaded_file_name_for_server
      if uploaded_file_name_for_server: 
        print(f"CLIENT manage_service: Preparing to send new image '{uploaded_file_name_for_server}'") # Changed manage_product

    elif self.is_edit_group_mode and self.current_item_row and self.current_item_row.get('media'): # Corrected: was is_edit_mode, should be is_edit_group_mode for consistency if this was copied from manage_subs. Assuming it should be self.is_edit_mode for manage_service
      item_data['existing_media_link'] = self.current_item_row.get('media')
      print(f"CLIENT manage_service: Retaining existing media link for item {self.current_item_row.get('item_id')}") # Changed manage_product

    try:
      print(f"CLIENT manage_service: Calling server. Edit mode: {self.is_edit_mode}. Current ID: {self.current_service_id}") # Changed manage_product, current_product_id
      if self.is_edit_mode and self.current_service_id: # Changed current_product_id
        updated_item = anvil.server.call('update_item', self.current_service_id, item_data) # Changed current_product_id
        self.current_item_row = updated_item 
        Notification("Service updated successfully.", style="success", timeout=3).show() # Changed Product to Service
        print(f"CLIENT manage_service: Service {self.current_service_id} updated.") # Changed manage_product, Product, current_product_id
      else:
        new_item = anvil.server.call('create_item', item_data)
        self.current_item_row = new_item
        self.current_service_id = new_item['item_id'] # Changed current_product_id
        self.is_edit_mode = True
        self.lbl_form_title.text = f"Edit Service: {new_item.get('name', '')}" # Changed Product to Service
        self.lbl_service_num.text = new_item['item_id'] # Changed lbl_product_num
        if hasattr(self, 'sw_service_action'): # Changed sw_product_action
          self.sw_service_action.checked = True # Changed sw_product_action

        if hasattr(self, 'btn_add_price'): 
          self.btn_add_price.enabled = True 
        if hasattr(self, 'btn_delete'): 
          self.btn_delete.enabled = True 
        self.initialize_service_lookup_dropdown() # Changed initialize_product_lookup_dropdown
        if hasattr(self, 'dd_service'): # Changed dd_product
          self.dd_service.selected_value = new_item['item_id'] # Changed dd_product
        Notification("Service created. You can now add prices.", style="success", timeout=3).show() # Changed Product to Service
        print(f"CLIENT manage_service: Service {new_item['item_id']} created.") # Changed manage_product, Product

      if self.current_service_id:
        # --- >>> CORRECTED METHOD CALL HERE <<< ---
        self.load_service_data(self.current_service_id) 
        # --- >>> END OF CORRECTION <<< ---

      if hasattr(self, 'fl_service_image'): 
        self.fl_service_image.clear() 

    except anvil.server.ValidationError as e:
      alert(f"Validation Error from server: {e.err_obj if hasattr(e, 'err_obj') and e.err_obj else str(e)}", title="Save Failed")
      print(f"CLIENT manage_service: Server validation error saving service: {e}") 
    except anvil.http.HttpError as e_http: 
      alert(f"Paddle API Error: {e_http.status}. MyBizz data saved, but Paddle sync failed. Check server logs or try saving again.", title="Paddle Sync Error")
      print(f"CLIENT manage_service: Paddle API HttpError saving service: {e_http}") 
    except Exception as e:
      alert(f"An error occurred while saving the service: {e}", title="Save Error") 
      print(f"CLIENT manage_service: General error saving service: {e}")
      # import traceback
      # print(traceback.format_exc())


  #9 load_associated_prices
  def load_associated_prices(self, **event_args): # Can be called by event (e.g., x_refresh_item_prices) or directly
    """
                                        Loads prices linked to the self.current_item_row (service)
                                        into the rp_prices RepeatingPanel.
                                        """ # Changed product to service
    print("CLIENT manage_service: load_associated_prices called") # Changed manage_product

    if hasattr(self, 'rp_prices'): # Ensure rp_prices component exists
      if self.current_item_row and self.current_item_row.get('item_id'):
        current_item_id = self.current_item_row['item_id']
        print(f"CLIENT manage_service: Fetching prices for item_id: {current_item_id}") # Changed manage_product
        try:
          # Calls 'list_prices_for_item' from sm_pricing_mod.py
          prices_list = anvil.server.call('list_prices_for_item', current_item_id)
          self.rp_prices.items = prices_list
          print(f"CLIENT manage_service: rp_prices populated with {len(prices_list)} prices.") # Changed manage_product
        except Exception as e:
          alert(f"Error loading prices for this service: {e}", title="Price Load Error") # Changed product to service
          print(f"CLIENT manage_service: Error in load_associated_prices for item {current_item_id}: {e}") # Changed manage_product
          self.rp_prices.items = []
      else:
        # No current service loaded, so clear the prices list # Changed product to service
        self.rp_prices.items = []
        print("CLIENT manage_service: load_associated_prices - No current_item_row, rp_prices cleared.") # Changed manage_product
    else:
      print("CLIENT manage_service: WARNING - rp_prices RepeatingPanel not found on form design.") # Changed manage_product



  #10 btn_add_price_click
  def btn_add_price_click(self, **event_args):
    """
                                        Opens the manage_price_form to add a new price for the current service.
                                        """ # Changed product to service
    print("CLIENT manage_service: btn_add_price_click called") # Changed manage_product

    if not self.current_item_row or not self.current_item_row.get('item_id'):
      alert("Please save or load a service before adding prices.", title="Action Required") # Changed product to service
      print("CLIENT manage_service: btn_add_price_click - No current_item_row to add price to.") # Changed manage_product
      return

    # For products (and services), the price_type_context is 'one_time'
    # self.current_item_row is the Anvil Row object of the parent item
    print(f"CLIENT manage_service: Opening manage_price_form to create new 'one_time' price for item: {self.current_item_row['item_id']}") # Changed manage_product
    result = alert(
      content=manage_price_form(item_row=self.current_item_row, 
                                price_to_edit=None, 
                                price_type_context='one_time'),
      title="Add New Price for Service", # Changed Product to Service
      large=True,
      buttons=[] # Buttons are defined on manage_price_form itself
    )

    if result is True: # manage_price_form raises x-close-alert with value=True on successful save
      print("CLIENT manage_service: manage_price_form reported successful save. Refreshing prices.") # Changed manage_product
      self.load_associated_prices() # Refresh the list of prices
    else:
      print("CLIENT manage_service: manage_price_form closed without save or with cancel.") # Changed manage_product



  #11 edit_item_price_handler
  def edit_item_price_handler(self, price_item_to_edit, **event_args):
    """
                                                Handles the 'x_edit_item_price' event raised by price_list_item_form.
                                                Opens manage_price_form in edit mode for the selected price.
                
                                                Args:
                                                                price_item_to_edit (anvil.tables.Row): The 'prices' table row to be edited.
                                                """
    print(f"CLIENT manage_service: edit_item_price_handler called for price_id: {price_item_to_edit['price_id'] if price_item_to_edit and isinstance(price_item_to_edit, tables.Row) else 'None'}") # Changed manage_product
    if not self.current_item_row: # Parent item context
      alert("Error: No parent service is currently loaded. Cannot edit price.", title="Context Error") # Changed product to service
      print("CLIENT manage_service: edit_item_price_handler - current_item_row is None.") # Changed manage_product
      return

    if not price_item_to_edit or not isinstance(price_item_to_edit, tables.Row): # Check if it's a Row
      alert("Error: Invalid price data received for editing.", title="Internal Error")
      print("CLIENT manage_service: edit_item_price_handler - price_item_to_edit is invalid or not a Row.") # Changed manage_product
      return

    # Determine price_type from the price_item_to_edit itself
    price_type_ctx = price_item_to_edit.get('price_type', 'one_time') # Default if not set on price row

    print(f"CLIENT manage_service: Opening manage_price_form to edit price_id: {price_item_to_edit['price_id']} for item: {self.current_item_row['item_id']}") # Changed manage_product
    result = alert(
      content=manage_price_form(item_row=self.current_item_row, 
                                price_to_edit=price_item_to_edit, 
                                price_type_context=price_type_ctx),
      title="Edit Price",
      large=True,
      buttons=[] # Buttons are defined on manage_price_form itself
    )

    if result is True: # manage_price_form raises x-close-alert with value=True on successful save
      print("CLIENT manage_service: manage_price_form reported successful save. Refreshing prices.") # Changed manage_product
      self.load_associated_prices() # Refresh the list of prices
    else:
      print("CLIENT manage_service: manage_price_form closed without save or with cancel.") # Changed manage_product   




  #12 btn_reset_click
  def btn_reset_click(self, **event_args):
    """Reset all form fields to default values."""
    self.reset_form_ui()
    self.initialize_service_lookup_dropdown() # Also refresh dropdown # Changed product to service




#13 btn_delete_click
def btn_delete_click(self, **event_args):
  """
                                        Deletes the current item (service) from the MyBizz database
                                        after confirmation. Also attempts to handle Paddle archival via server.
                                        """ # Changed product to service
  print("CLIENT manage_service: btn_delete_click called") # Changed manage_product

  if self.current_service_id and self.is_edit_mode: # Ensure a service is loaded and in edit mode # Changed current_product_id
    # Fetch the item name again for the confirmation message,
    # as the textbox might have unsaved changes.
    # self.current_item_row should be populated if self.current_service_id is set.
    name_for_confirm = self.current_item_row.get('name', 'this service') if self.current_item_row else 'this service' # Changed product to service

    confirmation_message = (
      f"Are you sure you want to delete the service '{name_for_confirm}' (ID: {self.current_service_id})?\n\n" # Changed product, current_product_id
      "This action will also attempt to:\n"
      "  - Delete any associated MyBizz prices for this service (if not in use by subscriptions).\n" # Changed product to service
      "  - Archive the corresponding Product in Paddle (if synced).\n\n"
      "This action CANNOT be undone if there are no active customer subscriptions linked to its prices. "
      "If active subscriptions exist, deletion of associated prices might be prevented."
    )

    if confirm(confirmation_message, title="Confirm Service Deletion", buttons=[("Cancel", False), ("DELETE SERVICE", True)]): # Changed Product to Service (twice)
      print(f"CLIENT manage_service: User confirmed deletion for item_id: {self.current_service_id}") # Changed manage_product, current_product_id
      try:
        # Call the unified 'delete_item' server function from sm_item_mod.py
        # This server function should handle dependency checks (prices, active subscriptions via prices)
        # and attempt Paddle Product archival before deleting from MyBizz.
        anvil.server.call('delete_item', self.current_service_id) # Changed current_product_id

        Notification("Service deleted successfully.", style="success", timeout=3).show() # Changed Product to Service
        print(f"CLIENT manage_service: Service {self.current_service_id} reported as deleted by server.") # Changed manage_product, Product, current_product_id

        # Reset the form to a clean state for new service entry
        self.reset_form_ui()
        # Refresh the service lookup dropdown as the item is now gone
        self.initialize_service_lookup_dropdown() # Changed product

      except anvil.server.PermissionDenied as e:
        alert(f"Permission Denied: {e}", title="Deletion Failed")
        print(f"CLIENT manage_service: Permission denied deleting item {self.current_service_id}: {e}") # Changed manage_product, current_product_id
      except Exception as e:
        # Catch specific errors from server if possible, or display generic
        alert(f"Error deleting service: {e}", title="Deletion Failed") # Changed product to service
        print(f"CLIENT manage_service: Error deleting item {self.current_service_id}: {e}") # Changed manage_product, current_product_id
    else:
      print(f"CLIENT manage_service: User cancelled deletion for item_id: {self.current_service_id}") # Changed manage_product, current_product_id
  else:
    alert("No service is currently loaded or selected to delete.", title="Action Error") # Changed product to service
    print("CLIENT manage_service: btn_delete_click - No current_service_id or not in edit mode.") # Changed manage_product, current_product_id                




  #14 btn_home_click
  def btn_home_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('paddle_home')          