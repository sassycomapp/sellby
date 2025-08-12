# Client Module: report_service_performance_mybizz_item.py

from ._anvil_designer import report_service_performance_mybizz_itemTemplate
from anvil import *
import anvil.server

class report_service_performance_mybizz_item(report_service_performance_mybizz_itemTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # self.item is a dictionary for a single service, 
    # with keys like: item_name, total_revenue, units_sold, customer_count, arpu
    if self.item:
      # Uses the standardized data key 'item_name'
      self.lbl_service_name.text = self.item.get('item_name', 'N/A')

      total_revenue_minor_units = self.item.get('total_revenue', 0) # Expecting minor units
      # Server sends amounts in minor units of the system currency.
      self.lbl_total_revenue.text = f"{(total_revenue_minor_units / 100.0):,.2f}" if total_revenue_minor_units is not None else "0.00"

      self.lbl_units_sold.text = f"{self.item.get('units_sold', 0):,}"
      self.lbl_customer_count.text = f"{self.item.get('customer_count', 0):,}"

      arpu_minor_units = self.item.get('arpu', 0) # Expecting minor units
      self.lbl_arpu.text = f"{(arpu_minor_units / 100.0):,.2f}" if arpu_minor_units is not None else "0.00"
    else:
      # Handle case where item is None
      self.lbl_service_name.text = "No Data"
      self.lbl_total_revenue.text = "0.00"
      self.lbl_units_sold.text = "0"
      self.lbl_customer_count.text = "0"
      self.lbl_arpu.text = "0.00"