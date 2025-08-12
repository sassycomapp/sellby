# Client Module: template_rp_subs_matrix.py
# Item Template for displaying one Tier row in the subscription price matrix.

from ._anvil_designer import template_rp_subs_matrixTemplate
from anvil import *
import anvil.server

class template_rp_subs_matrix(template_rp_subs_matrixTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item is automatically set by the parent RepeatingPanel (rp_subs_matrix).
    # It's expected to be a dictionary for one tier, structured like:
    # {
    #   'tier_name_display': "Tier Name", 'tier_num_identifier': "T1",
    #   'l1_level_name_display': "L1 Name", 'l1_price_display': "$0.00", 
    #   'l1_item_id': "item_id_l1t1", 'l1_is_paid': False,
    #   'l2_level_name_display': "L2 Name", 'l2_price_display': "$10.00", 
    #   'l2_item_id': "item_id_l2t1", 'l2_is_paid': True,
    #   ... and so on for l3 ...
    # }

    if self.item:
      # Populate Tier Name
      self.lbl_tier.text = self.item.get('tier_name_display', "N/A")

      # Populate Level 1 Info
      self.lbl_l1_price.text = self.item.get('l1_price_display', "Not Set")
      self.btn_edit_l1_price.visible = self.item.get('l1_is_paid', False)
      # Store item_id and is_paid status on the button itself for easy access in click handler
      self.btn_edit_l1_price.tag.item_id = self.item.get('l1_item_id')
      self.btn_edit_l1_price.tag.is_paid = self.item.get('l1_is_paid', False)
      self.btn_edit_l1_price.tag.level_name = self.item.get('l1_level_name_display')
      self.btn_edit_l1_price.tag.tier_name = self.item.get('tier_name_display')


      # Populate Level 2 Info
      self.lbl_l2_price.text = self.item.get('l2_price_display', "Not Set")
      self.btn_edit_l2_price.visible = self.item.get('l2_is_paid', False)
      self.btn_edit_l2_price.tag.item_id = self.item.get('l2_item_id')
      self.btn_edit_l2_price.tag.is_paid = self.item.get('l2_is_paid', False)
      self.btn_edit_l2_price.tag.level_name = self.item.get('l2_level_name_display')
      self.btn_edit_l2_price.tag.tier_name = self.item.get('tier_name_display')

      # Populate Level 3 Info
      self.lbl_l3_price.text = self.item.get('l3_price_display', "Not Set")
      self.btn_edit_l3_price.visible = self.item.get('l3_is_paid', False)
      self.btn_edit_l3_price.tag.item_id = self.item.get('l3_item_id')
      self.btn_edit_l3_price.tag.is_paid = self.item.get('l3_is_paid', False)
      self.btn_edit_l3_price.tag.level_name = self.item.get('l3_level_name_display')
      self.btn_edit_l3_price.tag.tier_name = self.item.get('tier_name_display')

    else:
      # Handle case where item is None (e.g., empty repeating panel)
      self.lbl_tier.text = "No Tier Data"
      self.lbl_l1_price.text = ""
      self.btn_edit_l1_price.visible = False
      self.lbl_l2_price.text = ""
      self.btn_edit_l2_price.visible = False
      self.lbl_l3_price.text = ""
      self.btn_edit_l3_price.visible = False

    # --- Event Handlers for Edit Buttons ---
    # We can use one generic handler if we store data on the buttons,
    # or create separate handlers for each. Let's use one generic one.

    def edit_price_button_clicked(self, sender_button, **event_args):
      """Generic handler for any of the 'Edit Price' buttons."""
      item_id_to_edit = sender_button.tag.get('item_id')
      is_paid_status = sender_button.tag.get('is_paid')
      # level_name = sender_button.tag.get('level_name') # For context if needed
      # tier_name = sender_button.tag.get('tier_name')   # For context if needed

      if not item_id_to_edit:
        alert("Cannot edit price: Plan item identifier is missing.", title="Error")
        print("CLIENT template_rp_subs_matrix: item_id missing from button tag.")
        return

        if not is_paid_status: # Double check, though button should be hidden
          alert("This plan variation is free and does not have an editable price.", title="Information")
          print("CLIENT template_rp_subs_matrix: Edit clicked for a non-paid plan.")
          return

      # Raise an event to be handled by the parent form (manage_subs.py)
      # Pass a dictionary with the necessary data
      plan_item_data_for_edit = {
        'item_id': item_id_to_edit,
        'is_paid': is_paid_status
        # Optionally pass level_name, tier_name if manage_subs needs them for the dialog title
      }
      self.parent.raise_event('x_edit_plan_price', plan_item_data=plan_item_data_for_edit)
      print(f"CLIENT template_rp_subs_matrix: x_edit_plan_price event raised for item_id: {item_id_to_edit}")


  def btn_edit_l1_price_click(self, **event_args):
    """This method is called when btn_edit_l1_price is clicked."""
    self.edit_price_button_clicked(self.btn_edit_l1_price, **event_args)

    def btn_edit_l2_price_click(self, **event_args):
      """This method is called when btn_edit_l2_price is clicked."""
      self.edit_price_button_clicked(self.btn_edit_l2_price, **event_args)

  def btn_edit_l3_price_click(self, **event_args):
    """This method is called when btn_edit_l3_price is clicked."""
    self.edit_price_button_clicked(self.btn_edit_l3_price, **event_args)