from storage import db,bcrypt,login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model,UserMixin):
    id=db.Column(db.Integer(),primary_key=True)
    username=db.Column(db.String(length=30),nullable=False,unique=True)
    email_id=db.Column(db.String(length=50),nullable=False,unique=True)
    password_hash=db.Column(db.String(length=60),nullable=False)
    repos=db.relationship('Repo',backref='owned_user',lazy=True)

    @property
    def password(self):
        return self.password
    
    @password.setter
    def password(self,plain_text_password):
        self.password_hash=bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self,attempted_password):
        return (bcrypt.check_password_hash(self.password_hash,attempted_password))

class Repo(db.Model):
    id=db.Column(db.Integer(),primary_key=True)
    reponame=db.Column(db.String(length=30),nullable=False,unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow) 
    owner = db.Column(db.Integer(), db.ForeignKey('user.id'),nullable=False)
    merkle_root = db.Column(db.String(256))  # Store the Merkle root hash
    user = db.relationship('User', backref=db.backref('repositories', lazy=True))


    def __repr__(self):
        return f'Item{self.name}'
