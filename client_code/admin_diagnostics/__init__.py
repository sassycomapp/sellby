from ._anvil_designer import admin_diagnosticsTemplate
from anvil import *
import anvil.server
import anvil.users
from anvil.tables import app_tables

class admin_diagnostics(admin_diagnosticsTemplate):

    def __init__(self, **properties):
        self.init_components(**properties)
        self.run_diagnostics()

    def run_diagnostics(self):
        try:
            result = anvil.server.call('run_admin_diagnostics')
    
            if 'error' in result:
                alert(result['error'])
                return
    
            self.lbl_user_email.text = f"Logged in as: {result['email']}"
            self.lbl_is_admin.text = f"Server says admin: {result['is_admin']}"
            self.lbl_temp_admin.text = f"Temp session active: {result['temp_session_active']}"
    
            if isinstance(result['session_info'], dict):
                self.lbl_session.text = (
                    f"Session found:\n"
                    f"  is_temp_admin={result['session_info']['is_temp_admin']}\n"
                    f"  expires_at={result['session_info']['expires_at']}\n"
                    f"  created_at={result['session_info']['created_at']}"
                )
            else:
                self.lbl_session.text = result['session_info']
    
            if isinstance(result['vault_info'], dict):
                self.lbl_vault_secret.text = (
                    f"Vault entry for owner_password:\n"
                    f"  owner: {result['vault_info']['owner_email']}"
                )
            else:
                self.lbl_vault_secret.text = result['vault_info']
    
        except Exception as e:
            alert(f"Error running diagnostics: {e}")