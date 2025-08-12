# Client ItemTemplate Form: permission_assignment_item_form.py
# Used in rp_permissions_for_role on manage_rbac.py

from ._anvil_designer import permission_assignment_item_formTemplate
from anvil import *
# import anvil.server # Not needed
# from ..cm_logs_helper import log # Optional: if you need specific logging

class permission_assignment_item_form(permission_assignment_item_formTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # self.module_name = "permission_assignment_item_form" # For logging if used

    # self.item is a dictionary passed by the RepeatingPanel, containing:
    # 'permission_id_anvil': Anvil's internal row ID for the permission
    # 'permission_id_mybizz': Your custom unique ID for the permission
    # 'name': Permission unique key (e.g., "manage_users")
    # 'description': User-friendly description of the permission
    # 'category': Permission category
    # 'is_assigned': Boolean, indicating if this permission is currently assigned to the selected role

    if self.item:
      permission_name = self.item.get('name', "Unknown Permission")
      permission_description = self.item.get('description', "No description available.")
      permission_category = self.item.get('category', "General")
      is_assigned_to_role = self.item.get('is_assigned', False)

      # Set the checkbox text to the permission name (the unique key)
      self.chk_assign_permission.text = permission_name
      # Set the checkbox state
      self.chk_assign_permission.checked = is_assigned_to_role

      # Display the user-friendly description and category
      self.lbl_item_permission_description.text = permission_description
      self.lbl_item_permission_category.text = f"Category: {permission_category}"

      # Tooltip for checkbox can show description for more context on hover
      self.chk_assign_permission.tooltip = permission_description

    else:
      # Fallback if item is None
      self.chk_assign_permission.text = "No Permission Data"
      self.chk_assign_permission.checked = False
      self.chk_assign_permission.enabled = False # Disable if no data
      self.lbl_item_permission_description.text = ""
      self.lbl_item_permission_category.text = ""

    # No event handlers needed in this item template itself if the parent form
    # iterates through get_components() to check checkbox states upon a main "Save" button click.
    # If you wanted immediate server calls on checkbox change (not recommended for many checkboxes),
    # you would add a change event handler for chk_assign_permission here.
    # For now, we assume the parent form (manage_rbac.py) will handle saving all assignments at once.