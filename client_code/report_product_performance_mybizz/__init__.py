# Client Module: report_product_performance_mybizz.py

from ._anvil_designer import report_product_performance_mybizzTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go
# Import the new item template
from ..report_product_performance_mybizz_item import report_product_performance_mybizz_item # Adjust path if needed

class report_product_performance_mybizz(report_product_performance_mybizzTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Set the item template for the RepeatingPanel
    self.rp_product_performance_mybizz.item_template = report_product_performance_mybizz_item # MODIFIED HERE

    self.load_report_data()

  def load_report_data(self, **event_args):
    """Loads data from the server and updates the report components."""
    try:
      # Show loading state
      self.btn_refresh.enabled = False
      self.btn_refresh.icon = 'fa:spinner'
      self.btn_refresh.text = 'Loading...'

      # Call the server function (from reports_server.py)
      # This function returns a list of dictionaries for products
      report_data = anvil.server.call('get_mybizz_product_performance_data')

      # --- Update RepeatingPanel ---
      self.rp_product_performance_mybizz.items = report_data # MODIFIED HERE

      # --- Update Plot ---
      if report_data:
        # Sort data by revenue for plotting, if desired
        plot_data = sorted(report_data, key=lambda x: x.get('total_revenue', 0), reverse=True)
        product_names = [d.get('product_name', 'Unknown') for d in plot_data]
        revenue_values = [d.get('total_revenue', 0) for d in plot_data]

        self.plt_product_revenue.data = [
          go.Bar(
            x=product_names,
            y=revenue_values,
            name='Total Revenue'
          )
        ]
        self.plt_product_revenue.layout = go.Layout(
          title='Revenue by Product (MyBizz View)',
          yaxis=dict(title='Total Revenue ($)'),
          xaxis=dict(title='Product Name'),
          bargap=0.2 
        )
      else:
        # Clear plot if no data
        self.plt_product_revenue.data = []
        self.plt_product_revenue.layout = go.Layout(title='Revenue by Product (MyBizz View - No data available)')

    except Exception as e:
      alert(f"An error occurred while loading the report: {e}")
      # Clear components on error
      self.rp_product_performance_mybizz.items = [] # MODIFIED HERE
      self.plt_product_revenue.data = []
      self.plt_product_revenue.layout = go.Layout(title='Revenue by Product (MyBizz View - Error loading data)')

    finally:
      # Reset loading state
      self.btn_refresh.enabled = True
      self.btn_refresh.icon = 'fa:refresh'
      self.btn_refresh.text = 'Refresh'

  def btn_refresh_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.load_report_data()