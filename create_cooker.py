from app import app
from models import db, Admin

# Активируем контекст приложения
app.app_context().push()

# Создаём админа
admin = Admin(username='cook', role='cook')
admin.set_password('cook')

# Сохраняем в БД
db.session.add(admin)
db.session.commit()

print("Админ создан!")