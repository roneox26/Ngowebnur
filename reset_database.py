from app import app, db
from models.user_model import User
from models.customer_model import Customer
from models.loan_model import Loan
from models.loan_collection_model import LoanCollection
from models.saving_collection_model import SavingCollection
from models.cash_balance_model import CashBalance
from models.investment_model import Investment
from models.withdrawal_model import Withdrawal
from models.expense_model import Expense
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

with app.app_context():
    # Delete all data
    LoanCollection.query.delete()
    SavingCollection.query.delete()
    Withdrawal.query.delete()
    Investment.query.delete()
    Expense.query.delete()
    Loan.query.delete()
    Customer.query.delete()
    User.query.filter_by(role='staff').delete()
    CashBalance.query.delete()
    
    # Reset cash balance to 0
    cash_balance = CashBalance(balance=0)
    db.session.add(cash_balance)
    
    db.session.commit()
    print("Database reset successfully!")
    print("Cash Balance: 0")
    print("Total Customers: 0")
