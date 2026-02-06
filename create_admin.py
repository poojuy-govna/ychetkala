from app import app
from models import db, Admin

# Активируем контекст приложения
app.app_context().push()

# Создаём админа
admin = Admin(username='admin', role='admin')
admin.set_password('secure_password_123')

# Сохраняем в БД
db.session.add(admin)
db.session.commit()

print("Админ создан!")