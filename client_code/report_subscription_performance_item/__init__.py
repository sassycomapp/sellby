from ._anvil_designer import report_subscription_performance_itemTemplate
from anvil import *
import anvil.server

class report_subscription_performance_item(report_subscription_performance_itemTemplate):
    def __init__(self, **properties):
        # Set Form properties and Data Bindings.
        self.init_components(**properties)

        # Any code you write here will run when the form opens.
        # Populate labels from the item dictionary (plan performance data)
        self.lbl_group_name.text = self.item.get('group_name', 'N/A')
        self.lbl_level.text = self.item.get('level_num', 'N/A') # Displaying number, adjust if name needed
        self.lbl_tier.text = self.item.get('tier_num', 'N/A')   # Displaying number, adjust if name needed
        self.lbl_active_subs.text = f"{self.item.get('active_subs', 0):,}"
        self.lbl_new_subs.text = f"{self.item.get('new_subs', 0):,}"
        self.lbl_canceled_subs.text = f"{self.item.get('canceled_subs', 0):,}"

        mrr = self.item.get('estimated_mrr', 0.0)
        # Only display MRR if it's likely calculated (e.g., for paid tiers)
        # Server function should return 0 for free tiers.
        self.lbl_mrr.text = f"${mrr:,.2f}" if mrr > 0 else "$0.00"
        # Optionally hide MRR label completely for free tiers if desired
        # tier_num = self.item.get('tier_num')
        # self.lbl_mrr.visible = tier_num is not None and int(tier_num) > 1
