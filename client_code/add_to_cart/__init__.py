from ._anvil_designer import AddToCartTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

#TODO: figure out why button in FlowPanel moves

class AddToCart(AddToCartTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)


  def add_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.quantity_box.text:
      get_open_form().add_to_cart(self.item, self.quantity_box.text)
      self.quantity_box.text = ""
      self.add_button.visible = False
      self.added_button.visible = True
      self.timer_1.interval = 1
    else:
        self.quantity_box.text = ""
        Notification("Please specify a quantity").show()

        
  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    self.add_button.visible = True
    self.added_button.visible = False
    self.timer_1.interval = 0