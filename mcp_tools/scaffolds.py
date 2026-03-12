class ZendeskClient:
    def fetch_tickets(self): pass

class FreshdeskClient:
    def fetch_tickets(self): pass

class ServiceNowClient:
    def create_incident(self, data): pass

class JiraClient:
    def create_issue(self, data): pass

class SlackClient:
    def send_message(self, channel, text): pass

class CRMClient:
    """Unified Salesforce + HubSpot"""
    def sync_contact(self, email): pass

class GoogleSheetsClient:
    def append_row(self, sheet_id, row): pass
