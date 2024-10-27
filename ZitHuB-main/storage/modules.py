from storage import db, bcrypt, login_manager
from flask_login import UserMixin
from datetime import datetime
from storage.commit import commitHistory, commitNode
from sqlalchemy import event

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), nullable=False, unique=True)
    email_id = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(60), nullable=False)
    repos = db.relationship('Repo', backref='owned_user', lazy=True)

    @property
    def password(self):
        raise AttributeError("Password is a write-only field.")  # Avoid recursion by omitting a getter

    @password.setter
    def password(self, plain_text_password):
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode('utf-8')

    def check_password_correction(self, attempted_password):
        return bcrypt.check_password_hash(self.password_hash, attempted_password)

class Repo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reponame = db.Column(db.String(30), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    owner = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    merkle_root = db.Column(db.String(256))
    is_private = db.Column(db.Boolean, default=False)
    forked_from = db.Column(db.Integer, db.ForeignKey('repo.id'), nullable=True)
    fork_origin = db.relationship('Repo', remote_side=[id], backref='forks')

    commit_history = commitHistory()