from app import app, db
from models.user_model import User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

with app.app_context():
    db.create_all()
    
    # Check if admin exists
    admin = User.query.filter_by(email='admin@example.com').first()
    if not admin:
        admin = User(
            name='Admin',
            email='admin@example.com',
            password=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin'
        )
        db.session.add(admin)
    
    # Check if staff exists
    staff = User.query.filter_by(email='staff@example.com').first()
    if not staff:
        staff = User(
            name='Staff',
            email='staff@example.com',
            password=bcrypt.generate_password_hash('staff123').decode('utf-8'),
            role='staff'
        )
        db.session.add(staff)
    
    db.session.commit()
    print("Database initialized successfully!")
