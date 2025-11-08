from app import app, db
from models.loan_collection_model import LoanCollection
from models.saving_collection_model import SavingCollection
from models.user_model import User

with app.app_context():
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        print("No admin user found!")
    else:
        loan_collections = LoanCollection.query.filter_by(staff_id=None).all()
        for lc in loan_collections:
            lc.staff_id = admin.id
        
        saving_collections = SavingCollection.query.filter_by(staff_id=None).all()
        for sc in saving_collections:
            sc.staff_id = admin.id
        
        db.session.commit()
        print(f"Updated {len(loan_collections)} loan collections and {len(saving_collections)} saving collections")
