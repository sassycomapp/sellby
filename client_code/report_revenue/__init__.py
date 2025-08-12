from ._anvil_designer import report_revenueTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go
from datetime import datetime # Keep for type hinting if used, though not directly used in this version

class report_revenue(report_revenueTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.system_currency_code = "USD" # Default, will be updated

    # --- Initialize Filters ---
    self.dd_period_type.items = ["Month", "Quarter"]
    self.dd_period_type.selected_value = "Month"

    self.dd_periods.items = ["Last 12", "Last 6", "Last 3"]
    self.dd_periods.selected_value = "Last 12"

    # --- Load Initial Data ---
    self.load_report_data()

  def load_report_data(self, **event_args):
    """Loads data from the server and updates the report components."""
    period_type = self.dd_period_type.selected_value.lower() if self.dd_period_type.selected_value else "month"

    periods_str = self.dd_periods.selected_value or "Last 12"
    try:
      # Extract the number from "Last X"
      periods = int(periods_str.split()[-1])
    except (ValueError, IndexError):
      periods = 12 # Default to 12 if parsing fails

    try:
      # Show loading indicator
      self.btn_refresh.enabled = False
      self.btn_refresh.icon = 'fa:spinner'
      self.btn_refresh.text = 'Loading...'

      # Fetch system currency
      try:
        currency_setting = anvil.server.call('get_system_currency') # Assumes this returns {'currency': 'USD'} or similar
        if currency_setting and currency_setting.get('currency'):
          self.system_currency_code = currency_setting.get('currency')
        else:
          self.system_currency_code = "N/A" # Fallback if not set
          alert("System currency is not set. Monetary values may not be accurately represented.", title="Configuration Warning")
      except Exception as e_curr:
        print(f"Error fetching system currency: {e_curr}")
        self.system_currency_code = "ERR" # Indicate error in currency display
        alert(f"Could not fetch system currency: {e_curr}", title="Configuration Error")


        # Call the server function
      report_data = anvil.server.call('get_revenue_sales_trend_data', period_type=period_type, periods=periods)

      # --- Update Summary Labels (use data from the last period) ---
      if report_data:
        latest_period_data = report_data[-1] # Data is ordered oldest to newest
        self.lbl_total_revenue.text = f"${latest_period_data.get('total_revenue', 0):,.2f} ({self.system_currency_code})"
        self.lbl_num_transactions.text = f"{latest_period_data.get('num_transactions', 0):,}"
        self.lbl_avg_transaction_value.text = f"${latest_period_data.get('avg_transaction_value', 0):,.2f} ({self.system_currency_code})"
      else:
        self.lbl_total_revenue.text = f"$0.00 ({self.system_currency_code})"
        self.lbl_num_transactions.text = "0"
        self.lbl_avg_transaction_value.text = f"$0.00 ({self.system_currency_code})"

        # --- Update Plot ---
      if report_data:
        periods_labels = [d['period'] for d in report_data]
        revenue_values = [d['total_revenue'] for d in report_data]
        transactions_values = [d['num_transactions'] for d in report_data]
        avg_value_values = [d['avg_transaction_value'] for d in report_data]

        # Create plot traces
        trace_revenue = go.Scatter(
          x=periods_labels,
          y=revenue_values,
          mode='lines+markers',
          name=f'Total Revenue ({self.system_currency_code})',
          yaxis='y1' 
        )
        trace_transactions = go.Scatter(
          x=periods_labels,
          y=transactions_values,
          mode='lines+markers',
          name='Transactions',
          yaxis='y2' 
        )
        trace_avg_value = go.Scatter(
          x=periods_labels,
          y=avg_value_values,
          mode='lines+markers',
          name=f'Avg Value ({self.system_currency_code})',
          yaxis='y1' 
        )

        # Define layout with dual y-axes
        layout = go.Layout(
          title=f'Revenue & Sales Trends ({self.system_currency_code})',
          yaxis=dict(
            title=f'Revenue / Avg Value ({self.system_currency_code})',
            titlefont=dict(color='#1f77b4'),
            tickfont=dict(color='#1f77b4')
          ),
          yaxis2=dict(
            title='Number of Transactions',
            titlefont=dict(color='#ff7f0e'),
            tickfont=dict(color='#ff7f0e'),
            overlaying='y',
            side='right',
            showgrid=False 
          ),
          legend=dict(x=0.1, y=1.1, orientation="h"),
          margin=dict(l=60, r=60, t=80, b=80) 
        )

        self.plt_revenue_trend.data = [trace_revenue, trace_avg_value, trace_transactions]
        self.plt_revenue_trend.layout = layout

      else:
        # Clear plot if no data
        self.plt_revenue_trend.data = []
        self.plt_revenue_trend.layout = go.Layout(title=f'Revenue & Sales Trends ({self.system_currency_code} - No data available)')

    except Exception as e:
      alert(f"An error occurred while loading the report: {e}")
      # Clear components on error
      self.lbl_total_revenue.text = f"Error ({self.system_currency_code})"
      self.lbl_num_transactions.text = "Error"
      self.lbl_avg_transaction_value.text = f"Error ({self.system_currency_code})"
      self.plt_revenue_trend.data = []
      self.plt_revenue_trend.layout = go.Layout(title=f'Revenue & Sales Trends ({self.system_currency_code} - Error loading data)')

    finally:
      # Reset loading state
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

