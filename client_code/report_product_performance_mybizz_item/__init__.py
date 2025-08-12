# Client Module: report_product_performance_mybizz_item.py

from ._anvil_designer import report_product_performance_mybizz_itemTemplate # Ensure this matches your template's class name
from anvil import *
import anvil.server

class report_product_performance_mybizz_item(report_product_performance_mybizz_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item is a dictionary for a single product, 
    # with keys like: item_name, total_revenue, units_sold, customer_count, arpu
    if self.item:
      # Uses the renamed UI component 'lbl_product_name' and the standardized data key 'item_name'
      self.lbl_product_name.text = self.item.get('item_name', 'N/A') 

      total_revenue_minor_units = self.item.get('total_revenue', 0) # Expecting minor units
      # Assuming system currency symbol needs to be dynamically fetched or is known
      # For now, we will format as a number and assume the currency symbol is handled by context or a global setting if needed.
      # The server sends amounts in minor units of the system currency.
      self.lbl_total_revenue.text = f"{(total_revenue_minor_units / 100.0):,.2f}" if total_revenue_minor_units is not None else "0.00"

      self.lbl_units_sold.text = f"{self.item.get('units_sold', 0):,}"
      self.lbl_customer_count.text = f"{self.item.get('customer_count', 0):,}"

      arpu_minor_units = self.item.get('arpu', 0) # Expecting minor units
      self.lbl_arpu.text = f"{(arpu_minor_units / 100.0):,.2f}" if arpu_minor_units is not None else "0.00"
    else:
      # Handle case where item is None
      self.lbl_product_name.text = "No Data" # Use the new component name
      self.lbl_total_revenue.text = "0.00"
      self.lbl_units_sold.text = "0"
      self.lbl_customer_count.text = "0"
      self.lbl_arpu.text = "0.00"