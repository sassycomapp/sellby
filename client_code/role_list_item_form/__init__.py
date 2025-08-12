from ._anvil_designer import role_list_item_formTemplate
from anvil import *

class role_list_item_form(role_list_item_formTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    print(f"DEBUG - role_list_item_form - __init__ - Item: {self.item}") # Log item on init

    if self.item:
      self.lbl_item_role_name.text = self.item.get('name', "Unknown Role")
      self.lbl_item_role_description.text = self.item.get('description', "No description.")

      is_system = self.item.get('is_system_role', False)
      self.lbl_item_is_system.visible = is_system

      if is_system:
        self.lbl_item_is_system.text = "(System Role)" # Simplified text
        self.btn_item_delete_role.visible = False
        self.btn_item_edit_role.visible = False # Edit button NOT visible for system roles
      else: # Custom role
        self.btn_item_delete_role.visible = True
        self.btn_item_delete_role.enabled = True
        self.btn_item_edit_role.visible = True  # Edit button IS visible for custom roles
        self.btn_item_edit_role.enabled = True
    else:
      self.lbl_item_role_name.text = "No Role Data"
      self.lbl_item_role_description.text = ""
      self.lbl_item_is_system.visible = False
      self.btn_item_edit_role.visible = False
      self.btn_item_delete_role.visible = False

    # Ensure event handler is set if button is visible and enabled
    if self.btn_item_edit_role.visible and self.btn_item_edit_role.enabled:
      self.btn_item_edit_role.set_event_handler('click', self.btn_item_edit_role_click_handler_test)
    if self.btn_item_delete_role.visible and self.btn_item_delete_role.enabled:
      self.btn_item_delete_role.set_event_handler('click', self.btn_item_delete_role_click_handler_test)


  # Using a slightly different name for the handler method for this test
  def btn_item_edit_role_click_handler_test(self, **event_args):
    print(f"DEBUG - role_list_item_form - HANDLER TEST - Edit clicked for item: {self.item.get('name') if self.item else 'NO ITEM'}")
    if self.item:
      self.parent.raise_event('x-edit-role', role_data_dict=self.item)

  # Using a slightly different name for the handler method for this test
  def btn_item_delete_role_click_handler_test(self, **event_args):
    print(f"DEBUG - role_list_item_form - HANDLER TEST - Delete clicked for item: {self.item.get('name') if self.item else 'NO ITEM'}")
    if self.item and not self.item.get('is_system_role', False):
      self.parent.raise_event('x-delete-role', role_data_dict=self.item)