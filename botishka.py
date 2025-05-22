import sqlite3
import telebot
from telebot import types
import os

# Константы
TOKEN = "6896892992:AAHHll2f4cwxis_1ykbOUQf750a6AmVyumU"
DB_NAME = "sqlite3.db"

# Инициализация бота
bot = telebot.TeleBot(TOKEN)
booking_sessions = {}

# Инициализация БД
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        role TEXT CHECK (role IN ('client', 'restaurant')),
        registration_date TEXT
    )
    ''')

    # Таблица клиентов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        client_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        phone TEXT,
        city TEXT,
        bookings_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # Таблица ресторанов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurants (
        restaurant_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        name TEXT,
        location TEXT,
        photo_id TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')

    # Таблица официантов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS waiters (
        waiter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id INTEGER,
        name TEXT,
        age INTEGER,
        photo_id TEXT,
        rating REAL DEFAULT 0.0,
        reviews_count INTEGER DEFAULT 0,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (restaurant_id)
    )
    ''')

    # Таблица бронирований
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        waiter_id INTEGER,
        date TEXT,
        time TEXT,
        persons INTEGER,
        notes TEXT,
        tips REAL DEFAULT 0.0,
        FOREIGN KEY (client_id) REFERENCES clients (client_id),
        FOREIGN KEY (waiter_id) REFERENCES waiters (waiter_id)
    )
    ''')

    # Таблица отзывов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        rating INTEGER CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        FOREIGN KEY (booking_id) REFERENCES bookings (booking_id)
    )
    ''')

    conn.commit()
    conn.close()

init_db()  # Создаём БД при запуске

# Проверка регистрации пользователя
def is_user_registered(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# Стартовый обработчик
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        show_main_menu(message)
    else:
        show_registration_choice(message)

# Выбор роли (Клиент/Ресторан)
def show_registration_choice(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_client = types.KeyboardButton('👤 Я клиент')
    btn_restaurant = types.KeyboardButton('🏢 Я ресторан')
    markup.add(btn_client, btn_restaurant)
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать! Выберите роль:",
        reply_markup=markup
    )

# Главное меню (будет доработано)
def show_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Здесь будут кнопки в зависимости от роли
    bot.send_message(
        message.chat.id,
        "🏠 Главное меню",
        reply_markup=markup
    )

# =============================================
# Регистрация клиента
# =============================================

@bot.message_handler(func=lambda message: message.text == '👤 Я клиент')
def handle_client_choice(message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        show_main_menu(message)
        return

    # Добавляем пользователя в БД с ролью 'client'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, role, registration_date) VALUES (?, ?, datetime('now'))",
        (user_id, 'client')
    )
    conn.commit()
    conn.close()

    # Запрашиваем имя
    bot.send_message(message.chat.id, "👤 Как вас зовут?")
    bot.register_next_step_handler(message, process_client_name)


def process_client_name(message):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "❌ Имя не может быть пустым. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_client_name)

    # Сохраняем имя во временные данные (позже добавим в БД)
    user_data = {'name': name}

    # Запрашиваем телефон
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton("📱 Отправить номер", request_contact=True)
    markup.add(btn_phone)
    bot.send_message(
        message.chat.id,
        "📱 Отправьте ваш номер телефона:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_client_phone, user_data)


def process_client_phone(message, user_data):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = message.text.strip()
        if not phone.isdigit():
            bot.send_message(message.chat.id, "❌ Номер должен содержать только цифры. Попробуйте ещё раз.")
            return bot.register_next_step_handler(message, process_client_phone, user_data)

    user_data['phone'] = phone

    # Запрашиваем город
    bot.send_message(message.chat.id, "🌆 В каком городе вы находитесь?")
    bot.register_next_step_handler(message, process_client_city, user_data)


def process_client_city(message, user_data):
    city = message.text.strip()
    if not city:
        bot.send_message(message.chat.id, "❌ Город не может быть пустым. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_client_city, user_data)

    # Сохраняем клиента в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clients (user_id, name, phone, city) VALUES (?, ?, ?, ?)",
        (message.from_user.id, user_data['name'], user_data['phone'], city)
    )
    conn.commit()
    conn.close()

    # Показываем главное меню
    show_main_menu(message)
    bot.send_message(message.chat.id, "✅ Регистрация завершена!")


# =============================================
# Главное меню клиента
# =============================================

def show_main_menu(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Проверяем роль пользователя
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()[0]
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if role == 'client':
        markup.add(
            types.KeyboardButton('👤 Профиль'),
            types.KeyboardButton('🏢 Рестораны'),
            types.KeyboardButton('📖 История бронирований'),
            types.KeyboardButton('🏆 Топ официантов')
        )
    else:
        # Меню для ресторана (добавим позже)
        pass

    bot.send_message(
        message.chat.id,
        "🏠 Главное меню:",
        reply_markup=markup
    )


# =============================================
# Обработка команды "Профиль"
# =============================================

@bot.message_handler(func=lambda message: message.text == '👤 Профиль')
def show_client_profile(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем данные клиента
    cursor.execute(
        "SELECT name, phone, city, bookings_count FROM clients WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        bot.send_message(message.chat.id, "❌ Профиль не найден.")
        return

    name, phone, city, bookings = data
    profile_text = (
        f"👤 *Ваш профиль*\n\n"
        f"▪️ *Имя:* {name}\n"
        f"▪️ *Телефон:* {phone}\n"
        f"▪️ *Город:* {city}\n"
        f"▪️ *Бронирований:* {bookings}"
    )

    # Кнопки для редактирования
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✏️ Изменить имя", callback_data="edit_name"),
        types.InlineKeyboardButton("📱 Изменить телефон", callback_data="edit_phone"),
        types.InlineKeyboardButton("🌆 Изменить город", callback_data="edit_city"),
    )
    markup.add(types.InlineKeyboardButton("", callback_data="back_to_menu"))

    bot.send_message(
        message.chat.id,
        profile_text,
        parse_mode="Markdown",
        reply_markup=markup
    )


# Обработка inline-кнопок профиля
@bot.callback_query_handler(func=lambda call: call.data.startswith('edit_') or call.data == 'back_to_menu')
def handle_profile_actions(call):
    if call.data == 'back_to_menu':
        show_main_menu(call.message)
    elif call.data == 'edit_name':
        bot.send_message(call.message.chat.id, "✏️ Введите новое имя:")
        bot.register_next_step_handler(call.message, update_client_name)
    elif call.data == 'edit_phone':
        bot.send_message(call.message.chat.id, "📱 Введите новый номер телефона:")
        bot.register_next_step_handler(call.message, update_client_phone)
    elif call.data == 'edit_city':
        bot.send_message(call.message.chat.id, "🌆 Введите новый город:")
        bot.register_next_step_handler(call.message, update_client_city)

def update_client_name(message):
    new_name = message.text.strip()
    if not new_name:
        bot.send_message(message.chat.id, "❌ Имя не может быть пустым.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clients SET name = ? WHERE user_id = ?",
        (new_name, message.from_user.id)
    )
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Имя обновлено!")
    show_client_profile(message)

def update_client_phone(message):
    new_phone = message.text.strip()
    if not new_phone:
        bot.send_message(message.chat.id, "❌ Номер телефона не может быть пустым.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clients SET phone = ? WHERE user_id = ?",
        (new_phone, message.from_user.id)
    )
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Номер телефона обновлён!")
    show_client_profile(message)

def update_client_city(message):
    new_city = message.text.strip()
    if not new_city:
        bot.send_message(message.chat.id, "❌ Город не может быть пустым.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE clients SET city = ? WHERE user_id = ?",
        (new_city, message.from_user.id)
    )
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Город обновлён!")
    show_client_profile(message)


# =============================================
# Регистрация ресторана
# =============================================

@bot.message_handler(func=lambda message: message.text == '🏢 Я ресторан')
def handle_restaurant_choice(message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        show_main_menu(message)
        return

    # Добавляем пользователя в БД с ролью 'restaurant'
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, role, registration_date) VALUES (?, ?, datetime('now'))",
        (user_id, 'restaurant')
    )
    conn.commit()
    conn.close()

    # Запрашиваем название ресторана
    bot.send_message(message.chat.id, "🏢 Введите название вашего ресторана:")
    bot.register_next_step_handler(message, process_restaurant_name)


def process_restaurant_name(message):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "❌ Название не может быть пустым. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_restaurant_name)

    # Сохраняем название во временные данные
    user_data = {'name': name}

    # Запрашиваем локацию
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_location = types.KeyboardButton("📍 Отправить локацию", request_location=True)
    markup.add(btn_location)
    bot.send_message(
        message.chat.id,
        "📍 Отправьте местоположение ресторана (или введите адрес вручную):",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_restaurant_location, user_data)


def process_restaurant_location(message, user_data):
    if message.location:
        location = f"{message.location.latitude},{message.location.longitude}"
    else:
        location = message.text.strip()
        if not location:
            bot.send_message(message.chat.id, "❌ Локация не может быть пустой. Попробуйте ещё раз.")
            return bot.register_next_step_handler(message, process_restaurant_location, user_data)

    user_data['location'] = location

    # Запрашиваем фото
    bot.send_message(message.chat.id, "📸 Пришлите фото ресторана:")
    bot.register_next_step_handler(message, process_restaurant_photo, user_data)


def process_restaurant_photo(message, user_data):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_restaurant_photo, user_data)

    # Сохраняем фото (используем file_id)
    photo_id = message.photo[-1].file_id
    user_data['photo_id'] = photo_id

    # Сохраняем ресторан в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO restaurants (user_id, name, location, photo_id) VALUES (?, ?, ?, ?)",
        (message.from_user.id, user_data['name'], user_data['location'], user_data['photo_id'])
    )
    restaurant_id = cursor.lastrowid

    # Требуем добавить хотя бы 1 официанта
    bot.send_message(message.chat.id, "🧑‍🍳 Теперь добавьте официанта. Введите его имя:")
    bot.register_next_step_handler(message, process_waiter_name, restaurant_id)
    conn.commit()
    conn.close()


# =============================================
# Добавление официанта
# =============================================

def process_waiter_name(message, restaurant_id):
    name = message.text.strip()
    if not name:
        bot.send_message(message.chat.id, "❌ Имя не может быть пустым. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_waiter_name, restaurant_id)

    user_data = {'name': name, 'restaurant_id': restaurant_id}

    # Запрашиваем возраст
    bot.send_message(message.chat.id, "🔢 Введите возраст официанта:")
    bot.register_next_step_handler(message, process_waiter_age, user_data)


def process_waiter_age(message, user_data):
    age = message.text.strip()
    if not age.isdigit() or int(age) < 18:
        bot.send_message(message.chat.id, "❌ Возраст должен быть числом (от 18 лет). Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_waiter_age, user_data)

    user_data['age'] = int(age)

    # Запрашиваем фото
    bot.send_message(message.chat.id, "📸 Пришлите фото официанта:")
    bot.register_next_step_handler(message, process_waiter_photo, user_data)


def process_waiter_photo(message, user_data):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото. Попробуйте ещё раз.")
        return bot.register_next_step_handler(message, process_waiter_photo, user_data)

    photo_id = message.photo[-1].file_id

    # Сохраняем официанта в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO waiters (restaurant_id, name, age, photo_id) VALUES (?, ?, ?, ?)",
        (user_data['restaurant_id'], user_data['name'], user_data['age'], photo_id)
    )
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "✅ Официант добавлен!")
    show_main_menu(message)


# =============================================
# Главное меню ресторана
# =============================================

def show_main_menu(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
    role = cursor.fetchone()[0]
    conn.close()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if role == 'client':
        markup.add(
            types.KeyboardButton('👤 Профиль'),
            types.KeyboardButton('🏢 Рестораны'),
            types.KeyboardButton('📖 История бронирований'),
            types.KeyboardButton('🏆 Топ официантов')
        )
    else:
        markup.add(
            types.KeyboardButton('🏠 Профиль ресторана'),
            types.KeyboardButton('🧑‍🍳 Официанты'),
            types.KeyboardButton('💰 История чаевых')
        )

    bot.send_message(
        message.chat.id,
        "🏠 Главное меню:",
        reply_markup=markup
    )


# =============================================
# Профиль ресторана
# =============================================

@bot.message_handler(func=lambda message: message.text == '🏠 Профиль ресторана')
def show_restaurant_profile(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, location, photo_id FROM restaurants WHERE user_id = ?",
        (user_id,)
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        bot.send_message(message.chat.id, "❌ Ресторан не найден.")
        return

    name, location, photo_id = data
    profile_text = (
        f"🏢 *Профиль ресторана*\n\n"
        f"▪️ *Название:* {name}\n"
        f"▪️ *Локация:* {location}\n"
    )

    # Кнопки для редактирования
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✏️ Изменить название", callback_data="edit_restaurant_name"),
        types.InlineKeyboardButton("📍 Изменить локацию", callback_data="edit_restaurant_location"),
        types.InlineKeyboardButton("📸 Изменить фото", callback_data="edit_restaurant_photo"),
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))

    # Отправляем фото + текст
    bot.send_photo(
        message.chat.id,
        photo_id,
        caption=profile_text,
        parse_mode="Markdown",
        reply_markup=markup
    )


# =============================================
# Просмотр списка официантов (для ресторана)
# =============================================

@bot.message_handler(func=lambda message: message.text == '🧑‍🍳 Официанты')
def show_waiters_list(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем ID ресторана
    cursor.execute("SELECT restaurant_id FROM restaurants WHERE user_id = ?", (user_id,))
    restaurant_id = cursor.fetchone()[0]

    # Получаем список официантов
    cursor.execute(
        "SELECT waiter_id, name FROM waiters WHERE restaurant_id = ?",
        (restaurant_id,)
    )
    waiters = cursor.fetchall()
    conn.close()

    if not waiters:
        bot.send_message(message.chat.id, "❌ У вас пока нет официантов.")
        return

    # Создаем inline-кнопки с именами официантов
    markup = types.InlineKeyboardMarkup()
    for waiter in waiters:
        markup.add(
            types.InlineKeyboardButton(
                waiter[1],
                callback_data=f"waiter_{waiter[0]}"
            )
        )
    markup.add(types.InlineKeyboardButton("➕ Добавить официанта", callback_data="add_waiter"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_menu"))

    bot.send_message(
        message.chat.id,
        "🧑‍🍳 Ваши официанты:",
        reply_markup=markup
    )


# =============================================
# Просмотр информации об официанте (исправленная версия)
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('waiter_info_'))
def show_waiter_details(call):
    waiter_id = call.data.split('_')[2]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем информацию об официанте и ресторане
    cursor.execute(
        """SELECT w.name, w.age, w.photo_id, w.rating, w.reviews_count, 
                  r.restaurant_id, r.name
           FROM waiters w
           JOIN restaurants r ON w.restaurant_id = r.restaurant_id
           WHERE w.waiter_id = ?""",
        (waiter_id,)
    )
    data = cursor.fetchone()
    conn.close()

    if not data:
        bot.answer_callback_query(call.id, "❌ Официант не найден")
        return

    name, age, photo_id, rating, reviews, restaurant_id, restaurant_name = data
    info_text = (
        f"🧑‍🍳 *{name}*\n\n"
        f"🏢 *Ресторан:* {restaurant_name}\n"
        f"🎂 *Возраст:* {age}\n"
        f"⭐ *Рейтинг:* {rating:.1f} ({reviews} отзывов)"
    )

    # Кнопки для клиента
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📅 Забронировать", callback_data=f"book_waiter_{waiter_id}"),
        types.InlineKeyboardButton("💸 Оставить чаевые", callback_data=f"send_tips_{waiter_id}"),
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_restaurant_{restaurant_id}"))

    # Отправляем информацию
    try:
        bot.send_photo(
            call.message.chat.id,
            photo_id,
            caption=info_text,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            info_text,
            parse_mode="Markdown",
            reply_markup=markup
        )


# =============================================
# Обработка кнопки "Назад" к ресторану
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('back_to_restaurant_'))
def back_to_restaurant(call):
    restaurant_id = call.data.split('_')[3]

    # Создаем искусственное сообщение для вызова show_restaurant_info
    class FakeMessage:
        def __init__(self):
            self.chat = call.message.chat
            self.message_id = call.message.message_id

    fake_msg = FakeMessage()

    # Создаем искусственный callback с нужными данными
    class FakeCall:
        def __init__(self):
            self.data = f"restaurant_{restaurant_id}"
            self.message = fake_msg

    fake_call = FakeCall()

    show_restaurant_info(fake_call)


# =============================================
# Раздел "Рестораны" для клиентов
# =============================================

@bot.message_handler(func=lambda message: message.text == '🏢 Рестораны')
def show_restaurants_list(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем список ресторанов (первые 10)
    cursor.execute("SELECT restaurant_id, name, photo_id FROM restaurants LIMIT 10")
    restaurants = cursor.fetchall()
    conn.close()

    if not restaurants:
        bot.send_message(message.chat.id, "❌ Пока нет доступных ресторанов.")
        return

    # Создаем inline-кнопки с ресторанами
    markup = types.InlineKeyboardMarkup()
    for restaurant in restaurants:
        markup.add(
            types.InlineKeyboardButton(
                restaurant[1],
                callback_data=f"restaurant_{restaurant[0]}"
            )
        )
    markup.add(types.InlineKeyboardButton("🔍 Поиск ресторана", switch_inline_query_current_chat=""))

    bot.send_message(
        message.chat.id,
        "🏢 Доступные рестораны:",
        reply_markup=markup
    )


# =============================================
# Просмотр информации о ресторане (исправленная версия)
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('restaurant_'))
def show_restaurant_info(call):
    parts = call.data.split('_')
    if len(parts) < 2:
        bot.answer_callback_query(call.id, "❌ Ошибка запроса")
        return

    restaurant_id = parts[1]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем информацию о ресторане
    cursor.execute(
        "SELECT name, location, photo_id FROM restaurants WHERE restaurant_id = ?",
        (restaurant_id,)
    )
    restaurant_data = cursor.fetchone()

    if not restaurant_data:
        bot.answer_callback_query(call.id, "❌ Ресторан не найден")
        conn.close()
        return

    # Получаем список официантов
    cursor.execute(
        "SELECT waiter_id, name FROM waiters WHERE restaurant_id = ?",
        (restaurant_id,)
    )
    waiters = cursor.fetchall()
    conn.close()

    name, location, photo_id = restaurant_data
    info_text = (
        f"🏢 *{name}*\n\n"
        f"📍 *Адрес:* {location}\n"
        f"🧑‍🍳 *Официанты:* {len(waiters)}"
    )

    # Создаем кнопки для официантов
    markup = types.InlineKeyboardMarkup()
    for waiter in waiters:
        markup.add(
            types.InlineKeyboardButton(
                f"🧑‍🍳 {waiter[1]}",
                callback_data=f"waiter_info_{waiter[0]}"
            )
        )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_restaurants"))

    # Отправляем сообщение с фото
    try:
        bot.send_photo(
            call.message.chat.id,
            photo_id,
            caption=info_text,
            parse_mode="Markdown",
            reply_markup=markup
        )
    except Exception as e:
        bot.send_message(
            call.message.chat.id,
            info_text,
            parse_mode="Markdown",
            reply_markup=markup
        )


# =============================================
# Обработка кнопки "Назад" в разных разделах
# =============================================

@bot.callback_query_handler(func=lambda call: call.data in ['back_to_menu', 'back_to_waiters', 'back_to_restaurants'])
def handle_back_buttons(call):
    if call.data == 'back_to_menu':
        show_main_menu(call.message)
    elif call.data == 'back_to_waiters':
        show_waiters_list(call.message)
    elif call.data == 'back_to_restaurants':
        show_restaurants_list(call.message)


# =============================================
# Бронирование официанта (клиент)
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('restaurant_waiter_'))
def start_booking(call):
    waiter_id = call.data.split('_')[2]
    user_data = {'waiter_id': waiter_id}

    # Запрашиваем дату
    bot.send_message(
        call.message.chat.id,
        "📅 Выберите дату бронирования (например, 15.06.2024):"
    )
    bot.register_next_step_handler(call.message, process_booking_date, user_data)


def process_booking_date(message, user_data):
    date = message.text.strip()
    if not date:
        bot.send_message(message.chat.id, "❌ Дата не может быть пустой.")
        return bot.register_next_step_handler(message, process_booking_date, user_data)

    user_data['date'] = date

    # Запрашиваем время
    bot.send_message(
        message.chat.id,
        "⏰ Выберите время (например, 19:30):"
    )
    bot.register_next_step_handler(message, process_booking_time, user_data)


def process_booking_time(message, user_data):
    time = message.text.strip()
    if not time:
        bot.send_message(message.chat.id, "❌ Время не может быть пустым.")
        return bot.register_next_step_handler(message, process_booking_time, user_data)

    user_data['time'] = time

    # Запрашиваем количество персон
    bot.send_message(
        message.chat.id,
        "👥 Укажите количество гостей:"
    )
    bot.register_next_step_handler(message, process_booking_persons, user_data)


def process_booking_persons(message, user_data):
    persons = message.text.strip()
    if not persons.isdigit() or int(persons) < 1:
        bot.send_message(message.chat.id, "❌ Введите число больше 0.")
        return bot.register_next_step_handler(message, process_booking_persons, user_data)

    user_data['persons'] = int(persons)

    # Запрашиваем пожелания (опционально)
    bot.send_message(
        message.chat.id,
        "💬 Есть особые пожелания? (или нажмите 'Пропустить')"
    )
    bot.register_next_step_handler(message, process_booking_notes, user_data)


def process_booking_notes(message, user_data):
    notes = message.text if message.text != "Пропустить" else ""
    user_data['notes'] = notes

    # Подтверждение брони
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_booking_{user_data['waiter_id']}"),
        types.InlineKeyboardButton("💸 Предоплатить чаевые", callback_data=f"prepay_tips_{user_data['waiter_id']}"),
        types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_booking")
    )

    booking_text = (
        f"📝 *Подтвердите бронирование:*\n\n"
        f"▪️ Дата: {user_data['date']}\n"
        f"▪️ Время: {user_data['time']}\n"
        f"▪️ Гости: {user_data['persons']}\n"
        f"▪️ Пожелания: {user_data['notes'] or 'нет'}"
    )

    bot.send_message(
        message.chat.id,
        booking_text,
        parse_mode="Markdown",
        reply_markup=markup
    )


# =============================================
# Подтверждение бронирования
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_booking_'))
def confirm_booking(call):
    waiter_id = call.data.split('_')[2]
    client_id = call.from_user.id

    # Сохраняем бронь в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO bookings (client_id, waiter_id, date, time, persons, notes) VALUES (?, ?, ?, ?, ?, ?)",
        (client_id, waiter_id, user_data['date'], user_data['time'], user_data['persons'], user_data['notes'])
    )
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "✅ Бронирование подтверждено!")
    bot.send_message(call.message.chat.id, "🎉 Ваш столик забронирован!")


# =============================================
# Оставление отзыва (клиент)
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith('review_'))
def ask_review_rating(call):
    booking_id = call.data.split('_')[1]

    markup = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"set_rating_{booking_id}_{i}"))

    bot.send_message(
        call.message.chat.id,
        "⭐ Оцените официанта (1-5 звезд):",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_rating_'))
def save_review(call):
    _, _, booking_id, rating = call.data.split('_')

    # Сохраняем отзыв в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO reviews (booking_id, rating) VALUES (?, ?)",
        (booking_id, rating)
    )
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "✅ Спасибо за отзыв!")


# =============================================
# Чаевые (общая функция)
# =============================================

@bot.callback_query_handler(func=lambda call: call.data.startswith(('prepay_tips_', 'send_tips_')))
def handle_tips(call):
    waiter_id = call.data.split('_')[2]
    bot.send_message(
        call.message.chat.id,
        "💸 Введите сумму чаевых:"
    )
    bot.register_next_step_handler(call.message, process_tips_amount, waiter_id)


def process_tips_amount(message, waiter_id):
    amount = message.text.strip()
    if not amount.isdigit() or int(amount) < 1:
        bot.send_message(message.chat.id, "❌ Введите корректную сумму.")
        return bot.register_next_step_handler(message, process_tips_amount, waiter_id)

    # Обновляем бронь или запись официанта
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE bookings SET tips = ? WHERE waiter_id = ?",
        (amount, waiter_id)
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"✅ Чаевые {amount}₽ учтены!"
    )


@bot.message_handler(func=lambda message: message.text == '📖 История бронирований')
def show_booking_history(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем историю бронирований с именами официантов и ресторанов
    cursor.execute('''
                   SELECT b.booking_id, w.name, r.name, b.date, b.time, b.tips
                   FROM bookings b
                            JOIN waiters w ON b.waiter_id = w.waiter_id
                            JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                   WHERE b.client_id = ?
                   ORDER BY b.date DESC
                   ''', (user_id,))

    bookings = cursor.fetchall()
    conn.close()

    if not bookings:
        bot.send_message(message.chat.id, "📭 У вас пока нет бронирований.")
        return

    # Отправляем первые 5 бронирований (с пагинацией)
    send_bookings_page(message.chat.id, bookings, page=0)


def send_bookings_page(chat_id, bookings, page):
    start_idx = page * 5
    end_idx = start_idx + 5
    current_bookings = bookings[start_idx:end_idx]

    # Формируем текст
    text = "📖 *Ваши бронирования:*\n\n"
    for booking in current_bookings:
        booking_id, waiter_name, restaurant_name, date, time, tips = booking
        text += (
            f"▪️ #{booking_id}\n"
            f"Официант: {waiter_name}\n"
            f"Ресторан: {restaurant_name}\n"
            f"Дата: {date} {time}\n"
            f"Чаевые: {tips or 0}₽\n"
            f"——————\n"
        )

    # Кнопки
    markup = types.InlineKeyboardMarkup()

    # Кнопки для каждого бронирования
    for booking in current_bookings:
        booking_id = booking[0]
        markup.add(
            types.InlineKeyboardButton(
                f"ℹ️ Подробнее #{booking_id}",
                callback_data=f"booking_details_{booking_id}"
            )
        )

    # Пагинация
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"bookings_page_{page - 1}"))
    if end_idx < len(bookings):
        markup.add(types.InlineKeyboardButton("▶️ Вперед", callback_data=f"bookings_page_{page + 1}"))

    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))

    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('booking_details_'))
def show_booking_details(call):
    booking_id = call.data.split('_')[2]
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute('''
                   SELECT b.date,
                          b.time,
                          b.persons,
                          b.notes,
                          b.tips,
                          w.name,
                          w.photo_id,
                          r.name
                   FROM bookings b
                            JOIN waiters w ON b.waiter_id = w.waiter_id
                            JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                   WHERE b.booking_id = ?
                   ''', (booking_id,))

    booking = cursor.fetchone()
    conn.close()

    if not booking:
        bot.answer_callback_query(call.id, "❌ Бронирование не найдено")
        return

    # Формируем текст
    text = (
        f"📝 *Детали бронирования*\n\n"
        f"▪️ Дата: {booking[0]}\n"
        f"▪️ Время: {booking[1]}\n"
        f"▪️ Гостей: {booking[2]}\n"
        f"▪️ Пожелания: {booking[3] or 'нет'}\n"
        f"▪️ Чаевые: {booking[4] or 0}₽\n"
        f"🧑‍🍳 Официант: {booking[5]}\n"
        f"🏢 Ресторан: {booking[7]}"
    )

    # Кнопки
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("⭐ Оставить отзыв", callback_data=f"review_{booking_id}"),
        types.InlineKeyboardButton("💸 Добавить чаевые", callback_data=f"add_tips_{booking_id}"),
    )
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_bookings"))

    # Отправляем фото официанта, если есть
    if booking[6]:
        try:
            bot.send_photo(
                call.message.chat.id,
                booking[6],
                caption=text,
                parse_mode="Markdown",
                reply_markup=markup
            )
            return
        except:
            pass

    bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == '🏆 Топ официантов')
def show_top_waiters(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем топ официантов по рейтингу
    cursor.execute('''
                   SELECT w.waiter_id, w.name, w.photo_id, w.rating, w.reviews_count, r.name
                   FROM waiters w
                            JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                   WHERE w.reviews_count > 0
                   ORDER BY w.rating DESC, w.reviews_count DESC LIMIT 10
                   ''')

    waiters = cursor.fetchall()
    conn.close()

    if not waiters:
        bot.send_message(message.chat.id, "📊 Рейтинг официантов пока пуст.")
        return

    send_waiters_page(message.chat.id, waiters, page=0)


def send_waiters_page(chat_id, waiters, page):
    start_idx = page * 5
    end_idx = start_idx + 5
    current_waiters = waiters[start_idx:end_idx]

    text = "🏆 *Топ официантов:*\n\n"
    for idx, waiter in enumerate(current_waiters, start=1):
        waiter_id, name, _, rating, reviews, restaurant = waiter
        text += (
            f"{start_idx + idx}. {name}\n"
            f"⭐ {rating:.1f} ({reviews} отзывов)\n"
            f"🏢 {restaurant}\n"
            f"——————\n"
        )

    markup = types.InlineKeyboardMarkup()

    # Кнопки для каждого официанта
    for waiter in current_waiters:
        markup.add(
            types.InlineKeyboardButton(
                f"🧑‍🍳 {waiter[1]}",
                callback_data=f"waiter_info_{waiter[0]}"
            )
        )

    # Пагинация
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"top_page_{page - 1}"))
    if end_idx < len(waiters):
        markup.add(types.InlineKeyboardButton("▶️ Вперед", callback_data=f"top_page_{page + 1}"))

    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))

    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == '💰 История чаевых')
def show_tips_history(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Получаем историю чаевых для ресторана
    cursor.execute('''
                   SELECT t.date, w.name, t.amount
                   FROM (SELECT b.date, b.waiter_id, b.tips as amount
                         FROM bookings b
                                  JOIN waiters w ON b.waiter_id = w.waiter_id
                                  JOIN restaurants r ON w.restaurant_id = r.restaurant_id
                         WHERE r.user_id = ?
                           AND b.tips > 0
                         UNION ALL
                         SELECT datetime('now') as date, waiter_id, tips as amount
                         FROM waiter_tips
                         WHERE restaurant_id IN (
                             SELECT restaurant_id FROM restaurants WHERE user_id = ?
                             )) t
                            JOIN waiters w ON t.waiter_id = w.waiter_id
                   ORDER BY t.date DESC LIMIT 50
                   ''', (user_id, user_id))

    tips = cursor.fetchall()
    conn.close()

    if not tips:
        bot.send_message(message.chat.id, "💸 История чаевых пуста.")
        return

    send_tips_page(message.chat.id, tips, page=0)


def send_tips_page(chat_id, tips, page):
    start_idx = page * 7
    end_idx = start_idx + 7
    current_tips = tips[start_idx:end_idx]

    text = "💰 *Последние чаевые:*\n\n"
    for tip in current_tips:
        date, waiter_name, amount = tip
        text += f"▪️ {date}: {waiter_name} — {amount}₽\n"

    markup = types.InlineKeyboardMarkup()

    # Пагинация
    if page > 0:
        markup.add(types.InlineKeyboardButton("◀️ Назад", callback_data=f"tips_page_{page - 1}"))
    if end_idx < len(tips):
        markup.add(types.InlineKeyboardButton("▶️ Вперед", callback_data=f"tips_page_{page + 1}"))

    markup.add(types.InlineKeyboardButton("⬅️ В меню", callback_data="back_to_menu"))

    bot.send_message(chat_id, text, reply_markup=markup)


# =============================================
# Обработка кнопки "Забронировать" у официанта
# =============================================



# ========== Обработка бронирования ==========
@bot.callback_query_handler(func=lambda call: call.data.startswith('book_waiter_'))
def start_booking(call):
    waiter_id = call.data.split('_')[2]
    user_id = call.from_user.id
    
    # Сохраняем данные сессии
    booking_sessions[user_id] = {
        'waiter_id': waiter_id,
        'step': 'date'
    }
    
    bot.send_message(
        call.message.chat.id,
        "📅 Введите дату бронирования (ДД.ММ.ГГГГ):",
        reply_markup=types.ForceReply()
    )

# Общий обработчик для всех шагов бронирования
@bot.message_handler(func=lambda message: message.from_user.id in booking_sessions)
def handle_booking_steps(message):
    user_id = message.from_user.id
    session = booking_sessions[user_id]
    
    try:
        if session['step'] == 'date':
            process_booking_date(message, user_id)
        elif session['step'] == 'time':
            process_booking_time(message, user_id)
        elif session['step'] == 'persons':
            process_booking_persons(message, user_id)
        elif session['step'] == 'notes':
            process_booking_notes(message, user_id)
        elif session['step'] == 'tips':
            process_tips_amount(message, user_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")
        del booking_sessions[user_id]

def process_booking_date(message, user_id):
    date = message.text.strip()
    if not date or len(date) != 10 or date[2] != '.' or date[5] != '.':
        bot.send_message(message.chat.id, "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return
        
    booking_sessions[user_id]['date'] = date
    booking_sessions[user_id]['step'] = 'time'
    
    bot.send_message(
        message.chat.id,
        "⏰ Введите время бронирования (ЧЧ:ММ):",
        reply_markup=types.ForceReply()
    )

def process_booking_time(message, user_id):
    time = message.text.strip()
    if not time or len(time) != 5 or time[2] != ':':
        bot.send_message(message.chat.id, "❌ Неверный формат времени. Используйте ЧЧ:ММ")
        return
        
    booking_sessions[user_id]['time'] = time
    booking_sessions[user_id]['step'] = 'persons'
    
    bot.send_message(
        message.chat.id,
        "👥 Введите количество гостей:",
        reply_markup=types.ForceReply()
    )

def process_booking_persons(message, user_id):
    try:
        persons = int(message.text.strip())
        if persons < 1:
            raise ValueError
    except:
        bot.send_message(message.chat.id, "❌ Введите число больше 0")
        return
        
    booking_sessions[user_id]['persons'] = persons
    booking_sessions[user_id]['step'] = 'notes'
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Пропустить"))
    
    bot.send_message(
        message.chat.id,
        "💬 Введите особые пожелания (или нажмите 'Пропустить'):",
        reply_markup=markup
    )

def process_booking_notes(message, user_id):
    notes = message.text if message.text != "Пропустить" else ""
    booking_sessions[user_id]['notes'] = notes
    
    # Показываем кнопки подтверждения
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"),
        types.InlineKeyboardButton("💸 Добавить чаевые", callback_data="add_tips")
    )
    markup.row(types.InlineKeyboardButton("❌ Отменить", callback_data="cancel_booking"))
    
    session = booking_sessions[user_id]
    text = (
        "📝 Подтвердите бронирование:\n\n"
        f"Дата: {session['date']}\n"
        f"Время: {session['time']}\n"
        f"Гостей: {session['persons']}\n"
        f"Пожелания: {session.get('notes', 'нет')}"
    )
    
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )
    
    # Удаляем клавиатуру "Пропустить"
    bot.send_message(message.chat.id, "Подтвердите действие:", reply_markup=types.ReplyKeyboardRemove())


# =============================================
# Подтверждение бронирования
# =============================================


# ========== Подтверждение бронирования ==========
@bot.callback_query_handler(func=lambda call: call.data == 'confirm_booking')
def confirm_booking(call):
    user_id = call.from_user.id
    if user_id not in booking_sessions:
        bot.answer_callback_query(call.id, "❌ Сессия устарела, начните заново")
        return
        
    session = booking_sessions[user_id]
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO bookings (client_id, waiter_id, date, time, persons, notes) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, session['waiter_id'], session['date'], session['time'], session['persons'], session.get('notes', ''))
        )
        
        cursor.execute(
            "UPDATE clients SET bookings_count = bookings_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        
        conn.commit()
        
        bot.answer_callback_query(call.id, "✅ Бронирование подтверждено!")
        bot.send_message(call.message.chat.id, "🎉 Ваш столик забронирован!")
        
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Произошла ошибка при подтверждении бронирования.")
        print(f"Ошибка: {e}")
        
    finally:
        cursor.close()
        conn.close()

        # Удаляем сообщение с кнопками
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            
        except Exception as e:
            bot.answer_callback_query(call.id, "❌ Ошибка при бронировании")
            bot.send_message(call.message.chat.id, f"⚠️ Произошла ошибка: {str(e)}")
        
        finally:
            if user_id in booking_sessions:
                del booking_sessions[user_id]
            if conn:
                conn.close()

# ========== Добавление чаевых ==========

@bot.callback_query_handler(func=lambda call: call.data == 'add_tips')
def add_tips(call):
    user_id = call.from_user.id

    # Создаем сессию, если её нет
    if user_id not in booking_sessions:
        booking_sessions[user_id] = {'step': '', 'tips': 0}  # Инициализируем сессию

    booking_sessions[user_id]['step'] = 'tips'
    bot.answer_callback_query(call.id)

    bot.send_message(
        call.message.chat.id,
        "💸 Введите сумму чаевых (руб):",
        reply_markup=types.ForceReply()
    )

    # Регистрация следующего шага
    bot.register_next_step_handler(call.message, process_tips_amount, user_id)


def process_tips_amount(message, user_id):
    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите положительное число")
        return

    # Убедимся, что сессия существует
    if user_id not in booking_sessions:
        booking_sessions[user_id] = {'step': '', 'tips': 0}  # Инициализируем сессию, если она отсутствует

    booking_sessions[user_id]['tips'] = amount

    # Подтверждение с чаевыми
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить с чаевыми", callback_data="confirm_with_tips"))

    bot.send_message(
        message.chat.id,
        f"Вы добавили чаевые: {amount}₽\nПодтвердите бронирование:",
        reply_markup=markup
    )

def process_tips_amount(message, user_id):
    try:
        amount = int(message.text.strip())
        if amount < 1:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите положительное число")
        return

    # Проверка наличия сессии перед записью
    if user_id not in booking_sessions:
        bot.send_message(message.chat.id, "❌ Сессия устарела, начните заново")
        return

    booking_sessions[user_id]['tips'] = amount

    # Подтверждение с чаевыми
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Подтвердить с чаевыми", callback_data="confirm_with_tips"))

    bot.send_message(
        message.chat.id,
        f"Вы добавили чаевые: {amount}₽\nПодтвердите бронирование:",
        reply_markup=markup
    )
@bot.callback_query_handler(func=lambda call: call.data == 'confirm_with_tips')
def confirm_with_tips(call):
    user_id = call.from_user.id
    if user_id not in booking_sessions:
        bot.answer_callback_query(call.id, "❌ Сессия устарела, начните заново")
        return
        
    session = booking_sessions[user_id]
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO bookings (client_id, waiter_id, date, time, persons, notes, tips) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, session['waiter_id'], session['date'], session['time'], 
             session['persons'], session.get('notes', ''), session['tips']))
        
        cursor.execute(
            "UPDATE clients SET bookings_count = bookings_count + 1 WHERE user_id = ?",
            (user_id,)
        )
        conn.commit()
        
        bot.answer_callback_query(call.id, "✅ Бронирование с чаевыми подтверждено!")
        bot.send_message(
            call.message.chat.id,
            f"🎉 Ваш столик забронирован! Чаевые: {session['tips']}₽"
        )
# Удаляем сообщение с кнопками
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
            
    except Exception as e:
        bot.answer_callback_query(call.id, "❌ Ошибка при бронировании")
        bot.send_message(call.message.chat.id, f"⚠️ Произошла ошибка: {str(e)}")
        
    finally:
        if user_id in booking_sessions:
            del booking_sessions[user_id]
        if conn:
            conn.close()


# =============================================
# Отмена бронирования
# =============================================
@bot.callback_query_handler(func=lambda call: call.data == 'cancel_booking')
def cancel_booking(call):
    user_id = call.from_user.id
    if user_id in booking_sessions:
        del booking_sessions[user_id]
        
    bot.answer_callback_query(call.id, "❌ Бронирование отменено")
    bot.send_message(call.message.chat.id, "Бронирование отменено")
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass




# Запуск бота
if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()
