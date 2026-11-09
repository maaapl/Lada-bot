# -*- coding: utf-8 -*-
"""
LADA Smart Assistant Belarus - Официальный цифровой консультант LADA в Беларуси
Разработано для Telegram
"""

import os
import sys
import json
import html
import logging
import datetime
import time
import threading
import telebot
from telebot import types

# Увеличенные таймауты для стабильного соединения без сбросов
telebot.apihelper.CONNECT_TIMEOUT = 30
telebot.apihelper.READ_TIMEOUT = 60

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

BOT_TOKEN = "9150739815:AAFykzJ3YgPcru-XkIzsNBLqLSxThRojeOk"
ADMIN_ID = 1559092711

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# База данных лидов в JSON
LEADS_FILE = "leads.json"
leads_lock = threading.Lock()

def deliver_unsent_leads():
    """Гарантированная доставка всех неотправленных лидов админу с повторами"""
    if not os.path.exists(LEADS_FILE):
        return
    with leads_lock:
        try:
            with open(LEADS_FILE, "r", encoding="utf-8") as f:
                leads = json.load(f)
        except Exception:
            return

        updated = False
        for lead in leads:
            if not lead.get("sent_to_admin", False):
                client_name = html.escape(str(lead.get('name', 'Не указано')))
                client_user = html.escape(str(lead.get('username', 'нет')))
                client_phone = html.escape(str(lead.get('phone', 'Не указан')))
                lead_type = html.escape(str(lead.get('type', 'Заявка')))

                html_text = (
                    f"🔥 <b>НОВАЯ ЗАЯВКА ИЗ БОТА LADA БЕЛАРУСЬ!</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🎯 <b>Тип:</b> {lead_type}\n"
                    f"👤 <b>Клиент:</b> {client_name} (<code>@{client_user}</code>)\n"
                    f"📱 <b>Телефон/Контакт:</b> <code>{client_phone}</code>\n"
                )
                if "details" in lead:
                    html_text += f"📝 <b>Детали:</b>\n{html.escape(str(lead['details']))}\n"
                if "gift" in lead:
                    html_text += f"🎁 <b>Выбранный бонус:</b> {html.escape(str(lead['gift']))}\n"
                html_text += f"⏱ <b>Время:</b> {lead['created_at']}\n━━━━━━━━━━━━━━━━━━"

                delivered = False
                for attempt in range(3):
                    try:
                        bot.send_message(ADMIN_ID, html_text, parse_mode="HTML")
                        delivered = True
                        print(f"[{datetime.datetime.now()}] Лид успешно доставлен админу {ADMIN_ID}!", flush=True)
                        break
                    except Exception as e:
                        try:
                            plain_text = (
                                f"🔥 НОВАЯ ЗАЯВКА ИЗ БОТА LADA БЕЛАРУСЬ!\n\n"
                                f"Тип: {lead.get('type')}\n"
                                f"Клиент: {lead.get('name')} (@{lead.get('username')})\n"
                                f"Телефон: {lead.get('phone')}\n"
                                f"Детали: {lead.get('details')}\n"
                                f"Бонус: {lead.get('gift')}\n"
                                f"Время: {lead['created_at']}"
                            )
                            bot.send_message(ADMIN_ID, plain_text, parse_mode=None)
                            delivered = True
                            print(f"[{datetime.datetime.now()}] Лид (plain text) доставлен админу {ADMIN_ID}!", flush=True)
                            break
                        except Exception:
                            time.sleep(1)

                if delivered:
                    lead["sent_to_admin"] = True
                    updated = True

        if updated:
            try:
                with open(LEADS_FILE, "w", encoding="utf-8") as f:
                    json.dump(leads, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


def save_lead(lead_data):
    """Сохранение нового лида и немедленный запуск отправки"""
    lead_data["created_at"] = datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    lead_data["sent_to_admin"] = False
    with leads_lock:
        leads = []
        if os.path.exists(LEADS_FILE):
            try:
                with open(LEADS_FILE, "r", encoding="utf-8") as f:
                    leads = json.load(f)
            except Exception:
                leads = []
        leads.append(lead_data)
        with open(LEADS_FILE, "w", encoding="utf-8") as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)

    # Немедленная попытка доставить
    deliver_unsent_leads()


def background_sync_worker():
    """Фоновый поток для проверки и повторной отправки лидов каждые 5 сек"""
    while True:
        try:
            deliver_unsent_leads()
        except Exception:
            pass
        time.sleep(5)


# Сессионное хранилище состояний пользователей
user_data = {}

def get_user_session(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "state": None,
            "tradein": {},
            "credit": {},
            "testdrive": {},
            "name": "",
            "phone": ""
        }
    return user_data[user_id]


# --- КЛАВИАТУРЫ ---

def main_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b1 = types.InlineKeyboardButton("🚗 Модельный ряд LADA", callback_data="menu_models")
    b2 = types.InlineKeyboardButton("🔄 Оценка Trade-In за 1 мин", callback_data="menu_tradein")
    b3 = types.InlineKeyboardButton("💰 Льготный кредит и Лизинг", callback_data="menu_credit")
    b4 = types.InlineKeyboardButton("🥊 LADA vs Иномарки (Мифы)", callback_data="menu_myths")
    b5 = types.InlineKeyboardButton("🏁 Запись на тест-драйв + Подарок 🎁", callback_data="menu_testdrive")
    b6 = types.InlineKeyboardButton("📍 Автоцентры в Минске и Эксперт", callback_data="menu_contacts")
    markup.add(b1)
    markup.add(b2, b3)
    markup.add(b4)
    markup.add(b5)
    markup.add(b6)
    return markup

def back_to_main_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main"))
    return markup


# --- КОМАНДА /START ---

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    session = get_user_session(message.chat.id)
    session["state"] = None
    
    user_name = message.from_user.first_name or "Уважаемый клиент"
    text = (
        f"👋 <b>Здравствуйте, {user_name}!</b>\n\n"
        f"Добро пожаловать в <b>LADA Smart Assistant Беларусь</b> — официальный цифровой консультант дилерской сети LADA.\n\n"
        f"Я помогу вам быстро и с максимальной выгодой выбрать новый автомобиль:\n"
        f"• 🚗 <b>Модельный ряд 2026:</b> комплектации, характеристики и цены в BYN\n"
        f"• 🔄 <b>Онлайн Trade-In:</b> экспресс-оценка вашего авто + выгода до 3 500 BYN\n"
        f"• 💰 <b>Автокредит и лизинг:</b> программы Беларусбанка от 5.5% годовых и расчет платежа\n"
        f"• 🥊 <b>Разрушитель мифов:</b> честный анализ оцинковки, вариатора и сравнение с «китайцами»\n"
        f"• 🏁 <b>Тест-драйв с подарком:</b> закрепите за собой комплект шин или топливную карту!\n\n"
        f"<i>Выберите интересующий раздел в меню ниже:</i> 👇"
    )
    
    hero_photo = "assets/showroom.jpg"
    if os.path.exists(hero_photo):
        try:
            with open(hero_photo, "rb") as photo:
                bot.send_photo(message.chat.id, photo, caption=text, reply_markup=main_menu_keyboard())
                return
        except Exception as e:
            logging.error(f"Error sending hero photo: {e}")
            
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())


# --- РАЗДЕЛ 1: МОДЕЛЬНЫЙ РЯД (ЦЕНЫ В BYN) ---

@bot.callback_query_handler(func=lambda call: call.data == "menu_models")
def cb_models_catalog(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🌟 LADA Vesta (Седан & SW Cross)", callback_data="car_vesta"),
        types.InlineKeyboardButton("🚙 LADA Granta (Народный выбор)", callback_data="car_granta"),
        types.InlineKeyboardButton("🌲 LADA Niva Travel (Комфортный 4х4)", callback_data="car_niva_travel"),
        types.InlineKeyboardButton("⛰️ LADA Niva Legend (Настоящий оффроуд)", callback_data="car_niva_legend"),
        types.InlineKeyboardButton("🚐 LADA Largus Cross (7 мест)", callback_data="car_largus"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "🚗 <b>Модельный ряд LADA 2026 года в Беларуси</b>\n\n"
        "Выберите модель, чтобы посмотреть фото, оснащение и официальные цены в белорусских рублях (BYN):"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("car_"))
def cb_car_detail(call):
    car_key = call.data.replace("car_", "")
    
    car_info = {
        "vesta": {
            "title": "🌟 LADA Vesta & Vesta SW Cross",
            "img": "assets/vesta.jpg",
            "desc": (
                "<b>Флагман линейки LADA:</b> просторный салон, светодиодная оптика LED и европейский уровень безопасности.\n\n"
                "⚙️ <b>Двигатели:</b> 1.6 л (106 л.с.) и тяговитый 1.8 Evo (122 л.с.)\n"
                "🕹️ <b>Трансмиссия:</b> 6-МКПП или надежный вариатор CVT (WLY)\n"
                "📱 <b>Оснащение:</b> цифровая приборная панель 10.25\", мультимедиа EnjoY Vision Pro с сервисами Яндекс, полный зимний пакет (обогрев сидений, руля и лобового стекла)\n"
                "🛡️ <b>Клиренс Cross:</b> 203 мм (уверенность на любых бордюрах и снежной колее)\n\n"
                "💳 <b>Цена:</b> от 44 900 BYN\n"
                "🎁 <b>По программе Trade-In:</b> выгода до 3 500 BYN\n"
                "📅 <b>Кредит / Лизинг:</b> от 390 BYN/мес"
            )
        },
        "granta": {
            "title": "🚙 LADA Granta (Седан / Лифтбек / Cross)",
            "img": "assets/granta.jpg",
            "desc": (
                "<b>Самый доступный и практичный новый автомобиль в Беларуси:</b> надежный помощник на каждый день с минимальной стоимостью владения.\n\n"
                "⚙️ <b>Двигатели:</b> 1.6 л (90 л.с. — отличная тяга на низких оборотах) или 16-кл. (106 л.с.)\n"
                "🕹️ <b>Трансмиссия:</b> надежная механическая 5-МКПП\n"
                "📦 <b>Багажник:</b> до 520 литров (удобно загружать детскую коляску, стройматериалы или урожай)\n"
                "⛽ <b>Расход:</b> от 6.5 л на 100 км АИ-92/95\n\n"
                "💳 <b>Цена:</b> от 31 500 BYN\n"
                "🎁 <b>По программе Trade-In:</b> выгода до 2 000 BYN\n"
                "📅 <b>Кредит / Лизинг:</b> от 270 BYN/мес"
            )
        },
        "niva_travel": {
            "title": "🌲 LADA Niva Travel",
            "img": "assets/niva_travel.jpg",
            "desc": (
                "<b>Комфортный внедорожник для белорусских дорог, лесов и рыбалки:</b> выразительный дизайн, энергоемкая подвеска и честный полный привод.\n\n"
                "⚙️ <b>Привод:</b> Постоянный полный 4х4 с блокировкой межосевого дифференциала и понижающей передачей\n"
                "🛡️ <b>Клиренс:</b> 220 мм — не боится ни глубоких бродов, ни весенней распутицы\n"
                "❄️ <b>Комфорт:</b> Кондиционер, камера заднего вида с омывателем, обогрев лобового стекла, мультимедиа\n\n"
                "💳 <b>Цена:</b> от 42 300 BYN\n"
                "🎁 <b>По программе Trade-In:</b> выгода до 2 500 BYN\n"
                "📅 <b>Кредит / Лизинг:</b> от 370 BYN/мес"
            )
        },
        "niva_legend": {
            "title": "⛰️ LADA Niva Legend (3-дв / 5-дв)",
            "img": "assets/niva_legend.jpg",
            "desc": (
                "<b>Легендарная классика без компромиссов:</b> эталонная геометрическая проходимость и максимальная ремонтопригодность.\n\n"
                "⚙️ <b>Привод:</b> Настоящий постоянный 4х4, неразрезной задний мост\n"
                "💪 <b>Проходимость:</b> Короткая база, большие ходы подвески\n"
                "🛡️ <b>Оснащение:</b> ГУР, ABS, улучшенная виброизоляция, электростеклоподъемники, обогрев сидений\n\n"
                "💳 <b>Цена:</b> от 32 900 BYN\n"
                "🎁 <b>По программе Trade-In:</b> выгода до 2 000 BYN\n"
                "📅 <b>Кредит / Лизинг:</b> от 280 BYN/мес"
            )
        },
        "largus": {
            "title": "🚐 LADA Largus Cross (5 или 7 мест)",
            "img": "assets/largus.jpg",
            "desc": (
                "<b>Идеальный автомобиль для большой семьи и бизнеса:</b> максимальная вместительность в классе и выносливая подвеска.\n\n"
                "👥 <b>Вместимость:</b> 5 или 7 полноценных пассажирских мест\n"
                "📦 <b>Багажник:</b> до рекордных 2350 литров при сложенных сиденьях!\n"
                "⚙️ <b>Двигатели:</b> надежные 1.6 л с усиленными компонентами\n"
                "🛡️ <b>Версия Cross:</b> увеличенный клиренс 200 мм и защитный пластиковый обвес кузова\n\n"
                "💳 <b>Цена:</b> от 53 800 BYN\n"
                "🎁 <b>По программе Trade-In:</b> выгода до 3 000 BYN\n"
                "📅 <b>Кредит / Лизинг:</b> от 460 BYN/мес"
            )
        }
    }
    
    info = car_info.get(car_key, car_info["vesta"])
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(f"🏁 Записаться на тест-драйв {car_key.upper()}", callback_data=f"td_car_{car_key}"),
        types.InlineKeyboardButton("💰 Рассчитать кредит/лизинг в BYN", callback_data=f"credit_car_{car_key}"),
        types.InlineKeyboardButton("🔙 Назад к списку моделей", callback_data="menu_models"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    
    caption = f"<b>{info['title']}</b>\n\n{info['desc']}"
    
    if os.path.exists(info["img"]):
        try:
            with open(info["img"], "rb") as photo:
                bot.send_photo(call.message.chat.id, photo, caption=caption, reply_markup=markup)
                return
        except Exception as e:
            logging.error(f"Error sending car photo: {e}")
            
    bot.send_message(call.message.chat.id, caption, reply_markup=markup)


# --- РАЗДЕЛ 2: TRADE-IN КАЛЬКУЛЯТОР ---

@bot.callback_query_handler(func=lambda call: call.data == "menu_tradein")
def cb_tradein_start(call):
    session = get_user_session(call.message.chat.id)
    session["state"] = "TRADEIN_CAR_NAME"
    session["tradein"] = {}
    
    text = (
        "🔄 <b>Экспресс-оценка авто в Trade-In за 1 минуту</b>\n\n"
        "Сдайте ваш подержанный автомобиль любой марки в зачет новой LADA и получите:\n"
        "• Честную рыночную оценку экспертами дилерского центра в Минске\n"
        "• <b>Дополнительную выгоду до 3 500 BYN</b> на покупку нового авто!\n\n"
        "Шаг 1 из 3: <b>Напишите марку и модель вашего текущего авто</b>\n"
        "<i>(Например: Volkswagen Polo, Renault Sandero, Skoda Fabia, Opel Astra, Geely Coolray):</i>"
    )
    msg = bot.send_message(call.message.chat.id, text, reply_markup=back_to_main_keyboard())
    bot.register_next_step_handler(msg, step_tradein_model)


def step_tradein_model(message):
    if message.text and message.text.startswith("/"):
        return
    session = get_user_session(message.chat.id)
    session["tradein"]["car_name"] = message.text
    session["state"] = "TRADEIN_YEAR"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("До 2012 года", callback_data="ti_year_old"),
        types.InlineKeyboardButton("2013 — 2017 гг.", callback_data="ti_year_mid"),
        types.InlineKeyboardButton("2018 — 2021 гг.", callback_data="ti_year_fresh"),
        types.InlineKeyboardButton("2022 — 2025 гг.", callback_data="ti_year_new"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    
    bot.send_message(
        message.chat.id,
        f"Отлично! Ваш авто: <b>{message.text}</b>.\n\n"
        f"Шаг 2 из 3: <b>Укажите примерный год выпуска автомобиля:</b>",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("ti_year_"))
def cb_tradein_year(call):
    year_map = {
        "ti_year_old": "До 2012 г.",
        "ti_year_mid": "2013-2017 гг.",
        "ti_year_fresh": "2018-2021 гг.",
        "ti_year_new": "2022-2025 гг."
    }
    session = get_user_session(call.message.chat.id)
    session["tradein"]["year"] = year_map.get(call.data, "2016 г.")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("До 60 000 км", callback_data="ti_mil_low"),
        types.InlineKeyboardButton("60 000 — 120 000 км", callback_data="ti_mil_mid"),
        types.InlineKeyboardButton("Более 120 000 км", callback_data="ti_mil_high"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    
    bot.send_message(
        call.message.chat.id,
        f"Шаг 3 из 3: <b>Укажите ориентировочный пробег автомобиля:</b>",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("ti_mil_"))
def cb_tradein_mileage(call):
    mil_map = {
        "ti_mil_low": "до 60 000 км",
        "ti_mil_mid": "60 000 - 120 000 км",
        "ti_mil_high": "свыше 120 000 км"
    }
    session = get_user_session(call.message.chat.id)
    session["tradein"]["mileage"] = mil_map.get(call.data, "средний")
    session["state"] = "TRADEIN_PHONE"
    
    car = session["tradein"].get("car_name", "Автомобиль")
    year = session["tradein"].get("year", "2016")
    mil = session["tradein"].get("mileage", "80 000 км")
    
    text = (
        f"✅ <b>Предварительный расчет Trade-In готов!</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🚘 <b>Ваш автомобиль:</b> {car} ({year}, {mil})\n"
        f"💰 <b>Оценочный диапазон выкупа:</b> по верхней границе рынка Беларуси\n"
        f"🎁 <b>Персональная субсидия на новую LADA:</b> <b>до 3 500 BYN</b> дополнительно к цене выкупа!\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Чтобы зафиксировать за собой бонус <b>3 500 BYN</b> и получить точный расчет от оценщика в Минске, "
        f"<b>напишите ваш номер телефона</b> (например: <code>+375 29 123-45-67</code>):"
    )
    
    msg = bot.send_message(call.message.chat.id, text, reply_markup=back_to_main_keyboard())
    bot.register_next_step_handler(msg, step_save_tradein_phone)


def step_save_tradein_phone(message):
    if message.text and message.text.startswith("/"):
        return
    phone = message.text.strip()
    session = get_user_session(message.chat.id)
    session["phone"] = phone
    
    lead = {
        "type": "🔄 Онлайн-оценка Trade-In (Беларусь)",
        "name": message.from_user.first_name or "Клиент",
        "username": message.from_user.username or "нет",
        "phone": phone,
        "details": f"Авто: {session['tradein'].get('car_name')}, Год: {session['tradein'].get('year')}, Пробег: {session['tradein'].get('mileage')}",
        "gift": "Сертификат на скидку до 3 500 BYN по Trade-In"
    }
    save_lead(lead)
    
    success_text = (
        f"🎉 <b>Спасибо, {message.from_user.first_name}! Заявка принята!</b>\n\n"
        f"Бонус <b>до 3 500 BYN</b> закреплен за вашим номером: <code>{phone}</code>.\n"
        f"Специалист отдела Trade-In автоцентра LADA в Минске свяжется с вами в течение 10–15 минут для согласования точной суммы выкупа."
    )
    bot.send_message(message.chat.id, success_text, reply_markup=main_menu_keyboard())


# --- РАЗДЕЛ 3: ФИНАНСОВЫЕ ПРОГРАММЫ В БЕЛАРУСИ ---

@bot.callback_query_handler(func=lambda call: call.data == "menu_credit")
def cb_credit_start(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏛️ Льготный кредит Беларусбанка (от 5.5% в BYN)", callback_data="prog_belarusbank"),
        types.InlineKeyboardButton("🤝 Партнерский автокредит без аванса (0% первый взнос)", callback_data="prog_no_deposit"),
        types.InlineKeyboardButton("💼 Выгодный лизинг для физлиц (минимальный платеж)", callback_data="prog_leasing"),
        types.InlineKeyboardButton("👨‍👩‍👧‍👦 Программа поддержки многодетных семей", callback_data="prog_family_by"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    
    text = (
        "💰 <b>Финансовые программы и льготное кредитование в Беларуси</b>\n\n"
        "Специальные условия от ведущих банков-партнеров (Беларусбанк, Сбер Банк, БТА Банк):\n"
        "• Ставки в белорусских рублях от <b>5.5% годовых</b>\n"
        "• Срок финансирования до 10 лет с возможностью досрочного погашения без штрафов\n"
        "• Оформление прямо в автоцентре без справок о доходах при авансе от 20%\n\n"
        "<b>Выберите подходящую программу:</b>"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("prog_"))
def cb_credit_calc(call):
    prog_names = {
        "prog_belarusbank": "Льготный кредит Беларусбанк (от 5.5% в BYN)",
        "prog_no_deposit": "Автокредит без первого взноса (0% аванс)",
        "prog_leasing": "Лизинг в белорусских рублях",
        "prog_family_by": "Специальная программа для многодетных семей"
    }
    prog = prog_names.get(call.data, "Автокредит LADA Finance Беларусь")
    session = get_user_session(call.message.chat.id)
    session["credit"]["program"] = prog
    
    text = (
        f"🎯 <b>Отличный выбор! Вы выбрали:</b>\n"
        f"<i>{prog}</i>\n\n"
        f"📊 <b>Пример расчета на новую LADA Vesta (Седан):</b>\n"
        f"• Стоимость авто: 44 900 BYN\n"
        f"• Первый взнос (20%): 8 980 BYN\n"
        f"• Ежемесячный платеж: всего <b>от 390 BYN/мес</b>\n"
        f"• Фиксация платежей в белорусских рублях (без привязки к курсам валют)!\n\n"
        f"Хотите получить предварительное одобрение банков за 15 минут без посещения отделения?\n\n"
        f"<b>Отправьте ваш номер телефона</b> (например: <code>+375 29 123-45-67</code>):"
    )
    session["state"] = "CREDIT_PHONE"
    msg = bot.send_message(call.message.chat.id, text, reply_markup=back_to_main_keyboard())
    bot.register_next_step_handler(msg, step_save_credit_phone)


def step_save_credit_phone(message):
    if message.text and message.text.startswith("/"):
        return
    phone = message.text.strip()
    session = get_user_session(message.chat.id)
    
    lead = {
        "type": "💰 Заявка на Кредит/Лизинг (Беларусь)",
        "name": message.from_user.first_name or "Клиент",
        "username": message.from_user.username or "нет",
        "phone": phone,
        "details": f"Программа: {session['credit'].get('program', 'Кредит Беларусбанк')}",
        "gift": "Фиксация льготной процентной ставки в BYN"
    }
    save_lead(lead)
    
    text = (
        f"✅ <b>Заявка на расчет кредита принята!</b>\n\n"
        f"Финансовый специалист автоцентра LADA в Минске подготовит персональный график платежей "
        f"и свяжется с вами по номеру <code>{phone}</code>."
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_keyboard())


# --- РАЗДЕЛ 4: РАЗРУШИТЕЛЬ МИФОВ (БЕЛОРУССКИЙ КОНТЕКСТ) ---

@bot.callback_query_handler(func=lambda call: call.data == "menu_myths")
def cb_myths_menu(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🛡️ Миф: «Кузов сгниет от белорусской соли»", callback_data="myth_rust"),
        types.InlineKeyboardButton("⚙️ Миф: «Вариатор на Весте ненадежен»", callback_data="myth_cvt"),
        types.InlineKeyboardButton("🇨🇳 LADA против «Китайцев» в Беларуси", callback_data="myth_chinese"),
        types.InlineKeyboardButton("💸 Реальная стоимость ТО и запчастей в BYN", callback_data="myth_parts"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "🥊 <b>Разрушитель мифов: Честные факты о современных LADA для Беларуси</b>\n\n"
        "Открыто отвечаем на самые частые сомнения покупателей с учетом нашего климата и дорог:\n\n"
        "<i>Нажмите на интересующую тему:</i> 👇"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("myth_"))
def cb_myth_answer(call):
    myths = {
        "myth_rust": (
            "🛡️ <b>Миф: «Кузов быстро сгниет от песчано-соляной смеси зимой»</b>\n\n"
            "❌ <b>Стереотип:</b> Машина покроется ржавчиной после двух минских зим.\n\n"
            "✅ <b>Реальность 2026 года:</b>\n"
            "• На автомобилях Vesta и Granta используется <b>двусторонняя горячая оцинковка</b> кузовных панелей.\n"
            "• Все скрытые полости обрабатываются методом полного погружения в катафорезную ванну.\n"
            "• Заводская гарантия от сквозной коррозии — <b>6 лет</b> без ограничения пробега.\n"
            "• Днище и колесные арки с завода покрыты прочным антигравийным мастичным слоем толщиной 1 мм."
        ),
        "myth_cvt": (
            "⚙️ <b>Миф: «Вариатор на LADA сломается при первой же пробуксовке»</b>\n\n"
            "❌ <b>Стереотип:</b> Вариатор боится сугробов и пробуксовок.\n\n"
            "✅ <b>Реальность:</b>\n"
            "• На LADA Vesta устанавливается бесступенчатый вариатор <b>CVT WLY</b> с гидротрансформатором, агрегатированный с модернизированным мотором 1.8 Evo (122 л.с.).\n"
            "• Гидротрансформатор берет на себя все ударные нагрузки при старте и буксовании в снегу или грязи, защищая шкивы и металлический ремень Bosch.\n"
            "• Агрегат прошел 150 000 км жестких ресурсных испытаний на полигонах в НАМИ и проверен в реальных условиях."
        ),
        "myth_chinese": (
            "🇨🇳 <b>LADA против новых «Китайцев»: В чем выгода для белоруса?</b>\n\n"
            "1. <b>Запчасти в наличии:</b> Любая деталь на LADA продается в любом автомагазине Беларуси или на Exist/Авто1. На китайские кроссоверы даже базовые кузовные элементы нередко ждут по 2–3 месяца.\n"
            "2. <b>КАСКО в 2.5 раза дешевле:</b> Страховка на LADA в Беларуси обходится в разы доступнее.\n"
            "3. <b>Адаптация к морозам:</b> Физические надежные кнопки подогрева руля, лобового стекла и сидений работают безотказно в любые морозы.\n"
            "4. <b>Высокая ликвидность:</b> Подержанная LADA в Беларуси всегда продается быстро и теряет минимум стоимости."
        ),
        "myth_parts": (
            "💸 <b>Стоимость ТО и обслуживания: Реальная экономия семейного бюджета</b>\n\n"
            "📊 <b>Сравнение базового ТО (масло + фильтры + диагностика):</b>\n"
            "• LADA Vesta / Granta: <b>~280 – 350 BYN</b>\n"
            "• Подержанный 'европеец' (VAG / Renault): ~550 – 750 BYN\n"
            "• Новый китайский авто: ~700 – 1 100 BYN\n\n"
            "За 3 года эксплуатации экономия на сервисе, КАСКО и расходниках составляет более <b>6 000 BYN</b>!"
        )
    }
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏁 Записаться на тест-драйв и проверить лично", callback_data="menu_testdrive"),
        types.InlineKeyboardButton("🔙 Другие мифы", callback_data="menu_myths"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    
    text = myths.get(call.data, "Информация обновляется...")
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


# --- РАЗДЕЛ 5: ТЕСТ-ДРАЙВ С ПОДАРКОМ В МИНСКЕ ---

@bot.callback_query_handler(func=lambda call: call.data.startswith("td_car_") or call.data == "menu_testdrive")
def cb_testdrive_select_car(call):
    session = get_user_session(call.message.chat.id)
    session["testdrive"] = {}
    
    if call.data.startswith("td_car_"):
        selected = call.data.replace("td_car_", "").upper()
        session["testdrive"]["car"] = selected
        return cb_testdrive_select_format(call)
        
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌟 Vesta SW Cross", callback_data="td_c_vesta"),
        types.InlineKeyboardButton("🚙 Granta Лифтбек", callback_data="td_c_granta"),
        types.InlineKeyboardButton("🌲 Niva Travel", callback_data="td_c_travel"),
        types.InlineKeyboardButton("⛰️ Niva Legend", callback_data="td_c_legend"),
        types.InlineKeyboardButton("🚐 Largus Cross", callback_data="td_c_largus"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "🏁 <b>Запись на персональный тест-драйв в Минске с подарком</b>\n\n"
        "Попробуйте автомобиль на городских улицах или специальном маршруте!\n"
        "🎁 <b>Бонус:</b> при записи через бота вы получаете гарантированный подарок на выбор (комплект шин или топливная карта Белоруснефть)!\n\n"
        "Шаг 1 из 3: <b>Выберите автомобиль для заезда:</b>"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("td_c_"))
def cb_testdrive_chosen_car(call):
    c_map = {
        "td_c_vesta": "LADA Vesta SW Cross",
        "td_c_granta": "LADA Granta Лифтбек",
        "td_c_travel": "LADA Niva Travel 4x4",
        "td_c_legend": "LADA Niva Legend",
        "td_c_largus": "LADA Largus Cross"
    }
    session = get_user_session(call.message.chat.id)
    session["testdrive"]["car"] = c_map.get(call.data, "LADA Vesta")
    cb_testdrive_select_format(call)


def cb_testdrive_select_format(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🏙️ Городской комфорт (проспект, разгоны, парковка)", callback_data="td_f_city"),
        types.InlineKeyboardButton("🌲 Внедорожный маршрут и грунтовка (для 4х4)", callback_data="td_f_offroad"),
        types.InlineKeyboardButton("👨‍👩‍👧‍👦 Семейный выезд (тест простора багажника и детских кресел)", callback_data="td_f_family"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "Шаг 2 из 3: <b>Какой формат тест-драйва вам интересен?</b>\n\n"
        "Мы подберем оптимальный маршрут с менеджером:"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("td_f_"))
def cb_testdrive_select_gift(call):
    f_map = {
        "td_f_city": "Городской комфорт в Минске",
        "td_f_offroad": "Оффроуд и бездорожье",
        "td_f_family": "Семейный комфорт"
    }
    session = get_user_session(call.message.chat.id)
    session["testdrive"]["format"] = f_map.get(call.data, "Городской тест-драйв")
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⛽ Топливная карта на 200 л (Белоруснефть)", callback_data="td_g_fuel"),
        types.InlineKeyboardButton("🛞 Комплект зимней резины при покупке", callback_data="td_g_tires"),
        types.InlineKeyboardButton("🛡️ Антикоррозийная обработка кузова Dinitrol", callback_data="td_g_pack"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "Шаг 3 из 3: <b>Выберите ваш гарантированный подарок:</b>\n\n"
        "Подарок закрепляется за вами при прохождении тест-драйва:"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("td_g_"))
def cb_testdrive_ask_contacts(call):
    g_map = {
        "td_g_fuel": "⛽ Топливная карта на 200 л (Белоруснефть)",
        "td_g_tires": "🛞 Комплект зимней резины",
        "td_g_pack": "🛡️ Антикор кузова Dinitrol в подарок"
    }
    session = get_user_session(call.message.chat.id)
    session["testdrive"]["gift"] = g_map.get(call.data, "Подарок")
    session["state"] = "TESTDRIVE_PHONE"
    
    car = session["testdrive"].get("car", "LADA Vesta")
    fmt = session["testdrive"].get("format", "Городской тест")
    gift = session["testdrive"].get("gift", "Подарок")
    
    text = (
        f"🎯 <b>Ваш заезд и подарок сформированы:</b>\n"
        f"• Автомобиль: <b>{car}</b>\n"
        f"• Маршрут: <b>{fmt}</b>\n"
        f"• Подарок: <b>{gift}</b>\n\n"
        f"<b>Напишите ваше имя и номер телефона</b> (например: <i>Михаил, +375 29 123-45-67</i>), "
        f"чтобы менеджер автоцентра забронировал за вами удобное время и автомобиль:"
    )
    msg = bot.send_message(call.message.chat.id, text, reply_markup=back_to_main_keyboard())
    bot.register_next_step_handler(msg, step_save_testdrive_phone)


def step_save_testdrive_phone(message):
    if message.text and message.text.startswith("/"):
        return
    text_data = message.text.strip()
    session = get_user_session(message.chat.id)
    
    lead = {
        "type": "🏁 Запись на тест-драйв с подарком (Минск)",
        "name": message.from_user.first_name or "Клиент",
        "username": message.from_user.username or "нет",
        "phone": text_data,
        "details": f"Авто: {session['testdrive'].get('car')}, Формат: {session['testdrive'].get('format')}",
        "gift": session['testdrive'].get('gift')
    }
    save_lead(lead)
    
    success_text = (
        f"✅ <b>Отлично, заявка успешно оформлена!</b>\n\n"
        f"Мы закрепили за вами тест-драйв на <b>{session['testdrive'].get('car')}</b> "
        f"и подарок: <b>{session['testdrive'].get('gift')}</b>.\n\n"
        f"Менеджер официального автоцентра LADA в Минске свяжется с вами для согласования удобного времени. До встречи! 🚗💨"
    )
    bot.send_message(message.chat.id, success_text, reply_markup=main_menu_keyboard())


# --- РАЗДЕЛ 6: КОНТАКТЫ АВТОЦЕНТРОВ В БЕЛАРУСИ ---

@bot.callback_query_handler(func=lambda call: call.data == "menu_contacts")
def cb_contacts(call):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("👤 Позвать живого менеджера в чат", callback_data="call_manager"),
        types.InlineKeyboardButton("📍 Проложить маршрут в салон (Минск, Серова 1)", callback_data="show_geo"),
        types.InlineKeyboardButton("🏠 В главное меню", callback_data="go_main")
    )
    text = (
        "📍 <b>Официальные автоцентры LADA в Минске</b>\n\n"
        "🏢 <b>Главный автоцентр:</b> г. Минск, ул. Серова, 1\n"
        "🏢 <b>Филиал Каменная Горка:</b> г. Минск, ул. Каменногорская, 11\n"
        "🏢 <b>Филиал Юго-Запад:</b> г. Минск, пр-т Дзержинского, 134\n\n"
        "🕒 <b>Режим работы:</b>\n"
        "• Пн – Сб: с 08:00 до 20:00\n"
        "• Вс: с 09:00 до 18:00\n\n"
        "📞 <b>Единая справочная LADA Беларусь:</b>\n"
        "• Короткий номер для всех мобильных (А1, МТС, Life): <b>5811</b>\n"
        "• Городской телефон: <b>+375 (17) 279-97-97</b>\n\n"
        "☕ В салоне: большой парк тест-драйва, кафе, детский уголок и консультанты Беларусбанка."
    )
    bot.send_message(call.message.chat.id, text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "show_geo")
def cb_geo(call):
    bot.send_location(call.message.chat.id, latitude=53.847743, longitude=27.545803)
    bot.send_message(
        call.message.chat.id,
        "📍 Ждем вас в автоцентре LADA на <b>ул. Серова, 1 (Минск)</b>!\nНа территории есть просторная клиентская парковка.",
        reply_markup=main_menu_keyboard()
    )


@bot.callback_query_handler(func=lambda call: call.data == "call_manager")
def cb_call_manager(call):
    text = (
        "👤 <b>Связь с менеджером автоцентра в Минске</b>\n\n"
        "Напишите ваш вопрос или оставьте контактный телефон, "
        "и специалист свяжется с вами в Telegram или по телефону в течение 5 минут:"
    )
    msg = bot.send_message(call.message.chat.id, text, reply_markup=back_to_main_keyboard())
    bot.register_next_step_handler(msg, step_manager_question)


def step_manager_question(message):
    if message.text and message.text.startswith("/"):
        return
    lead = {
        "type": "👤 Прямой запрос к менеджеру (Минск)",
        "name": message.from_user.first_name or "Клиент",
        "username": message.from_user.username or "нет",
        "phone": message.text,
        "details": f"Вопрос/контакт клиента: {message.text}"
    }
    save_lead(lead)
    
    bot.send_message(
        message.chat.id,
        "✅ <b>Запрос передан дежурному менеджеру в Минске!</b>\nСпециалист уже готовит ответ и свяжется с вами в ближайшее время.",
        reply_markup=main_menu_keyboard()
    )


# --- ВОЗВРАТ В МЕНЮ ---

@bot.callback_query_handler(func=lambda call: call.data == "go_main")
def cb_go_main(call):
    text = (
        f"🏠 <b>Главное меню LADA Smart Assistant Беларусь</b>\n\n"
        f"Чем я могу помочь вам сейчас?"
    )
    bot.send_message(call.message.chat.id, text, reply_markup=main_menu_keyboard())


from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"LADA Smart Assistant is online!")
    def log_message(self, format, *args):
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"HTTP server note: {e}", flush=True)

if __name__ == "__main__":
    print("Запуск LADA Smart Assistant Беларусь...", flush=True)
    
    # Запускаем фоновый HTTP сервер для облачных платформ (Render, HuggingFace и др.)
    http_thread = threading.Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Запускаем фоновый поток синхронизации лидов
    sync_thread = threading.Thread(target=background_sync_worker, daemon=True)
    sync_thread.start()
    
    try:
        bot.send_message(ADMIN_ID, "🚀 <b>LADA Smart Assistant запущен!</b>\nСистема синхронизации и отправки заявок активна в режиме 100% надежности.")
        print(f"Стартовое оповещение успешно отправлено админу {ADMIN_ID}!", flush=True)
    except Exception as e:
        print(f"Предупреждение при стартовом оповещении: {e}", flush=True)
        
    logging.info("LADA Smart Assistant bot started polling...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=10, skip_pending=True)
        except Exception as e:
            logging.error(f"Сбой polling: {e}. Автоматический перезапуск через 3 сек...")
            time.sleep(3)
