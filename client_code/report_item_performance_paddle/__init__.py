from ._anvil_designer import report_item_performance_paddleTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go

class report_item_performance_paddle(report_item_performance_paddleTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run when the form opens.
        self.load_report_data()

    def load_report_data(self, **event_args):
        """Loads data from the server and updates the report components."""
        try:
            # Show loading state
            self.btn_refresh.enabled = False
            self.btn_refresh.icon = 'fa:spinner'
            self.btn_refresh.text = 'Loading...'

            # Call the server function
            report_data = anvil.server.call('get_paddle_item_performance_data')

            # --- Update DataGrid ---
            self.dg_item_performance.columns = [
                {"id": "product_name", "title": "Item Name", "data_key": "product_name"}, # Using 'product_name' as the unified item name
                {"id": "total_revenue", "title": "Total Revenue", "data_key": "total_revenue", "format": "$%,.2f"},
                {"id": "units_sold", "title": "Units Sold", "data_key": "units_sold"},
                {"id": "customer_count", "title": "Customer Count", "data_key": "customer_count"},
                {"id": "arpu", "title": "ARPU", "data_key": "arpu", "format": "$%,.2f"}
            ]
            self.dg_item_performance.items = report_data

            # --- Update Plot ---
            if report_data:
                # Sort data by revenue for plotting, if desired
                plot_data = sorted(report_data, key=lambda x: x.get('total_revenue', 0), reverse=True)
                item_names = [d.get('product_name', 'Unknown') for d in plot_data]
                revenue_values = [d.get('total_revenue', 0) for d in plot_data]

                self.plt_item_revenue.data = [
                    go.Bar(
                        x=item_names,
                        y=revenue_values,
                        name='Total Revenue'
                    )
                ]
                self.plt_item_revenue.layout = go.Layout(
                    title='Revenue by Item (Paddle Combined View)',
                    yaxis=dict(title='Total Revenue ($)'),
                    xaxis=dict(title='Item Name'),
                    bargap=0.2 # Adjust gap between bars
                )
            else:
                # Clear plot if no data
                self.plt_item_revenue.data = []
                self.plt_item_revenue.layout = go.Layout(title='Revenue by Item (Paddle Combined View - No data available)')

        except Exception as e:
            alert(f"An error occurred while loading the report: {e}")
            # Clear components on error
            self.dg_item_performance.items = []
            self.plt_item_revenue.data = []
            self.plt_item_revenue.layout = go.Layout(title='Revenue by Item (Paddle Combined View - Error loading data)')

        finally:
            # Reset loading state
            self.btn_refresh.enabled = True
            self.btn_refresh.icon = 'fa:refresh'
            self.btn_refresh.text = 'Refresh'

    def btn_refresh_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.load_report_data()