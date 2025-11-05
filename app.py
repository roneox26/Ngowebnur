from flask import Flask, render_template, redirect, url_for, flash, request, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models.user_model import db, User
import config
from models.staff_model import Staff
from models.loan_model import Loan
from models.saving_model import Saving
from models.customer_model import Customer
from models.collection_model import Collection
from models.loan_collection_model import LoanCollection
from models.saving_collection_model import SavingCollection
from models.cash_balance_model import CashBalance
from models.investment_model import Investment
from models.withdrawal_model import Withdrawal
from models.expense_model import Expense
from models.message_model import Message
from datetime import datetime, timedelta
import csv
import io
import logging

app = Flask(__name__)
app.config.from_object(config)
app.config['TRAP_BAD_REQUEST_ERRORS'] = True
logging.basicConfig(level=logging.DEBUG)

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.errorhandler(400)
def bad_request(e):
    logging.error(f"400 Error: {e}")
    logging.error(f"Request data: {request.data}")
    logging.error(f"Request form: {request.form}")
    flash('Invalid request. Please check your input.', 'danger')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.filter_by(role='admin').first():
        flash('Admin already exists!', 'info')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            admin = User(name=name, email=email, password=hashed_pw, role='admin')
            db.session.add(admin)
            db.session.commit()
            flash('Admin created! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    
    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Login Successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        staff_count = User.query.filter_by(role='staff').count()
        total_loans = db.session.query(db.func.sum(Customer.total_loan)).scalar() or 0
        pending_loans = db.session.query(db.func.sum(Customer.remaining_loan)).scalar() or 0
        total_savings = db.session.query(db.func.sum(Customer.savings_balance)).scalar() or 0
        total_customers = Customer.query.count()
        
        cash_balance_record = CashBalance.query.first()
        cash_balance = cash_balance_record.balance if cash_balance_record else 0
        
        period = request.args.get('period', 'all')
        fee_period = request.args.get('fee_period', 'all')
        
        admission_fees = db.session.query(db.func.sum(Customer.admission_fee)).scalar() or 0
        service_charges = db.session.query(db.func.sum(Loan.service_charge)).scalar() or 0
        total_fees = admission_fees + service_charges
        
        return render_template('admin_dashboard.html', name=current_user.name, staff_count=staff_count, total_loans=total_loans, pending_loans=pending_loans, total_savings=total_savings, total_customers=total_customers, cash_balance=cash_balance, period=period, fee_period=fee_period, total_fees=total_fees)
    elif current_user.role == 'staff':
        my_customers = Customer.query.filter_by(staff_id=current_user.id).count()
        total_remaining = db.session.query(db.func.sum(Customer.remaining_loan)).filter_by(staff_id=current_user.id).scalar() or 0
        today = datetime.now().replace(hour=0, minute=0, second=0)
        today_loan_collections = LoanCollection.query.filter_by(staff_id=current_user.id).filter(LoanCollection.collection_date >= today).count()
        today_saving_collections = SavingCollection.query.filter_by(staff_id=current_user.id).filter(SavingCollection.collection_date >= today).count()
        today_collections = today_loan_collections + today_saving_collections
        unread_messages = Message.query.filter_by(staff_id=current_user.id, is_read=False).count()
        return render_template('staff_dashboard.html', name=current_user.name, my_customers=my_customers, total_remaining=total_remaining, today_collections=today_collections, unread_messages=unread_messages)
    else:
        flash('Invalid role!', 'danger')
        return redirect(url_for('logout'))

@app.route('/admin/staffs')
@login_required
def manage_staff():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    staffs = User.query.filter_by(role='staff').all()
    return render_template('manage_staff.html', staffs=staffs)

@app.route('/admin/staff/add', methods=['GET', 'POST'])
@login_required
def add_staff():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            
            if User.query.filter_by(email=email).first():
                flash('Email already exists!', 'danger')
                return redirect(url_for('add_staff'))
            
            hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
            new_staff = User(name=name, email=email, password=hashed_pw, role='staff')
            db.session.add(new_staff)
            db.session.commit()
            flash('Staff added successfully!', 'success')
            return redirect(url_for('manage_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('add_staff'))
    
    return render_template('add_staff.html')

@app.route('/loan_collection/collect', methods=['POST'])
@login_required
def collect_loan():
    print("\n" + "="*50)
    print("LOAN COLLECTION DEBUG")
    print("="*50)
    print(f"All form data: {dict(request.form)}")
    print(f"Form keys: {list(request.form.keys())}")
    
    customer_id = request.form.get('customer_id')
    amount = request.form.get('amount')
    
    print(f"customer_id value: '{customer_id}' (type: {type(customer_id)})")
    print(f"amount value: '{amount}' (type: {type(amount)})")
    print("="*50 + "\n")
    
    if not customer_id:
        print("ERROR: customer_id is empty")
        flash('গ্রাহক নির্বাচন করুন!', 'danger')
        return redirect(url_for('loan_collection'))
    
    if not amount:
        print("ERROR: amount is empty")
        flash('টাকার পরিমাণ দিন!', 'danger')
        return redirect(url_for('loan_collection'))
    
    try:
        customer_id = int(customer_id)
        amount = float(amount)
        print(f"Converted - customer_id: {customer_id}, amount: {amount}")
    except Exception as e:
        print(f"ERROR converting: {e}")
        flash('সঠিক তথ্য দিন!', 'danger')
        return redirect(url_for('loan_collection'))
    
    if amount <= 0:
        flash('টাকার পরিমাণ ০ এর বেশি হতে হবে!', 'danger')
        return redirect(url_for('loan_collection'))
    
    customer = Customer.query.get(customer_id)
    if not customer:
        flash('গ্রাহক পাওয়া যায়নি!', 'danger')
        return redirect(url_for('loan_collection'))
    
    if customer.remaining_loan <= 0:
        flash(f'{customer.name} এর কোনো বকেয়া লোন নেই!', 'warning')
        return redirect(url_for('loan_collection'))
    
    if amount > customer.remaining_loan:
        flash(f'টাকা বাকি লোন থেকে বেশি!', 'danger')
        return redirect(url_for('loan_collection'))
    
    try:
        collection = LoanCollection(customer_id=customer_id, amount=amount, staff_id=current_user.id)
        customer.remaining_loan -= amount
        
        cash_balance_record = CashBalance.query.first()
        if not cash_balance_record:
            cash_balance_record = CashBalance(balance=0)
            db.session.add(cash_balance_record)
        cash_balance_record.balance += amount
        
        db.session.add(collection)
        db.session.commit()
        print(f"SUCCESS: Collection saved - Customer: {customer.name}, Amount: {amount}")
        flash(f'সফলভাবে ৳{amount} কালেকশন সম্পন্ন!', 'success')
    except Exception as e:
        print(f"ERROR saving: {e}")
        db.session.rollback()
        flash(f'এরর: {str(e)}', 'danger')
    
    return redirect(url_for('loan_collection'))

@app.route('/saving_collection/collect', methods=['POST'])
@login_required
def collect_saving():
    customer_id = request.form.get('customer_id')
    amount = request.form.get('amount')
    
    if not customer_id:
        flash('গ্রাহক নির্বাচন করুন!', 'danger')
        return redirect(url_for('saving_collection'))
    
    if not amount:
        flash('টাকার পরিমাণ দিন!', 'danger')
        return redirect(url_for('saving_collection'))
    
    try:
        customer_id = int(customer_id)
        amount = float(amount)
    except:
        flash('সঠিক তথ্য দিন!', 'danger')
        return redirect(url_for('saving_collection'))
    
    if amount <= 0:
        flash('টাকার পরিমাণ ০ এর বেশি হতে হবে!', 'danger')
        return redirect(url_for('saving_collection'))
    
    customer = Customer.query.get(customer_id)
    if not customer:
        flash('গ্রাহক পাওয়া যায়নি!', 'danger')
        return redirect(url_for('saving_collection'))
    
    try:
        collection = SavingCollection(customer_id=customer_id, amount=amount, staff_id=current_user.id)
        customer.savings_balance += amount
        
        cash_balance_record = CashBalance.query.first()
        if not cash_balance_record:
            cash_balance_record = CashBalance(balance=0)
            db.session.add(cash_balance_record)
        cash_balance_record.balance += amount
        
        db.session.add(collection)
        db.session.commit()
        flash(f'সফলভাবে ৳{amount} সেভিংস জমা!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'এরর: {str(e)}', 'danger')
    
    return redirect(url_for('saving_collection'))

@app.route('/loans')
@login_required
def manage_loans():
    if current_user.role == 'staff':
        loans = Loan.query.filter_by(staff_id=current_user.id).all()
    else:
        loans = Loan.query.all()
    staffs = User.query.filter_by(role='staff').all()
    return render_template('manage_loans.html', loans=loans, staffs=staffs)

@app.route('/loan/add', methods=['GET', 'POST'])
@login_required
def add_loan():
    if current_user.role != 'admin':
        flash('শুধুমাত্র Admin লোন দিতে পারবে!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            customer_id = int(request.form['customer_id'])
            amount = float(request.form['amount'])
            interest_rate = float(request.form['interest'])
            customer = Customer.query.get_or_404(customer_id)
            
            cash_balance_record = CashBalance.query.first()
            if not cash_balance_record:
                cash_balance_record = CashBalance(balance=0)
                db.session.add(cash_balance_record)
            
            if cash_balance_record.balance < amount:
                flash(f'পর্যাপ্ত টাকা নেই! বর্তমান ব্যালেন্স: ৳{cash_balance_record.balance}', 'danger')
                return redirect(url_for('add_loan'))
            
            interest_amount = (amount * interest_rate) / 100
            service_charge = float(request.form.get('service_charge', 0))
            welfare_fee = float(request.form.get('welfare_fee', 0))
            total_with_interest = amount + interest_amount
            
            loan = Loan(
                customer_name=customer.name,
                amount=amount,
                interest=interest_rate,
                loan_date=datetime.now(),
                due_date=datetime.strptime(request.form['due_date'], '%Y-%m-%d'),
                service_charge=service_charge,
                welfare_fee=welfare_fee,
                staff_id=customer.staff_id
            )
            
            customer.total_loan += total_with_interest
            customer.remaining_loan += total_with_interest
            cash_balance_record.balance -= amount
            cash_balance_record.balance += service_charge + welfare_fee
            
            db.session.add(loan)
            db.session.commit()
            flash(f'ঋণ যোগ সফল! পরিমাণ: ৳{amount}, সুদ: ৳{interest_amount}, মোট: ৳{total_with_interest}', 'success')
            return redirect(url_for('manage_loans'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('add_loan'))
    
    cash_balance_record = CashBalance.query.first()
    cash_balance = cash_balance_record.balance if cash_balance_record else 0
    customers = Customer.query.all()
    return render_template('add_loan.html', customers=customers, cash_balance=cash_balance)

@app.route('/loan_collection', methods=['GET'])
@login_required
def loan_collection():
    if current_user.role == 'staff':
        customers = Customer.query.filter_by(staff_id=current_user.id).filter(Customer.remaining_loan > 0).all()
    else:
        customers = Customer.query.filter(Customer.remaining_loan > 0).all()
    return render_template('loan_collection.html', customers=customers)

@app.route('/loan_collections_history')
@login_required
def loan_collections_history():
    staff_filter = request.args.get('staff_id', type=int)
    customer_filter = request.args.get('customer', '')
    
    if current_user.role == 'staff':
        query = LoanCollection.query.filter_by(staff_id=current_user.id)
        total = db.session.query(db.func.sum(LoanCollection.amount)).filter_by(staff_id=current_user.id).scalar() or 0
    else:
        query = LoanCollection.query
        if staff_filter:
            query = query.filter_by(staff_id=staff_filter)
        total = db.session.query(db.func.sum(LoanCollection.amount)).scalar() or 0
    
    if customer_filter:
        query = query.join(Customer).filter(Customer.name.contains(customer_filter))
    
    loan_collections = query.order_by(LoanCollection.collection_date.desc()).all()
    staffs = User.query.filter_by(role='staff').all()
    return render_template('loan_collections_history.html', loan_collections=loan_collections, staffs=staffs, total=total)

@app.route('/saving_collection', methods=['GET'])
@login_required
def saving_collection():
    if current_user.role == 'staff':
        customers = Customer.query.filter_by(staff_id=current_user.id).all()
    else:
        customers = Customer.query.all()
    return render_template('saving_collection.html', customers=customers)

@app.route('/savings')
@login_required
def manage_savings():
    query = SavingCollection.query
    if current_user.role == 'staff':
        query = query.filter_by(staff_id=current_user.id)
    savings = query.all()
    staffs = User.query.filter_by(role='staff').all()
    total = db.session.query(db.func.sum(SavingCollection.amount)).scalar() or 0
    return render_template('manage_savings.html', savings=savings, staffs=staffs, total=total)

@app.route('/daily_collections')
@login_required
def daily_collections():
    from datetime import date
    today_date = date.today()
    
    if current_user.role == 'staff':
        all_loan = LoanCollection.query.filter_by(staff_id=current_user.id).all()
        all_saving = SavingCollection.query.filter_by(staff_id=current_user.id).all()
        
        loan_collections = [lc for lc in all_loan if lc.collection_date.date() == today_date]
        saving_collections = [sc for sc in all_saving if sc.collection_date.date() == today_date]
    else:
        all_loan = LoanCollection.query.all()
        all_saving = SavingCollection.query.all()
        
        loan_collections = [lc for lc in all_loan if lc.collection_date.date() == today_date]
        saving_collections = [sc for sc in all_saving if sc.collection_date.date() == today_date]
    
    total_loan = sum(lc.amount for lc in loan_collections)
    total_saving = sum(sc.amount for sc in saving_collections)
    
    return render_template('daily_collections.html', loan_collections=loan_collections, saving_collections=saving_collections, total_loan=total_loan, total_saving=total_saving)

@app.route('/reports')
@login_required
def reports():
    period = request.args.get('period', 'daily')
    staff_id = request.args.get('staff_id', type=int)
    
    today = datetime.now()
    if period == 'daily':
        start_date = today.replace(hour=0, minute=0, second=0)
    elif period == 'weekly':
        start_date = today - timedelta(days=7)
    else:
        start_date = today - timedelta(days=30)
    
    loan_collection_query = LoanCollection.query.filter(LoanCollection.collection_date >= start_date)
    saving_collection_query = SavingCollection.query.filter(SavingCollection.collection_date >= start_date)
    
    if staff_id:
        loan_collection_query = loan_collection_query.filter_by(staff_id=staff_id)
        saving_collection_query = saving_collection_query.filter_by(staff_id=staff_id)
    
    loan_collections = loan_collection_query.all()
    saving_collections = saving_collection_query.all()
    
    total_loans = sum(l.amount for l in loan_collections)
    total_savings = sum(s.amount for s in saving_collections)
    total_payments = total_loans
    
    staffs = User.query.filter_by(role='staff').all()
    
    return render_template('reports.html', 
                         loan_collections=loan_collections, saving_collections=saving_collections,
                         total_loans=total_loans, total_savings=total_savings, 
                         total_payments=total_payments, staffs=staffs, period=period)

@app.route('/customers')
@login_required
def manage_customers():
    if current_user.role == 'staff':
        customers = Customer.query.filter_by(staff_id=current_user.id).all()
    else:
        customers = Customer.query.all()
    return render_template('manage_customers.html', customers=customers)

@app.route('/loan_customers')
@login_required
def loan_customers():
    if current_user.role == 'staff':
        customers = Customer.query.filter_by(staff_id=current_user.id).filter(Customer.total_loan > 0).all()
    else:
        customers = Customer.query.filter(Customer.total_loan > 0).all()
    return render_template('loan_customers.html', customers=customers)

@app.route('/customer_details/<int:id>')
@login_required
def customer_details(id):
    customer = Customer.query.get_or_404(id)
    
    if current_user.role == 'staff' and customer.staff_id != current_user.id:
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    loan_collections = LoanCollection.query.filter_by(customer_id=id).order_by(LoanCollection.collection_date.desc()).all()
    saving_collections = SavingCollection.query.filter_by(customer_id=id).order_by(SavingCollection.collection_date.desc()).all()
    
    total_collected = sum(lc.amount for lc in loan_collections)
    
    return render_template('customer_details.html', customer=customer, loan_collections=loan_collections, saving_collections=saving_collections, total_collected=total_collected)

@app.route('/customer/add', methods=['GET', 'POST'])
@login_required
def add_customer():
    if request.method == 'POST':
        try:
            admission_fee = float(request.form.get('admission_fee', 0))
            
            cash_balance_record = CashBalance.query.first()
            if not cash_balance_record:
                cash_balance_record = CashBalance(balance=0)
                db.session.add(cash_balance_record)
            
            cash_balance_record.balance += admission_fee
            
            customer = Customer(
                name=request.form['name'],
                member_no=request.form.get('member_no', ''),
                phone=request.form['phone'],
                father_husband=request.form.get('father_husband', ''),
                village=request.form.get('village', ''),
                post=request.form.get('post', ''),
                thana=request.form.get('thana', ''),
                district=request.form.get('district', ''),
                granter=request.form.get('granter', ''),
                profession=request.form.get('profession', ''),
                nid_no=request.form.get('nid_no', ''),
                admission_fee=admission_fee,
                address=request.form.get('address', ''),
                staff_id=current_user.id
            )
            db.session.add(customer)
            db.session.commit()
            flash(f'সদস্য সফলভাবে যোগ হয়েছে! ভর্তি ফি: ৳{admission_fee}', 'success')
            return redirect(url_for('manage_customers'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('add_customer'))
    return render_template('add_customer.html')

@app.route('/cash_balance', methods=['GET', 'POST'])
@login_required
def manage_cash_balance():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            action = request.form['action']
            amount = float(request.form['amount'])
            
            cash_balance_record = CashBalance.query.first()
            if not cash_balance_record:
                cash_balance_record = CashBalance(balance=0)
                db.session.add(cash_balance_record)
            
            if action == 'add':
                investor_name = request.form.get('investor_name', '')
                note = request.form.get('note', '')
                
                investment = Investment(
                    investor_name=investor_name,
                    amount=amount,
                    note=note
                )
                cash_balance_record.balance += amount
                db.session.add(investment)
                flash(f'৳{amount} যোগ করা হয়েছে!', 'success')
            elif action == 'withdraw':
                investor_name = request.form.get('investor_name', '')
                note = request.form.get('note', '')
                
                if cash_balance_record.balance >= amount:
                    withdrawal = Withdrawal(
                        investor_name=investor_name,
                        amount=amount,
                        note=note
                    )
                    cash_balance_record.balance -= amount
                    db.session.add(withdrawal)
                    flash(f'৳{amount} Withdrawal সফল হয়েছে!', 'success')
                else:
                    flash('পর্যাপ্ত টাকা নেই!', 'danger')
            
            db.session.commit()
            return redirect(url_for('manage_cash_balance'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('manage_cash_balance'))
    
    cash_balance_record = CashBalance.query.first()
    cash_balance = cash_balance_record.balance if cash_balance_record else 0
    investments = Investment.query.order_by(Investment.date.desc()).all()
    withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).all()
    total_investment = db.session.query(db.func.sum(Investment.amount)).scalar() or 0
    total_withdrawal = db.session.query(db.func.sum(Withdrawal.amount)).scalar() or 0
    return render_template('manage_cash_balance.html', cash_balance=cash_balance, investments=investments, withdrawals=withdrawals, total_investment=total_investment, total_withdrawal=total_withdrawal)

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def manage_expenses():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            category = request.form['category']
            amount = float(request.form['amount'])
            description = request.form.get('description', '')
            
            cash_balance_record = CashBalance.query.first()
            if not cash_balance_record:
                cash_balance_record = CashBalance(balance=0)
                db.session.add(cash_balance_record)
            
            if cash_balance_record.balance >= amount:
                expense = Expense(
                    category=category,
                    amount=amount,
                    description=description
                )
                cash_balance_record.balance -= amount
                db.session.add(expense)
                db.session.commit()
                flash(f'{category} - ৳{amount} ব্যয় সফল হয়েছে!', 'success')
            else:
                flash('পর্যাপ্ত টাকা নেই!', 'danger')
            
            return redirect(url_for('manage_expenses'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('manage_expenses'))
    
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    total_expenses = db.session.query(db.func.sum(Expense.amount)).scalar() or 0
    
    cash_balance_record = CashBalance.query.first()
    cash_balance = cash_balance_record.balance if cash_balance_record else 0
    
    return render_template('manage_expenses.html', expenses=expenses, total_expenses=total_expenses, cash_balance=cash_balance)

@app.route('/messages')
@login_required
def view_messages():
    if current_user.role == 'staff':
        messages = Message.query.filter_by(staff_id=current_user.id).order_by(Message.created_date.desc()).all()
        return render_template('staff_messages.html', messages=messages)
    else:
        staffs = User.query.filter_by(role='staff').all()
        return render_template('admin_messages.html', staffs=staffs)

@app.route('/message/send', methods=['POST'])
@login_required
def send_message():
    if current_user.role == 'admin':
        try:
            staff_id = int(request.form['staff_id'])
            content = request.form['content']
            message = Message(staff_id=staff_id, content=content)
            db.session.add(message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('view_messages'))

@app.route('/manage_withdrawals')
@login_required
def manage_withdrawals():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).all()
    customers = Customer.query.all()
    cash_balance_record = CashBalance.query.first()
    cash_balance = cash_balance_record.balance if cash_balance_record else 0
    total_withdrawal = sum(w.amount for w in withdrawals)
    return render_template('manage_withdrawals.html', withdrawals=withdrawals, customers=customers, cash_balance=cash_balance, total_withdrawal=total_withdrawal)

@app.route('/daily_report')
@login_required
def daily_report():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    from datetime import date
    selected_date_str = request.args.get('date')
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        selected_date = date.today()
    
    today_start = datetime.combine(selected_date, datetime.min.time())
    today_end = datetime.combine(selected_date, datetime.max.time())
    
    loan_collections = LoanCollection.query.filter(LoanCollection.collection_date >= today_start, LoanCollection.collection_date <= today_end).all()
    saving_collections = SavingCollection.query.filter(SavingCollection.collection_date >= today_start, SavingCollection.collection_date <= today_end).all()
    loans_given_today = Loan.query.filter(Loan.loan_date >= today_start, Loan.loan_date <= today_end).all()
    withdrawals_today = Withdrawal.query.filter(Withdrawal.date >= today_start, Withdrawal.date <= today_end).all()
    expenses_today = Expense.query.filter(Expense.date >= today_start, Expense.date <= today_end).all()
    customers_added_today = Customer.query.filter(Customer.created_date >= today_start, Customer.created_date <= today_end).all()
    
    total_installment = sum(lc.amount for lc in loan_collections)
    total_saving = sum(sc.amount for sc in saving_collections)
    total_admission_fee = sum(c.admission_fee for c in customers_added_today)
    total_welfare_fee = sum(l.welfare_fee for l in loans_given_today)
    total_application_fee = sum(l.service_charge for l in loans_given_today)
    total_loan_distributed = sum(l.amount for l in loans_given_today)
    total_withdrawal = sum(w.amount for w in withdrawals_today)
    total_expense = sum(e.amount for e in expenses_today)
    total_outflow = total_loan_distributed + total_withdrawal + total_expense
    
    customers = Customer.query.order_by(Customer.member_no).all()
    collections = []
    for customer in customers:
        loan_amount = sum(lc.amount for lc in loan_collections if lc.customer_id == customer.id)
        saving_amount = sum(sc.amount for sc in saving_collections if sc.customer_id == customer.id)
        collections.append({'customer': customer, 'loan_amount': loan_amount, 'saving_amount': saving_amount})
    
    return render_template('daily_report.html', 
                         report_date=selected_date.strftime('%d-%m-%Y'), 
                         selected_date=selected_date.strftime('%Y-%m-%d'), 
                         total_installment=total_installment, 
                         total_saving=total_saving, 
                         total_welfare_fee=total_welfare_fee,
                         total_admission_fee=total_admission_fee,
                         total_application_fee=total_application_fee,
                         total_expense=total_expense,
                         total_loan_distributed=total_loan_distributed,
                         total_withdrawal=total_withdrawal,
                         total_outflow=total_outflow,
                         collections=collections)

@app.route('/monthly_report')
@login_required
def monthly_report():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    import calendar
    today = datetime.now()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    
    available_years = list(range(2020, today.year + 2))
    month_names = ['', 'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর']
    month_name = month_names[month]
    last_day = calendar.monthrange(year, month)[1]
    
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, last_day, 23, 59, 59)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_month_end = datetime(prev_year, prev_month, calendar.monthrange(prev_year, prev_month)[1], 23, 59, 59)
    
    prev_remaining = db.session.query(db.func.sum(Customer.remaining_loan)).scalar() or 0
    
    loan_collections = LoanCollection.query.filter(LoanCollection.collection_date >= month_start, LoanCollection.collection_date <= month_end).all()
    saving_collections = SavingCollection.query.filter(SavingCollection.collection_date >= month_start, SavingCollection.collection_date <= month_end).all()
    loans_given = Loan.query.filter(Loan.loan_date >= month_start, Loan.loan_date <= month_end).all()
    withdrawals = Withdrawal.query.filter(Withdrawal.date >= month_start, Withdrawal.date <= month_end).all()
    expenses = Expense.query.filter(Expense.date >= month_start, Expense.date <= month_end).all()
    customers_added = Customer.query.filter(Customer.created_date >= month_start, Customer.created_date <= month_end).all() if hasattr(Customer, 'created_date') else []
    
    total_capital_savings = sum(sc.amount for sc in saving_collections)
    total_loan_distributed = sum(l.amount for l in loans_given)
    total_interest = sum((l.amount * l.interest / 100) for l in loans_given)
    total_monthly_expenses = sum(e.amount for e in expenses)
    current_remaining = db.session.query(db.func.sum(Customer.remaining_loan)).scalar() or 0
    
    cash_balance_record = CashBalance.query.first()
    opening_balance = cash_balance_record.balance if cash_balance_record else 0
    
    daily_data = {}
    for day in range(1, last_day + 1):
        day_start = datetime(year, month, day, 0, 0, 0)
        day_end = datetime(year, month, day, 23, 59, 59)
        
        day_loan_collections = [lc for lc in loan_collections if lc.collection_date.date() == day_start.date()]
        day_saving_collections = [sc for sc in saving_collections if sc.collection_date.date() == day_start.date()]
        day_loans = [l for l in loans_given if l.loan_date.date() == day_start.date()]
        day_withdrawals = [w for w in withdrawals if w.date.date() == day_start.date()]
        day_expenses = [e for e in expenses if e.date.date() == day_start.date()]
        day_customers = [c for c in customers_added if hasattr(c, 'created_date') and c.created_date.date() == day_start.date()]
        
        installments = sum(lc.amount for lc in day_loan_collections)
        savings = sum(sc.amount for sc in day_saving_collections)
        admission_fee = sum(c.admission_fee for c in day_customers)
        welfare_fee = sum(l.welfare_fee for l in day_loans)
        service_charge = sum(l.service_charge for l in day_loans)
        loan_given = sum(l.amount for l in day_loans)
        interest = sum((l.amount * l.interest / 100) for l in day_loans)
        loan_with_interest = loan_given + interest
        savings_return = sum(w.amount for w in day_withdrawals)
        day_expense = sum(e.amount for e in day_expenses)
        
        total_income = installments + savings + admission_fee + welfare_fee + service_charge
        total_expense = loan_given + savings_return + day_expense
        balance = total_income - total_expense
        
        is_weekend = calendar.weekday(year, month, day) in [4, 5]
        
        daily_data[day] = {
            'installments': installments,
            'savings': savings,
            'welfare_fee': welfare_fee,
            'admission_fee': admission_fee,
            'service_charge': service_charge,
            'capital_savings': savings,
            'total_income': total_income,
            'loan_given': loan_given,
            'interest': interest,
            'loan_with_interest': loan_with_interest,
            'savings_return': savings_return,
            'expenses': day_expense,
            'total_expense': total_expense,
            'balance': balance,
            'is_weekend': is_weekend
        }
    
    return render_template('monthly_report.html', 
                         month=month, 
                         month_name=month_name, 
                         year=year, 
                         available_years=available_years, 
                         daily_data=daily_data, 
                         last_day=last_day, 
                         opening_balance=opening_balance,
                         total_capital_savings=total_capital_savings,
                         total_loan_distributed=total_loan_distributed,
                         total_interest=total_interest,
                         total_monthly_expenses=total_monthly_expenses,
                         prev_remaining=prev_remaining,
                         current_remaining=current_remaining)

@app.route('/profit_loss')
@login_required
def profit_loss():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    period = request.args.get('period', 'monthly')
    today = datetime.now()
    
    if period == 'monthly':
        start_date = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start_date = today.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    loan_collections = LoanCollection.query.filter(LoanCollection.collection_date >= start_date).all()
    saving_collections = SavingCollection.query.filter(SavingCollection.collection_date >= start_date).all()
    
    total_loan_collected = sum(lc.amount for lc in loan_collections)
    total_savings_collected = sum(sc.amount for sc in saving_collections)
    total_income = total_loan_collected + total_savings_collected
    
    expenses = Expense.query.filter(Expense.date >= start_date).all()
    total_expenses = sum(exp.amount for exp in expenses)
    
    withdrawals = Withdrawal.query.filter(Withdrawal.date >= start_date).all()
    total_withdrawals = sum(wd.amount for wd in withdrawals)
    
    loans_given = Loan.query.filter(Loan.loan_date >= start_date).all()
    total_loans_given = sum(loan.amount for loan in loans_given)
    
    net_profit = total_income - (total_expenses + total_withdrawals + total_loans_given)
    
    return render_template('profit_loss.html', period=period, total_income=total_income, total_loan_collected=total_loan_collected, total_savings_collected=total_savings_collected, total_expenses=total_expenses, total_withdrawals=total_withdrawals, total_loans_given=total_loans_given, net_profit=net_profit)

@app.route('/withdrawal_report')
@login_required
def withdrawal_report():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    withdrawals = Withdrawal.query.order_by(Withdrawal.date.desc()).all()
    total = sum(w.amount for w in withdrawals)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    return render_template('withdrawal_report.html', withdrawals=withdrawals, total=total, from_date=from_date, to_date=to_date)

@app.route('/customer_details_print/<int:id>')
@login_required
def customer_details_print(id):
    customer = Customer.query.get_or_404(id)
    loan_collections = LoanCollection.query.filter_by(customer_id=id).order_by(LoanCollection.collection_date.desc()).all()
    saving_collections = SavingCollection.query.filter_by(customer_id=id).order_by(SavingCollection.collection_date.desc()).all()
    withdrawals = []
    total_loan_collected = sum(lc.amount for lc in loan_collections)
    total_saving_collected = sum(sc.amount for sc in saving_collections)
    total_withdrawn = 0
    return render_template('customer_details_print.html', customer=customer, loan_collections=loan_collections, saving_collections=saving_collections, total_loan_collected=total_loan_collected, total_saving_collected=total_saving_collected, withdrawals=withdrawals, total_withdrawn=total_withdrawn)

@app.route('/admin/staff/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_staff(id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    staff = User.query.get_or_404(id)
    if staff.role != 'staff':
        flash('Invalid staff!', 'danger')
        return redirect(url_for('manage_staff'))
    
    if request.method == 'POST':
        try:
            staff.name = request.form['name']
            staff.email = request.form['email']
            
            if request.form.get('password'):
                staff.password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
            
            db.session.commit()
            flash('Staff updated successfully!', 'success')
            return redirect(url_for('manage_staff'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('edit_staff', id=id))
    
    return render_template('edit_staff.html', staff=staff)

@app.route('/admin/staff/delete/<int:id>')
@login_required
def delete_staff(id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        staff = User.query.get_or_404(id)
        if staff.role != 'staff':
            flash('Invalid staff!', 'danger')
            return redirect(url_for('manage_staff'))
        
        db.session.delete(staff)
        db.session.commit()
        flash('Staff deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'danger')
    return redirect(url_for('manage_staff'))

@app.route('/loan/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_loan(id):
    loan = Loan.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            loan.customer_name = request.form['customer_name']
            loan.amount = float(request.form['amount'])
            loan.interest = float(request.form['interest'])
            loan.due_date = datetime.strptime(request.form['due_date'], '%Y-%m-%d')
            db.session.commit()
            flash('Loan updated successfully!', 'success')
            return redirect(url_for('manage_loans'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('edit_loan', id=id))
    
    return render_template('edit_loan.html', loan=loan)

@app.route('/collection', methods=['GET', 'POST'])
@login_required
def collection():
    if request.method == 'POST':
        try:
            customer_id = request.form.get('customer_id')
            loan_amount = float(request.form.get('loan_amount', 0) or 0)
            saving_amount = float(request.form.get('saving_amount', 0) or 0)
            
            if not customer_id:
                flash('গ্রাহক নির্বাচন করুন!', 'danger')
                return redirect(url_for('collection'))
            
            if loan_amount <= 0 and saving_amount <= 0:
                flash('লোন অথবা সঞ্চয় কালেকশন পরিমাণ দিন!', 'danger')
                return redirect(url_for('collection'))
            
            customer_id = int(customer_id)
            customer = Customer.query.get_or_404(customer_id)
            
            cash_balance_record = CashBalance.query.first()
            if not cash_balance_record:
                cash_balance_record = CashBalance(balance=0)
                db.session.add(cash_balance_record)
            
            if loan_amount > 0:
                if loan_amount > customer.remaining_loan:
                    flash(f'লোন কালেকশন বাকি লোন (৳{customer.remaining_loan}) থেকে বেশি হতে পারবে না!', 'danger')
                    return redirect(url_for('collection'))
                
                loan_collection = LoanCollection(
                    customer_id=customer_id,
                    amount=loan_amount,
                    staff_id=current_user.id
                )
                customer.remaining_loan -= loan_amount
                cash_balance_record.balance += loan_amount
                db.session.add(loan_collection)
            
            if saving_amount > 0:
                saving_collection = SavingCollection(
                    customer_id=customer_id,
                    amount=saving_amount,
                    staff_id=current_user.id
                )
                customer.savings_balance += saving_amount
                cash_balance_record.balance += saving_amount
                db.session.add(saving_collection)
            
            db.session.commit()
            flash(f'সফলভাবে কালেকশন সম্পন্ন! লোন: ৳{loan_amount}, সঞ্চয়: ৳{saving_amount}', 'success')
            return redirect(url_for('collection'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('collection'))
    
    if current_user.role == 'staff':
        customers = Customer.query.filter_by(staff_id=current_user.id).all()
    else:
        customers = Customer.query.all()
    return render_template('collection.html', customers=customers)

@app.route('/manage_collections')
@login_required
def manage_collections():
    if current_user.role == 'staff':
        loan_collections = LoanCollection.query.filter_by(staff_id=current_user.id).all()
        saving_collections = SavingCollection.query.filter_by(staff_id=current_user.id).all()
    else:
        loan_collections = LoanCollection.query.all()
        saving_collections = SavingCollection.query.all()
    return render_template('manage_collections.html', loan_collections=loan_collections, saving_collections=saving_collections)

@app.route('/staff_collection_report/<int:id>')
@login_required
def staff_collection_report(id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    staff = User.query.get_or_404(id)
    if staff.role != 'staff':
        flash('Invalid staff!', 'danger')
        return redirect(url_for('manage_staff'))
    
    from datetime import date
    selected_date_str = request.args.get('date')
    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    else:
        selected_date = date.today()
    
    day_start = datetime.combine(selected_date, datetime.min.time())
    day_end = datetime.combine(selected_date, datetime.max.time())
    
    loan_collections = LoanCollection.query.filter_by(staff_id=id).filter(LoanCollection.collection_date >= day_start, LoanCollection.collection_date <= day_end).all()
    saving_collections = SavingCollection.query.filter_by(staff_id=id).filter(SavingCollection.collection_date >= day_start, SavingCollection.collection_date <= day_end).all()
    
    total_loan = sum(lc.amount for lc in loan_collections)
    total_saving = sum(sc.amount for sc in saving_collections)
    
    return render_template('staff_collection_report.html', staff=staff, total_loan=total_loan, total_saving=total_saving, selected_date=selected_date.strftime('%Y-%m-%d'), report_date=selected_date.strftime('%d-%m-%Y'))

@app.route('/expense_invoice/<int:id>')
@login_required
def expense_invoice(id):
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    expense = Expense.query.get_or_404(id)
    return render_template('expense_invoice.html', expense=expense)

@app.route('/monthly_expense_invoice')
@login_required
def monthly_expense_invoice():
    if current_user.role != 'admin':
        flash('Access denied!', 'danger')
        return redirect(url_for('dashboard'))
    
    import calendar
    today = datetime.now()
    month = int(request.args.get('month', today.month))
    year = int(request.args.get('year', today.year))
    
    month_names = ['', 'জানুয়ারি', 'ফেব্রুয়ারি', 'মার্চ', 'এপ্রিল', 'মে', 'জুন', 'জুলাই', 'আগস্ট', 'সেপ্টেম্বর', 'অক্টোবর', 'নভেম্বর', 'ডিসেম্বর']
    month_name = month_names[month]
    last_day = calendar.monthrange(year, month)[1]
    
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, last_day, 23, 59, 59)
    
    expenses = Expense.query.filter(Expense.date >= month_start, Expense.date <= month_end).order_by(Expense.date).all()
    total = sum(e.amount for e in expenses)
    salary_total = sum(e.amount for e in expenses if e.category == 'Salary')
    office_total = sum(e.amount for e in expenses if e.category == 'Office')
    transport_total = sum(e.amount for e in expenses if e.category == 'Transport')
    other_total = sum(e.amount for e in expenses if e.category == 'Other')
    
    return render_template('monthly_expense_invoice.html', expenses=expenses, total=total, month=month, year=year, month_name=month_name, salary_total=salary_total, office_total=office_total, transport_total=transport_total, other_total=other_total)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    logging.error(f"500 Error: {error}")
    flash('একটি সমস্যা হয়েছে। আবার চেষ্টা করুন।', 'danger')
    return redirect(url_for('dashboard'))

# Initialize database
try:
    with app.app_context():
        db.create_all()
except Exception as e:
    logging.error(f"Database initialization error: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
