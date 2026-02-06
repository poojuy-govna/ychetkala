# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Student, Cook, Admin, Meal, MealType, MealTaken, Payment, Feedback, Product, Recipe, PurchaseOrder, OrderItem
import os
from datetime import datetime # Не забудьте импортировать datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Сменить на что-то сложное!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///canteen.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Роуты ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        # Проверяем роль, а не тип класса, так как current_user всегда User
        if current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
        elif current_user.role == 'cook':
            return redirect(url_for('cook_dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('base.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash(f'Добро пожаловать, {current_user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль.', 'error')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return render_template('register.html')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует.', 'error')
            return render_template('register.html')

        new_student = Student(username=username, role='student')
        new_student.set_password(password)
        db.session.add(new_student)
        db.session.commit()
        flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

# --- Студент ---
@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        abort(403)
    student_details = Student.query.get(current_user.id)
    meals = Meal.query.all()  # Передаем список блюд
    return render_template('student/dashboard.html', user=current_user, student_details=student_details, meals=meals)


@app.route('/menu')
def view_menu():
    breakfasts = Meal.query.join(MealType).filter(MealType.name == 'Завтрак').all()
    lunches = Meal.query.join(MealType).filter(MealType.name == 'Обед').all()
    return render_template('menu.html', breakfasts=breakfasts, lunches=lunches)

@app.route('/student/pay', methods=['GET', 'POST'])
@login_required
def pay():
    if current_user.role != 'student':
        abort(403)
    if request.method == 'POST':
        amount = float(request.form['amount'])
        payment_type = request.form['type']

        # Используем current_user.id, так как он равен id в таблице user
        new_payment = Payment(student_id=current_user.id, amount=amount, type=payment_type)
        db.session.add(new_payment)
        db.session.commit()
        flash(f'Оплата на сумму {amount} выполнена успешно.', 'success')
        return redirect(url_for('student_dashboard'))
    return render_template('student/pay.html')

@app.route('/student/preferences', methods=['GET', 'POST'])
@login_required
def preferences():
    if current_user.role != 'student':
        abort(403)
    # Получаем конкретный объект Student
    student_obj = Student.query.get(current_user.id)
    if not student_obj:
         flash("Ошибка: Профиль студента не найден.", "error")
         return redirect(url_for('index'))

    if request.method == 'POST':
        allergies = request.form.get('allergies', '')
        preferences = request.form.get('preferences', '')
        # Изменяем данные объекта Student
        student_obj.allergies = allergies
        student_obj.preferences = preferences
        db.session.commit()
        flash('Пищевые особенности сохранены.', 'success')
        return redirect(url_for('student_dashboard'))
    # Передаем объект Student в шаблон
    return render_template('student/preferences.html', user=current_user, student_obj=student_obj)

@app.route('/student/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if current_user.role != 'student':
        abort(403)
    meals = Meal.query.all()
    if request.method == 'POST':
        meal_id = int(request.form['meal_id'])
        rating = int(request.form['rating'])
        comment = request.form.get('comment', '')

        # Используем current_user.id
        new_feedback = Feedback(student_id=current_user.id, meal_id=meal_id, rating=rating, comment=comment)
        db.session.add(new_feedback)
        db.session.commit()
        flash('Отзыв отправлен. Спасибо!', 'success')
        return redirect(url_for('student_dashboard'))
    return render_template('student/feedback.html', meals=meals)

@app.route('/student/mark_taken', methods=['POST'])
@login_required
def mark_taken():
    if current_user.role != 'student':
        abort(403)
    meal_id = int(request.form['meal_id'])
    meal_date = datetime.utcnow().date()

    # Проверка, не отмечал ли студент уже прием пищи сегодня
    # Используем current_user.id
    existing_mark = MealTaken.query.filter_by(student_id=current_user.id, taken_date=meal_date).first()
    if existing_mark:
        flash('Вы уже отметили получение питания сегодня.', 'warning')
        return redirect(url_for('student_dashboard'))

    # Используем current_user.id
    new_meal_taken = MealTaken(student_id=current_user.id, meal_id=meal_id)
    db.session.add(new_meal_taken)
    db.session.commit()
    flash('Получение питания отмечено.', 'success')
    return redirect(url_for('student_dashboard'))

# --- Повар ---
@app.route('/cook/dashboard')
@login_required
def cook_dashboard():
    if current_user.role != 'cook':
        abort(403)
    inventory = Product.query.all()
    return render_template('cook/dashboard.html', user=current_user, inventory=inventory)

@app.route('/cook/track_meals', methods=['GET', 'POST'])
@login_required
def track_meals():
    if current_user.role != 'cook':
        abort(403)
    # Загружаем студентов и блюда
    students = Student.query.all() # Загружаем только студентов
    meals = Meal.query.all()
    if request.method == 'POST':
        student_id = int(request.form['student_id'])
        meal_id = int(request.form['meal_id'])

        meal_date = datetime.utcnow().date()
        existing_mark = MealTaken.query.filter_by(student_id=student_id, taken_date=meal_date).first()
        if existing_mark:
             flash(f'Студент {Student.query.get(student_id).username} уже получил питание сегодня.', 'warning')
             return redirect(url_for('track_meals'))

        new_meal_taken = MealTaken(student_id=student_id, meal_id=meal_id)
        db.session.add(new_meal_taken)
        db.session.commit()
        flash(f'Получение питания отмечено за студентом {Student.query.get(student_id).username}.', 'success')
        return redirect(url_for('track_meals'))
    return render_template('cook/track_meals.html', students=students, meals=meals)


@app.route('/cook/purchase_order', methods=['GET', 'POST'])
@login_required
def purchase_order():
    if current_user.role != 'cook':
        abort(403)
    products = Product.query.all()
    if request.method == 'POST':
        order_items = []
        for product in products:
            quantity = request.form.get(f'quantity_{product.id}', 0)
            if float(quantity) > 0:
                order_item = OrderItem(product_id=product.id, quantity_requested=float(quantity))
                order_items.append(order_item)

        if not order_items:
             flash('Заявка пуста. Добавьте продукты.', 'warning')
             return redirect(url_for('purchase_order'))

        # Используем current_user.id для cook_id
        new_order = PurchaseOrder(cook_id=current_user.id, status='pending')
        db.session.add(new_order)
        db.session.flush()
        for item in order_items:
            item.order_id = new_order.id
            db.session.add(item)
        db.session.commit()
        flash('Заявка на закупку создана и ожидает рассмотрения.', 'success')
        return redirect(url_for('cook_dashboard'))
    return render_template('cook/purchase_order.html', products=products)

# --- Администратор ---
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        abort(403)
    pending_orders = PurchaseOrder.query.filter_by(status='pending').all()
    return render_template('admin/dashboard.html', user=current_user, pending_orders=pending_orders)

@app.route('/admin/manage_orders')
@login_required
def manage_orders():
    if current_user.role != 'admin':
        abort(403)
    orders = PurchaseOrder.query.all()
    return render_template('admin/manage_orders.html', orders=orders)

@app.route('/admin/approve_order/<int:order_id>', methods=['POST'])
@login_required
def approve_order(order_id):
    if current_user.role != 'admin':
        abort(403)
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != 'pending':
        flash('Статус заявки уже изменен.', 'warning')
        return redirect(url_for('manage_orders'))

    order.status = 'approved'
    # Используем current_user.id для approver_id
    order.approver_id = current_user.id
    order.approved_at = datetime.utcnow()
    db.session.commit()
    flash(f'Заявка #{order_id} одобрена.', 'success')
    return redirect(url_for('manage_orders'))

@app.route('/admin/reject_order/<int:order_id>', methods=['POST'])
@login_required
def reject_order(order_id):
    if current_user.role != 'admin':
        abort(403)
    order = PurchaseOrder.query.get_or_404(order_id)
    if order.status != 'pending':
        flash('Статус заявки уже изменен.', 'warning')
        return redirect(url_for('manage_orders'))

    order.status = 'rejected'
    # Используем current_user.id для approver_id
    order.approver_id = current_user.id
    order.approved_at = datetime.utcnow()
    db.session.commit()
    flash(f'Заявка #{order_id} отклонена.', 'info')
    return redirect(url_for('manage_orders'))

@app.route('/admin/reports')
@login_required
def reports():
    if current_user.role != 'admin':
        abort(403)
    total_payments = db.session.query(db.func.sum(Payment.amount)).scalar() or 0
    meals_count = MealTaken.query.count()
    return render_template('admin/reports.html', total_payments=total_payments, meals_count=meals_count)


if __name__ == '__main__':
    with app.app_context():
        # Убедитесь, что старая база данных удалена при первом запуске, если вы меняете структуру
        # os.remove('canteen.db') # Раскомментируйте, если нужно полностью пересоздать БД
        db.create_all()
        # --- Добавление тестовых данных ---
        if not MealType.query.first():
            breakfast = MealType(name='Завтрак')
            lunch = MealType(name='Обед')
            db.session.add(breakfast)
            db.session.add(lunch)
            db.session.commit()

        if not Meal.query.first():
            meal1 = Meal(name='Каша овсяная', description='На молоке с маслом', price=80.0, meal_type_id=1)
            meal2 = Meal(name='Борщ', description='Со сметаной и пампушками', price=90.0, meal_type_id=2)
            meal3 = Meal(name='Греча с котлеткой', description='Гречневая каша с мясной котлетой', price=100.0, meal_type_id=2)
            db.session.add(meal1)
            db.session.add(meal2)
            db.session.add(meal3)
            db.session.commit()

        if not Product.query.first():
            prod1 = Product(name='Молоко', unit='л', current_stock=100.0)
            prod2 = Product(name='Овсянка', unit='кг', current_stock=50.0)
            prod3 = Product(name='Мясо фарш', unit='кг', current_stock=30.0)
            prod4 = Product(name='Картофель', unit='кг', current_stock=200.0)
            db.session.add(prod1)
            db.session.add(prod2)
            db.session.add(prod3)
            db.session.add(prod4)
            db.session.commit()

        # Создание тестовых пользователей
        if not User.query.filter_by(username='student1').first():
            s1 = Student(username='student1', role='student')
            s1.set_password('password')
            db.session.add(s1)
        if not User.query.filter_by(username='cook1').first():
            c1 = Cook(username='cook1', role='cook')
            c1.set_password('password')
            db.session.add(c1)
        if not User.query.filter_by(username='admin1').first():
            a1 = Admin(username='admin1', role='admin')
            a1.set_password('password')
            db.session.add(a1)
        db.session.commit()
        # -------------------------------

    app.run(debug=True)