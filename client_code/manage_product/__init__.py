# Client Module: manage_product.py

from ._anvil_designer import manage_productTemplate
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

class manage_product(manage_productTemplate):

  #__init__
  def __init__(self, **properties):
    # --- State Variables ---
    self.is_edit_mode = False
    self.current_product_id = None # This will now store the item_id from 'items' table

    self.init_components(**properties) # Initialize components from designer FIRST
    print("CLIENT manage_product: __init__ called") 

    # --- Configure Price Management UI ---
    if hasattr(self, 'rp_prices'): 
      self.rp_prices.item_template = price_list_item_form
      self.rp_prices.set_event_handler('x_edit_item_price', self.edit_item_price_handler)
      self.rp_prices.set_event_handler('x_refresh_item_prices', self.load_associated_prices)
    else:
      print("CLIENT manage_product: WARNING - rp_prices RepeatingPanel not found on manage_product form.")

    # --- Populate Dropdowns ---
    self.populate_tax_category_use_case_dropdown()
    self.initialize_product_lookup_dropdown()

    # --- Set Event Handlers ---
    if hasattr(self, 'fl_product_image'):
      self.fl_product_image.set_event_handler('change', self.fl_product_image_change)

    if hasattr(self, 'btn_product_save'):
      self.btn_product_save.set_event_handler('click', self.btn_product_save_click)
    if hasattr(self, 'btn_reset'):
      self.btn_reset.set_event_handler('click', self.btn_reset_click)
    if hasattr(self, 'btn_delete'):
      self.btn_delete.set_event_handler('click', self.btn_delete_click)
    if hasattr(self, 'btn_home'):
      self.btn_home.set_event_handler('click', self.btn_home_click)
    if hasattr(self, 'dd_product'): 
      self.dd_product.set_event_handler('change', self.dd_product_change)
    if hasattr(self, 'dd_product_use_case'): 
      self.dd_product_use_case.set_event_handler('change', self.dd_product_use_case_change)
    if hasattr(self, 'btn_add_price'): 
      self.btn_add_price.set_event_handler('click', self.btn_add_price_click)
    if hasattr(self, 'sw_product_action'):
      # Assuming you will create a self.sw_product_action_change method
      self.sw_product_action.set_event_handler('change', self.sw_product_action_change) 

    # --- Initial UI State ---
    self.reset_form_ui() 

    passed_item_id = properties.get('product_id') or properties.get('item_id') 
    if passed_item_id:
      self.current_product_id = passed_item_id
      self.is_edit_mode = True
      if hasattr(self, 'sw_product_action'): 
        self.sw_product_action.checked = True 
      self.load_product_data(self.current_product_id) 
    else:
      if hasattr(self, 'sw_product_action'): 
        self.sw_product_action.checked = False 

    print("CLIENT manage_product: __init__ completed.")

  
  #1 reset_form_ui
  def reset_form_ui(self):
    """Resets the form to its initial state for creating a new product."""
    print("CLIENT manage_product: reset_form_ui called")

    self.lbl_form_title.text = "Create New Product"
    self.current_item_row = None
    self.current_product_id = None # Ensure this is also cleared
    self.is_edit_mode = False
    # self.uploaded_file_media_object = None # If you use this state variable for FileLoader

    # Clear main product input fields
    self.tb_product_name.text = ""
    if hasattr(self, 'ta_product_description'): # Check if component exists
      self.ta_product_description.text = ""

    if hasattr(self, 'sw_product_status'): # Check if component exists # Corrected Indent
      self.sw_product_status.checked = True # Default to active

    if hasattr(self, 'dd_product'): # Product lookup dropdown # Corrected Indent
      self.dd_product.selected_value = None 

    # Corrected Indent for lbl_product_num
    if hasattr(self, 'lbl_product_num'):
      self.lbl_product_num.text = "(New Product)" # Display for internal item_id

    # Clear image related fields
    if hasattr(self, 'fl_product_image'):
      self.fl_product_image.clear()
    if hasattr(self, 'img_product'): # Corrected Indent
      self.img_product.source = None
    if hasattr(self, 'tb_img_name'): # Corrected Indent
      self.tb_img_name.text = ""
      # If you have tb_product_image_url for displaying URL:
      # if hasattr(self, 'tb_product_image_url'):
      #    self.tb_product_image_url.text = ""

    # Clear new Tax Category Use Case Dropdown
    if hasattr(self, 'dd_product_use_case'): # Corrected Indent
      self.dd_product_use_case.selected_value = None
    if hasattr(self, 'lbl_selected_paddle_tax_category'): # Optional display label # Corrected Indent
      self.lbl_selected_paddle_tax_category.visible = False
      self.lbl_selected_paddle_tax_category.text = "Paddle Tax Category: "

    # Clear Custom Data TextArea
    if hasattr(self, 'ta_custom_data'): # Corrected Indent
      self.ta_custom_data.text = ""

    # Reset action switch if it exists
    if hasattr(self, 'sw_product_action'): 
      self.sw_product_action.checked = False # Default to "Update" visual, but form is for "New"

    # Clear Prices RepeatingPanel
    if hasattr(self, 'rp_prices'): # Corrected Indent
      self.rp_prices.items = []

    # Disable buttons that require a loaded/saved product
    if hasattr(self, 'btn_add_price'): # Corrected Indent
      self.btn_add_price.enabled = False
    if hasattr(self, 'btn_delete'): # Corrected Indent
      self.btn_delete.enabled = False

    print("CLIENT manage_product: reset_form_ui completed.")

  
  #2 populate_tax_category_use_case_dropdown
  # --- NEW: Populate Tax Category Use Case Dropdown ---
  def populate_tax_category_use_case_dropdown(self):
    if hasattr(self, 'dd_product_use_case'):
      try:
        use_cases = anvil.server.call('get_tax_use_cases', mybizz_sector_filter='product')
        self.dd_product_use_case.items = [("Select a use case...", None)] + sorted(use_cases)
      except Exception as e:
        print(f"Error loading product use cases: {e}")
        alert(f"Could not load product types: {e}", role="warning")
        self.dd_product_use_case.items = [("Error loading...", None)]

  
  
  #3 initialize_product_lookup_dropdown
  # --- MODIFIED: Initialize Product Lookup Dropdown ---
  # Method to Replace/Refactor: initialize_product_lookup_dropdown (was initialize_product_dropdown)
  def initialize_product_lookup_dropdown(self):
    """Initializes the product lookup dropdown (dd_product) with items of type 'product'."""
    print("CLIENT manage_product: initialize_product_lookup_dropdown called")

    if hasattr(self, 'dd_product'): # Check if the dropdown component exists
      try:
        # Call the unified 'list_items' server function, filtering for products
        product_list_for_dd = anvil.server.call('list_items', item_type_filter='product')

        # Format for DropDown: items should be a list of (display_text, value) tuples
        # The value will be the item_id.
        dropdown_items = [("Create New Product...", None)] # Option to switch to new product mode
        if product_list_for_dd: # Check if list is not empty
          dropdown_items.extend(sorted([(p['name'], p['item_id']) for p in product_list_for_dd]))

        # Corrected: These lines were inside the if product_list_for_dd block
        self.dd_product.items = dropdown_items
        self.dd_product.selected_value = None # Default to placeholder
        # Corrected: Use len(product_list_for_dd) if product_list_for_dd else 0 for accurate count
        print(f"CLIENT manage_product: Product lookup dropdown populated with {len(product_list_for_dd) if product_list_for_dd else 0} products.")

      except Exception as e:
        print(f"CLIENT manage_product: Error loading product list for dropdown: {e}")
        alert(f"Could not load product list: {e}", role="warning", title="Data Load Error")
        # Provide a fallback in case of error
        self.dd_product.items = [("Error loading products...", None)]
    else:
      print("CLIENT manage_product: WARNING - dd_product DropDown not found on form design.")

  #4 dd_product_change
  def dd_product_change(self, **event_args):
    """
          Handles selection changes in the 'dd_product' (product lookup) DropDown.
          Loads the selected product's details or resets the form for new product creation.
          """
    selected_item_id = None
    if hasattr(self, 'dd_product'): # Ensure component exists
      selected_item_id = self.dd_product.selected_value

    # Corrected: This print was inside the if hasattr(self, 'dd_product') block
    print(f"CLIENT manage_product: dd_product_change - selected_item_id: {selected_item_id}")

    if selected_item_id:
      # An existing product is selected, load its details
      self.load_product_data(selected_item_id) # Calls the refactored load method
      # Ensure form is in "Update" mode visually if sw_product_action exists
      if hasattr(self, 'sw_product_action'):
        self.sw_product_action.checked = True # This might trigger its own change event
    else:
      # "Create New Product..." (or placeholder with None value) was selected
      self.reset_form_ui()
      # Ensure form is in "New" mode visually if sw_product_action exists
      if hasattr(self, 'sw_product_action'):
        self.sw_product_action.checked = False # This might trigger its own change event

    # Corrected: This print was inside the inner if hasattr(self, 'sw_product_action') block
    print("CLIENT manage_product: dd_product_change processing complete.")

    #5 dd_product_use_case_change
    def dd_product_use_case_change(self, **event_args):
      if hasattr(self, 'lbl_selected_paddle_tax_category'): # Optional display label
        selected_paddle_category = self.dd_product_use_case.selected_value
        if selected_paddle_category:
          self.lbl_selected_paddle_tax_category.text = f"Paddle Tax Category: {selected_paddle_category}"
          self.lbl_selected_paddle_tax_category.visible = True
        else:
          self.lbl_selected_paddle_tax_category.text = "Paddle Tax Category: "
          self.lbl_selected_paddle_tax_category.visible = False


          #6 load_product_data 
          def load_product_data(self, item_id_to_load):
            """Loads data for a specific item_id (product) into the form."""
            print(f"CLIENT manage_product: load_product_data called for item_id: {item_id_to_load}")

            if not item_id_to_load:
              self.reset_form_ui() # If no ID, reset to new product state
              print("CLIENT manage_product: load_product_data - no item_id_to_load provided.")
              return

              try:
                # Call the unified 'get_item' server function
                item_row = anvil.server.call('get_item', item_id_to_load)

                if item_row and item_row.get('item_type') == 'product':
                  self.current_item_row = item_row
                  self.current_product_id = item_row['item_id'] # Update current_product_id state
                  self.is_edit_mode = True
                  if hasattr(self, 'sw_product_action'):
                    self.sw_product_action.checked = True # Set switch to "Update" mode

                    self.lbl_form_title.text = f"Edit Product: {item_row.get('name', '(No Name)')}"
                    self.lbl_product_num.text = item_row['item_id']
                  self.tb_product_name.text = item_row.get('name', "")
                  self.ta_product_description.text = item_row.get('description', "") # Assumes ta_product_description
                  self.sw_product_status.checked = item_row.get('status', True) # Default to True if not present

                  # Set Tax Category Use Case Dropdown
                  stored_paddle_tax_category = item_row.get('tax_category')
                  if hasattr(self, 'dd_product_use_case'):
                    self.dd_product_use_case.selected_value = stored_paddle_tax_category
                    # Check if the value actually got set (i.e., was in the dropdown items)
                    if self.dd_product_use_case.selected_value != stored_paddle_tax_category and stored_paddle_tax_category is not None:
                      print(f"CLIENT manage_product: Warning - Loaded tax category '{stored_paddle_tax_category}' for item {item_id_to_load} was not found in dd_product_use_case items. Dropdown may show placeholder.")
                      # Optionally, you could add the missing value to items if desired, or alert user.
                      # For now, it will default to placeholder if not found.
                      self.dd_product_use_case_change() # Trigger change to update optional display label

                      # Custom Data
                      if hasattr(self, 'ta_custom_data'):
                        custom_data_val = item_row.get('custom_data')
                        if isinstance(custom_data_val, dict):
                          try:
                            self.ta_custom_data.text = json.dumps(custom_data_val, indent=2)
                          except TypeError: # Handles non-serializable dicts, though rare for SimpleObjects
                            self.ta_custom_data.text = str(custom_data_val)
                          except Exception as e_json: # Broader catch for other json errors
                            print(f"CLIENT manage_product: Error serializing custom_data: {e_json}")
                            self.ta_custom_data.text = str(custom_data_val) # Fallback
                        elif custom_data_val is not None:
                          self.ta_custom_data.text = str(custom_data_val)
                        else:
                          self.ta_custom_data.text = ""

                          # Image Display
                          if hasattr(self, 'fl_product_image'): 
                            self.fl_product_image.clear() # Clear any pending upload
                            media_row = item_row.get('media') # 'media' is a Link to 'files' table row
                          if hasattr(self, 'img_product'):
                            self.img_product.source = media_row['file'] if media_row and media_row.get('file') else None
                            if hasattr(self, 'tb_img_name'):
                              self.tb_img_name.text = media_row['name'] if media_row and media_row.get('name') else ""
                              # If you have tb_product_image_url and files table stores URL:
                              # if hasattr(self, 'tb_product_image_url'):
                              #    self.tb_product_image_url.text = media_row['img_url'] if media_row and media_row.get('img_url') else ""

                              # Enable buttons relevant for an existing product
                              self.btn_add_price.enabled = True
                  self.btn_delete.enabled = True

                  # Load associated prices for this product
                  self.load_associated_prices()
                  print(f"CLIENT manage_product: Product details loaded for item_id: {item_id_to_load}")

                else:
                  alert(f"Could not load details for ID '{item_id_to_load}'. It might not be a product or does not exist.", title="Load Error")
                  print(f"CLIENT manage_product: Item {item_id_to_load} not found or not a product.")
                  self.reset_form_ui() # Reset form if product not found or wrong type
              except Exception as e:
                alert(f"An error occurred while loading product details: {e}", title="Load Error")
                print(f"CLIENT manage_product: Exception in load_product_data for item_id {item_id_to_load} - {e}")
                # import traceback # For client-side traceback in browser console during dev
                # print(traceback.format_exc())
                self.reset_form_ui()

    #7 fl_product_image_change
    def fl_product_image_change(self, file, **event_args):
      """Display the uploaded image and file name."""
      # This function should only update the UI preview.
      # Actual file saving happens in btn_product_save_click via server call.
      if hasattr(self, 'img_product') and hasattr(self, 'tb_img_name'):
        if file:
          self.img_product.source = file
          self.tb_img_name.text = file.name if hasattr(file, "name") else "Unknown"
          # Store the file object to be passed to server on save
          # self.uploaded_file_media_object = file # We'll handle this in save
        else: # File cleared from FileLoader
          self.img_product.source = None
          self.tb_img_name.text = ""
          # self.uploaded_file_media_object = None
          # Optionally revert to saved image if editing:
          # if self.is_edit_mode and self.current_item_row and self.current_item_row.get('media'):
          #    media_row = self.current_item_row['media']
          #    self.img_product.source = media_row['file'] if media_row else None
          #    self.tb_img_name.text = media_row['name'] if media_row else ""


  #8 btn_product_save_click
  def btn_product_save_click(self, **event_args):
    """Saves the current product (item) details."""
    print("CLIENT manage_product: btn_product_save_click called") # For client-side debugging

    if not self.tb_product_name.text.strip():
      alert("Product Name is required.")
      return

    # Corrected: This block was incorrectly indented under the previous return
    selected_paddle_tax_category = None
    if hasattr(self, 'dd_product_use_case'):
      selected_paddle_tax_category = self.dd_product_use_case.selected_value
      if not selected_paddle_tax_category:
        alert("Please select a 'Use Case' for this product (this sets the tax category).")
        return
    else:
      alert("Critical Error: Tax Category UI component (dd_product_use_case) is missing from the form design.", title="UI Configuration Error")
      return

    # Corrected: This block was incorrectly indented
    item_data = {
      'name': self.tb_product_name.text.strip(),
      'description': self.ta_product_description.text.strip(), # Assumes ta_product_description exists
      'status': self.sw_product_status.checked, # Assumes sw_product_status exists
      'tax_category': selected_paddle_tax_category,
      'item_type': 'product', # Hardcoded for this form
      'media': None # Initialize, will be set if new image uploaded or existing retained
    }

    if hasattr(self, 'ta_custom_data'):
      custom_data_str = self.ta_custom_data.text.strip()
      if custom_data_str:
        try:
          item_data['custom_data'] = json.loads(custom_data_str) # Ensure json is imported
        except json.JSONDecodeError:
          alert("Custom Data is not valid JSON. Please correct it or leave it blank.")
          return
      else:
        item_data['custom_data'] = None

    # Corrected: This block was incorrectly indented
    uploaded_file_for_server = None
    # Corrected: This was defined inside the if block below
    uploaded_file_name_for_server = None 
    if hasattr(self, 'fl_product_image') and self.fl_product_image.file:
      uploaded_file_for_server = self.fl_product_image.file
      if hasattr(self, 'tb_img_name') and self.tb_img_name.text.strip():
        uploaded_file_name_for_server = self.tb_img_name.text.strip()
      else:
        # Corrected: Potential NameError if uploaded_file_for_server is None before .name
        if uploaded_file_for_server:
          uploaded_file_name_for_server = uploaded_file_for_server.name
        # else: uploaded_file_name_for_server remains None

      # Corrected: These assignments were inside the inner if block
      item_data['file_upload'] = uploaded_file_for_server
      item_data['file_upload_name'] = uploaded_file_name_for_server
      if uploaded_file_name_for_server: # Only print if a name was determined
        print(f"CLIENT manage_product: Preparing to send new image '{uploaded_file_name_for_server}'")

    elif self.is_edit_mode and self.current_item_row and self.current_item_row.get('media'):
      item_data['existing_media_link'] = self.current_item_row.get('media')
      print(f"CLIENT manage_product: Retaining existing media link for item {self.current_item_row.get('item_id')}")

    # Corrected: This try block was incorrectly indented
    try:
      print(f"CLIENT manage_product: Calling server. Edit mode: {self.is_edit_mode}. Current ID: {self.current_product_id}")
      if self.is_edit_mode and self.current_product_id:
        updated_item = anvil.server.call('update_item', self.current_product_id, item_data)
        self.current_item_row = updated_item 
        Notification("Product updated successfully.", style="success", timeout=3).show()
        print(f"CLIENT manage_product: Product {self.current_product_id} updated.")
      else:
        new_item = anvil.server.call('create_item', item_data)
        self.current_item_row = new_item
        self.current_product_id = new_item['item_id'] 
        self.is_edit_mode = True
        self.lbl_form_title.text = f"Edit Product: {new_item.get('name', '')}"
        self.lbl_product_num.text = new_item['item_id']
        if hasattr(self, 'sw_product_action'): 
          self.sw_product_action.checked = True 

        # Corrected: These were inside the sw_product_action if block
        if hasattr(self, 'btn_add_price'): 
          self.btn_add_price.enabled = True 
        if hasattr(self, 'btn_delete'): 
          self.btn_delete.enabled = True 
        self.initialize_product_lookup_dropdown() 
        if hasattr(self, 'dd_product'):
          self.dd_product.selected_value = new_item['item_id']
        # Corrected: This Notification was inside the dd_product if block
        Notification("Product created. You can now add prices.", style="success", timeout=3).show()
        print(f"CLIENT manage_product: Product {new_item['item_id']} created.")

      if self.current_product_id: # Corrected: This block was inside the else
        self.load_product_by_id(self.current_product_id) 

      if hasattr(self, 'fl_product_image'): # Corrected: This block was inside the if self.current_product_id
        self.fl_product_image.clear() 

    except anvil.server.ValidationError as e:
      alert(f"Validation Error from server: {e.err_obj if hasattr(e, 'err_obj') and e.err_obj else str(e)}", title="Save Failed")
      print(f"CLIENT manage_product: Server validation error saving product: {e}")
    except anvil.http.HttpError as e_http: 
      alert(f"Paddle API Error: {e_http.status}. MyBizz data saved, but Paddle sync failed. Check server logs or try saving again.", title="Paddle Sync Error")
      print(f"CLIENT manage_product: Paddle API HttpError saving product: {e_http}")
    except Exception as e:
      alert(f"An error occurred while saving the product: {e}", title="Save Error")
      print(f"CLIENT manage_product: General error saving product: {e}")
      # For detailed client-side trace during development:
      # import traceback
      # print(traceback.format_exc())


  #9 load_associated_prices
  def load_associated_prices(self, **event_args): # Can be called by event (e.g., x_refresh_item_prices) or directly
    """
                                        Loads prices linked to the self.current_item_row (product)
                                        into the rp_prices RepeatingPanel.
                                        """
    print("CLIENT manage_product: load_associated_prices called")

    if hasattr(self, 'rp_prices'): # Ensure rp_prices component exists
      if self.current_item_row and self.current_item_row.get('item_id'):
        current_item_id = self.current_item_row['item_id']
        print(f"CLIENT manage_product: Fetching prices for item_id: {current_item_id}")
        try:
          # Calls 'list_prices_for_item' from sm_pricing_mod.py
          prices_list = anvil.server.call('list_prices_for_item', current_item_id)
          self.rp_prices.items = prices_list
          print(f"CLIENT manage_product: rp_prices populated with {len(prices_list)} prices.")
        except Exception as e:
          alert(f"Error loading prices for this product: {e}", title="Price Load Error")
          print(f"CLIENT manage_product: Error in load_associated_prices for item {current_item_id}: {e}")
          self.rp_prices.items = []
      else:
        # No current product loaded, so clear the prices list
        self.rp_prices.items = []
        print("CLIENT manage_product: load_associated_prices - No current_item_row, rp_prices cleared.")
    else:
      print("CLIENT manage_product: WARNING - rp_prices RepeatingPanel not found on form design.")  


  #10 btn_add_price_click
  def btn_add_price_click(self, **event_args):
    """
                                        Opens the manage_price_form to add a new price for the current product.
                                        """
    print("CLIENT manage_product: btn_add_price_click called")

    if not self.current_item_row or not self.current_item_row.get('item_id'):
      alert("Please save or load a product before adding prices.", title="Action Required")
      print("CLIENT manage_product: btn_add_price_click - No current_item_row to add price to.")
      return

    # For products (and services), the price_type_context is 'one_time'
    # self.current_item_row is the Anvil Row object of the parent item
    print(f"CLIENT manage_product: Opening manage_price_form to create new 'one_time' price for item: {self.current_item_row['item_id']}")
    result = alert(
      content=manage_price_form(item_row=self.current_item_row, 
                                price_to_edit=None, 
                                price_type_context='one_time'),
      title="Add New Price for Product",
      large=True,
      buttons=[] # Buttons are defined on manage_price_form itself
    )

    if result is True: # manage_price_form raises x-close-alert with value=True on successful save
      print("CLIENT manage_product: manage_price_form reported successful save. Refreshing prices.")
      self.load_associated_prices() # Refresh the list of prices
    else:
      print("CLIENT manage_product: manage_price_form closed without save or with cancel.")


  #11 edit_item_price_handler
  def edit_item_price_handler(self, price_item_to_edit, **event_args):
    """
                                                Handles the 'x_edit_item_price' event raised by price_list_item_form.
                                                Opens manage_price_form in edit mode for the selected price.
                
                                                Args:
                                                                price_item_to_edit (anvil.tables.Row): The 'prices' table row to be edited.
                                                """
    print(f"CLIENT manage_product: edit_item_price_handler called for price_id: {price_item_to_edit['price_id'] if price_item_to_edit and isinstance(price_item_to_edit, tables.Row) else 'None'}") # Added type check
    if not self.current_item_row: # Parent item context
      alert("Error: No parent product is currently loaded. Cannot edit price.", title="Context Error")
      print("CLIENT manage_product: edit_item_price_handler - current_item_row is None.")
      return

    # Corrected: This block was incorrectly indented
    if not price_item_to_edit or not isinstance(price_item_to_edit, tables.Row): # Check if it's a Row
      alert("Error: Invalid price data received for editing.", title="Internal Error")
      print("CLIENT manage_product: edit_item_price_handler - price_item_to_edit is invalid or not a Row.")
      return

    # Corrected: This block was incorrectly indented
    # Determine price_type from the price_item_to_edit itself
    price_type_ctx = price_item_to_edit.get('price_type', 'one_time') # Default if not set on price row

    print(f"CLIENT manage_product: Opening manage_price_form to edit price_id: {price_item_to_edit['price_id']} for item: {self.current_item_row['item_id']}")
    result = alert(
      content=manage_price_form(item_row=self.current_item_row, 
                                price_to_edit=price_item_to_edit, 
                                price_type_context=price_type_ctx),
      title="Edit Price",
      large=True,
      buttons=[] # Buttons are defined on manage_price_form itself
    )

    if result is True: # manage_price_form raises x-close-alert with value=True on successful save
      print("CLIENT manage_product: manage_price_form reported successful save. Refreshing prices.")
      self.load_associated_prices() # Refresh the list of prices
    else:
      print("CLIENT manage_product: manage_price_form closed without save or with cancel.")         


  #12 btn_reset_click
  def btn_reset_click(self, **event_args):
    """Reset all form fields to default values."""
    self.reset_form_ui()
    self.initialize_product_lookup_dropdown() # Also refresh dropdown


  #13 btn_delete_click
  def btn_delete_click(self, **event_args):
    """
                                        Deletes the current item (product) from the MyBizz database
                                        after confirmation. Also attempts to handle Paddle archival via server.
                                        """
    print("CLIENT manage_product: btn_delete_click called")

    if self.current_product_id and self.is_edit_mode: # Ensure a product is loaded and in edit mode
      # Fetch the item name again for the confirmation message,
      # as the textbox might have unsaved changes.
      # self.current_item_row should be populated if self.current_product_id is set.
      name_for_confirm = self.current_item_row.get('name', 'this product') if self.current_item_row else 'this product'

      confirmation_message = (
        f"Are you sure you want to delete the product '{name_for_confirm}' (ID: {self.current_product_id})?\n\n"
        "This action will also attempt to:\n"
        "  - Delete any associated MyBizz prices for this product (if not in use by subscriptions).\n"
        "  - Archive the corresponding Product in Paddle (if synced).\n\n"
        "This action CANNOT be undone if there are no active customer subscriptions linked to its prices. "
        "If active subscriptions exist, deletion of associated prices might be prevented."
      )

      # Corrected: confirm() returns the button text, not a boolean directly unless buttons are (text, value)
      if confirm(confirmation_message, title="Confirm Product Deletion", buttons=[("Cancel", False), ("DELETE PRODUCT", True)]): # Or check string "DELETE PRODUCT"
        print(f"CLIENT manage_product: User confirmed deletion for item_id: {self.current_product_id}")
        try:
          # Call the unified 'delete_item' server function from sm_item_mod.py
          # This server function should handle dependency checks (prices, active subscriptions via prices)
          # and attempt Paddle Product archival before deleting from MyBizz.
          anvil.server.call('delete_item', self.current_product_id)

          Notification("Product deleted successfully.", style="success", timeout=3).show()
          print(f"CLIENT manage_product: Product {self.current_product_id} reported as deleted by server.")

          # Reset the form to a clean state for new product entry
          self.reset_form_ui()
          # Refresh the product lookup dropdown as the item is now gone
          self.initialize_product_lookup_dropdown()

        except anvil.server.PermissionDenied as e:
          alert(f"Permission Denied: {e}", title="Deletion Failed")
          print(f"CLIENT manage_product: Permission denied deleting item {self.current_product_id}: {e}")
        except Exception as e:
          # Catch specific errors from server if possible, or display generic
          alert(f"Error deleting product: {e}", title="Deletion Failed")
          print(f"CLIENT manage_product: Error deleting item {self.current_product_id}: {e}")
      else:
        print(f"CLIENT manage_product: User cancelled deletion for item_id: {self.current_product_id}")
    else:
      alert("No product is currently loaded or selected to delete.", title="Action Error")
      print("CLIENT manage_product: btn_delete_click - No current_product_id or not in edit mode.")                

  #14 btn_home_click
  def btn_home_click(self, **event_args):
    """This method is called when the button is clicked"""
    open_form('paddle_home')          