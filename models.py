# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin # Хорошая практика использовать UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

# --- Основная модель пользователя ---
class User(UserMixin, db.Model):
    __tablename__ = 'user' # Явно указываем имя таблицы для родителя
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'student', 'cook', 'admin'

    # Связи определяются здесь, так как они относятся к User.id
    meals_taken = db.relationship('MealTaken', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    orders_made = db.relationship('PurchaseOrder', backref='user', lazy=True) # Для повара
    orders_approved = db.relationship('PurchaseOrder', backref='admin_approver', lazy=True, foreign_keys="PurchaseOrder.approver_id") # Для админа


    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.role})>'

# --- Конкретные модели пользователей ---
class Student(User):
    __tablename__ = 'student'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True) # FK на user.id
    allergies = db.Column(db.Text) # Текстовое поле для аллергий
    preferences = db.Column(db.Text) # Текстовое поле для предпочтений
    # Связи теперь наследуются от User через user.id, НЕ через student.id

class Cook(User):
    __tablename__ = 'cook'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True) # FK на user.id
    # Связи наследуются от User

class Admin(User):
    __tablename__ = 'admin'
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True) # FK на user.id
    # Связи наследуются от User

# --- Другие модели ---
class MealType(db.Model):
    __tablename__ = 'meal_type'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False) # 'Завтрак', 'Обед'

class Meal(db.Model):
    __tablename__ = 'meal'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    meal_type_id = db.Column(db.Integer, db.ForeignKey('meal_type.id'), nullable=False)
    meal_type = db.relationship('MealType', backref='meals')

class MealTaken(db.Model):
    __tablename__ = 'meal_taken'
    id = db.Column(db.Integer, primary_key=True)
    # Ссылка теперь на user.id, так как Student.id = User.id
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False)
    taken_date = db.Column(db.Date, default=datetime.utcnow().date())
    # Чтобы избежать дубликатов, можно добавить уникальный индекс
    __table_args__ = (db.UniqueConstraint('student_id', 'taken_date', name='_student_meal_uc'),)

class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    # Ссылка на user.id
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    type = db.Column(db.String(20)) # 'single', 'subscription'

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    # Ссылка на user.id
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    __tablename__ = 'product'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(20), nullable=False) # 'кг', 'шт', 'л'
    current_stock = db.Column(db.Float, nullable=False)

class Recipe(db.Model):
    __tablename__ = 'recipe'
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey('meal.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_needed = db.Column(db.Float, nullable=False) # Количество продукта на 1 порцию блюда

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    id = db.Column(db.Integer, primary_key=True)
    # Ссылка на user.id (повар)
    cook_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Ссылка на user.id (админ)
    approver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # Может быть NULL до одобрения
    status = db.Column(db.String(20), default='pending') # 'pending', 'approved', 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('purchase_order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity_requested = db.Column(db.Float, nullable=False)
    quantity_approved = db.Column