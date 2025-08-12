import anvil.email
import anvil.users
import anvil.google.auth, anvil.google.drive, anvil.google.mail
from anvil.google.drive import app_files
import anvil.files
from anvil.files import data_files
import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from sm_logs_mod import log

@anvil.server.callable
def get_products_with_settings():
    """Fetch product data and app settings, including images from Anvil's built-in Files table."""
    products = app_tables.product.search()
    settings = {s['setting_name']: s['value_bool'] for s in app_tables.app_settings.search()}  

    product_list = []
    for product in products:
        file_row = product['media']  # Now linked to 'Files' table

        product_list.append({
            'product_id': product.get_id(),
            'product_name': product['product_name'],
            'product_description': product['product_description'],
            'product_status': product['product_status'],
            'currency_code': product['currency_id']['currency_code'] if product['currency_id'] else "N/A",
            'base_price': product['price_id']['base_price'] if product['price_id'] else None,
            'tax_included': settings.get('tax_included', False),
            'image': file_row['file'] if file_row else None  # ✅ Get actual image file
        })

    return product_list
