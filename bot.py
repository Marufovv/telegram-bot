import os
import json
import re
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
USERS_FILE = os.path.join(BASE_DIR, "users.json")
REFERAT_FOLDER = os.path.join(BASE_DIR, "referatlar")

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


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_users(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


users = load_users()


def is_valid_uzbek_phone(phone):
    pattern = r"^\+998\d{9}$"
    return re.match(pattern, phone) is not None


def is_registered(user_id):
    return str(user_id) in users and users[str(user_id)].get("registered") is True


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
    buttons = []
    for i in range(1, 27):
        buttons.append(types.KeyboardButton(str(i)))
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

    if is_registered(user_id):
        bot.send_message(
            message.chat.id,
            f"Xush kelibsiz, {users[user_id]['full_name']}!\nKerakli bo‘limni tanlang:",
            reply_markup=make_main_menu()
        )
    else:
        users[user_id] = {
            "registered": False,
            "step": "phone"
        }
        save_users(users)

        bot.send_message(
            message.chat.id,
            "🎓 Assalomu alaykum!\n\n"
            "Ushbu bot orqali dinshunoslik fanidan mavzular va referatlarni olishingiz mumkin.\n\n"
            "Botdan foydalanish uchun avval telefon raqamingizni yuboring.\n\n"
            "Format: +998XXXXXXXXX\n"
            "yoki pastdagi tugma orqali yuboring.",
            reply_markup=make_phone_button()
        )


@bot.message_handler(content_types=['contact'])
def contact_handler(message):
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {}

    phone = message.contact.phone_number

    if not phone.startswith("+"):
        phone = "+" + phone

    if is_valid_uzbek_phone(phone):
        users[user_id]["phone"] = phone
        users[user_id]["step"] = "fullname"
        save_users(users)

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

    if not users:
        bot.send_message(message.chat.id, "📭 Hali hech kim ro‘yxatdan o‘tmagan.")
        return

    text = "📋 RO‘YXATDAN O‘TGAN FOYDALANUVCHILAR:\n\n"
    count = 0

    for user_id, data in users.items():
        full_name = data.get("full_name", "Noma'lum")
        phone = data.get("phone", "Telefon yo‘q")

        count += 1
        text += f"{count}) 👤 {full_name}\n"
        text += f"📱 {phone}\n"
        text += f"🆔 {user_id}\n\n"

    text += f"📊 Jami foydalanuvchilar: {count} ta"

    for i in range(0, len(text), 3500):
        bot.send_message(message.chat.id, text[i:i + 3500])


@bot.message_handler(func=lambda message: True, content_types=['text'])
def text_handler(message):
    user_id = str(message.from_user.id)
    text = message.text.strip()

    if user_id not in users:
        users[user_id] = {"registered": False, "step": "phone"}
        save_users(users)
        bot.send_message(message.chat.id, "Avval /start bosing.")
        return

    if users[user_id].get("step") == "phone":
        if is_valid_uzbek_phone(text):
            users[user_id]["phone"] = text
            users[user_id]["step"] = "fullname"
            save_users(users)

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

    if users[user_id].get("step") == "fullname":
        if len(text.split()) >= 2:
            users[user_id]["full_name"] = text
            users[user_id]["registered"] = True
            users[user_id]["step"] = "done"
            save_users(users)

            bot.send_message(
                message.chat.id,
                f"Ro‘yxatdan o‘tdingiz ✅\n\n"
                f"Familiya Ism: {text}\n"
                f"Telefon: {users[user_id]['phone']}\n\n"
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

    elif text == "Jismoniy tarbiya":
        bot.send_message(
            message.chat.id,
            "Jismoniy tarbiya bo‘limi hozircha tayyorlanmoqda.",
            reply_markup=make_main_menu()
        )
        return

    elif text == "Boshqalar":
        bot.send_message(
            message.chat.id,
            "Boshqa fanlar bo‘limi hozircha tayyorlanmoqda.",
            reply_markup=make_main_menu()
        )
        return

    elif text == "⬅️ Orqaga":
        bot.send_message(
            message.chat.id,
            "Asosiy menyuga qaytdingiz.",
            reply_markup=make_main_menu()
        )
        return

    elif text in topic_names:
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

    else:
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
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook o‘rnatildi")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
