from sheets_db import SheetsDB
from datetime import datetime

# Initialize
db = SheetsDB('credentials.json', 'NGO Management System')

# Customer যোগ করুন
def add_customer(name, phone, address, staff_id):
    customer_id = len(db.get_all('customers')) + 1
    data = [customer_id, name, phone, address, 0, 0, staff_id, datetime.now().strftime('%Y-%m-%d')]
    db.insert('customers', data)
    return customer_id

# Loan যোগ করুন
def add_loan(customer_id, amount, interest, due_date):
    loan_id = len(db.get_all('loans')) + 1
    data = [loan_id, customer_id, amount, interest, datetime.now().strftime('%Y-%m-%d'), due_date, amount]
    db.insert('loans', data)
    
    # Customer এর remaining_loan update করুন
    customers = db.get_all('customers')
    for i, c in enumerate(customers, start=2):
        if c['id'] == customer_id:
            c['remaining_loan'] += amount
            db.update_row('customers', i, list(c.values()))
            break

# Loan Collection
def add_loan_collection(customer_id, amount, staff_id):
    collection_id = len(db.get_all('loan_collections')) + 1
    data = [collection_id, customer_id, amount, datetime.now().strftime('%Y-%m-%d'), staff_id]
    db.insert('loan_collections', data)
    
    # Customer এর remaining_loan update করুন
    customers = db.get_all('customers')
    for i, c in enumerate(customers, start=2):
        if c['id'] == customer_id:
            c['remaining_loan'] -= amount
            db.update_row('customers', i, list(c.values()))
            break

# Savings Collection
def add_savings_collection(customer_id, amount, staff_id):
    collection_id = len(db.get_all('saving_collections')) + 1
    data = [collection_id, customer_id, amount, datetime.now().strftime('%Y-%m-%d'), staff_id]
    db.insert('saving_collections', data)
    
    # Customer এর savings_balance update করুন
    customers = db.get_all('customers')
    for i, c in enumerate(customers, start=2):
        if c['id'] == customer_id:
            c['savings_balance'] += amount
            db.update_row('customers', i, list(c.values()))
            break

# সব customers দেখুন
def get_all_customers():
    return db.get_all('customers')

# Example usage:
if __name__ == '__main__':
    # Setup sheets with headers
    db.insert('customers', ['id', 'name', 'phone', 'address', 'remaining_loan', 'savings_balance', 'staff_id', 'created_at'])
    db.insert('loans', ['id', 'customer_id', 'amount', 'interest', 'loan_date', 'due_date', 'remaining'])
    db.insert('loan_collections', ['id', 'customer_id', 'amount', 'collection_date', 'staff_id'])
    db.insert('saving_collections', ['id', 'customer_id', 'amount', 'collection_date', 'staff_id'])
