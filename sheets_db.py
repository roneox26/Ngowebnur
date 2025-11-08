import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

class SheetsDB:
    _instance = None
    
    def __new__(cls, credentials_file='credentials.json', spreadsheet_name='NGO Management'):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, credentials_file='credentials.json', spreadsheet_name='NGO Management'):
        if not hasattr(self, 'client'):
            if not os.path.exists(credentials_file):
                self.enabled = False
                return
            try:
                scopes = ['https://www.googleapis.com/auth/spreadsheets']
                creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
                self.client = gspread.authorize(creds)
                self.spreadsheet = self.client.open(spreadsheet_name)
                self.enabled = True
            except:
                self.enabled = False
    
    def sync_customer(self, customer):
        if not self.enabled:
            return
        try:
            sheet = self.spreadsheet.worksheet('Customers')
            sheet.append_row([customer.id, customer.name, customer.phone, customer.address, 
                            customer.total_loan, customer.remaining_loan, customer.savings_balance, 
                            str(customer.created_date)])
        except:
            pass
    
    def sync_loan(self, loan):
        if not self.enabled:
            return
        try:
            sheet = self.spreadsheet.worksheet('Loans')
            sheet.append_row([loan.id, loan.customer_name, loan.amount, loan.interest, 
                            str(loan.loan_date), str(loan.due_date)])
        except:
            pass
    
    def sync_loan_collection(self, collection, customer_name):
        if not self.enabled:
            return
        try:
            sheet = self.spreadsheet.worksheet('Loan Collections')
            sheet.append_row([collection.id, customer_name, collection.amount, 
                            str(collection.collection_date)])
        except:
            pass
    
    def sync_saving_collection(self, collection, customer_name):
        if not self.enabled:
            return
        try:
            sheet = self.spreadsheet.worksheet('Saving Collections')
            sheet.append_row([collection.id, customer_name, collection.amount, 
                            str(collection.collection_date)])
        except:
            pass

sheets_db = SheetsDB()
