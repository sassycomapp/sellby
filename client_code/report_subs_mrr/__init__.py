from ._anvil_designer import report_subs_mrrTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go
from datetime import datetime # Keep for type hinting if used
import math # For parsing periods

class report_subs_mrr(report_subs_mrrTemplate):
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
        currency_setting = anvil.server.call('get_system_currency') 
        if currency_setting and currency_setting.get('currency'):
          self.system_currency_code = currency_setting.get('currency')
        else:
          self.system_currency_code = "N/A" 
          alert("System currency is not set. Monetary values may not be accurately represented.", title="Configuration Warning")
      except Exception as e_curr:
        print(f"Error fetching system currency: {e_curr}")
        self.system_currency_code = "ERR"
        alert(f"Could not fetch system currency: {e_curr}", title="Configuration Error")

        # Call the server function
      report_data = anvil.server.call('get_subscription_mrr_data', period_type=period_type, periods=periods)

      # --- Update Summary Labels (use data from the last period) ---
      if report_data:
        latest_period_data = report_data[-1] 
        self.lbl_active_subs.text = f"{latest_period_data.get('active_subscriptions', 0):,}"
        self.lbl_estimated_mrr.text = f"${latest_period_data.get('estimated_mrr', 0):,.2f} ({self.system_currency_code})"
        self.lbl_new_mrr.text = f"${latest_period_data.get('new_mrr', 0):,.2f} ({self.system_currency_code})"
        self.lbl_churn_mrr.text = f"${latest_period_data.get('churn_mrr', 0):,.2f} ({self.system_currency_code})"
      else:
        self.lbl_active_subs.text = "0"
        self.lbl_estimated_mrr.text = f"$0.00 ({self.system_currency_code})"
        self.lbl_new_mrr.text = f"$0.00 ({self.system_currency_code})"
        self.lbl_churn_mrr.text = f"$0.00 ({self.system_currency_code})"

        # --- Update Plot ---
      if report_data:
        periods_labels = [d['period'] for d in report_data]
        active_subs_values = [d['active_subscriptions'] for d in report_data]
        new_subs_values = [d['new_subscriptions'] for d in report_data]
        canceled_subs_values = [d['canceled_subscriptions'] for d in report_data]
        mrr_values = [d['estimated_mrr'] for d in report_data]
        new_mrr_values = [d['new_mrr'] for d in report_data]
        churn_mrr_values = [d['churn_mrr'] for d in report_data]

        trace_mrr = go.Scatter(x=periods_labels, y=mrr_values, mode='lines+markers', name=f'Est. MRR ({self.system_currency_code})', yaxis='y1')
        trace_new_mrr = go.Scatter(x=periods_labels, y=new_mrr_values, mode='lines+markers', name=f'New MRR ({self.system_currency_code})', yaxis='y1')
        trace_churn_mrr = go.Scatter(x=periods_labels, y=churn_mrr_values, mode='lines+markers', name=f'Churn MRR ({self.system_currency_code})', yaxis='y1')

        trace_active_subs = go.Scatter(x=periods_labels, y=active_subs_values, mode='lines+markers', name='Active Subs', yaxis='y2')
        trace_new_subs = go.Scatter(x=periods_labels, y=new_subs_values, mode='lines+markers', name='New Subs', yaxis='y2')
        trace_canceled_subs = go.Scatter(x=periods_labels, y=canceled_subs_values, mode='lines+markers', name='Canceled Subs', yaxis='y2')

        layout = go.Layout(
          title=f'Subscription & MRR Trends ({self.system_currency_code})',
          yaxis=dict(
            title=f'MRR ({self.system_currency_code})',
            titlefont=dict(color='#1f77b4'),
            tickfont=dict(color='#1f77b4')
          ),
          yaxis2=dict(
            title='Subscription Counts',
            titlefont=dict(color='#ff7f0e'),
            tickfont=dict(color='#ff7f0e'),
            overlaying='y',
            side='right',
            showgrid=False
          ),
          legend=dict(x=0.1, y=1.1, orientation="h"),
          margin=dict(l=60, r=60, t=80, b=80)
        )
        self.plt_mrr_trend.data = [trace_mrr, trace_new_mrr, trace_churn_mrr, trace_active_subs, trace_new_subs, trace_canceled_subs]
        self.plt_mrr_trend.layout = layout
      else:
        self.plt_mrr_trend.data = []
        self.plt_mrr_trend.layout = go.Layout(title=f'Subscription & MRR Trends ({self.system_currency_code} - No data available)')

    except Exception as e:
      alert(f"An error occurred while loading the report: {e}")
      self.lbl_active_subs.text = "Error"
      self.lbl_estimated_mrr.text = f"Error ({self.system_currency_code})"
      self.lbl_new_mrr.text = f"Error ({self.system_currency_code})"
      self.lbl_churn_mrr.text = f"Error ({self.system_currency_code})"
      self.plt_mrr_trend.data = []
      self.plt_mrr_trend.layout = go.Layout(title=f'Subscription & MRR Trends ({self.system_currency_code} - Error loading data)')

    finally:
      self.btn_refresh.enabled = True
      self.btn_refresh.icon = 'fa:refresh'
      self.btn_refresh.text = 'Refresh'

  def btn_refresh_click(self, **event_args):
    self.load_report_data()

  def dd_period_type_change(self, **event_args):
    self.load_report_data()

  def dd_periods_change(self, **event_args):
    self.load_report_data()