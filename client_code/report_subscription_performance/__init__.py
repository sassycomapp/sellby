# Client Module: report_subscription_performance.py

from ._anvil_designer import report_subscription_performanceTemplate
from anvil import *
import anvil.server
import plotly.graph_objects as go
from datetime import datetime # Ensure datetime is imported if used directly, though not in this snippet
import math # For parsing periods

# Import the item template that will be used by repeating_panel_1
from ..report_subscription_performance_item import report_subscription_performance_item # Adjust path if needed

class report_subscription_performance(report_subscription_performanceTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # --- Initialize Filters ---
    self.populate_group_filter() # Populate group dropdown first

    self.dd_level_filter.items = ["All Levels", "Level 1", "Level 2", "Level 3"]
    self.dd_level_filter.selected_value = "All Levels"

    self.dd_period_type.items = ["Monthly", "Quarterly"]
    self.dd_period_type.selected_value = "Monthly"

    # Default to snapshot, plot hidden initially
    self.dd_periods.items = ["Current Snapshot", "Last 3 Periods", "Last 6 Periods", "Last 12 Periods"]
    self.dd_periods.selected_value = "Current Snapshot"
    self.plt_overall_trend.visible = False

    # --- Configure RepeatingPanel ---
    # Ensure your RepeatingPanel is named repeating_panel_1 in the designer
    self.repeating_panel_1.item_template = report_subscription_performance_item

    # --- Load Initial Data ---
    self.load_report_data()

  def populate_group_filter(self):
    """Fetches subscription groups and populates the filter dropdown."""
    try:
      group_list = [("All Groups", None)]
      server_groups = anvil.server.call('get_subscription_group_list')
      group_list.extend([(g[0], g[1]) for g in server_groups]) 
      self.dd_group_filter.items = group_list
      self.dd_group_filter.selected_value = None 
    except Exception as e:
      print(f"Error populating group filter: {e}")
      self.dd_group_filter.items = [("Error loading groups", None)]

  def load_report_data(self, **event_args):
    """Loads data from the server and updates the report components."""
    filter_group_id = self.dd_group_filter.selected_value
    level_str = self.dd_level_filter.selected_value
    filter_level_num = int(level_str.split()[-1]) if level_str and level_str != "All Levels" else None
    period_type = self.dd_period_type.selected_value.lower() if self.dd_period_type.selected_value else "monthly"
    periods_str = self.dd_periods.selected_value or "Current Snapshot"
    show_trend = periods_str != "Current Snapshot"
    try:
      periods = int(periods_str.split()[-2]) if show_trend else 0 
    except (ValueError, IndexError):
      periods = 0 

    try:
      self.btn_refresh.enabled = False
      self.btn_refresh.icon = 'fa:spinner'
      self.btn_refresh.text = 'Loading...'
      self.plt_overall_trend.visible = False 

      report_data = anvil.server.call('get_subscription_plan_performance_data',
                                      period_type=period_type,
                                      periods=periods,
                                      filter_group_id=filter_group_id,
                                      filter_level_num=filter_level_num)

      self.lbl_total_active_subs.text = f"{report_data.get('total_active_subs', 0):,}"
      self.lbl_total_mrr.text = f"${report_data.get('total_mrr', 0):,.2f}"

      # --- Update RepeatingPanel ---
      self.repeating_panel_1.items = report_data.get('details', [])

      trend_data = report_data.get('trend_data')
      if show_trend and trend_data:
        self.plt_overall_trend.visible = True
        periods_labels = [d['period'] for d in trend_data]
        active_subs_values = [d['total_active_subs'] for d in trend_data]
        mrr_values = [d['total_mrr'] for d in trend_data]

        trace_mrr = go.Scatter(x=periods_labels, y=mrr_values, mode='lines+markers', name='Total MRR ($)', yaxis='y1')
        trace_active_subs = go.Scatter(x=periods_labels, y=active_subs_values, mode='lines+markers', name='Total Active Subs', yaxis='y2')

        layout = go.Layout(
          title='Overall Subscription Trend',
          yaxis=dict(title='MRR ($)', titlefont=dict(color='#1f77b4'), tickfont=dict(color='#1f77b4')),
          yaxis2=dict(title='Active Subscribers', titlefont=dict(color='#ff7f0e'), tickfont=dict(color='#ff7f0e'), overlaying='y', side='right', showgrid=False),
          legend=dict(x=0.1, y=1.1, orientation="h"),
          margin=dict(l=60, r=60, t=80, b=80)
        )
        self.plt_overall_trend.data = [trace_mrr, trace_active_subs]
        self.plt_overall_trend.layout = layout
      else:
        self.plt_overall_trend.visible = False
        self.plt_overall_trend.data = []
        self.plt_overall_trend.layout = {}

    except Exception as e:
      alert(f"An error occurred while loading the report: {e}")
      self.lbl_total_active_subs.text = "Error"
      self.lbl_total_mrr.text = "Error"
      self.repeating_panel_1.items = [] # Clear RepeatingPanel on error
      self.plt_overall_trend.visible = False
      self.plt_overall_trend.data = []
      self.plt_overall_trend.layout = {}

    finally:
      self.btn_refresh.enabled = True
      self.btn_refresh.icon = 'fa:refresh'
      self.btn_refresh.text = 'Refresh'

  def btn_refresh_click(self, **event_args):
    self.load_report_data()

  def dd_group_filter_change(self, **event_args):
    self.load_report_data()

  def dd_level_filter_change(self, **event_args):
    self.load_report_data()

  def dd_period_type_change(self, **event_args):
    if self.dd_periods.selected_value != "Current Snapshot":
      self.load_report_data()

  def dd_periods_change(self, **event_args):
    self.load_report_data()