import os
import re
import sqlite3
import telebot
from telebot import types
from flask import Flask, request

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL topilmadi")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REFERAT_FOLDER = os.path.join(BASE_DIR, "referatlar")
DB_PATH = os.path.join(BASE_DIR, "users.db")


topic_names = {
    "1": "Ilk diniy tasavvurlar va ularning zamonaviy dinlarni rivojlantirishdagi ahamiyati",
    "2": "“Avesto” - zardushtiylikning mukaddas manbasi",
    "3": "Yahudiylik dinining xususiyatlari. Dinning ijtimoiy hayotdagi o‘rni",
    "4": "Hinduiylikdagi uchlik (trimurti) xudolari",
    "5": "Zardushtiylikning vujudga kelishi",
    "6": "Islomdagi mazhablar",
    "7": "Xristianlik manbalari",
    "8": "Milliy dinlar: yahudiylik",
    "9": "Kibermakonda din omilining ijtimoiy xavfi",
    "10": "Diniylik va dunyoviylik muammosi",
    "11": "Globallashuv va din",
    "12": "Missionerlik va prozelitizm: tarix va bugun, targ‘ibot usullari",
    "13": "Tasavvuf ta’limoti va tariqatlari",
    "14": "Islomning vujudga kelishi va tarqalishi",
    "15": "Milliy dinlar: daosizm va konfutsiylik",
    "16": "Xristianlikdagi oqimlar",
    "17": "Buddizmni jahon diniga aylanishi omillari",
    "18": "Yangi diniy harakatlar va sektalar",
    "19": "Milliy dinlar: sintoizm",
    "20": "Diniy ekstremizm va terrorizmga qarshi kurash: O‘zbekiston tajribasi",
    "21": "Qur’on Sharq xalqlarining diniy, ilmiy va ma’naviy merosi sifatida",
    "22": "Axborotlashgan jamiyatda ekstremistik targ‘ibotning ijtimoiy xavfining ortib borishi",
    "23": "Hadislarda milliy va diniy qadriyatlarning aks etishi",
    "24": "O‘zbekistonda vijdon erkinligi",
    "25": "Qadimgi Yunon va Misr xudolari",
    "26": "Xristianlik jahon dini"
}


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            phone TEXT,
            full_name TEXT,
            registered INTEGER DEFAULT 0,
            step TEXT DEFAULT 'phone'
        )
    """)
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
    user = cur.fetchone()
    conn.close()
    return user


def create_or_reset_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (user_id, registered, step)
        VALUES (?, 0, 'phone')
        ON CONFLICT(user_id) DO UPDATE SET
            registered = 0,
            step = 'phone'
    """, (str(user_id),))
    conn.commit()
    conn.close()


def create_user_if_not_exists(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR IGNORE INTO users (user_id, registered, step)
        VALUES (?, 0, 'phone')
    """, (str(user_id),))
    conn.commit()
    conn.close()


def update_user_phone(user_id, phone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET phone = ?, step = 'fullname'
        WHERE user_id = ?
    """, (phone, str(user_id)))
    conn.commit()
    conn.close()


def complete_registration(user_id, full_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET full_name = ?, registered = 1, step = 'done'
        WHERE user_id = ?
    """, (full_name, str(user_id)))
    conn.commit()
    conn.close()


def is_valid_uzbek_phone(phone):
    pattern = r"^\+998\d{9}$"
    return re.match(pattern, phone) is not None


def is_registered(user_id):
    user = get_user(user_id)
    return user is not None and user["registered"] == 1


def make_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Dinshunoslik")
    btn2 = types.KeyboardButton("Jismoniy tarbiya")
    btn3 = types.KeyboardButton("Boshqalar")
    markup.add(btn1, btn2)
    markup.add(btn3)
    return markup


def make_phone_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    contact_btn = types.KeyboardButton("📱 Telefon raqam yuborish", request_contact=True)
    markup.add(contact_btn)
    return markup


def make_dinshunoslik_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    buttons = [types.KeyboardButton(str(i)) for i in range(1, 27)]
    markup.add(*buttons)
    markup.add(types.KeyboardButton("⬅️ Orqaga"))
    return markup


def read_topic_file(topic_number):
    file_path = os.path.join(REFERAT_FOLDER, f"{topic_number}.txt")

    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()

    if not content:
        return None

    return content


def split_text(text, chunk_size=3500):
    parts = []
    while len(text) > chunk_size:
        cut = text.rfind("\n", 0, chunk_size)
        if cut == -1:
            cut = chunk_size
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts


@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)

    if user and user["registered"] == 1:
        bot.send_message(
            message.chat.id,
            f"Xush kelibsiz, {user['full_name']}!\nKerakli bo‘limni tanlang:",
            reply_markup=make_main_menu()
        )
    else:
        create_or_reset_user(user_id)
        bot.send_message(
            message.chat.id,
            "🎓 Assalomu alaykum!\n\n"
            "Ushbu bot orqali siz:\n\n"
            "⚡ Qisqa vaqt ichida kerakli natijaga erishasiz\n"
            "📚 Jurnaldagi raqamingiz asosida maxsus tayyorlangan referatni olasiz\n\n"
            "Botdan foydalanish uchun avval telefon raqamingizni yuboring.\n\n"
            "Format: +998XXXXXXXXX\n"
            "yoki pastdagi tugma orqali yuboring.",
            reply_markup=make_phone_button()
        )


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    user_id = str(message.from_user.id)
    create_user_if_not_exists(user_id)

    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    if is_valid_uzbek_phone(phone):
        update_user_phone(user_id, phone)
        bot.send_message(
            message.chat.id,
            "Telefon raqamingiz qabul qilindi ✅\n\n"
            "Endi Familiya Ismingizni kiriting.\n"
            "Masalan: Karimov Ozodbek"
        )
    else:
        bot.send_message(
            message.chat.id,
            "Telefon raqam noto‘g‘ri.\nTo‘g‘ri format: +998901234567",
            reply_markup=make_phone_button()
        )


@bot.message_handler(commands=['users'])
def show_users(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "⛔ Siz admin emassiz!")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, full_name, phone
        FROM users
        WHERE registered = 1
        ORDER BY rowid DESC
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "📭 Hali hech kim ro‘yxatdan o‘tmagan.")
        return

    text = "📋 RO‘YXATDAN O‘TGAN FOYDALANUVCHILAR:\n\n"
    count = 0

    for row in rows:
        count += 1
        full_name = row["full_name"] if row["full_name"] else "Noma'lum"
        phone = row["phone"] if row["phone"] else "Telefon yo‘q"

        text += f"{count}) 👤 {full_name}\n"
        text += f"📱 {phone}\n"
        text += f"🆔 {row['user_id']}\n\n"

    text += f"📊 Jami foydalanuvchilar: {count} ta"

    for i in range(0, len(text), 3500):
        bot.send_message(message.chat.id, text[i:i + 3500])


@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()

    user = get_user(user_id)

    if not user:
        create_user_if_not_exists(user_id)
        bot.send_message(message.chat.id, "Avval /start bosing.")
        return

    if user["step"] == "phone":
        if is_valid_uzbek_phone(text):
            update_user_phone(user_id, text)
            bot.send_message(
                message.chat.id,
                "Telefon raqamingiz qabul qilindi ✅\n\n"
                "Endi Familiya Ismingizni kiriting.\n"
                "Masalan: Karimov Ozodbek"
            )
        else:
            bot.send_message(
                message.chat.id,
                "Telefon raqam noto‘g‘ri.\nTo‘g‘ri format: +998901234567",
                reply_markup=make_phone_button()
            )
        return

    if user["step"] == "fullname":
        if len(text.split()) >= 2:
            complete_registration(user_id, text)
            user = get_user(user_id)

            bot.send_message(
                message.chat.id,
                f"Ro‘yxatdan o‘tdingiz ✅\n\n"
                f"Familiya Ism: {text}\n"
                f"Telefon: {user['phone']}\n\n"
                f"Endi kerakli bo‘limni tanlang:",
                reply_markup=make_main_menu()
            )
        else:
            bot.send_message(
                message.chat.id,
                "Iltimos, Familiya va Ismni to‘liq kiriting.\n"
                "Masalan: Karimov Ozodbek"
            )
        return

    if not is_registered(user_id):
        bot.send_message(message.chat.id, "Avval ro‘yxatdan o‘ting. /start bosing.")
        return

    if text == "Dinshunoslik":
        bot.send_message(
            message.chat.id,
            "Dinshunoslik bo‘limi.\nKerakli mavzu raqamini tanlang:",
            reply_markup=make_dinshunoslik_menu()
        )
        return

    if text == "Jismoniy tarbiya":
        bot.send_message(
            message.chat.id,
            "Jismoniy tarbiya bo‘limi hozircha tayyorlanmoqda.",
            reply_markup=make_main_menu()
        )
        return

    if text == "Boshqalar":
        bot.send_message(
            message.chat.id,
            "Boshqa fanlar bo‘limi hozircha tayyorlanmoqda.",
            reply_markup=make_main_menu()
        )
        return

    if text == "⬅️ Orqaga":
        bot.send_message(
            message.chat.id,
            "Asosiy menyuga qaytdingiz.",
            reply_markup=make_main_menu()
        )
        return

    if text in topic_names:
        topic_title = topic_names[text]
        topic_text = read_topic_file(text)

        if topic_text is None:
            bot.send_message(
                message.chat.id,
                f"{text}-mavzu: {topic_title}\n\nBu mavzu uchun referat hali joylanmagan.",
                reply_markup=make_dinshunoslik_menu()
            )
            return

        bot.send_message(
            message.chat.id,
            f"{text}-mavzu: {topic_title}\n\nReferat yuborilmoqda...",
            reply_markup=make_dinshunoslik_menu()
        )

        parts = split_text(topic_text, chunk_size=3500)
        for i, part in enumerate(parts, start=1):
            bot.send_message(
                message.chat.id,
                f"{text}-mavzu | {i}-qism\n\n{part}"
            )
        return

    bot.send_message(
        message.chat.id,
        "Iltimos, menyudagi tugmalardan foydalaning.",
        reply_markup=make_main_menu()
    )


@app.route("/", methods=["GET"])
def home():
    return "Bot ishlayapti!", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_str = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return "OK", 200
    return "Invalid request", 403


if __name__ == "__main__":
    init_db()
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook o‘rnatildi")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
