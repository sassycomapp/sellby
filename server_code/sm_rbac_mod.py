# Server Module: sm_rbac_mod.py
# Handles Role-Based Access Control (RBAC) logic,
# including role/permission management and checking.

import anvil.server
import anvil.users
import anvil.tables as tables
from anvil.tables import app_tables # Use this alias consistently
from .sm_logs_mod import log 
from datetime import datetime, timezone
import traceback
import anvil.tables.query as q

# --- Constants for RBAC ---

# Predefined System Role Names (used for seeding and checks)
SYSTEM_ROLE_OWNER = "Owner"
SYSTEM_ROLE_ADMIN = "Admin"
SYSTEM_ROLE_TECH = "Tech"
SYSTEM_ROLE_USER = "User"
SYSTEM_ROLE_VISITOR = "Visitor"

# Temporary role name used during initial owner setup
TEMP_SETUP_ROLE_NAME = "owner" # Lowercase, as per your plan

# Optional: List of all system roles for easy iteration if needed elsewhere in this module
ALL_SYSTEM_ROLES_LIST = [ 
  SYSTEM_ROLE_OWNER,
  SYSTEM_ROLE_ADMIN,
  SYSTEM_ROLE_TECH,
  SYSTEM_ROLE_USER,
  SYSTEM_ROLE_VISITOR
]
# --- Helper Functions for Initialization ---

def _create_permission_if_not_exists(name, description, category):
  """Creates a permission if it doesn't already exist by name."""
  module_name = "sm_rbac_mod"
  function_name = "_create_permission_if_not_exists"
  permission = app_tables.permissions.get(name=name)
  if not permission:
    try:
      permission = app_tables.permissions.add_row(
        name=name,
        description=description,
        category=category,
        created_at_anvil=datetime.now(timezone.utc),
        updated_at_anvil=datetime.now(timezone.utc)
      )
      log("INFO", module_name, function_name, f"Permission '{name}' created.", {"category": category})
      return permission
    except Exception as e:
      log("ERROR", module_name, function_name, f"Failed to create permission '{name}'.", {"error": str(e)})
      raise # Re-raise to halt initialization if a core permission fails
  else:
    # Optionally update description/category if they differ, or just log
    # For now, just ensure it exists.
    # log("DEBUG", module_name, function_name, f"Permission '{name}' already exists.")
    pass
  return permission

def _create_role_if_not_exists(name, description, is_system_role=True):
  """Creates a role if it doesn't already exist by name."""
  module_name = "sm_rbac_mod"
  function_name = "_create_role_if_not_exists"
  role = app_tables.roles.get(name=name)
  if not role:
    try:
      role = app_tables.roles.add_row(
        name=name,
        description=description,
        is_system_role=is_system_role,
        created_at_anvil=datetime.now(timezone.utc),
        updated_at_anvil=datetime.now(timezone.utc)
      )
      log("INFO", module_name, function_name, f"Role '{name}' created.", {"is_system": is_system_role})
      return role
    except Exception as e:
      log("ERROR", module_name, function_name, f"Failed to create role '{name}'.", {"error": str(e)})
      raise # Re-raise to halt initialization if a core role fails
  else:
    # Optionally update description/is_system_role if they differ
    # log("DEBUG", module_name, function_name, f"Role '{name}' already exists.")
    pass
  return role

def _assign_permission_to_role_if_not_exists(role_row, permission_row):
  """Assigns a permission to a role if the mapping doesn't already exist."""
  module_name = "sm_rbac_mod"
  function_name = "_assign_permission_to_role_if_not_exists"
  if not role_row or not permission_row:
    log("WARNING", module_name, function_name, "Role or Permission row is None, cannot assign.", {"role_id": role_row['role_id'] if role_row else None, "permission_id": permission_row['permission_id'] if permission_row else None})
    return

  existing_mapping = app_tables.role_permission_mapping.get(
    role_id=role_row,
    permission_id=permission_row
  )
  if not existing_mapping:
    try:
      app_tables.role_permission_mapping.add_row(
        role_id=role_row,
        permission_id=permission_row,
        assigned_at_anvil=datetime.now(timezone.utc)
      )
      log("INFO", module_name, function_name, f"Permission '{permission_row['name']}' assigned to role '{role_row['name']}'.")
    except Exception as e:
      log("ERROR", module_name, function_name, f"Failed to assign permission '{permission_row['name']}' to role '{role_row['name']}'.", {"error": str(e)})
      # Decide if this should raise an error and halt. For default setup, it probably should.
      raise
    # else:
      # log("DEBUG", module_name, function_name, f"Permission '{permission_row['name']}' already assigned to role '{role_row['name']}'.")


# --- Main Seeding Function ---
@anvil.server.callable(require_user=True) 
def initialize_default_rbac_data():
  """
    Populates the database with predefined system roles, permissions,
    and their default mappings. This function should be idempotent.
    Also upgrades the initial user from the temporary 'owner' role to the
    permanent 'Owner' role and deletes the temporary role.
    """
  module_name = "sm_rbac_mod"
  function_name = "initialize_default_rbac_data"
  user_who_triggered = anvil.users.get_user() 
  log_context = {"triggered_by_user": user_who_triggered['email'] if user_who_triggered else "Unknown"}

  # Optional Permission Check (ensure only Owner can run this after initial setup)
  # if user_who_triggered and user_who_triggered['role'] and user_who_triggered['role']['name'] != SYSTEM_ROLE_OWNER:
  #     # This check might be too restrictive if the user is still on the temporary "owner" role
  #     # For initial seeding, the require_user=True might be enough, or a check that they are the *only* user.
  #     pass 

  log("INFO", module_name, function_name, "Starting initialization of default RBAC data.", log_context)

  try:
    # 1. Define and Create All Permissions
    permissions_definitions = [
      # Category: Public
      {"name": "view_public_products", "desc": "View publicly listed products", "cat": "Public Access"},
      {"name": "view_public_services", "desc": "View publicly listed services", "cat": "Public Access"},
      {"name": "view_public_subscription_plans", "desc": "View publicly listed subscription plans", "cat": "Public Access"},
      {"name": "view_public_documentation", "desc": "Access public help documentation", "cat": "Public Access"},
      {"name": "view_company_contact_info", "desc": "View company contact information", "cat": "Public Access"},
      {"name": "access_help_center", "desc": "Access the help center or FAQs", "cat": "Public Access"},

      # Category: Account Self-Service
      {"name": "edit_own_profile", "desc": "Edit own user profile details (excluding role)", "cat": "Account Self-Service"},
      {"name": "manage_own_payment_methods", "desc": "Add, update, or remove own payment methods", "cat": "Account Self-Service"},
      {"name": "view_own_usage_analytics", "desc": "View own usage data or analytics", "cat": "Account Self-Service"},
      {"name": "view_own_subscriptions", "desc": "View own active and past subscriptions", "cat": "Account Self-Service"},
      {"name": "manage_own_subscriptions", "desc": "General management of own subscriptions", "cat": "Account Self-Service"},
      {"name": "cancel_own_subscriptions", "desc": "Cancel own active subscriptions", "cat": "Account Self-Service"},
      {"name": "upgrade_downgrade_own_subscriptions", "desc": "Change/upgrade/downgrade own subscription plans", "cat": "Account Self-Service"},
      {"name": "view_own_orders", "desc": "View own order history", "cat": "Account Self-Service"},
      {"name": "view_own_invoices", "desc": "View and download own invoices", "cat": "Account Self-Service"},

      # Category: Product Catalog
      {"name": "view_all_items", "desc": "View all products, services, and subscription plan definitions", "cat": "Product Catalog"},
      {"name": "create_edit_items", "desc": "Create and edit products, services, and subscription plan definitions", "cat": "Product Catalog"},
      {"name": "delete_items", "desc": "Delete products, services, or subscription plan definitions", "cat": "Product Catalog"},
      {"name": "manage_subscription_groups", "desc": "Create, edit, and manage subscription groups", "cat": "Product Catalog"},
      {"name": "manage_prices_overrides", "desc": "Create, edit, and manage prices and price overrides for items", "cat": "Product Catalog"},

      # Category: Customer Admin
      {"name": "view_all_customers", "desc": "View list of all customers", "cat": "Customer Admin"},
      {"name": "view_customer_details", "desc": "View detailed profile of any customer", "cat": "Customer Admin"},
      {"name": "edit_customer_details", "desc": "Edit customer profile information", "cat": "Customer Admin"},
      {"name": "manage_customer_communications", "desc": "Manage or send communications to customers", "cat": "Customer Admin"},

      # Category: User & Role Admin
      {"name": "view_all_users_list", "desc": "View list of all users in the tenant app", "cat": "User & Role Admin"},
      {"name": "invite_users", "desc": "Invite new users to the tenant app", "cat": "User & Role Admin"},
      {"name": "edit_any_user_profile", "desc": "Edit profile details of any user", "cat": "User & Role Admin"},
      {"name": "enable_disable_users", "desc": "Enable or disable user accounts", "cat": "User & Role Admin"},
      {"name": "assign_user_roles", "desc": "Assign roles to users", "cat": "User & Role Admin"},
      {"name": "assign_tech_roles", "desc": "Assign 'Tech' or lower roles", "cat": "User & Role Admin"},
      {"name": "manage_roles", "desc": "Create, edit, delete custom roles (Owner only)", "cat": "User & Role Admin"},
      {"name": "manage_permissions_for_roles", "desc": "Assign/unassign permissions to roles (Owner only)", "cat": "User & Role Admin"},
      {"name": "delete_users", "desc": "Delete user accounts (with safeguards)", "cat": "User & Role Admin"},

      # Category: Discount Admin
      {"name": "view_discounts", "desc": "View all discount codes and their configurations", "cat": "Discount Admin"},
      {"name": "create_edit_discounts", "desc": "Create and edit discount codes", "cat": "Discount Admin"},
      {"name": "delete_discounts", "desc": "Delete discount codes", "cat": "Discount Admin"},

      # Category: Reporting
      {"name": "view_all_reports", "desc": "Access all standard business and operational reports", "cat": "Reporting"},
      {"name": "run_standard_reports", "desc": "Generate and view standard system reports", "cat": "Reporting"},
      {"name": "view_billing_summaries", "desc": "View summaries of billing and revenue", "cat": "Reporting"},
      {"name": "view_financial_reports", "desc": "Access detailed financial reports (Owner/Admin focus)", "cat": "Reporting"},
      {"name": "export_all_system_data", "desc": "Export comprehensive system data (Owner only)", "cat": "Reporting"},
      {"name": "export_audit_data", "desc": "Export audit log data (Owner/Admin)", "cat": "Reporting"},

      # Category: System Admin
      {"name": "view_system_logs", "desc": "View application system logs", "cat": "System Admin"},
      {"name": "view_webhook_settings", "desc": "View webhook endpoint configurations and history", "cat": "System Admin"},
      {"name": "manage_webhook_settings", "desc": "Retry webhook events, view details (not change secrets)", "cat": "System Admin"},
      {"name": "view_technical_documentation", "desc": "Access technical system documentation", "cat": "System Admin"},
      {"name": "access_api_documentation", "desc": "Access documentation for available APIs", "cat": "System Admin"},
      {"name": "view_system_health_metrics", "desc": "View system performance and health dashboards", "cat": "System Admin"},
      {"name": "view_error_reports", "desc": "View detailed error reports and diagnostics", "cat": "System Admin"},
      {"name": "access_api_keys", "desc": "Manage/view API keys for system integrations (Owner/Admin)", "cat": "System Admin"},

      # Category: Settings Admin
      {"name": "manage_app_settings", "desc": "Configure general application settings", "cat": "Settings Admin"},
      {"name": "manage_paddle_settings", "desc": "View Paddle integration settings", "cat": "Settings Admin"},
      {"name": "manage_mybizz_vault", "desc": "Manage secrets in the MyBizz Vault (Owner only)", "cat": "Settings Admin"},
      {"name": "manage_billing_settings", "desc": "Configure tenant company billing settings (Owner only)", "cat": "Settings Admin"},
      {"name": "manage_company_profile", "desc": "Edit tenant company's public profile information", "cat": "Settings Admin"},
      {"name": "manage_sso_integrations", "desc": "Configure Single Sign-On integrations (Owner only)", "cat": "Settings Admin"},

      # Category: Support
      {"name": "create_support_tickets", "desc": "Create new support tickets", "cat": "Support"},
      {"name": "manage_support_tickets", "desc": "View, assign, and respond to support tickets", "cat": "Support"},
      {"name": "submit_technical_support_requests", "desc": "Submit technical support requests to MyBizz platform support", "cat": "Support"},

      # Category: Security
      {"name": "view_audit_logs", "desc": "View audit trails of system and user actions", "cat": "Security"},
      {"name": "delete_critical_data", "desc": "Perform high-impact data deletions (Owner only)", "cat": "Security"},
      {"name": "approve_high_risk_operations", "desc": "Approve operations flagged as high-risk (Owner only)", "cat": "Security"},
      {"name": "view_security_alerts", "desc": "View system security alerts and notifications", "cat": "Security"},
    ]

    all_permissions_map = {} 
    if permissions_definitions: # Only loop if there are definitions
      for p_def in permissions_definitions:
        p_row = _create_permission_if_not_exists(p_def["name"], p_def["desc"], p_def["cat"])
        if p_row:
          all_permissions_map[p_def["name"]] = p_row
    else:
      log("WARNING", module_name, function_name, "permissions_definitions list is empty. No permissions will be created.", log_context)


      # 2. Define and Create System Roles
    roles_definitions = [
      {"name": SYSTEM_ROLE_OWNER, "desc": "Full control over the tenant account and application.", "is_system": True},
      {"name": SYSTEM_ROLE_ADMIN, "desc": "Administrative access to manage most aspects of the application.", "is_system": True},
      {"name": SYSTEM_ROLE_TECH, "desc": "Technical staff access for system monitoring and support.", "is_system": True},
      {"name": SYSTEM_ROLE_USER, "desc": "Standard signed-up customer with self-service capabilities.", "is_system": True},
      {"name": SYSTEM_ROLE_VISITOR, "desc": "Anonymous or new visitor with limited public access.", "is_system": True},
    ]
    roles_map = {} 
    for r_def in roles_definitions:
      r_row = _create_role_if_not_exists(r_def["name"], r_def["desc"], r_def["is_system"])
      if r_row:
        roles_map[r_def["name"]] = r_row

        # 3. Assign Default Permissions to Roles
        # (Ensure these permission names match what's in your permissions_definitions list once populated)
    visitor_perms = [
      "view_public_products", "view_public_services", "view_public_subscription_plans",
      "view_public_documentation", "view_company_contact_info", "access_help_center"
    ]
    if roles_map.get(SYSTEM_ROLE_VISITOR):
      for p_name in visitor_perms:
        if all_permissions_map.get(p_name):
          _assign_permission_to_role_if_not_exists(roles_map[SYSTEM_ROLE_VISITOR], all_permissions_map[p_name])

    user_perms = visitor_perms + [
      "edit_own_profile", "manage_own_payment_methods", "view_own_usage_analytics",
      "view_own_subscriptions", "manage_own_subscriptions", "cancel_own_subscriptions",
      "upgrade_downgrade_own_subscriptions", "view_own_orders", "view_own_invoices",
      "create_support_tickets"
    ]
    if roles_map.get(SYSTEM_ROLE_USER):
      for p_name in user_perms:
        if all_permissions_map.get(p_name):
          _assign_permission_to_role_if_not_exists(roles_map[SYSTEM_ROLE_USER], all_permissions_map[p_name])

    tech_perms = user_perms + [
      "view_system_logs", "view_webhook_settings", "manage_webhook_settings",
      "view_all_users_list", "view_all_items", "view_technical_documentation",
      "access_api_documentation", "view_system_health_metrics", "view_error_reports",
      "submit_technical_support_requests", "manage_support_tickets"
    ]
    if roles_map.get(SYSTEM_ROLE_TECH):
      for p_name in tech_perms:
        if all_permissions_map.get(p_name):
          _assign_permission_to_role_if_not_exists(roles_map[SYSTEM_ROLE_TECH], all_permissions_map[p_name])

    admin_perms = tech_perms + [
      "invite_users", "edit_any_user_profile", "enable_disable_users", "assign_tech_roles",
      "create_edit_items", "delete_items", "manage_subscription_groups", "manage_prices_overrides",
      "view_discounts", "create_edit_discounts", "delete_discounts",
      "view_all_reports", "run_standard_reports", "view_billing_summaries",
      "manage_app_settings", "manage_customer_communications", "view_audit_logs",
      "manage_company_profile", "view_security_alerts"
    ]
    if roles_map.get(SYSTEM_ROLE_ADMIN):
      for p_name in admin_perms:
        if all_permissions_map.get(p_name):
          _assign_permission_to_role_if_not_exists(roles_map[SYSTEM_ROLE_ADMIN], all_permissions_map[p_name])
      if all_permissions_map.get("assign_user_roles"): # Specific extra permission for Admin
        _assign_permission_to_role_if_not_exists(roles_map[SYSTEM_ROLE_ADMIN], all_permissions_map["assign_user_roles"])

    owner_role_row = roles_map.get(SYSTEM_ROLE_OWNER)
    if owner_role_row and all_permissions_map: # Check if all_permissions_map is not empty
      for p_name, p_row in all_permissions_map.items():
        _assign_permission_to_role_if_not_exists(owner_role_row, p_row)
    
        # --- Logic to upgrade initial user and delete temporary "owner" (lowercase) role ---
        log("INFO", module_name, function_name, "Attempting to upgrade initial user from temporary role and delete temporary role.", log_context)
    
    temp_role_to_delete = app_tables.roles.get(name=TEMP_SETUP_ROLE_NAME) # TEMP_SETUP_ROLE_NAME = "owner"
    
    if temp_role_to_delete:
      users_on_temp_role = list(app_tables.users.search(role=temp_role_to_delete))
      permanent_owner_role_from_map = roles_map.get(SYSTEM_ROLE_OWNER) # Get the "Owner" (uppercase) role row from our map
    
      if permanent_owner_role_from_map:
        for user_to_upgrade in users_on_temp_role:
          user_to_upgrade.update(role=permanent_owner_role_from_map)
          log("INFO", module_name, function_name, f"User {user_to_upgrade['email']} upgraded from temporary role '{TEMP_SETUP_ROLE_NAME}' to permanent role '{SYSTEM_ROLE_OWNER}'.", log_context)
    
          # This block should be indented to be part of the "if permanent_owner_role_from_map:"
        log("INFO", module_name, function_name, f"Deleting temporary setup role: '{TEMP_SETUP_ROLE_NAME}'.", log_context)
        temp_role_to_delete.delete()
      else: # This else corresponds to "if permanent_owner_role_from_map:"
        log("ERROR", module_name, function_name, f"Permanent '{SYSTEM_ROLE_OWNER}' role not found in roles_map after seeding. Cannot upgrade user or safely delete temporary role '{TEMP_SETUP_ROLE_NAME}'.", log_context)
    else: # This else corresponds to "if temp_role_to_delete:"
      log("INFO", module_name, function_name, f"Temporary setup role '{TEMP_SETUP_ROLE_NAME}' not found, no cleanup needed for it.", log_context)
      # --- End logic ---
    
      # This log and return are part of the main 'try' block
      log("INFO", module_name, function_name, "Default RBAC data initialization completed successfully.", log_context)
    return "Default RBAC data initialized successfully."
    
  except Exception as e: # This except corresponds to the main 'try' block at the beginning of the function
    log("CRITICAL", module_name, function_name, "Error during RBAC data initialization.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    return f"Error initializing RBAC data: {str(e)}"

# --- Helper for the new background task structure ---
def _get_permissions_and_roles_maps():
  """Internal helper to get all_permissions_map and roles_map."""
  # This is the permission definition part from the original reset function
  permissions_definitions = [
    # ... (COPY THE ENTIRE permissions_definitions list from initialize_default_rbac_data HERE) ...
    # Category: Public
    {"name": "view_public_products", "desc": "View publicly listed products", "cat": "Public Access"},
    {"name": "view_public_services", "desc": "View publicly listed services", "cat": "Public Access"},
    {"name": "view_public_subscription_plans", "desc": "View publicly listed subscription plans", "cat": "Public Access"},
    {"name": "view_public_documentation", "desc": "Access public help documentation", "cat": "Public Access"},
    {"name": "view_company_contact_info", "desc": "View company contact information", "cat": "Public Access"},
    {"name": "access_help_center", "desc": "Access the help center or FAQs", "cat": "Public Access"},
    # Category: Account Self-Service
    {"name": "edit_own_profile", "desc": "Edit own user profile details (excluding role)", "cat": "Account Self-Service"},
    {"name": "manage_own_payment_methods", "desc": "Add, update, or remove own payment methods", "cat": "Account Self-Service"},
    {"name": "view_own_usage_analytics", "desc": "View own usage data or analytics", "cat": "Account Self-Service"},
    {"name": "view_own_subscriptions", "desc": "View own active and past subscriptions", "cat": "Account Self-Service"},
    {"name": "manage_own_subscriptions", "desc": "General management of own subscriptions", "cat": "Account Self-Service"},
    {"name": "cancel_own_subscriptions", "desc": "Cancel own active subscriptions", "cat": "Account Self-Service"},
    {"name": "upgrade_downgrade_own_subscriptions", "desc": "Change/upgrade/downgrade own subscription plans", "cat": "Account Self-Service"},
    {"name": "view_own_orders", "desc": "View own order history", "cat": "Account Self-Service"},
    {"name": "view_own_invoices", "desc": "View and download own invoices", "cat": "Account Self-Service"},
    # Category: Product Catalog
    {"name": "view_all_items", "desc": "View all products, services, and subscription plan definitions", "cat": "Product Catalog"},
    {"name": "create_edit_items", "desc": "Create and edit products, services, and subscription plan definitions", "cat": "Product Catalog"},
    {"name": "delete_items", "desc": "Delete products, services, or subscription plan definitions", "cat": "Product Catalog"},
    {"name": "manage_subscription_groups", "desc": "Create, edit, and manage subscription groups", "cat": "Product Catalog"},
    {"name": "manage_prices_overrides", "desc": "Create, edit, and manage prices and price overrides for items", "cat": "Product Catalog"},
    # Category: Customer Admin
    {"name": "view_all_customers", "desc": "View list of all customers", "cat": "Customer Admin"},
    {"name": "view_customer_details", "desc": "View detailed profile of any customer", "cat": "Customer Admin"},
    {"name": "edit_customer_details", "desc": "Edit customer profile information", "cat": "Customer Admin"},
    {"name": "manage_customer_communications", "desc": "Manage or send communications to customers", "cat": "Customer Admin"},
    # Category: User & Role Admin
    {"name": "view_all_users_list", "desc": "View list of all users in the tenant app", "cat": "User & Role Admin"},
    {"name": "invite_users", "desc": "Invite new users to the tenant app", "cat": "User & Role Admin"},
    {"name": "edit_any_user_profile", "desc": "Edit profile details of any user", "cat": "User & Role Admin"},
    {"name": "enable_disable_users", "desc": "Enable or disable user accounts", "cat": "User & Role Admin"},
    {"name": "assign_user_roles", "desc": "Assign roles to users", "cat": "User & Role Admin"},
    {"name": "assign_tech_roles", "desc": "Assign 'Tech' or lower roles", "cat": "User & Role Admin"},
    {"name": "manage_roles", "desc": "Create, edit, delete custom roles (Owner only)", "cat": "User & Role Admin"},
    {"name": "manage_permissions_for_roles", "desc": "Assign/unassign permissions to roles (Owner only)", "cat": "User & Role Admin"},
    {"name": "delete_users", "desc": "Delete user accounts (with safeguards)", "cat": "User & Role Admin"},
    # Category: Discount Admin
    {"name": "view_discounts", "desc": "View all discount codes and their configurations", "cat": "Discount Admin"},
    {"name": "create_edit_discounts", "desc": "Create and edit discount codes", "cat": "Discount Admin"},
    {"name": "delete_discounts", "desc": "Delete discount codes", "cat": "Discount Admin"},
    # Category: Reporting
    {"name": "view_all_reports", "desc": "Access all standard business and operational reports", "cat": "Reporting"},
    {"name": "run_standard_reports", "desc": "Generate and view standard system reports", "cat": "Reporting"},
    {"name": "view_billing_summaries", "desc": "View summaries of billing and revenue", "cat": "Reporting"},
    {"name": "view_financial_reports", "desc": "Access detailed financial reports (Owner/Admin focus)", "cat": "Reporting"},
    {"name": "export_all_system_data", "desc": "Export comprehensive system data (Owner only)", "cat": "Reporting"},
    {"name": "export_audit_data", "desc": "Export audit log data (Owner/Admin)", "cat": "Reporting"},
    # Category: System Admin
    {"name": "view_system_logs", "desc": "View application system logs", "cat": "System Admin"},
    {"name": "view_webhook_settings", "desc": "View webhook endpoint configurations and history", "cat": "System Admin"},
    {"name": "manage_webhook_settings", "desc": "Retry webhook events, view details (not change secrets)", "cat": "System Admin"},
    {"name": "view_technical_documentation", "desc": "Access technical system documentation", "cat": "System Admin"},
    {"name": "access_api_documentation", "desc": "Access documentation for available APIs", "cat": "System Admin"},
    {"name": "view_system_health_metrics", "desc": "View system performance and health dashboards", "cat": "System Admin"},
    {"name": "view_error_reports", "desc": "View detailed error reports and diagnostics", "cat": "System Admin"},
    {"name": "access_api_keys", "desc": "Manage/view API keys for system integrations (Owner/Admin)", "cat": "System Admin"},
    # Category: Settings Admin
    {"name": "manage_app_settings", "desc": "Configure general application settings", "cat": "Settings Admin"},
    {"name": "manage_paddle_settings", "desc": "View Paddle integration settings", "cat": "Settings Admin"},
    {"name": "manage_mybizz_vault", "desc": "Manage secrets in the MyBizz Vault (Owner only)", "cat": "Settings Admin"},
    {"name": "manage_billing_settings", "desc": "Configure tenant company billing settings (Owner only)", "cat": "Settings Admin"},
    {"name": "manage_company_profile", "desc": "Edit tenant company's public profile information", "cat": "Settings Admin"},
    {"name": "manage_sso_integrations", "desc": "Configure Single Sign-On integrations (Owner only)", "cat": "Settings Admin"},
    # Category: Support
    {"name": "create_support_tickets", "desc": "Create new support tickets", "cat": "Support"},
    {"name": "manage_support_tickets", "desc": "View, assign, and respond to support tickets", "cat": "Support"},
    {"name": "submit_technical_support_requests", "desc": "Submit technical support requests to MyBizz platform support", "cat": "Support"},
    # Category: Security
    {"name": "view_audit_logs", "desc": "View audit trails of system and user actions", "cat": "Security"},
    {"name": "delete_critical_data", "desc": "Perform high-impact data deletions (Owner only)", "cat": "Security"},
    {"name": "approve_high_risk_operations", "desc": "Approve operations flagged as high-risk (Owner only)", "cat": "Security"},
    {"name": "view_security_alerts", "desc": "View system security alerts and notifications", "cat": "Security"},
  ]
  all_permissions_map = {}
  for p_def in permissions_definitions:
    p_row = _create_permission_if_not_exists(p_def["name"], p_def["desc"], p_def["cat"])
    if not p_row: 
      raise Exception(f"Failed to create/ensure permission {p_def['name']}")
    all_permissions_map[p_def["name"]] = p_row

  roles_definitions = [
    {"name": SYSTEM_ROLE_OWNER, "desc": "Full control over the tenant account and application.", "is_system": True},
    {"name": SYSTEM_ROLE_ADMIN, "desc": "Administrative access to manage most aspects of the application.", "is_system": True},
    {"name": SYSTEM_ROLE_TECH, "desc": "Technical staff access for system monitoring and support.", "is_system": True},
    {"name": SYSTEM_ROLE_USER, "desc": "Standard signed-up customer with self-service capabilities.", "is_system": True},
    {"name": SYSTEM_ROLE_VISITOR, "desc": "Anonymous or new visitor with limited public access.", "is_system": True},
  ]
  roles_map = {}
  for r_def in roles_definitions:
    r_row = _create_role_if_not_exists(r_def["name"], r_def["desc"], r_def["is_system"])
    if not r_row: 
      raise Exception(f"Failed to create/ensure role {r_def['name']}")
    roles_map[r_def["name"]] = r_row
  return all_permissions_map, roles_map

def _get_default_permission_set_for_role(role_name_key, all_permissions_map):
  """Returns the list of default permission names for a given system role key."""
  visitor_perms_list = [
    "view_public_products", "view_public_services", "view_public_subscription_plans",
    "view_public_documentation", "view_company_contact_info", "access_help_center"
  ]
  user_perms_list = visitor_perms_list + [
    "edit_own_profile", "manage_own_payment_methods", "view_own_usage_analytics",
    "view_own_subscriptions", "manage_own_subscriptions", "cancel_own_subscriptions",
    "upgrade_downgrade_own_subscriptions", "view_own_orders", "view_own_invoices",
    "create_support_tickets"
  ]
  tech_perms_list = user_perms_list + [
    "view_system_logs", "view_webhook_settings", "manage_webhook_settings",
    "view_all_users_list", "view_all_items", "view_technical_documentation",
    "access_api_documentation", "view_system_health_metrics", "view_error_reports",
    "submit_technical_support_requests", "manage_support_tickets"
  ]
  admin_perms_list = tech_perms_list + [
    "invite_users", "edit_any_user_profile", "enable_disable_users", "assign_tech_roles", "assign_user_roles",
    "create_edit_items", "delete_items", "manage_subscription_groups", "manage_prices_overrides",
    "view_discounts", "create_edit_discounts", "delete_discounts",
    "view_all_reports", "run_standard_reports", "view_billing_summaries",
    "manage_app_settings", "manage_customer_communications", "view_audit_logs",
    "manage_company_profile", "view_security_alerts"
  ]

  system_role_permission_sets = {
    SYSTEM_ROLE_VISITOR: visitor_perms_list,
    SYSTEM_ROLE_USER: user_perms_list,
    SYSTEM_ROLE_TECH: tech_perms_list,
    SYSTEM_ROLE_ADMIN: admin_perms_list,
    SYSTEM_ROLE_OWNER: list(all_permissions_map.keys())
  }
  return system_role_permission_sets.get(role_name_key, [])

@anvil.server.background_task
def _reset_permissions_for_single_role_task(role_name_key, next_task_function_name=None):
  module_name = "sm_rbac_mod"
  function_name = f"_reset_permissions_for_single_role_task ({role_name_key})"
  log("INFO", module_name, function_name, f"Background task started for role: {role_name_key}")

  try:
    all_permissions_map, roles_map = _get_permissions_and_roles_maps()
    role_row = roles_map.get(role_name_key)

    if not role_row:
      log("ERROR", module_name, function_name, f"Role {role_name_key} not found in roles_map. Task cannot proceed.")
      return

      # Clear existing permissions
    assignments_to_delete = list(app_tables.role_permission_mapping.search(role_id=role_row))
    deleted_count = 0
    if assignments_to_delete:
      for assignment in assignments_to_delete:
        assignment.delete()
        deleted_count += 1
    log("INFO", module_name, function_name, f"Deleted {deleted_count} assignments for role '{role_name_key}'.")

    # Assign default permissions
    default_perms_for_this_role = _get_default_permission_set_for_role(role_name_key, all_permissions_map)
    assigned_count = 0
    for p_name in default_perms_for_this_role:
      permission_row = all_permissions_map.get(p_name)
      if permission_row:
        try:
          app_tables.role_permission_mapping.add_row(
            role_id=role_row,
            permission_id=permission_row,
            assigned_at_anvil=datetime.now(timezone.utc)
          )
          assigned_count += 1
        except Exception as e_assign:
          log("ERROR", module_name, function_name, f"Failed to assign perm '{p_name}' to role '{role_name_key}'. Error: {e_assign}")
      else:
        log("WARNING", module_name, function_name, f"Perm '{p_name}' for role '{role_name_key}' not in all_permissions_map.")
    log("INFO", module_name, function_name, f"Assigned {assigned_count} default permissions to role '{role_name_key}'.")

    if next_task_function_name:
      log("INFO", module_name, function_name, f"Launching next task: {next_task_function_name}")
      anvil.server.launch_background_task(next_task_function_name)
    else:
      log("INFO", module_name, function_name, "All role permission resets complete.")
      # Optionally, notify the initiating user upon completion of all tasks
      # This would require passing the user ID through the tasks or storing it.

  except Exception as e:
    log("CRITICAL", module_name, function_name, f"Error resetting permissions for role {role_name_key}.", {"error": str(e), "trace": traceback.format_exc()})

# Create individual task functions for each role
@anvil.server.background_task
def _reset_owner_permissions_task():
  _reset_permissions_for_single_role_task(SYSTEM_ROLE_OWNER, '_reset_admin_permissions_task')

@anvil.server.background_task
def _reset_admin_permissions_task():
  _reset_permissions_for_single_role_task(SYSTEM_ROLE_ADMIN, '_reset_tech_permissions_task')

@anvil.server.background_task
def _reset_tech_permissions_task():
  _reset_permissions_for_single_role_task(SYSTEM_ROLE_TECH, '_reset_user_permissions_task')

@anvil.server.background_task
def _reset_user_permissions_task():
  _reset_permissions_for_single_role_task(SYSTEM_ROLE_USER, '_reset_visitor_permissions_task')

@anvil.server.background_task
def _reset_visitor_permissions_task():
  _reset_permissions_for_single_role_task(SYSTEM_ROLE_VISITOR, None) # Last task

# 3. New Orchestrator Function (replaces the old reset_system_role_permissions_to_default)
@anvil.server.callable(require_user=True)
def start_system_role_permissions_reset():
  module_name = "sm_rbac_mod"
  function_name = "start_system_role_permissions_reset"

  user = anvil.users.get_user()
  if not user or not user['role'] or user['role']['name'] != SYSTEM_ROLE_OWNER:
    log("WARNING", module_name, function_name, "Attempt to start reset by non-Owner.", {"user_email": user['email'] if user else "Unknown"})
    raise anvil.server.PermissionDenied("Only an Owner can start the system role permissions reset.")

  log("INFO", module_name, function_name, "Owner initiated system role permissions reset. Launching first background task for Owner role.")

  # Ensure all permissions and roles are created/verified synchronously first.
  # This part is quick and essential before background tasks.
  try:
    all_permissions_map, roles_map = _get_permissions_and_roles_maps()
    if not all_permissions_map or not roles_map: # Basic check
      log("CRITICAL", module_name, function_name, "Failed to get permissions/roles maps. Aborting reset start.")
      return "Error: Could not verify core permissions/roles before starting reset."
    log("INFO", module_name, function_name, "Core permissions and roles verified. Starting background tasks.")
  except Exception as e_init_check:
    log("CRITICAL", module_name, function_name, f"Critical error during pre-reset check: {str(e_init_check)}", {"trace": traceback.format_exc()})
    return f"Error during pre-reset check: {str(e_init_check)}"

    # Launch the first task in the chain
  anvil.server.launch_background_task('_reset_owner_permissions_task')

  return "System role permissions reset process initiated in the background. Check logs for progress."

@anvil.server.callable(require_user=True) # Or restrict to users with 'manage_rbac' permission
def get_all_roles():
  """
    Fetches all roles from the 'roles' table.
    Returns a list of dictionaries, each containing role details.
    """
  module_name = "sm_rbac_mod"
  function_name = "get_all_roles"
  log("INFO", module_name, function_name, "Fetching all roles.")

  # Permission Check: Ensure user has permission to view roles
  # user = anvil.users.get_user()
  # if not user_has_permission(user, "manage_roles"): # Assuming 'manage_roles' is Owner only
  #     log("WARNING", module_name, function_name, "Permission denied to get all roles.", {"user_email": user['email'] if user else "Unknown"})
  #     raise anvil.server.PermissionDenied("You do not have permission to view roles.")

  try:
    role_rows = app_tables.roles.search(tables.order_by("name"))
    roles_list = []
    for r_row in role_rows:
      roles_list.append({
        'role_id_anvil': r_row.get_id(), # Anvil's internal row ID
        'role_id_mybizz': r_row['role_id'], # Your custom unique ID for the role
        'name': r_row['name'],
        'description': r_row['description'],
        'is_system_role': r_row['is_system_role']
        # Add other fields if needed by the client
      })
    log("INFO", module_name, function_name, f"Successfully fetched {len(roles_list)} roles.")
    return roles_list
  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error fetching all roles.", {"error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while fetching roles: {str(e)}")


# In sm_rbac_mod.py

# In sm_rbac_mod.py

@anvil.server.callable(require_user=True) 
def get_all_permissions():
  module_name = "sm_rbac_mod"
  function_name = "get_all_permissions"
  log("INFO", module_name, function_name, "Attempting to fetch all permissions.")

  try:
    log("DEBUG", module_name, function_name, "Executing app_tables.permissions.search with order_by.")
    permission_rows = app_tables.permissions.search(
      tables.order_by("category", ascending=True), 
      tables.order_by("name", ascending=True)
    )
    # Convert iterator to list to get length for logging, then iterate original iterator
    # This is slightly less efficient but good for debugging this specific issue.
    # For production, if len is not strictly needed here, iterate permission_rows directly.
    temp_permission_rows_list = list(permission_rows)
    log("DEBUG", module_name, function_name, f"Search complete. Found {len(temp_permission_rows_list)} potential rows.")

    permissions_list = []
    row_count = 0
    # Iterate over the temporary list now
    for p_row in temp_permission_rows_list: 
      row_count += 1
      log("DEBUG", module_name, function_name, f"Processing row {row_count}. Row object: {p_row}")
      if p_row is None:
        log("WARNING", module_name, function_name, f"Encountered a None row at index {row_count -1} in permission_rows.")
        continue

      try:
        permission_id_anvil = p_row.get_id()

        # MODIFIED - Use direct dictionary access for 'permission_id'
        # Ensure 'permission_id' is the correct column name for your custom PK.
        # If it can be None or missing, use p_row.get('permission_id')
        permission_id_mybizz = p_row['permission_id'] if 'permission_id' in p_row else None

        name = p_row['name'] 
        description = p_row['description'] 
        category = p_row['category'] 

        permissions_list.append({
          'permission_id_anvil': permission_id_anvil, 
          'permission_id_mybizz': permission_id_mybizz, 
          'name': name,
          'description': description,
          'category': category
        })
        log("DEBUG", module_name, function_name, f"Successfully processed and appended row {row_count} with name '{name}'.")
      except Exception as e_row_processing:
        # Prepare context for logging, ensuring serializability
        row_data_preview_serializable = {}
        if p_row:
          try:
            row_data_preview_serializable = {k: str(v) for k, v in dict(p_row).items()}
          except Exception:
            row_data_preview_serializable = {"error": "Could not serialize row data"}
        else:
          row_data_preview_serializable = {"error": "p_row is None"}

        log("ERROR", module_name, function_name, f"Error processing row {row_count}. Anvil ID: {p_row.get_id() if p_row else 'N/A'}. Error: {str(e_row_processing)}", {"row_data_preview": row_data_preview_serializable, "trace": traceback.format_exc()})

    log("INFO", module_name, function_name, f"Successfully processed {len(permissions_list)} permissions into list.")
    return permissions_list

  except Exception as e:
    log("ERROR", module_name, function_name, "General error fetching all permissions.", {"error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred server-side while fetching permissions: {str(e)}")

@anvil.server.callable(require_user=True) # Or restrict
def get_permissions_for_role(role_anvil_id):
  """
    Fetches all permission_id_mybizz (the unique name like 'view_users')
    assigned to a specific role.

    Args:
        role_anvil_id (str): The Anvil Row ID of the role.
    
    Returns:
        list: A list of permission names (strings) assigned to the role.
    """
  module_name = "sm_rbac_mod"
  function_name = "get_permissions_for_role"
  log_context = {"role_anvil_id": role_anvil_id}

  if not role_anvil_id:
    log("WARNING", module_name, function_name, "No role_anvil_id provided.", log_context)
    return []

  log("INFO", module_name, function_name, "Fetching permissions for role.", log_context)

  # Permission Check
  # ...

  try:
    role_row = app_tables.roles.get_by_id(role_anvil_id)
    if not role_row:
      log("WARNING", module_name, function_name, "Role not found for the given role_anvil_id.", log_context)
      return []

    log_context['role_name'] = role_row['name']

    assigned_mappings = app_tables.role_permission_mapping.search(role_id=role_row)

    permission_names_assigned = []
    for mapping in assigned_mappings:
      if mapping['permission_id'] and mapping['permission_id']['name']: # Ensure link and name exist
        permission_names_assigned.append(mapping['permission_id']['name'])
      else:
        log("WARNING", module_name, function_name, "Found a role_permission_mapping with a missing or invalid permission_id link.", 
            {**log_context, "mapping_id": mapping.get_id(), "linked_permission_id_obj": mapping['permission_id']})

    log("INFO", module_name, function_name, f"Role '{role_row['name']}' has {len(permission_names_assigned)} permissions assigned.", log_context)
    return permission_names_assigned
  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error fetching permissions for role.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while fetching permissions for the role: {str(e)}")

@anvil.server.callable(require_user=True) 
def update_permissions_for_role(role_anvil_id, list_of_permission_names_to_assign):
  """
    Updates all permission assignments for a given role.
    It first clears all existing assignments for the role, then adds the new ones.
    """
  module_name = "sm_rbac_mod"
  function_name = "update_permissions_for_role"
  log_context = {"role_anvil_id": role_anvil_id, "num_permissions_to_assign": len(list_of_permission_names_to_assign)}

  # user = anvil.users.get_user() # Only get user if needed for an immediate permission check or logging
  # For now, assuming require_user=True is the primary check, detailed permission check to be added.
  # If user_has_permission is implemented and used here, then user = anvil.users.get_user() would be needed.

  if not role_anvil_id:
    log("ERROR", module_name, function_name, "No role_anvil_id provided.", log_context)
    raise ValueError("Role ID must be provided to update permissions.")

  log("INFO", module_name, function_name, "Attempting to update permissions for role.", log_context)

  try:
    role_row = app_tables.roles.get_by_id(role_anvil_id)
    if not role_row:
      log("ERROR", module_name, function_name, "Role not found for the given role_anvil_id.", log_context)
      raise ValueError(f"Role with ID '{role_anvil_id}' not found.")

    log_context['role_name'] = role_row['name']

    log("INFO", module_name, function_name, f"Clearing existing permissions for role '{role_row['name']}'.", log_context)
    existing_assignments = app_tables.role_permission_mapping.search(role_id=role_row)
    deleted_count = 0
    for assignment in existing_assignments:
      assignment.delete()
      deleted_count += 1
    log("INFO", module_name, function_name, f"Deleted {deleted_count} existing assignments for role '{role_row['name']}'.", log_context)

    assigned_count = 0
    for permission_name in list_of_permission_names_to_assign:
      permission_row = app_tables.permissions.get(name=permission_name)
      if permission_row:
        _assign_permission_to_role_if_not_exists(role_row, permission_row)
        assigned_count += 1
      else:
        log("WARNING", module_name, function_name, f"Permission '{permission_name}' not found in permissions table. Cannot assign to role '{role_row['name']}'.", 
            {**log_context, "missing_permission_name": permission_name})

    log("INFO", module_name, function_name, f"Assigned {assigned_count} permissions to role '{role_row['name']}'.", log_context)
    return f"Permissions for role '{role_row['name']}' updated successfully."

  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error updating permissions for role.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while updating permissions for the role: {str(e)}")


@anvil.server.callable(require_user=True)
def create_custom_role(name, description):
  """
    Creates a new custom (non-system) role.
    Ensures role name is unique.
    """
  module_name = "sm_rbac_mod"
  function_name = "create_custom_role"
  log_context = {"role_name_to_create": name, "description": description}

  # user = anvil.users.get_user() # Only get user if needed for an immediate permission check or logging
  # For now, assuming require_user=True is the primary check.

  if not name or not name.strip():
    log("WARNING", module_name, function_name, "Role name cannot be empty.", log_context)
    raise ValueError("Role name cannot be empty.")

  name = name.strip()
  log_context["role_name_to_create"] = name 

  log("INFO", module_name, function_name, "Attempting to create custom role.", log_context)

  try:
    existing_role = app_tables.roles.get(name=name)
    if existing_role:
      log("WARNING", module_name, function_name, f"Role name '{name}' already exists.", log_context)
      raise ValueError(f"A role with the name '{name}' already exists.")

    new_role_row = _create_role_if_not_exists(name, description, is_system_role=False)

    if not new_role_row: 
      log("ERROR", module_name, function_name, "Failed to create role using helper, but no exception was raised.", log_context)
      raise Exception("Role creation failed unexpectedly.")

    log("INFO", module_name, function_name, f"Custom role '{name}' created successfully.", {**log_context, "new_role_anvil_id": new_role_row.get_id()})
    return {
      'role_id_anvil': new_role_row.get_id(),
      'role_id_mybizz': new_role_row['role_id'],
      'name': new_role_row['name'],
      'description': new_role_row['description'],
      'is_system_role': new_role_row['is_system_role']
    }
  except ValueError as ve: 
    raise ve
  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error creating custom role.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while creating the role: {str(e)}")

    
@anvil.server.callable(require_user=True)
def update_custom_role(role_anvil_id, name, description):
  """
    Updates the name and/or description of an existing CUSTOM role.
    System roles cannot be modified in this way (name/description).
    """
  module_name = "sm_rbac_mod"
  function_name = "update_custom_role"
  log_context = {"role_anvil_id_to_update": role_anvil_id, "new_name": name, "new_description": description}

  # user = anvil.users.get_user() # Only get user if needed for an immediate permission check or logging
  # For now, assuming require_user=True is the primary check.

  if not role_anvil_id:
    log("WARNING", module_name, function_name, "No role_anvil_id provided for update.", log_context)
    raise ValueError("Role ID must be provided for update.")
  if not name or not name.strip():
    log("WARNING", module_name, function_name, "Role name cannot be empty for update.", log_context)
    raise ValueError("Role name cannot be empty.")

  name = name.strip()
  log_context["new_name"] = name

  log("INFO", module_name, function_name, "Attempting to update custom role.", log_context)

  try:
    role_row = app_tables.roles.get_by_id(role_anvil_id)
    if not role_row:
      log("ERROR", module_name, function_name, "Role to update not found.", log_context)
      raise ValueError(f"Role with ID '{role_anvil_id}' not found.")

    log_context['original_role_name'] = role_row['name']

    if role_row['is_system_role']:
      log("WARNING", module_name, function_name, f"Attempt to update a system role '{role_row['name']}'. Denied.", log_context)
      raise PermissionError("System roles (name/description) cannot be modified directly.")

    if role_row['name'] != name: 
      existing_role_with_new_name = app_tables.roles.get(name=name)
      if existing_role_with_new_name and existing_role_with_new_name.get_id() != role_anvil_id:
        log("WARNING", module_name, function_name, f"New role name '{name}' already exists for a different role.", log_context)
        raise ValueError(f"A role with the name '{name}' already exists.")

    role_row.update(
      name=name,
      description=description,
      updated_at_anvil=datetime.now(timezone.utc)
    )
    log("INFO", module_name, function_name, f"Custom role '{name}' updated successfully.", log_context)
    return {
      'role_id_anvil': role_row.get_id(),
      'role_id_mybizz': role_row['role_id'],
      'name': role_row['name'],
      'description': role_row['description'],
      'is_system_role': role_row['is_system_role']
    }
  except (ValueError, PermissionError) as ve: 
    raise ve
  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error updating custom role.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while updating the role: {str(e)}")

@anvil.server.callable(require_user=True)
def delete_custom_role(role_anvil_id):
  """
    Deletes a CUSTOM role. System roles cannot be deleted.
    Also deletes associated mappings in role_permission_mapping.
    Checks if any users are currently assigned to this role before deletion.
    """
  module_name = "sm_rbac_mod"
  function_name = "delete_custom_role"
  log_context = {"role_anvil_id_to_delete": role_anvil_id}

  # user = anvil.users.get_user() # Only get user if needed for an immediate permission check or logging
  # For now, assuming require_user=True is the primary check.

  if not role_anvil_id:
    log("WARNING", module_name, function_name, "No role_anvil_id provided for deletion.", log_context)
    raise ValueError("Role ID must be provided for deletion.")

  log("INFO", module_name, function_name, "Attempting to delete custom role.", log_context)

  try:
    role_row = app_tables.roles.get_by_id(role_anvil_id)
    if not role_row:
      log("ERROR", module_name, function_name, "Role to delete not found.", log_context)
      raise ValueError(f"Role with ID '{role_anvil_id}' not found.")

    role_name_deleted = role_row['name']
    log_context['role_name_being_deleted'] = role_name_deleted

    if role_row['is_system_role']:
      log("WARNING", module_name, function_name, f"Attempt to delete a system role '{role_name_deleted}'. Denied.", log_context)
      raise PermissionError("System roles cannot be deleted.")

    users_with_this_role = app_tables.users.search(role=role_row)
    # Convert SearchIterator to list to get its length or check if it's empty
    assigned_users_list = list(users_with_this_role)
    if assigned_users_list: # Check if the list is not empty
      user_count = len(assigned_users_list)
      log("WARNING", module_name, function_name, f"Cannot delete role '{role_name_deleted}' as {user_count} user(s) are currently assigned to it.", {**log_context, "assigned_user_count": user_count})
      raise ValueError(f"Cannot delete role '{role_name_deleted}'. It is currently assigned to {user_count} user(s). Please reassign them first.")

    mappings_to_delete = app_tables.role_permission_mapping.search(role_id=role_row)
    deleted_mapping_count = 0
    for mapping in mappings_to_delete:
      mapping.delete()
      deleted_mapping_count += 1
    log("INFO", module_name, function_name, f"Deleted {deleted_mapping_count} permission mappings for role '{role_name_deleted}'.", log_context)

    role_row.delete()

    log("INFO", module_name, function_name, f"Custom role '{role_name_deleted}' and its permission mappings deleted successfully.", log_context)
    return f"Role '{role_name_deleted}' deleted successfully."

  except (ValueError, PermissionError) as ve: 
    raise ve
  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, "Error deleting custom role.", {**log_context, "error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError(f"An error occurred while deleting the role: {str(e)}")


# This is the complete get_all_users_with_role_details function for sm_rbac_mod.py

# This is the complete get_all_users_with_role_details function for sm_rbac_mod.py

# This is a DIAGNOSTIC version of the get_all_users_with_role_details function.

# This is the complete get_all_users_with_role_details function for sm_rbac_mod.py

@anvil.server.callable(require_user=True)
def get_all_users_with_role_details():
  """
    Fetches all users with their role details, correctly handling LiveObjectProxy
    objects returned by the data service.
    """
  import traceback
  import anvil.tables.query as q
  module_name = "sm_rbac_mod"
  function_name = "get_all_users_with_role_details"
  log("INFO", module_name, function_name, "Attempting to fetch all users with role details.")

  try:
    # Step 1: Get a simple, stable list of all user emails.
    all_user_emails = [r['email'] for r in app_tables.users.search(email=q.not_(None))]
    users_with_roles_list = []
    log("DEBUG", module_name, function_name, f"Found {len(all_user_emails)} valid user emails to process.")

    # Step 2: Loop through the email list and fetch each user row individually.
    for email in all_user_emails:
      try:
        user_row = app_tables.users.get(email=email)

        if not user_row:
          log("WARNING", module_name, function_name, f"Could not retrieve user row for email '{email}', skipping.")
          continue

        log("DEBUG", module_name, function_name, f"Processing user: {email}")

        # Use dictionary-style access for LiveObjectProxy.
        # Use try/except KeyError for safety with optional columns.
        user_dict = {'anvil_user_id': user_row.get_id(), 'email': user_row['email']}

        try: 
          user_dict['enabled'] = user_row['enabled']
        except KeyError: 
          user_dict['enabled'] = None

        try: 
          user_dict['confirmed_email'] = user_row['confirmed_email']
        except KeyError: 
          user_dict['confirmed_email'] = None

        try: 
          user_dict['first_name'] = user_row['first_name']
        except KeyError: 
          user_dict['first_name'] = None

        try:
          user_dict['last_name'] = user_row['last_name']
        except KeyError: 
          user_dict['last_name'] = None

        try: 
          user_dict['full_name'] = user_row['full_name']
        except KeyError: 
          user_dict['full_name'] = None

        try: 
          user_dict['signed_up'] = user_row['signed_up']
        except KeyError: 
          user_dict['signed_up'] = None

        try: 
          user_dict['last_login'] = user_row['last_login']
        except KeyError: 
          user_dict['last_login'] = None

        user_dict['role_name'] = None
        user_dict['role_anvil_id'] = None

        try:
          assigned_role_link = user_row['role']
          if assigned_role_link and assigned_role_link['name']:
            user_dict['role_name'] = assigned_role_link['name']
            user_dict['role_anvil_id'] = assigned_role_link.get_id()
        except KeyError:
          pass # Role is not assigned, values remain None.

        users_with_roles_list.append(user_dict)

      except Exception as e_proc:
        log("ERROR", module_name, function_name, f"Error processing individual user with email '{email}': {str(e_proc)}", 
            {"trace": traceback.format_exc()})
        continue

    log("INFO", module_name, function_name, f"Successfully processed {len(users_with_roles_list)} users.")
    return users_with_roles_list

  except Exception as e:
    log("ERROR", module_name, function_name, "Outer error during robust user fetch.", 
        {"error": str(e), "trace": traceback.format_exc()})
    raise anvil.server.AnvilWrappedError("An error occurred while fetching user data. Please check server logs.")

# Add this function to sm_rbac_mod.py

def user_has_permission(permission_name_to_check, user_obj=None):
  """
    Checks if a given user (or the currently logged-in user if user_obj is None)
    has a specific permission.

    Args:
        permission_name_to_check (str): The unique name of the permission (e.g., "create_edit_items").
        user_obj (anvil.users.Row, optional): The user row object to check. 
                                             If None, anvil.users.get_user() is used.

    Returns:
        bool: True if the user has the permission, False otherwise.
    """
  module_name = "sm_rbac_mod"
  function_name = "user_has_permission"

  if user_obj is None:
    user_obj = anvil.users.get_user()

  if not user_obj:
    # log("DEBUG", module_name, function_name, f"Permission check for '{permission_name_to_check}': No user logged in or provided.")
    return False # No user, so no permissions

  user_role_link = user_obj.get('role') # Get the linked role row from the user object

  if not user_role_link:
    # log("DEBUG", module_name, function_name, f"Permission check for '{permission_name_to_check}': User '{user_obj['email']}' has no role assigned.")
    return False # User has no role, so no permissions from roles

    # Ensure we have the full role row, not just a proxy, to be safe
  try:
    # It's possible user_role_link is already the full row.
    # Accessing an attribute forces a fetch if it's a proxy.
    # If it's already fetched, this is quick.
    # We need the role_id (Anvil's internal ID) of the role row.
    role_anvil_id = user_role_link.get_id()
    if not role_anvil_id: # Should not happen if user_role_link is a valid row object
      log("WARNING", module_name, function_name, f"Permission check for '{permission_name_to_check}': User '{user_obj['email']}' role link has no ID. Role link: {user_role_link}")
      return False

      # Fetch the role row again by ID to ensure we have its direct attributes if needed,
      # though for searching role_permission_mapping, the link object itself is usually sufficient.
      # For clarity and robustness, let's use the fetched role_row.
    actual_role_row = app_tables.roles.get_by_id(role_anvil_id)
    if not actual_role_row:
      log("WARNING", module_name, function_name, f"Permission check for '{permission_name_to_check}': Role row not found by ID '{role_anvil_id}' for user '{user_obj['email']}'.")
      return False

  except Exception as e_role_fetch:
    log("ERROR", module_name, function_name, f"Error fetching role details for user '{user_obj['email']}' during permission check for '{permission_name_to_check}'. Error: {str(e_role_fetch)}")
    return False # Error fetching role details

    # Find the permission row by its name
  permission_row_to_check = app_tables.permissions.get(name=permission_name_to_check)
  if not permission_row_to_check:
    # log("WARNING", module_name, function_name, f"Permission check: Permission name '{permission_name_to_check}' not found in permissions table.")
    return False # Permission doesn't exist in the system

    # Check if a mapping exists in role_permission_mapping
  mapping_exists = app_tables.role_permission_mapping.get(
    role_id=actual_role_row, # Use the fully fetched role row
    permission_id=permission_row_to_check
  )

  if mapping_exists:
    # log("DEBUG", module_name, function_name, f"Permission '{permission_name_to_check}' GRANTED for user '{user_obj['email']}' via role '{actual_role_row['name']}'.")
    return True
  else:
    # log("DEBUG", module_name, function_name, f"Permission '{permission_name_to_check}' DENIED for user '{user_obj['email']}' via role '{actual_role_row['name']}'.")
    return False

@anvil.server.callable(require_user=True)
def get_user_permissions_for_ui():
  """
    Fetches all permission names assigned to the currently logged-in user's role.
    This is intended to be called by client forms to adapt the UI.
    Returns a list of permission name strings (e.g., ["create_edit_items", "view_all_users_list"]).
    Returns an empty list if the user has no role or no permissions.
    """
  module_name = "sm_rbac_mod"
  function_name = "get_user_permissions_for_ui"

  user_obj = anvil.users.get_user()
  if not user_obj:
    log("INFO", module_name, function_name, "No user logged in. Returning empty permission list.")
    return []

  user_email_for_log = user_obj['email'] if 'email' in user_obj else "Unknown User (no email)"

  user_role_link = None
  if 'role' in user_obj: # Check if 'role' key exists
    user_role_link = user_obj['role']

  log("DEBUG", module_name, function_name, f"User: {user_email_for_log}, Role Link from user object: {user_role_link}")

  if not user_role_link:
    log("INFO", module_name, function_name, f"User '{user_email_for_log}' has no role assigned. Returning empty permission list.")
    return []

  actual_role_row = None
  try:
    if hasattr(user_role_link, 'get_id'): # Check if it's a row proxy/row object
      role_anvil_id = user_role_link.get_id()
      if role_anvil_id:
        actual_role_row = app_tables.roles.get_by_id(role_anvil_id)

    if not actual_role_row and 'name' in user_role_link: # Fallback if get_id failed or link is just a dict with name
      actual_role_row = app_tables.roles.get(name=user_role_link['name'])

    if not actual_role_row:
      log("WARNING", module_name, function_name, f"Could not fully resolve role for user '{user_email_for_log}'. Role link: {user_role_link}. Returning empty permission list.")
      return []

    log("DEBUG", module_name, function_name, f"Resolved role for {user_email_for_log} to: {actual_role_row['name']} (Anvil ID: {actual_role_row.get_id()})")

  except Exception as e_role_fetch:
    log("ERROR", module_name, function_name, f"Error fetching/resolving role details for user '{user_email_for_log}'. Error: {str(e_role_fetch)}", {"trace": traceback.format_exc()})
    return [] 

  try:
    # get_permissions_for_role expects the Anvil Row ID of the role
    permission_names = get_permissions_for_role(actual_role_row.get_id())
    log("DEBUG", module_name, function_name, f"Permissions returned by get_permissions_for_role for role '{actual_role_row['name']}': {permission_names}")
    return permission_names
  except Exception as e:
    log("ERROR", module_name, function_name, f"Error calling get_permissions_for_role for user '{user_email_for_log}'. Error: {str(e)}", {"trace": traceback.format_exc()})
    return []


@anvil.server.callable(require_user=True)
def get_user_data_for_ui():
  """
    Securely fetches the current user's email, role name, permissions, and profile completion status.
    This version uses the proven pattern of fetching a fresh user row and robustly accessing all custom columns.
    """
  module_name = "sm_rbac_mod"
  function_name = "get_user_data_for_ui"

  session_user = anvil.users.get_user()
  if not session_user:
    log("WARNING", module_name, function_name, "Function called but no user was found.")
    return {"email": "Guest", "role_name": "Visitor", "permissions": [], "profile_complete": False}

  try:
    user_email = session_user['email']
    full_user_row = app_tables.users.get(email=user_email)

    if not full_user_row:
      log("CRITICAL", module_name, function_name, f"User '{user_email}' is authenticated but has no corresponding row in the 'users' table.")
      raise Exception("User data integrity error. Please contact support.")

    email = full_user_row['email']
    role_name = "No Role Assigned"
    permissions = []

    # --- Robustly access the 'profile_complete' column using EAFP ---
    profile_complete = False # Default value
    try:
      # Try to get the value. This will raise a KeyError if the column doesn't exist.
      retrieved_value = full_user_row['profile_complete']
      # If the column exists but is empty (None), it will be treated as False.
      if retrieved_value is True:
        profile_complete = True
    except KeyError:
      # This handles the case where the column itself doesn't exist on the row object.
      log("WARNING", module_name, function_name, f"The 'profile_complete' column does not exist on the user row for '{email}'. Defaulting to False.", {"user_id": full_user_row.get_id()})

    # --- Robustly access the 'role' column using EAFP ---
    try:
      role_link = full_user_row['role']
      if role_link:
        role_name = role_link['name']
        permissions = get_permissions_for_role(role_link.get_id())
      else:
        log("WARNING", module_name, function_name, f"User '{email}' has a 'role' column, but it is empty (None).", {"user_id": full_user_row.get_id()})

    except KeyError:
      log("ERROR", module_name, function_name, f"A KeyError occurred when accessing the role or role name for user '{email}'.", {"user_id": full_user_row.get_id()})
      role_name = "Unnamed Role"

    log("INFO", module_name, function_name, f"Successfully fetched UI data for user '{email}'.", {"role": role_name, "permission_count": len(permissions), "profile_complete": profile_complete})

    return {
      "email": email,
      "role_name": role_name,
      "permissions": permissions,
      "profile_complete": profile_complete
    }
  except Exception as e:
    import traceback
    user_id_for_log = session_user.get_id() if hasattr(session_user, 'get_id') else "N/A"
    log("CRITICAL", module_name, function_name, "An unexpected error occurred while fetching user UI data.", 
        {"user_id": user_id_for_log, "error": str(e), "trace": traceback.format_exc()})
    raise e

@anvil.server.callable(require_user=True)
def update_user_profile_names(first_name, last_name):
  """
    Updates the current user's profile with their first and last name,
    concatenates to create a full name, and sets the profile_complete flag to True.
    """
  module_name = "sm_rbac_mod"
  function_name = "update_user_profile_names"

  user = anvil.users.get_user()
  if not user:
    # This should not be hit due to require_user=True, but is a safeguard.
    raise anvil.server.PermissionDenied("You must be logged in to update your profile.")

  # --- Server-side validation ---
  first_name = first_name.strip()
  last_name = last_name.strip()
  if not first_name or not last_name:
    raise ValueError("First Name and Last Name cannot be empty.")

  try:
    # --- Update the user row ---
    user.update(
      first_name=first_name,
      last_name=last_name,
      full_name=f"{first_name} {last_name}",
      profile_complete=True
    )
    log("INFO", module_name, function_name, f"User profile updated successfully for {user['email']}.", {"user_id": user.get_id()})
    return True

  except Exception as e:
    import traceback
    log("ERROR", module_name, function_name, f"Failed to update profile for user {user['email']}.", 
        {"user_id": user.get_id(), "error": str(e), "trace": traceback.format_exc()})
    # Re-raise the exception to inform the client of the failure.
    raise Exception(f"Could not update profile: {str(e)}")