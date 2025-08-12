from ._anvil_designer import HomeTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

from ..product import Product

class Home(HomeTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    best_sellers = app_tables.products.search(best_seller=True)
    
    self.banner.role = ['spaced-title', 'left-right-padding']
    
    for p in best_sellers:
      self.flow_panel_1.add_component(Product(item=p), width='30%')


  def shop_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    get_open_form().shop_link_click()