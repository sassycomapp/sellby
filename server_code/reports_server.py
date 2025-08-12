# Server Module: reports_server.py (Tenant App)
# In reports_server.py
from sm_logs_mod import log
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import math # Ensure math is imported
from collections import defaultdict # Ensure defaultdict is imported
# Ensure helper functions like _get_period_start_end and _normalize_price_to_monthly are defined
# in this file or imported correctly if they are in a different helper module.
from datetime import datetime, date, timezone, timedelta # Ensure 'date' is explicitly imported
import traceback



# Assuming _get_period_start_end is defined as previously:
def _get_period_start_end(period_type="month", offset=0):
  """
    Calculates the start (inclusive) and end (exclusive) datetimes for a given period type and offset.
    All datetimes are in UTC.
    period_type: "month" or "quarter".
    offset: 0 for current period, 1 for previous, etc.
    """
  now = datetime.now(timezone.utc)
  # period_type is already lowercased by the calling function, but defensive lowercasing here is fine.
  period_type = period_type.lower()

  if period_type == "month":
    current_year, current_month_1_indexed = now.year, now.month

    # Calculate the target month (1-indexed) and year, considering the offset
    # Total months from a reference point (e.g., year 0, month 0)
    total_months_ref = current_year * 12 + (current_month_1_indexed - 1)
    target_total_months_ref = total_months_ref - offset

    start_year = target_total_months_ref // 12
    start_month_1_indexed = (target_total_months_ref % 12) + 1

    start_dt = datetime(start_year, start_month_1_indexed, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Calculate end_dt (start of the next month)
    end_month_1_indexed = start_month_1_indexed + 1
    end_year = start_year
    if end_month_1_indexed > 12:
      end_month_1_indexed = 1
      end_year += 1
    end_dt = datetime(end_year, end_month_1_indexed, 1, 0, 0, 0, tzinfo=timezone.utc)

  elif period_type == "quarter":
    current_year, current_month_1_indexed = now.year, now.month
    current_quarter_1_indexed = (current_month_1_indexed - 1) // 3 + 1

    # Calculate the target quarter (1-indexed) and year
    total_quarters_ref = current_year * 4 + (current_quarter_1_indexed - 1)
    target_total_quarters_ref = total_quarters_ref - offset

    start_year = target_total_quarters_ref // 4
    start_quarter_1_indexed = (target_total_quarters_ref % 4) + 1

    start_month_of_quarter_1_indexed = (start_quarter_1_indexed - 1) * 3 + 1
    start_dt = datetime(start_year, start_month_of_quarter_1_indexed, 1, 0, 0, 0, tzinfo=timezone.utc)

    # Calculate end_dt (start of the next quarter)
    end_quarter_1_indexed = start_quarter_1_indexed + 1
    end_year_of_next_quarter = start_year
    if end_quarter_1_indexed > 4:
      end_quarter_1_indexed = 1
      end_year_of_next_quarter += 1

    end_month_of_next_quarter_1_indexed = (end_quarter_1_indexed - 1) * 3 + 1
    end_dt = datetime(end_year_of_next_quarter, end_month_of_next_quarter_1_indexed, 1, 0, 0, 0, tzinfo=timezone.utc)

  else:
    # Fallback for unknown period_type, though client should only send "month" or "quarter"
    print(f"Warning (MRR Calc): Unknown period_type '{period_type}' in _get_period_start_end. Defaulting to last 30 days.")
    end_dt = now
    start_dt = now - timedelta(days=30)

  return start_dt, end_dt
# In reports_server.py (ensure it's defined before get_subscription_mrr_data or imported)

# Assuming _normalize_price_to_monthly is defined as previously:
def _normalize_price_to_monthly(amount_in_system_currency, interval, frequency):
  if not amount_in_system_currency or not interval or not frequency:
    return 0.0
  try:
    amount = float(str(amount_in_system_currency)) # Amount is already in system currency
    frequency = int(frequency)
    if frequency <= 0:
      return 0.0
    interval = interval.lower()
    if interval == 'month':
      return amount / frequency
    elif interval == 'year':
      return amount / (frequency * 12)
    elif interval == 'week':
      return (amount / frequency) * (52 / 12)
    elif interval == 'day':
      return (amount / frequency) * (365.25 / 12)
    else:
      print(f"Warning (MRR Calc): Unknown billing interval '{interval}'.")
      return 0.0
  except (ValueError, TypeError) as e:
    print(f"Warning (MRR Calc): Could not normalize price amount={amount_in_system_currency}, interval={interval}, freq={frequency}. Error: {e}")
    return 0.0
# --- Report Data Functions ---

# Report 1: Revenue & Sales Trend
# In reports_server.py

@anvil.server.callable(require_user=True)
def get_revenue_sales_trend_data(period_type="monthly", periods=12):
  """
    Fetches data for the Revenue & Sales Trend report.
    Calculates metrics for the last 'periods' number of 'period_type'.
    MODIFIED: Uses 'details_totals_earnings' for revenue.
    """
  results = []
  for i in range(periods - 1, -1, -1): # Iterate from oldest to newest period
    start_dt, end_dt = _get_period_start_end(period_type, i) # Assumes _get_period_start_end helper exists
    period_label = start_dt.strftime("%Y-%m") if period_type=="monthly" else start_dt.strftime("%Y-Q%q").replace('%q', str(math.ceil(start_dt.month/3))) # Assumes math is imported

    paid_transactions = list(app_tables.transaction.search(
      status='paid', 
      billed_at=q.between(start_dt, end_dt, min_inclusive=True, max_inclusive=False)
    ))

    # MODIFICATION: Use 'details_totals_earnings' for revenue
    # Ensure this field is consistently populated in your 'transaction' table
    # and represents the value in your system/payout currency.
    total_revenue = sum(t['details_totals_earnings'] or 0 for t in paid_transactions)
    num_transactions = len(paid_transactions)
    avg_transaction_value = total_revenue / num_transactions if num_transactions > 0 else 0

    results.append({
      'period': period_label,
      'start_date': start_dt,
      'end_date': end_dt,
      'total_revenue': total_revenue,
      'num_transactions': num_transactions,
      'avg_transaction_value': avg_transaction_value
    })
  return results

# Report 2: Subscription Overview & MRR Insights
# In reports_server.py

@anvil.server.callable(require_user=True)
def get_subscription_mrr_data(period_type="month", periods=12):
  """
    Fetches data for the Subscription Overview & MRR Insights report.
    MODIFIED: Calculates Estimated MRR, New MRR, and Churn MRR based on
              normalized 'details_totals_earnings' from relevant transactions.
    """
  results = []

  for i in range(periods - 1, -1, -1): # Iterate from oldest to newest period
    start_dt, end_dt = _get_period_start_end(period_type, i)
    period_label = start_dt.strftime("%Y-%m") if period_type=="month" else start_dt.strftime("%Y-Q%q").replace('%q', str(math.ceil(start_dt.month/3)))

    # --- Subscriptions active at the END of the period ---
    active_subs_at_end_rows = list(app_tables.subs.search(
      status='active',
      started_at=q.less_than(end_dt),
      canceled_at=None
    ))
    active_subs_count = len(active_subs_at_end_rows)

    # --- Subscriptions started WITHIN the period ---
    new_subs_in_period_rows = list(app_tables.subs.search(
      started_at=q.between(start_dt, end_dt, min_inclusive=True, max_inclusive=False)
    ))
    new_subs_count = len(new_subs_in_period_rows)

    # --- Subscriptions canceled WITHIN the period ---
    canceled_in_period_rows = list(app_tables.subs.search(
      canceled_at=q.between(start_dt, end_dt, min_inclusive=True, max_inclusive=False)
    ))
    canceled_count = len(canceled_in_period_rows)

    # --- MRR Calculations ---
    estimated_mrr = 0.0
    new_mrr = 0.0
    churn_mrr = 0.0

    # Calculate Total Estimated MRR from subs active at period end
    for sub_row in active_subs_at_end_rows:
      # Find the most recent 'paid' transaction for this subscription
      # to get its earnings in system currency.
      latest_paid_txn = app_tables.transaction.search(
        tables.order_by("billed_at", ascending=False),
        subscription_id=sub_row,
        status='paid',
        # Optimization: consider billed_at <= end_dt if relevant
      )
      if latest_paid_txn and len(latest_paid_txn) > 0:
        txn_earnings = latest_paid_txn[0]['details_totals_earnings']
        if txn_earnings is not None: # Ensure earnings is not None
          monthly_value = _normalize_price_to_monthly(
            txn_earnings, # Already in system currency
            sub_row['billing_cycle_interval'],
            sub_row['billing_cycle_frequency']
          )
          estimated_mrr += monthly_value
          # If no paid transaction found, it contributes 0 to this MRR calculation

        # Calculate New MRR from subs started in period
    for sub_row in new_subs_in_period_rows:
      # Find the first 'paid' transaction for this new subscription
      # (ideally billed within the current or very near future period)
      first_paid_txn = app_tables.transaction.search(
        tables.order_by("billed_at", ascending=True),
        subscription_id=sub_row,
        status='paid',
        billed_at=q.greater_equal(sub_row['started_at']) # Ensure txn is not from before start
      )
      if first_paid_txn and len(first_paid_txn) > 0:
        txn_earnings = first_paid_txn[0]['details_totals_earnings']
        if txn_earnings is not None:
          monthly_value = _normalize_price_to_monthly(
            txn_earnings,
            sub_row['billing_cycle_interval'],
            sub_row['billing_cycle_frequency']
          )
          new_mrr += monthly_value
          # If no paid transaction yet, it contributes 0 to New MRR (as per your instruction)

        # Calculate Churn MRR from subs canceled in period
    for sub_row in canceled_in_period_rows:
      # Find the last 'paid' transaction before or at cancellation to represent lost MRR
      last_paid_txn = app_tables.transaction.search(
        tables.order_by("billed_at", ascending=False),
        subscription_id=sub_row,
        status='paid',
        billed_at=q.less_than_or_equal_to(sub_row['canceled_at']) # Txn before or at cancellation
      )
      if last_paid_txn and len(last_paid_txn) > 0:
        txn_earnings = last_paid_txn[0]['details_totals_earnings']
        if txn_earnings is not None:
          monthly_value = _normalize_price_to_monthly(
            txn_earnings,
            sub_row['billing_cycle_interval'],
            sub_row['billing_cycle_frequency']
          )
          churn_mrr += monthly_value
          # If no prior paid transaction, it means it churned before any value was realized/recorded as earnings.

    results.append({
      'period': period_label,
      'start_date': start_dt,
      'end_date': end_dt,
      'active_subscriptions': active_subs_count,
      'new_subscriptions': new_subs_count,
      'canceled_subscriptions': canceled_count,
      'estimated_mrr': estimated_mrr,
      'new_mrr': new_mrr,
      'churn_mrr': churn_mrr
    })
  return results

# Report 3: Customer Churn Rate
@anvil.server.callable(require_user=True)
def get_customer_churn_data(period_type="monthly", periods=12):
    """
    Fetches data for the Customer Churn Rate report.
    NOTE: Calculation is simplified. Assumes churn based on cancellations within the period
          relative to active customers at the start. Needs refinement for accuracy.
    """
    results = []
    for i in range(periods - 1, -1, -1):
        start_dt, end_dt = _get_period_start_end(period_type, i)
        period_label = start_dt.strftime("%Y-%m") if period_type=="monthly" else start_dt.strftime("%Y-Q%q").replace('%q', str(math.ceil(start_dt.month/3)))

        active_at_start_subs = app_tables.subs.search(
            status='active',
            started_at=q.less_than(start_dt),
            canceled_at=q.any_of(None, q.greater_equal(start_dt))
        )
        starting_customers = {s['customer_id'].get_id() for s in active_at_start_subs if s['customer_id']}
        starting_customer_count = len(starting_customers)

        canceled_in_period_subs = app_tables.subs.search(
            canceled_at=q.between(start_dt, end_dt, min_inclusive=True, max_inclusive=False)
        )
        canceled_customers = {s['customer_id'].get_id() for s in canceled_in_period_subs if s['customer_id'] and s['customer_id'].get_id() in starting_customers}
        canceled_customer_count = len(canceled_customers)

        churn_rate = (canceled_customer_count / starting_customer_count * 100) if starting_customer_count > 0 else 0

        results.append({
            'period': period_label,
            'start_date': start_dt,
            'end_date': end_dt,
            'starting_customers': starting_customer_count,
            'canceled_customers': canceled_customer_count,
            'churn_rate_percent': churn_rate
        })
    return results

# --- Performance Reports (4a, 4b, 4c) ---
# NOTE: These currently only reflect performance based on subscription-linked transactions
# due to limitations in current webhook processing linking non-subscription transactions.

def _get_base_item_performance_data():
  """
    Internal helper to get performance data for all items (products and services).
    Includes revenue and units from all billed transaction line items.
    Revenue is attributed per line item. Customer uniqueness is per item.
    Monetary values (revenue, arpu) are returned in minor units.
    """
  module_name = "reports_server"
  function_name = "_get_base_item_performance_data"
  log("INFO", module_name, function_name, "Starting base item performance data aggregation.")

  performance = defaultdict(lambda: {'revenue': 0, 'units_sold': 0, 'customers': set()})

  # 1. Fetch all relevant items (products and services) to build a lookup map.
  # This ensures we only process items defined as 'product' or 'service'.
  all_mybizz_items_rows = list(app_tables.items.search(
    item_type=q.any_of('product', 'service')
  ))
  # Create a map for quick lookup by item_id (MyBizz primary key string, e.g., "ITM-xxxx")
  all_mybizz_items_map = {row['item_id']: row for row in all_mybizz_items_rows}
  log("DEBUG", module_name, function_name, f"Fetched {len(all_mybizz_items_map)} product/service items for tracking.")

  # 2. Iterate through all transaction line items.
  # This relies on webhook_handler.py correctly populating transaction_items for ALL sales,
  # including one-time purchases and items billed as part of subscription transactions.
  for txn_item in app_tables.transaction_items.search():
    # a. Access parent transaction and check status
    transaction_row = txn_item['transaction_id'] # Link to 'transaction' table
    if not transaction_row or transaction_row['status'] not in ['paid', 'completed']:
      # log("DEBUG", module_name, function_name, f"Skipping txn_item {txn_item.get_id()} as parent transaction {transaction_row['paddle_id'] if transaction_row else 'N/A'} is not paid/completed.")
      continue

      # b. Access linked price
    price_row = txn_item['price_id'] # Link to 'prices' table
    if not price_row:
      log("WARNING", module_name, function_name, f"Transaction item {txn_item.get_id()} (Paddle ID: {txn_item['paddle_id']}) has no linked MyBizz price_id. Skipping.")
      continue

      # c. Access linked item from the price
    item_linked_via_price = price_row['item_id'] # Link from 'prices' to 'items' table
    if not item_linked_via_price:
      log("WARNING", module_name, function_name, f"MyBizz Price {price_row['price_id']} (Paddle ID: {price_row['paddle_price_id']}) from txn_item {txn_item.get_id()} has no linked MyBizz item_id. Skipping.")
      continue

      # d. Get the MyBizz item_id string (PK)
    item_id_key = item_linked_via_price['item_id']

    # e. Check if this item is one of the products/services we are tracking
    if item_id_key not in all_mybizz_items_map:
      # This item is not a 'product' or 'service' based on our initial filter.
      # log("DEBUG", module_name, function_name, f"Item {item_id_key} from txn_item {txn_item.get_id()} is not a tracked product/service. Skipping.")
      continue

      # f. Aggregate metrics if it's a tracked item
      # i. Revenue Attribution: Use totals_total from transaction_items (minor units)
    line_revenue_str = txn_item['totals_total']
    if line_revenue_str is not None:
      try:
        performance[item_id_key]['revenue'] += int(str(line_revenue_str)) # Ensure it's string then int
      except (ValueError, TypeError) as e:
        log("WARNING", module_name, function_name, f"Could not parse revenue '{line_revenue_str}' for txn_item {txn_item.get_id()} (Paddle ID: {txn_item['paddle_id']}). Error: {e}")
        # Decide if you want to add 0 or skip. Adding 0 might skew ARPU if units are counted.
        # For now, we'll let it be, effectively adding 0 if parsing fails.

        # ii. Units Sold Aggregation
    quantity_val = txn_item['quantity']
    if quantity_val is not None:
      try:
        performance[item_id_key]['units_sold'] += int(quantity_val)
      except (ValueError, TypeError) as e:
        log("WARNING", module_name, function_name, f"Could not parse quantity '{quantity_val}' for txn_item {txn_item.get_id()} (Paddle ID: {txn_item['paddle_id']}). Error: {e}")

        # iii. Customer Tracking (using Anvil's internal row ID for the customer for uniqueness)
    if transaction_row['customer_id']: # Link to 'customer' table
      customer_anvil_id = transaction_row['customer_id'].get_id() 
      performance[item_id_key]['customers'].add(customer_anvil_id)

    # 3. Prepare final results list
  results = []
  for item_id_key, data in performance.items():
    item_info = all_mybizz_items_map.get(item_id_key) 
    if not item_info: 
      log("ERROR", module_name, function_name, f"Item info not found in map for key {item_id_key} during result preparation. This should not happen.")
      continue 

    customer_count = len(data['customers'])
    # Revenue is in minor units. ARPU will also be in minor units.
    arpu = (data['revenue'] / customer_count) if customer_count > 0 else 0

    results.append({
      'item_id': item_id_key,                 # MyBizz item_id (e.g., "ITM-xxxx")
      'item_name': item_info['name'],         # Name from the 'items' table
      'item_type': item_info['item_type'],    # 'product' or 'service'
      'total_revenue': data['revenue'],       # Sum of totals_total from transaction_items (integer, minor units)
      'units_sold': data['units_sold'],       # Sum of quantity from transaction_items (integer)
      'customer_count': customer_count,       # Count of unique customers who purchased this item (integer)
      'arpu': int(round(arpu))                # ARPU (integer, minor units, rounded)
    })

    # Sort results (e.g., by total_revenue descending)
  results.sort(key=lambda x: x['total_revenue'], reverse=True)
  log("INFO", module_name, function_name, f"Aggregated performance data for {len(results)} items.")
  return results


# Report 4a: Product Performance (MyBizz View)

@anvil.server.callable(require_user=True) # Or specific permission
def get_mybizz_product_performance_data():
  """
    Fetches performance data for items categorized as 'product'.
    Uses the standardized output from _get_base_item_performance_data.
    """
  # _ensure_admin() # Or specific report permission
  all_item_data = _get_base_item_performance_data()
  # Filter for items where item_type is 'product'
  product_data = [
    item for item in all_item_data 
    if item.get('item_type', '').lower() == 'product'
  ]
  # No renaming needed if client template for products expects 'item_name'
  return product_data

  
# Report 4b: Service Performance (MyBizz View)
@anvil.server.callable(require_user=True) # Or specific permission
def get_mybizz_service_performance_data():
  """
    Fetches performance data for items categorized as 'service'.
    Uses the standardized output from _get_base_item_performance_data.
    """
  # _ensure_admin() # Or specific report permission
  all_item_data = _get_base_item_performance_data()
  # Filter for items where item_type is 'service'
  service_data = []
  for item in all_item_data:
    if item.get('item_type', '').lower() == 'service':
      # The client template report_service_performance_mybizz_item.py
      # will expect 'item_name' for its lbl_service_name.
      # No need to rename 'item_name' to 'service_name' here if the client adapts.
      service_data.append(item) 
  return service_data

# Report 4c: Item Performance (Paddle Combined View)
@anvil.server.callable(require_user=True) # Or specific permission
def get_paddle_item_performance_data():
  """
    Fetches performance data for all items combined (Paddle view).
    Uses the standardized output from _get_base_item_performance_data.
    The DataGrid on the client will use the keys directly.
    """
  # _ensure_admin() # Or specific report permission
  # Returns all items (products and services) without filtering by type here.
  # The base function already provides 'item_name' and 'item_type'.
  # The DataGrid on report_item_performance_paddle.py will be configured
  # to display 'item_name' as "Item Name".
  all_item_data = _get_base_item_performance_data()

  # For the DataGrid in report_item_performance_paddle.py,
  # it's configured with "product_name" as a data_key.
  # To maintain compatibility with that DataGrid's current column definition
  # without changing the DataGrid component's `data_key` property,
  # we can transform the key here.
  # Alternatively, and preferably for long-term consistency, update the DataGrid's
  # column definition to use 'item_name'.
  # For now, let's transform to match existing DataGrid:

  transformed_data_for_datagrid = []
  for item in all_item_data:
    new_item_dict = item.copy() # Create a copy to modify
    new_item_dict['product_name'] = new_item_dict.pop('item_name') # Rename item_name to product_name
    transformed_data_for_datagrid.append(new_item_dict)

  return transformed_data_for_datagrid
# Report 5: Subscription Plan Performance
@anvil.server.callable(require_user=True) # Or add specific permission check
def get_subscription_plan_performance_data(period_type="monthly", periods=0, filter_group_id=None, filter_level_num=None):
  """
    Fetches performance data per subscription plan (Group/Level/Tier).
    If periods=0, returns current snapshot. Otherwise, calculates trends.
    MRR is now calculated based on most recent 'paid'/'completed' transaction earnings for active subscriptions.
    """
  module_name = "reports_server"
  function_name = "get_subscription_plan_performance_data"
  log_context = {
    "period_type": period_type, "periods": periods,
    "filter_group_id": filter_group_id, "filter_level_num": filter_level_num
  }
  log("INFO", module_name, function_name, "Fetching subscription plan performance data.", log_context)

  # _ensure_admin() # Or specific report permission check

  # --- Pre-fetch data (can be optimized if memory becomes an issue for very large datasets) ---
  # all_prices map is no longer the primary source for MRR amount, but might be useful for other details if needed.
  # For this refactor, we'll fetch transaction earnings directly.

  all_groups_list = list(app_tables.subscription_group.search())
  all_groups_map = {g.get_id(): g for g in all_groups_list}

  # --- Determine calculation mode ---
  is_snapshot = (periods == 0)
  num_periods_to_calc = 1 if is_snapshot else periods

  # --- Data storage ---
  # plan_performance stores aggregated data for the final period (snapshot) or current period in a trend
  plan_performance = defaultdict(lambda: {
    'group_name': 'Unknown', 'level_num': None, 'tier_num': None, 'glt_key': None, # Added glt_key
    'active_subs': 0, 'new_subs': 0, 'canceled_subs': 0, 'estimated_mrr': 0.0
  })
  trend_data = [] # For storing period-based aggregates if calculating a trend

  # --- Main Calculation Loop (Iterates from oldest to newest period if not a snapshot) ---
  for i in range(num_periods_to_calc - 1, -1, -1):
    current_period_start_dt, current_period_end_dt = _get_period_start_end(period_type, i)
    period_label = current_period_start_dt.strftime("%Y-%m") if period_type.lower()=="month" else current_period_start_dt.strftime("%Y-Q%q").replace('%q', str(math.ceil(current_period_start_dt.month/3)))

    period_log_context = {**log_context, "current_period_label": period_label, "start_dt": str(current_period_start_dt), "end_dt": str(current_period_end_dt)}
    # log("DEBUG", module_name, function_name, f"Processing period: {period_label}", period_log_context)

    # Build base query for subscriptions based on filters
    subs_query_conditions = []
    if filter_group_id:
      group_row_for_filter = all_groups_map.get(filter_group_id)
      if group_row_for_filter:
        subs_query_conditions.append(q.subscription_group == group_row_for_filter)
      else:
        log("WARNING", module_name, function_name, f"Filter group_id {filter_group_id} not found. No data will be returned for this filter.", period_log_context)
        return {'details': [], 'total_active_subs': 0, 'total_mrr': 0.0, 'trend_data': []}

    if filter_level_num is not None:
      subs_query_conditions.append(q.level_num == str(filter_level_num)) # Assuming level_num is stored as string like "L1"

      # Fetch all subscriptions that could be relevant (active, started, or canceled within broader timeframe)
      # More refined querying per metric might be more performant but more complex.
      # This approach fetches a wider set and then filters in Python for each metric.
    relevant_subs_in_scope = list(app_tables.subs.search(*subs_query_conditions))

    # --- Period Aggregates (if calculating trend, reset for each period) ---
    if not is_snapshot:
      plan_performance.clear() # Recalculate per period for trend

    period_total_active_subs_for_trend = 0
    period_total_mrr_for_trend = 0.0

    # --- Calculate metrics for the current period ---

    # 1. Active Subscriptions at the END of the current_period_end_dt
    for sub_row in relevant_subs_in_scope:
      if sub_row['status'] == 'active' and \
      (sub_row['started_at'] is None or sub_row['started_at'] < current_period_end_dt) and \
      (sub_row['canceled_at'] is None or sub_row['canceled_at'] >= current_period_end_dt):

        glt_key = sub_row['glt'] or f"G{sub_row['subscription_group']['group_number'] if sub_row['subscription_group'] else '?'}_L{sub_row['level_num']}_T{sub_row['tier_num']}"

        plan_performance[glt_key]['active_subs'] += 1
        if plan_performance[glt_key]['glt_key'] is None: # Populate details on first encounter
          plan_performance[glt_key]['glt_key'] = glt_key
          plan_performance[glt_key]['group_name'] = sub_row['subscription_group']['group_name'] if sub_row['subscription_group'] else 'Unknown Group'
          plan_performance[glt_key]['level_num'] = sub_row['level_num']
          plan_performance[glt_key]['tier_num'] = sub_row['tier_num']

        period_total_active_subs_for_trend +=1

        # Calculate MRR based on most recent 'paid'/'completed' transaction earnings
        if sub_row['tier_num'] and str(sub_row['tier_num']).upper().startswith('T') and int(str(sub_row['tier_num'])[1:]) > 1: # Assuming T1 is free
          most_recent_paid_txn = app_tables.transaction.search(
            tables.order_by("billed_at", ascending=False),
            subscription_id=sub_row,
            status=q.any_of('paid', 'completed'),
            billed_at=q.less_than(current_period_end_dt) # Transaction must be within or before period end
          )

          if most_recent_paid_txn and len(most_recent_paid_txn) > 0:
            latest_txn = most_recent_paid_txn[0]
            # Use details_totals_earnings, assumed to be in system currency
            earnings_minor_units = latest_txn['details_totals_earnings']

            if earnings_minor_units is not None:
              try:
                earnings_amount = int(str(earnings_minor_units))
                monthly_value = _normalize_price_to_monthly(
                  earnings_amount, # Already in system currency (minor units)
                  sub_row['billing_cycle_interval'],
                  sub_row['billing_cycle_frequency']
                )
                plan_performance[glt_key]['estimated_mrr'] += monthly_value
                period_total_mrr_for_trend += monthly_value
              except (ValueError, TypeError) as e:
                log("WARNING", module_name, function_name, f"Could not parse/normalize earnings for MRR. Sub: {sub_row['paddle_id']}, Txn: {latest_txn['paddle_id']}, Earnings: {earnings_minor_units}. Error: {e}", period_log_context)
                # else:
                # log("DEBUG", module_name, function_name, f"No earnings found on latest paid transaction {latest_txn['paddle_id']} for sub {sub_row['paddle_id']}.", period_log_context)
                # else:
                # log("DEBUG", module_name, function_name, f"No recent paid transaction found for active sub {sub_row['paddle_id']} to calculate MRR.", period_log_context)

        # 2. New Subscriptions started WITHIN the current_period
    for sub_row in relevant_subs_in_scope:
      if sub_row['started_at'] and current_period_start_dt <= sub_row['started_at'] < current_period_end_dt:
        glt_key = sub_row['glt'] or f"G{sub_row['subscription_group']['group_number'] if sub_row['subscription_group'] else '?'}_L{sub_row['level_num']}_T{sub_row['tier_num']}"
        plan_performance[glt_key]['new_subs'] += 1
        if plan_performance[glt_key]['glt_key'] is None: # Populate details if first encounter
          plan_performance[glt_key]['glt_key'] = glt_key
          plan_performance[glt_key]['group_name'] = sub_row['subscription_group']['group_name'] if sub_row['subscription_group'] else 'Unknown Group'
          plan_performance[glt_key]['level_num'] = sub_row['level_num']
          plan_performance[glt_key]['tier_num'] = sub_row['tier_num']

        # 3. Canceled Subscriptions canceled WITHIN the current_period
    for sub_row in relevant_subs_in_scope:
      if sub_row['canceled_at'] and current_period_start_dt <= sub_row['canceled_at'] < current_period_end_dt:
        glt_key = sub_row['glt'] or f"G{sub_row['subscription_group']['group_number'] if sub_row['subscription_group'] else '?'}_L{sub_row['level_num']}_T{sub_row['tier_num']}"
        plan_performance[glt_key]['canceled_subs'] += 1
        if plan_performance[glt_key]['glt_key'] is None: # Populate details if first encounter
          plan_performance[glt_key]['glt_key'] = glt_key
          plan_performance[glt_key]['group_name'] = sub_row['subscription_group']['group_name'] if sub_row['subscription_group'] else 'Unknown Group'
          plan_performance[glt_key]['level_num'] = sub_row['level_num']
          plan_performance[glt_key]['tier_num'] = sub_row['tier_num']

        # Store trend data if calculating multiple periods
    if not is_snapshot:
      trend_data.append({
        'period': period_label,
        'total_active_subs': period_total_active_subs_for_trend,
        'total_mrr': period_total_mrr_for_trend # This is sum of MRR from plans in system currency
            })

    # --- Prepare final results ---
    # plan_performance now holds the data for the most recent period (or the snapshot)
    details_list = list(plan_performance.values())
    
    # Calculate overall totals for the final state (snapshot or last period of a trend)
    final_total_active_subs = sum(p['active_subs'] for p in details_list)
    final_total_mrr = sum(p['estimated_mrr'] for p in details_list) # Already in system currency

    log("INFO", module_name, function_name, f"Successfully generated subscription plan performance data. Details: {len(details_list)} plans. Total Active: {final_total_active_subs}, Total MRR: {final_total_mrr:.2f}", log_context)
    
    return {
        'details': details_list, # List of dicts, one per G/L/T plan
        'total_active_subs': final_total_active_subs,
        'total_mrr': final_total_mrr, # In system currency, minor units (due to _normalize_price_to_monthly)
        'trend_data': trend_data if not is_snapshot else None 
    }
# Helper for Report 5 Filter
@anvil.server.callable(require_user=True)
def get_subscription_group_list():
    """Fetches subscription groups for filter dropdown."""
    # Assuming 'subscription_group' table has 'group_name' and 'group_number' or similar
    groups = app_tables.subscription_group.search(tables.order_by("group_name"))
    # Return list of (display_name, row_id) tuples
    return [(g['group_name'], g.get_id()) for g in groups]


# Report 6: Review Transactions
@anvil.server.callable(require_user=True)
def get_all_transactions(start_date=None, end_date=None, status_filter=None, 
                         sort_by=None, page_number=1, page_size=15):
  """
    Fetches a paginated and sorted list of transactions.
    Returns a dictionary: {'items': [...], 'total_count': X}
    """
  # Basic permission check (can be enhanced with roles if needed)
  # user = anvil.users.get_user()
  # if not user:
  #     raise anvil.server.PermissionDenied("You must be logged in to view transactions.")

  query_args = [] # Use a list for query expressions for q.all_of / q.any_of if needed

  # Date filtering
  if start_date:
    # Ensure start_date is datetime for comparison if billed_at includes time
    if isinstance(start_date, date) and not isinstance(start_date, datetime):
      start_date = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    query_args.append(q.billed_at >= start_date)

  if end_date:
    # Ensure end_date is datetime and represents end of day for inclusive range
    if isinstance(end_date, date) and not isinstance(end_date, datetime):
      end_date = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
    query_args.append(q.billed_at <= end_date)

    # Status filtering (case-insensitive if using q.ilike, direct match if not)
  if status_filter and status_filter != "All Statuses": # Assuming "All Statuses" means no filter
    # Using direct equality for status, assuming status values in DB match filter values
    query_args.append(q.status == status_filter.lower()) # Match client's lowercase values

    # Construct the final query using q.all_of if multiple conditions
  final_query = None
  if query_args:
    final_query = q.all_of(*query_args)

    # Sorting
  order_by_clause = None
  if sort_by:
    if sort_by == "billed_at_desc":
      order_by_clause = tables.order_by("billed_at", ascending=False)
    elif sort_by == "billed_at_asc":
      order_by_clause = tables.order_by("billed_at", ascending=True)
    elif sort_by == "total_desc":
      # Sorting by 'details_totals_total' (string) directly might not be numerically correct.
      # This requires fetching all, converting to number, then sorting, or storing as number.
      # For simplicity now, we'll sort by the string representation, which is not ideal for numerics.
      # A better solution would be to store 'details_totals_total' as a number if possible,
      # or fetch all matching, convert, sort, then paginate in Python (less efficient for DB).
      # For now, direct string sort:
      order_by_clause = tables.order_by("details_totals_total", ascending=False)
    elif sort_by == "total_asc":
      order_by_clause = tables.order_by("details_totals_total", ascending=True)
    elif sort_by == "customer_email_asc":
      # Sorting by linked field requires a different approach or denormalization.
      # For now, this won't work directly with tables.order_by on a linked field's attribute.
      # We'll sort in Python after fetching for this, or skip if too complex for now.
      # This example will sort by customer link's internal ID, not email.
      # A proper solution involves denormalizing email or more complex query/post-processing.
      # For now, let's sort by a field directly on the transaction table if possible, or omit this sort.
      # To keep it simple and functional with direct DB sort, let's assume we sort by a direct field.
      # If customer email sort is critical, it needs more advanced handling.
      # For this iteration, we'll sort by customer_id (the link object itself, which sorts by internal ID)
      order_by_clause = tables.order_by("customer_id", ascending=True) # Placeholder sort
    elif sort_by == "customer_email_desc":
      order_by_clause = tables.order_by("customer_id", ascending=False) # Placeholder sort
    elif sort_by == "status_asc":
      order_by_clause = tables.order_by("status", ascending=True)
    elif sort_by == "status_desc":
      order_by_clause = tables.order_by("status", ascending=False)
    else: # Default sort
      order_by_clause = tables.order_by("billed_at", ascending=False)
  else: # Default sort if none provided
    order_by_clause = tables.order_by("billed_at", ascending=False)

    # Get total count for pagination before applying page limits
  if final_query:
    total_count = len(app_tables.transaction.search(final_query))
  else:
    total_count = len(app_tables.transaction.search())

    # Fetch paginated results
    # Anvil's search doesn't directly support offset for q.fetch_only with complex queries easily.
    # A common pattern is to fetch IDs first if performance is an issue, or fetch a limited set.
    # For robust pagination with sorting, it's often best to let the database handle it if possible.
    # Anvil's simple search with `limit` and then slicing is not true DB pagination.
    # However, for `RepeatingPanel` and typical Anvil use, fetching all matching rows
    # (that match filters) and then slicing in Python for the current page is common
    # if the total number of filtered items isn't excessively large (e.g., many tens of thousands).
    # If it is, a more advanced pagination strategy is needed.

    # Let's try a slice-based approach after sorting, assuming filtered results are manageable.
  if final_query:
    if order_by_clause:
      all_matching_transactions = app_tables.transaction.search(final_query, order_by_clause)
    else:
      all_matching_transactions = app_tables.transaction.search(final_query)
  else:
    if order_by_clause:
      all_matching_transactions = app_tables.transaction.search(order_by_clause)
    else:
      all_matching_transactions = app_tables.transaction.search()

  start_index = (page_number - 1) * page_size
  end_index = start_index + page_size
  paginated_transactions = list(all_matching_transactions[start_index:end_index])

  results = []
  for t in paginated_transactions:
    customer_email = t['customer_id']['email'] if t['customer_id'] and t['customer_id']['email'] else None
    sub_paddle_id = t['subscription_id']['paddle_id'] if t['subscription_id'] and t['subscription_id']['paddle_id'] else None
    discount_code = t['discount_id']['coupon_code'] if t['discount_id'] and t['discount_id']['coupon_code'] else None

    results.append({
      'paddle_id': t['paddle_id'],
      'billed_at': t['billed_at'],
      'status': t['status'],
      'customer_email': customer_email,
      'total': t['details_totals_total'], # This is the original transaction amount in minor units
      'currency_code': t['currency_code'],
      'subscription_paddle_id': sub_paddle_id,
      'discount_code': discount_code,
      'origin': t.get('origin'), # Use .get for potentially missing fields
      'collection_mode': t.get('collection_mode'),
    })

  return {'items': results, 'total_count': total_count}

# Report 7: View a Transaction
@anvil.server.callable(require_user=True)
def get_single_transaction(transaction_paddle_id):
  """
    Fetches detailed data for a single transaction, including its line items.
    Formats monetary values for line items.
    """
  # module_name = "reports_server"
  # function_name = "get_single_transaction"
  # log_context = {"transaction_paddle_id": transaction_paddle_id}

  if not transaction_paddle_id:
    # log("WARNING", module_name, function_name, "No transaction_paddle_id provided.", log_context)
    return None

    # log("INFO", module_name, function_name, "Fetching single transaction details.", log_context)

  t = app_tables.transaction.get(paddle_id=transaction_paddle_id)
  if not t:
    # log("WARNING", module_name, function_name, "Transaction not found.", log_context)
    return None

    # --- Prepare main transaction data (as before) ---
  customer_details = None
  if t['customer_id']:
    c = t['customer_id']
    customer_details = {
      'paddle_id': c.get('paddle_id'), 
      'email': c.get('email'), 
      'full_name': c.get('full_name'), 
      'status': c.get('status')
    }

  subscription_details = None
  if t['subscription_id']:
    s = t['subscription_id']
    subscription_details = {
      'paddle_id': s.get('paddle_id'), 
      'status': s.get('status'), 
      'started_at': s.get('started_at')
    }

  discount_details = None
  if t['discount_id']:
    d = t['discount_id']
    discount_details = {
      'paddle_id': d.get('paddle_id'), 
      'coupon_code': d.get('coupon_code'), 
      'description': d.get('description'), 
      'type': d.get('type')
    }

  result = dict(t) # Convert main transaction row to dict
  # Nullify link objects after extracting details to avoid sending full linked rows if not needed
  result['customer_id'] = customer_details['paddle_id'] if customer_details else None
  result['subscription_id'] = subscription_details['paddle_id'] if subscription_details else None
  result['discount_id'] = discount_details['paddle_id'] if discount_details else None
  result['address_id'] = t['address_id']['paddle_id'] if t['address_id'] else None # Assuming address has paddle_id
  result['user_id'] = t['user_id']['email'] if t['user_id'] else None # Send email for user_id display

  result['customer_details'] = customer_details
  result['subscription_details'] = subscription_details
  result['discount_details'] = discount_details

  # --- Fetch and Format Transaction Line Items ---
  transaction_line_items = []
  line_item_rows = app_tables.transaction_items.search(transaction_id=t)

  for li_row in line_item_rows:
    item_name = "N/A"
    unit_price_formatted = "N/A"
    currency_code_item = t['currency_code'] # Default to transaction currency

    if li_row['price_id']:
      price_row = li_row['price_id'] # This is the linked 'prices' row
      if price_row['item_id']: # Link to 'items' table
        item_name = price_row['item_id']['name'] or price_row['item_id']['description'] or "Unnamed Item"

        # Format unit price from the 'prices' table definition for this line item
      if price_row['unit_price_amount'] is not None and price_row['unit_price_currency_code']:
        currency_code_item = price_row['unit_price_currency_code']
        try:
          unit_major_units = int(str(price_row['unit_price_amount'])) / 100.0
          unit_price_formatted = f"{currency_code_item} {unit_major_units:,.2f}"
        except (ValueError, TypeError):
          unit_price_formatted = f"{currency_code_item} {price_row['unit_price_amount']} (raw)"

        # Format line item totals (subtotal, discount, tax, total)
        # These are from transaction_items.totals_... and should use the transaction's currency_code
    def format_line_item_monetary(value_str, currency):
      if value_str is not None and currency:
        try:
          major_units = int(str(value_str)) / 100.0
          return f"{currency} {major_units:,.2f}"
        except (ValueError, TypeError):
          return f"{currency} {value_str} (raw)"
      elif value_str is not None:
        return f"{value_str} (raw, currency N/A)"
      return "N/A"

    proration_display = ""
    if li_row.get('proration_billing_period_starts_at') and li_row.get('proration_billing_period_ends_at'):
      starts = li_row['proration_billing_period_starts_at'].strftime('%Y-%m-%d')
      ends = li_row['proration_billing_period_ends_at'].strftime('%Y-%m-%d')
      proration_display = f"Prorated: {starts} to {ends}"
      if li_row.get('proration_rate'):
        proration_display += f" (Rate: {li_row['proration_rate']})"


    transaction_line_items.append({
      'item_name_or_description': item_name,
      'quantity': li_row.get('quantity'),
      'unit_price_formatted': unit_price_formatted, # Price definition for one unit
      'line_subtotal_formatted': format_line_item_monetary(li_row.get('totals_subtotal'), t['currency_code']),
      'line_discount_formatted': format_line_item_monetary(li_row.get('totals_discount'), t['currency_code']),
      'line_tax_formatted': format_line_item_monetary(li_row.get('totals_tax'), t['currency_code']),
      'line_total_formatted': format_line_item_monetary(li_row.get('totals_total'), t['currency_code']),
      'proration_details_display': proration_display if proration_display else None,
      # Add other fields from transaction_items if needed by the item template
      'paddle_price_id_of_item': price_row['paddle_price_id'] if li_row['price_id'] else None 
    })

  result['line_items'] = transaction_line_items
  # log("INFO", module_name, function_name, f"Returning details for transaction {transaction_paddle_id} with {len(transaction_line_items)} line items.", log_context)
  return result

def _ensure_admin():
  """Checks if the current user is an administrator. Raises PermissionDenied if not."""
  # Replace this with your actual admin check logic
  user = anvil.users.get_user(allow_remembered=True) # Get current user
  # Example: Check if user has an 'admin' role (adjust to your user table structure)
  if not user or not user['role'] or user['role'].lower() != 'admin':
    raise anvil.server.PermissionDenied("Administrator access required for this action.")
    # Alternatively, if you have an is_admin_user() function:
    # if not is_admin_user():
    #     raise anvil.server.PermissionDenied("Administrator access required for this action.")


  
# Report 8: Customer Profile
@anvil.server.callable # Removed require_user=True, _ensure_admin() will handle permissions
def get_customer_profile(customer_identifier):
  """
    Fetches comprehensive profile data for a customer by email or Paddle ID.
    Admin access required.
    """
  _ensure_admin() # Enforce admin-only access

  if not customer_identifier:
    return None

    # Attempt to find customer by email or paddle_id
  customer_row = app_tables.customer.get(email=customer_identifier)
  if not customer_row:
    customer_row = app_tables.customer.get(paddle_id=customer_identifier)

  if not customer_row:
    return None

    # --- Basic Customer Details ---
  profile_data = dict(customer_row) # Start with all fields from the customer row

  # --- Business Details (if applicable) ---
  business_row = app_tables.business.get(customer_id=customer_row)
  if business_row:
    profile_data['business_details'] = {
      'name': business_row['name'],
      'company_number': business_row['company_number'],
      'tax_identifier': business_row['tax_identifier']
    }
    # Use business name as primary name if business exists
    profile_data['display_name'] = business_row['name']
  else:
    profile_data['business_details'] = None
    profile_data['display_name'] = customer_row['full_name']


    # --- Address Details (assuming one primary address) ---
  address_row = app_tables.address.get(customer_id=customer_row) # Add more criteria if needed to select one
  if address_row:
    country_name = address_row['country_code'] # Default to code
    if address_row['country_code']:
      country_record = app_tables.country.get(country_code=address_row['country_code'])
      if country_record:
        country_name = country_record['country_name']

    profile_data['address_details'] = {
      'first_line': address_row['first_line'],
      'city': address_row['city'],
      'region': address_row['region'],
      'postal_code': address_row['postal_code'],
      'country_name': country_name, # Display-friendly country name
      'country_code': address_row['country_code'] # Original code for reference
    }
  else:
    profile_data['address_details'] = None

    # --- Subscriptions Summary (all subscriptions) ---
  subscriptions_summary = []
  customer_subs = app_tables.subs.search(customer_id=customer_row)
  for sub_row in customer_subs:
    plan_product_name = "N/A"
    if sub_row['item_id']: # item_id is a link to the 'items' table
      plan_product_name = sub_row['item_id']['name'] or "Unnamed Plan/Product"

    subscriptions_summary.append({
      'paddle_subscription_id': sub_row['paddle_id'], # Assuming paddle_id is the subscription ID from Paddle
      'plan_product_name': plan_product_name,
      'status': sub_row['status'],
      'started_at': sub_row['started_at'],
      'canceled_at': sub_row['canceled_at'],
      'paused_at': sub_row['paused_at'],
      'next_billed_at': sub_row['next_billed_at'],
      # Add any other fields from 'subs' table needed for display logic in item template
    })
  profile_data['subscriptions'] = subscriptions_summary

  # --- Transactions Summary (all transactions) ---
  transactions_summary = []
  # Fetch all transactions, ordered by most recent first
  customer_txns = app_tables.transaction.search(
    tables.order_by("billed_at", ascending=False),
    customer_id=customer_row
  )
  for txn_row in customer_txns:
    transactions_summary.append({
      'paddle_transaction_id': txn_row['paddle_id'], # Assuming paddle_id is the transaction ID from Paddle
      'billed_at': txn_row['billed_at'],
      'status': txn_row['status'],
      'details_totals_earnings': txn_row['details_totals_earnings'], # String, minor units (System Currency)
      'currency_code': txn_row['currency_code'] # Original transaction currency (for reference, not primary display)
      # No need to fetch system currency code here, client will get it once for all formatting
    })
  profile_data['transactions'] = transactions_summary

  # Remove raw linked row objects if they were copied by dict(customer_row) and are not needed
  # This depends on how Anvil handles linked rows when converting to dict.
  # For safety, explicitly set them to None or desired values if they were part of the initial dict conversion.
  profile_data['user_id'] = customer_row['user_id']['email'] if customer_row['user_id'] else None
  # Any other linked fields on customer_row that you don't want to send as full rows.

  return profile_data

# Report 9: All Products and Services
@anvil.server.callable
def get_all_products_and_services(status_filter=None, item_type_filter=None, sort_by=None):
  """
    Fetches a list of all products and services from the 'items' table,
    with filtering and sorting capabilities.
    Includes default price information.
    Admin access required.
    """
  _ensure_admin()

  query_conditions = []

  # Base filter for item_type 'product' or 'service'
  query_conditions.append(q.any_of(
    app_tables.items.item_type == 'product',
    app_tables.items.item_type == 'service'
  ))

  # Apply status filter
  if status_filter and status_filter.lower() != 'all':
    query_conditions.append(app_tables.items.status == status_filter.lower())

    # Apply item_type filter (if user selected 'Product' or 'Service' specifically)
  if item_type_filter and item_type_filter.lower() != 'all':
    query_conditions.append(app_tables.items.item_type == item_type_filter.lower())

    # Determine sorting order
  order_by_clause = None
  if sort_by:
    if sort_by == "name_asc":
      order_by_clause = tables.order_by("name", ascending=True)
    elif sort_by == "name_desc":
      order_by_clause = tables.order_by("name", ascending=False)
    elif sort_by == "created_at_desc":
      order_by_clause = tables.order_by("created_at_paddle", ascending=False)
    elif sort_by == "created_at_asc":
      order_by_clause = tables.order_by("created_at_paddle", ascending=True)
    elif sort_by == "item_id_asc":
      order_by_clause = tables.order_by("item_id", ascending=True)
    elif sort_by == "item_id_desc":
      order_by_clause = tables.order_by("item_id", ascending=False)
    elif sort_by == "item_type_asc":
      order_by_clause = tables.order_by("item_type", ascending=True)
    elif sort_by == "item_type_desc":
      order_by_clause = tables.order_by("item_type", ascending=False)
      # Add more sort options here if needed

  if not order_by_clause: # Default sort if none matched or provided
    order_by_clause = tables.order_by("name", ascending=True)

    # Construct the final query
  final_query = q.all_of(*query_conditions)

  items_rows = app_tables.items.search(final_query, order_by_clause)

  results = []
  for item_row in items_rows:
    item_dict = dict(item_row) # Convert row to dictionary

    # Fetch default price information
    default_price_amount = None
    default_price_currency = None
    if item_row['default_price_id']: # This is a link to the 'prices' table
      price_row = item_row['default_price_id'] # Get the linked row
      if price_row:
        default_price_amount = price_row['unit_price_amount'] # String, minor units
        default_price_currency = price_row['unit_price_currency_code']

    item_dict['default_price_unit_price_amount'] = default_price_amount
    item_dict['default_price_currency_code'] = default_price_currency

    # Ensure necessary fields for the client are present, even if None
    # (Most should be directly from item_row via dict conversion)
    item_dict.setdefault('item_id', None)
    item_dict.setdefault('name', None)
    item_dict.setdefault('description', None)
    item_dict.setdefault('item_type', None)
    item_dict.setdefault('status', None)
    item_dict.setdefault('paddle_product_id', None)
    item_dict.setdefault('created_at_paddle', None)

    results.append(item_dict)

  return results

# Report 11: All Discounts
@anvil.server.callable(require_user=True)
def get_all_discounts():
    """Fetches a list of all discounts."""
    discounts = app_tables.discount.search(tables.order_by("coupon_code"))
    return [dict(d) for d in discounts]

# Report 12: Failed Transactions
@anvil.server.callable(require_user=True)
def get_failed_transactions(limit=100, start_date=None, end_date=None): # Added date filters
  """
    Fetches a list of failed transactions with their failure reasons.
    MODIFIED: Queries 'failed_transactions' table and links to 'transaction' for some details.
              Accepts optional date filters.
    """
  query_args = {}
  if start_date and end_date:
    query_args['failed_at'] = q.between(start_date, end_date, min_inclusive=True, max_inclusive=False)
  elif start_date:
    query_args['failed_at'] = q.greater_equal(start_date)
  elif end_date:
    query_args['failed_at'] = q.less_than(end_date)

    # Query the failed_transactions table
  failed_entries = app_tables.failed_transactions.search(
    tables.order_by("failed_at", ascending=False),
    **query_args
  )

  results = []
  count = 0
  for entry in failed_entries:
    if count >= limit:
      break

      # Attempt to get related info from the main transaction table if needed
      # For this report, most key info is now in failed_transactions table.
      # We might want the original transaction's total attempted amount if not stored directly.
    original_transaction_row = app_tables.transaction.get(paddle_id=entry['paddle_transaction_id'])
    attempted_total = None
    attempted_currency = None
    if original_transaction_row:
      attempted_total_str = original_transaction_row.get('details_totals_total') # This is the gross amount
      attempted_currency = original_transaction_row.get('currency_code')
      if attempted_total_str and attempted_currency:
        try:
          attempted_total = int(attempted_total_str) # Assuming minor units
        except (ValueError, TypeError):
          attempted_total = None # Or log error

    results.append({
      'paddle_id': entry['paddle_transaction_id'], # This is the Paddle Transaction ID
      'failed_at': entry['failed_at'],
      'status': entry['status'], # Status from failed_transactions table (e.g., "Logged")
      # Or, if you prefer, the status from the main transaction table:
      # 'transaction_status': original_transaction_row['status'] if original_transaction_row else 'Unknown',
      'customer_email': entry['email'],
      'total': attempted_total, # The amount that failed to process (minor units)
      'currency_code': attempted_currency,
      'failure_reason_paddle': entry['failure_reason_paddle'],
      'mybizz_failure_reason': entry.get('mybizz_failure_reason'), # Use .get for optional field
      'attempted_items_summary': entry.get('attempted_items_summary')
      # Add other fields from failed_transactions table as needed for the report item template
    })
    count += 1
  return results

# Report 5 (Old Report 10): All Subscription Plans (Prices)
@anvil.server.callable(require_user=True) # Consider specific permission
def get_all_subscription_plans():
  """
    Fetches a list of all prices that are of type 'recurring' (i.e., subscription plans),
    including details from the linked 'items' table (name, GLT) and the item's 'subscription_group' (name).
    Sorted by the subscription group name, then linked item's name, then by the price description.
    """
  module_name = "reports_server"
  function_name = "get_all_subscription_plans"
  # log("INFO", module_name, function_name, "Fetching all subscription plan prices for report.")

  # _ensure_admin() # Or a more specific permission

  results = []
  try:
    # Fetching prices that are 'recurring'
    # Sorting: We want to sort by group name, then item name, then price description.
    # This requires careful handling of linked fields in order_by.
    # A simpler approach for complex sorts is to sort in Python after fetching,
    # if the dataset isn't excessively large. For now, let's try a basic DB sort.
    # Anvil's tables.order_by can handle linked fields like item_id__name.
    # For item_id__subscription_group_id__group_name, it might be more complex or less performant.
    # Let's fetch and then sort in Python for robust multi-level linked sorting.

    recurring_prices = app_tables.prices.search(
      price_type='recurring'
      # Initial sort by description, further sorting will be done in Python
      # order_by=tables.order_by(description=True) 
    )

    for price_row in recurring_prices:
      linked_item_name = "N/A"
      linked_item_mybizz_id = "N/A" # MyBizz PK for the item
      linked_item_type = "N/A"
      item_glt = "N/A"
      subscription_group_name = "N/A"
      mybizz_item_anvil_id = None # Anvil row ID for the item, for manage_price_form context

      item_link = price_row['item_id'] # This is the linked row from the 'items' table
      if item_link:
        linked_item_name = item_link['name']
        linked_item_mybizz_id = item_link['item_id'] 
        linked_item_type = item_link['item_type']
        item_glt = item_link.get('glt', "N/A") # Get GLT from item
        mybizz_item_anvil_id = item_link.get_id() # Get Anvil row ID of the item

        group_link = item_link['subscription_group_id'] # Link from 'items' to 'subscription_group'
        if group_link:
          subscription_group_name = group_link['group_name']
        else:
          # This case should ideally not happen if an item of type 'subscription_plan'
          # (which is what recurring prices should link to) always has a group.
          log("WARNING", module_name, function_name,
              f"Item {linked_item_mybizz_id} (linked to price {price_row['price_id']}) has no subscription_group_id link.")
      else:
        log("WARNING", module_name, function_name, 
            f"Price {price_row['price_id']} (Paddle: {price_row.get('paddle_price_id', 'N/A')}) is recurring but has no linked item. Skipping.")
        continue 

      plan_price_details = {
        'mybizz_price_id': price_row['price_id'], 
        'paddle_price_id': price_row.get('paddle_price_id'),
        'price_description': price_row['description'], # For the item template's lbl_price_description

        'subscription_group_name': subscription_group_name, # For the item template
        'linked_item_name': linked_item_name, # For the item template (e.g., "Beginner Monthly")
        'glt': item_glt, # For the item template (e.g., "G1L1T2")

        'unit_price_amount': price_row['unit_price_amount'],
        'unit_price_currency_code': price_row['unit_price_currency_code'],

        'billing_cycle_interval': price_row.get('billing_cycle_interval'),
        'billing_cycle_frequency': price_row.get('billing_cycle_frequency'),
        'trial_period_interval': price_row.get('trial_period_interval'),
        'trial_period_frequency': price_row.get('trial_period_frequency'),

        'status': price_row['status'], # Price status (active/archived)
        'tax_mode': price_row.get('tax_mode'),
        'quantity_minimum': price_row.get('quantity_minimum'),
        'quantity_maximum': price_row.get('quantity_maximum'),

        'linked_item_mybizz_id': linked_item_mybizz_id, # MyBizz PK of the item
        'linked_item_anvil_id': mybizz_item_anvil_id, # Anvil Row ID of the item, useful for manage_price_form
        'linked_item_type': linked_item_type,

        'created_at_anvil': price_row.get('created_at_anvil'),
        'updated_at_anvil': price_row.get('updated_at_anvil'),
        'paddle_created_at': price_row.get('paddle_created_at'),
        'paddle_updated_at': price_row.get('paddle_updated_at')
      }
      results.append(plan_price_details)

      # Sort in Python for multi-level linked field sorting robustness
      # Sort by: Subscription Group Name (asc), then Linked Item Name (asc), then Price Description (asc)
    results.sort(key=lambda x: (
      x.get('subscription_group_name', '').lower() if x.get('subscription_group_name') else '',
      x.get('linked_item_name', '').lower() if x.get('linked_item_name') else '',
      x.get('price_description', '').lower() if x.get('price_description') else ''
    ))

    # log("INFO", module_name, function_name, f"Successfully fetched and sorted {len(results)} subscription plan prices.")
    return results

  except Exception as e:
    log("ERROR", module_name, function_name, "Error fetching subscription plan prices.", {"error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while fetching subscription plan prices: {str(e)}")