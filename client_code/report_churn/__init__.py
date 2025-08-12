from ._anvil_designer import report_churnTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go
from datetime import datetime
import math # For parsing periods

class report_churn(report_churnTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run when the form opens.

        # --- Initialize Filters ---
        self.dd_period_type.items = ["Monthly", "Quarterly"]
        self.dd_period_type.selected_value = "Monthly" # Default

        self.dd_periods.items = ["Last 3 Periods", "Last 6 Periods", "Last 12 Periods"]
        self.dd_periods.selected_value = "Last 12 Periods" # Default

        # --- Load Initial Data ---
        self.load_report_data()

    def load_report_data(self, **event_args):
        """Loads data from the server and updates the report components."""
        period_type = self.dd_period_type.selected_value.lower() if self.dd_period_type.selected_value else "monthly"

        periods_str = self.dd_periods.selected_value or "Last 12 Periods"
        try:
            # Extract the number from "Last X Periods"
            periods = int(periods_str.split()[-2]) # Get the number before "Periods"
        except (ValueError, IndexError):
            periods = 12 # Default to 12 if parsing fails

        try:
            # Show loading indicator
            self.btn_refresh.enabled = False
            self.btn_refresh.icon = 'fa:spinner'
            self.btn_refresh.text = 'Loading...'

            # Call the server function
            report_data = anvil.server.call('get_customer_churn_data', period_type=period_type, periods=periods)

            # --- Update Summary Labels (use data from the last period) ---
            if report_data:
                latest_period_data = report_data[-1] # Data is ordered oldest to newest
                self.lbl_current_churn_rate.text = f"{latest_period_data.get('churn_rate_percent', 0):.2f}%"
                self.lbl_starting_customers.text = f"{latest_period_data.get('starting_customers', 0):,}"
                self.lbl_canceled_customers.text = f"{latest_period_data.get('canceled_customers', 0):,}"
            else:
                self.lbl_current_churn_rate.text = "0.00%"
                self.lbl_starting_customers.text = "0"
                self.lbl_canceled_customers.text = "0"

            # --- Update Plot ---
            if report_data:
                periods_labels = [d['period'] for d in report_data]
                churn_rate_values = [d['churn_rate_percent'] for d in report_data]

                # Create plot trace
                trace_churn = go.Scatter(
                    x=periods_labels,
                    y=churn_rate_values,
                    mode='lines+markers',
                    name='Churn Rate (%)'
                )

                # Define layout
                layout = go.Layout(
                    title='Customer Churn Rate Trend',
                    yaxis=dict(
                        title='Churn Rate (%)',
                        ticksuffix='%' # Add percent sign to y-axis ticks
                    ),
                    legend=dict(x=0.1, y=1.1, orientation="h"),
                    margin=dict(l=60, r=60, t=80, b=80) # Adjust margins as needed
                )

                self.plt_churn_trend.data = [trace_churn]
                self.plt_churn_trend.layout = layout

            else:
                # Clear plot if no data
                self.plt_churn_trend.data = []
                self.plt_churn_trend.layout = go.Layout(title='Customer Churn Rate Trend (No data available)')

        except Exception as e:
            alert(f"An error occurred while loading the report: {e}")
            # Clear components on error
            self.lbl_current_churn_rate.text = "Error"
            self.lbl_starting_customers.text = "Error"
            self.lbl_canceled_customers.text = "Error"
            self.plt_churn_trend.data = []
            self.plt_churn_trend.layout = go.Layout(title='Customer Churn Rate Trend (Error loading data)')

        finally:
            # Hide loading indicator
            self.btn_refresh.enabled = True
            self.btn_refresh.icon = 'fa:refresh'
            self.btn_refresh.text = 'Refresh'


    def btn_refresh_click(self, **event_args):
        """This method is called when the button is clicked"""
        self.load_report_data()

    def dd_period_type_change(self, **event_args):
        """This method is called when an item is selected"""
        self.load_report_data()

    def dd_periods_change(self, **event_args):
        """This method is called when an item is selected"""
        self.load_report_data()

   

 

  

