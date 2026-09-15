"""Passenger-facing bot texts in Uzbek (default) and Russian.

Staff screens (telegram_admin) stay Russian: they serve operators, not passengers.
"""

RUSSIAN_SPEAKING = {"ru", "uk", "be", "kk", "ky"}


def detect_lang(language_code: str | None) -> str:
    return "ru" if (language_code or "").split("-")[0].lower() in RUSSIAN_SPEAKING else "uz"


COMMANDS = {
    "uz": [
        {"command": "start", "description": "Bosh menyu"},
        {"command": "book", "description": "Chipta sotib olish"},
        {"command": "tickets", "description": "Chiptalarim"},
        {"command": "faq", "description": "Ko‘p so‘raladigan savollar"},
        {"command": "support", "description": "Yordam xizmatiga yozish"},
        {"command": "lang", "description": "Tilni almashtirish · Сменить язык"},
    ],
    "ru": [
        {"command": "start", "description": "Главное меню"},
        {"command": "book", "description": "Купить билет"},
        {"command": "tickets", "description": "Мои билеты"},
        {"command": "faq", "description": "Частые вопросы"},
        {"command": "support", "description": "Написать в поддержку"},
        {"command": "lang", "description": "Сменить язык · Tilni almashtirish"},
    ],
}

SHORT_DESCRIPTIONS = {
    "uz": "🚌 NWay — shaharlararo avtobus chiptalari. Joy band qiling va QR-chiptani Telegramda oling.",
    "ru": "🚌 NWay — билеты на междугородние автобусы. Забронируйте место и получите QR-билет в Telegram.",
}

WEEKDAYS = {
    "uz": ["dush", "sesh", "chor", "pay", "jum", "shan", "yak"],
    "ru": ["пн", "вт", "ср", "чт", "пт", "сб", "вс"],
}

TEXTS: dict[str, dict[str, str]] = {
    "uz": {
        "welcome": "NWay’ga xush kelibsiz! 👋",
        "home": (
            "🚌 <b>NWay — yo‘lingiz shu yerdan boshlanadi!</b>\n\n"
            "Qulay joy, oson bron va barcha chiptalaringiz bir joyda.\n\n"
            "🗺 Yo‘nalish va sanani tanlang\n💺 Avtobusdan joyingizni belgilang\n🎫 QR-chiptani shu chatda oling\n\n"
            "💵 To‘lov — avtobusga chiqishda"
        ),
        "demo_home": "\n\n🧪 <b>Sinov rejimi.</b> Reyslar namuna uchun. Pul yechilmaydi, chipta haqiqiy safar uchun yaroqsiz.",
        "open_app": (
            "🎫 <b>Qayerga boramiz?</b>\n\nYo‘nalish → sana → qulay joy → tasdiqlash.\n"
            "Chipta rasmini shu chatga yuboramiz. 💌\n\n💵 To‘lov — avtobusga chiqishda."
        ),
        "btn_buy": "🎫 Chipta sotib olish",
        "btn_app": "📱 Ilovani ochish",
        "btn_my": "🧾 Chiptalarim",
        "btn_my_app": "📱 Ilovada ochish",
        "btn_faq": "❓ Savollar",
        "btn_support": "💬 Yordam",
        "btn_lang": "🌐 Русский",
        "btn_home": "🏠 Bosh menyu",
        "btn_find": "🎫 Reys topish",
        "btn_back": "← Orqaga",
        "origin": "<b>1 / 5 · Yo‘nalish</b>\n\nQayerdan jo‘naysiz?",
        "destination": "<b>1 / 5 · Yo‘nalish</b>\n\n📍 Jo‘nash: {origin}\nQayerga borasiz?",
        "date": "<b>2 / 5 · Safar sanasi</b>\n\n{origin} → {destination}\n\nQachon yo‘lga chiqasiz?",
        "today": "Bugun",
        "tomorrow": "Ertaga",
        "btn_directions": "← Yo‘nalishlar",
        "trips": "<b>3 / 5 · Reys</b>\n\n📅 {day}\n",
        "trips_found": "Jo‘nash vaqtini tanlang. Narx bir yo‘lovchi uchun.",
        "trips_none": "Bu sanaga bo‘sh reys yo‘q. Boshqa kunni tanlang.",
        "trip_row": "{time} · {price} · {seats} joy",
        "btn_other_date": "← Boshqa sana",
        "seats": (
            "<b>4 / 5 · Joyingiz</b>\n\n{origin} → {destination}\n📅 {when} · {price}\n\n"
            "▫️ Bo‘sh · ✖️ Band · ✅ Tanlangan\n🌸 Ayollar uchun joy\n\n"
            "Sxemadan bitta joy tanlang. Bron buyurtma tasdiqlangandan keyin yaratiladi."
        ),
        "btn_continue": "Davom etish →",
        "btn_other_trip": "← Boshqa reys",
        "phone_request": (
            "<b>5 / 5 · Yo‘lovchi</b>\n\nPastdagi tugma orqali raqamingizni ulashing. U safar bo‘yicha aloqa uchun kerak. "
            "Boshqa odamning raqami qabul qilinmaydi.\n\n/start — menyuga qaytish"
        ),
        "btn_share_phone": "📱 Raqamimni ulashish",
        "name_prompt": (
            "<b>5 / 5 · Yo‘lovchi</b>\n\nChiptada qaysi ism yozilsin?\n"
            "Telegramdagi ismni tasdiqlang yoki ism-familiyani bitta xabarda yozing."
        ),
        "btn_seat_back": "← Joy tanlash",
        "review": (
            "<b>Buyurtmani tekshiring</b>\n\n🚌 {origin} → {destination}\n📅 {date} · {time}\n💺 Joy {seat}\n👤 {name}\n📱 {phone}"
            "\n\n<b>Jami: {price}</b>\n💵 To‘lov chiqishda. Hozir to‘lash shart emas."
            "\n\nTasdiqlagach joy band qilinadi, chipta rasm bo‘lib keladi."
        ),
        "demo_review": "\n\n🧪 Bu sinov reysi. Chipta safar huquqini bermaydi.",
        "btn_confirm": "✅ Tasdiqlash va chipta olish",
        "btn_edit_passenger": "✏️ Yo‘lovchi",
        "btn_seat_short": "← Joy",
        "btn_abort": "Rasmiylashtirishni bekor qilish",
        "done": (
            "✅ <b>Tayyor! Joy band qilindi.</b>\n\nBuyurtma <code>{code}</code>\n"
            "Chipta keyingi xabarda keladi. Rasmni saqlab qo‘ying.\n\n💵 To‘lov chiqishda — chipta safar to‘langanini bildirmaydi."
        ),
        "btn_another": "🎫 Yana chipta",
        "my_list": "<b>🧾 Chiptalarim</b>\n\nBronni tanlang. Chiptani qayta oling yoki to‘lanmagan safarni bekor qiling.",
        "my_empty": "<b>🧾 Chiptalarim</b>\n\nHozircha chipta yo‘q. Reys tanlang — tasdiqlangan chiptangiz shu yerda paydo bo‘ladi.",
        "booking": (
            "<b>Bron {code}</b>\n\n{origin} → {destination}\n📅 {when}\n💺 Joy {seats}\n\n"
            "Holati: <b>{status}</b>\n{price} · {payment}"
        ),
        "status_confirmed": "Tasdiqlangan",
        "status_cancelled": "Bekor qilingan",
        "status_expired": "Muddati tugagan",
        "status_completed": "Safar yakunlangan",
        "status_no_show": "Kelmadi",
        "status_pending": "Tasdiq kutilmoqda",
        "paid": "To‘langan",
        "pay_on_board": "To‘lov chiqishda",
        "btn_image": "🖼 Chiptani rasm qilib olish",
        "btn_cancel_trip": "Safarni bekor qilish",
        "btn_all_tickets": "← Barcha chiptalar",
        "image_sending": "🖼 Chiptani yuboryapman. U alohida xabar bo‘lib keladi.",
        "btn_to_booking": "← Buyurtmaga",
        "cancel_ask": (
            "<b>{code} buyurtmasini bekor qilasizmi?</b>\n\n"
            "Joy boshqa yo‘lovchilar uchun yana bo‘shaydi. Chipta amal qilmay qoladi."
        ),
        "btn_cancel_yes": "Ha, bekor qilish",
        "btn_keep": "Safarni saqlash",
        "phone_not_needed": "Raqam bron uchun kerak bo‘ladi. «Reys topish» tugmasini bosing.",
        "phone_saved": "Raqam saqlandi ✓",
        "use_buttons": "Pastdagi tugmalardan foydalaning yoki bosh menyuni oching.",
        "stale": "Bu tugma eskirgan. Qidiruvni qayta oching — chiptalaringiz saqlangan.",
        "error_generic": "Amalni bajarib bo‘lmadi. Ma’lumotlarni tekshiring yoki qidiruvni qaytadan boshlang.",
        "err_SEAT_ALREADY_RESERVED": "Bu joyni boshqa yo‘lovchi band qildi. Boshqasini tanlang — yangi buyurtma yaratilmadi.",
        "err_USER_BLOCKED": "Bu akkaunt uchun bron qilish mumkin emas. Yordam xizmatiga yozing.",
        "err_RESERVATION_EXPIRED": "Rasmiylashtirish vaqti tugadi. Reysni qaytadan tanlang.",
        "err_TRIP_NOT_BOOKABLE": "Bu reys endi mavjud emas.",
        "err_SEAT_NOT_BOOKABLE": "Bu joy mavjud emas. Boshqasini tanlang.",
        "err_CITY_NOT_FOUND": "Shahar topilmadi.",
        "err_ROUTE_NOT_FOUND": "Bu yo‘nalishda hozircha reys yo‘q.",
        "err_STALE_BUTTON": "Bu buyurtma o‘zgargan. Qidiruvni qaytadan boshlang.",
        "err_SEAT_WRONG_BUS": "Bu joy boshqa avtobusga tegishli.",
        "err_NO_SEATS": "Avval joy tanlang.",
        "err_INVALID_NAME": "Ism va familiyani kiriting, 100 belgigacha.",
        "err_TRIP_DEPARTED": "Jo‘nashga juda oz vaqt qoldi. Boshqa reysni tanlang.",
        "err_BOOKING_OWNER_MISMATCH": "Bron topilmadi.",
        "err_RESERVATION_NOT_FOUND": "Bron topilmadi.",
        "err_BOOKING_CLOSED": "Bu buyurtma yopilgan. Yangisini yarating.",
        "err_TICKET_INACTIVE": "Bu chipta endi amal qilmaydi.",
        "err_CANCEL_UNAVAILABLE": "Bu buyurtmani bekor qilish uchun yordam xizmatiga yozing.",
        "err_CONTACT_NOT_YOURS": "Aynan o‘z raqamingizni xabar ostidagi tugma orqali ulashing.",
        "err_INVALID_PHONE": "Raqam noto‘g‘ri. Qaytadan ulashing.",
        "faq": "❓ <b>Ko‘p so‘raladigan savollar</b>\n\nSavolni tanlang. Javob topilmasa — «Yordam» tugmasini bosing.",
        "faq_empty": "❓ <b>Savollar</b>\n\nHozircha savollar ro‘yxati bo‘sh. Yordam xizmatiga yozing — tezda javob beramiz.",
        "btn_faq_back": "← Savollar",
        "support_intro": (
            "💬 <b>Yordam xizmati</b>\n\nSavolingizni yozing — matn, rasm yoki ovozli xabar. "
            "Operator javobi shu chatga keladi.\n\nBuyurtma bo‘yicha bo‘lsa, bron kodini ham yozing."
        ),
        "support_offline": "💬 <b>Yordam xizmati</b>\n\nOnlayn yordam hozircha ulanmagan.",
        "support_contact": "\n\n📞 Aloqa: {contact}",
        "support_sent": "✅ Xabaringiz operatorga yuborildi. Javob shu chatga keladi.\n\nYana yozishingiz yoki menyuga qaytishingiz mumkin.",
        "support_reply": "💬 <b>Yordam xizmati javobi</b>",
        "btn_support_done": "✓ Tugatish",
        "btn_support_answer": "✍️ Javob yozish",
        "ticket_caption": (
            "🎫 <b>Sizning chiptangiz · {ticket}</b>\n{origin} → {destination}\n{date}, {time} · joy {seat}\n{payment}\n\n"
            "Rasmni saqlab qo‘ying. Joriy holat — «Chiptalarim» bo‘limida."
        ),
        "demo_ticket": "\n🧪 Sinov chiptasi. Haqiqiy safar uchun yaroqsiz.",
        "btn_open_booking": "Bronni ochish",
        "btn_open_ticket": "📱 Chiptani ochish",
        "reminder_day": (
            "⏰ <b>Safaringizga bir kundan kam qoldi</b>\n\n🚌 {origin} → {destination}\n📅 {date}, {time}\n📍 {boarding}\n\n"
            "Jo‘nashdan 20 daqiqa oldin keling. Bron: <code>{code}</code>"
        ),
        "reminder_soon": (
            "🚌 <b>Tez orada jo‘nash!</b>\n\n{origin} → {destination}\n📅 {date}, {time}\n📍 {boarding}\n\n"
            "Chipta rasmini tayyorlab qo‘ying. Bron: <code>{code}</code>"
        ),
        "boarding_unknown": "Chiqish joyini tashuvchidan aniqlang",
        "inline_desc": "{price} dan · chipta sotib olish",
        "inline_message": "🚌 <b>{origin} → {destination}</b>\n\nNWay orqali joy tanlang va QR-chiptani Telegramda oling.",
        "btn_inline_buy": "🎫 Chipta olish",
        "inline_open_bot": "🚌 NWay botini ochish",
    },
    "ru": {
        "welcome": "Добро пожаловать в NWay! 👋",
        "home": (
            "🚌 <b>NWay — ваша дорога начинается здесь!</b>\n\n"
            "Удобное место, простое бронирование и все билеты в одном месте.\n\n"
            "🗺 Выберите направление и дату\n💺 Отметьте место в автобусе\n🎫 Получите QR-билет в этот чат\n\n"
            "💵 Оплата — при посадке"
        ),
        "demo_home": "\n\n🧪 <b>Тестовый режим.</b> Рейсы для примера. Деньги не списываются, билет недействителен для поездки.",
        "open_app": (
            "🎫 <b>Куда поедем?</b>\n\nНаправление → дата → удобное место → подтверждение.\n"
            "Билет пришлём картинкой в этот чат. 💌\n\n💵 Оплата — при посадке."
        ),
        "btn_buy": "🎫 Купить билет",
        "btn_app": "📱 Открыть приложение",
        "btn_my": "🧾 Мои билеты",
        "btn_my_app": "📱 Открыть в приложении",
        "btn_faq": "❓ Вопросы",
        "btn_support": "💬 Поддержка",
        "btn_lang": "🌐 O‘zbekcha",
        "btn_home": "🏠 Главное меню",
        "btn_find": "🎫 Найти рейс",
        "btn_back": "← Назад",
        "origin": "<b>1 / 5 · Маршрут</b>\n\nОткуда поедем?",
        "destination": "<b>1 / 5 · Маршрут</b>\n\n📍 Отправление: {origin}\nКуда отправимся?",
        "date": "<b>2 / 5 · Дата поездки</b>\n\n{origin} → {destination}\n\nКогда хотите поехать?",
        "today": "Сегодня",
        "tomorrow": "Завтра",
        "btn_directions": "← Направления",
        "trips": "<b>3 / 5 · Рейс</b>\n\n📅 {day}\n",
        "trips_found": "Выберите время отправления. Цена указана за одного пассажира.",
        "trips_none": "На эту дату свободных рейсов нет. Выберите другой день.",
        "trip_row": "{time} · {price} · {seats} мест",
        "btn_other_date": "← Другая дата",
        "seats": (
            "<b>4 / 5 · Ваше место</b>\n\n{origin} → {destination}\n📅 {when} · {price}\n\n"
            "▫️ Свободно · ✖️ Занято · ✅ Выбрано\n🌸 Место для пассажирки\n\n"
            "Выберите одно место на схеме. Бронь создаётся после подтверждения заказа."
        ),
        "btn_continue": "Продолжить →",
        "btn_other_trip": "← Другой рейс",
        "phone_request": (
            "<b>5 / 5 · Пассажир</b>\n\nПоделитесь своим номером кнопкой ниже. Он нужен для связи по поездке. "
            "Чужие контакты не принимаются.\n\n/start — вернуться в меню"
        ),
        "btn_share_phone": "📱 Поделиться моим номером",
        "name_prompt": (
            "<b>5 / 5 · Пассажир</b>\n\nКак указать имя в билете?\n"
            "Подтвердите имя из Telegram или напишите имя и фамилию одним сообщением."
        ),
        "btn_seat_back": "← Выбор места",
        "review": (
            "<b>Проверьте заказ</b>\n\n🚌 {origin} → {destination}\n📅 {date} · {time}\n💺 Место {seat}\n👤 {name}\n📱 {phone}"
            "\n\n<b>Итого: {price}</b>\n💵 Оплата при посадке. Сейчас платить не нужно."
            "\n\nПосле подтверждения место будет забронировано, а билет придёт картинкой."
        ),
        "demo_review": "\n\n🧪 Это тестовый рейс. Билет не даёт права проезда.",
        "btn_confirm": "✅ Подтвердить и получить билет",
        "btn_edit_passenger": "✏️ Пассажир",
        "btn_seat_short": "← Место",
        "btn_abort": "Отменить оформление",
        "done": (
            "✅ <b>Готово! Место забронировано.</b>\n\nЗаказ <code>{code}</code>\n"
            "Билет отправляется следующим сообщением. Сохраните картинку.\n\n💵 Оплата при посадке — билет не означает, что поездка оплачена."
        ),
        "btn_another": "🎫 Ещё один билет",
        "my_list": "<b>🧾 Мои билеты</b>\n\nВыберите бронь. Можно получить билет заново или отменить неоплаченную поездку.",
        "my_empty": "<b>🧾 Мои билеты</b>\n\nПока билетов нет. Выберите рейс — подтверждённый билет появится здесь.",
        "booking": (
            "<b>Бронь {code}</b>\n\n{origin} → {destination}\n📅 {when}\n💺 Место {seats}\n\n"
            "Статус: <b>{status}</b>\n{price} · {payment}"
        ),
        "status_confirmed": "Подтверждена",
        "status_cancelled": "Отменена",
        "status_expired": "Истекла",
        "status_completed": "Поездка завершена",
        "status_no_show": "Пассажир не явился",
        "status_pending": "Ожидает подтверждения",
        "paid": "Оплачено",
        "pay_on_board": "Оплата при посадке",
        "btn_image": "🖼 Получить билет картинкой",
        "btn_cancel_trip": "Отменить поездку",
        "btn_all_tickets": "← Все билеты",
        "image_sending": "🖼 Отправляю билет. Он появится отдельным сообщением.",
        "btn_to_booking": "← К заказу",
        "cancel_ask": (
            "<b>Отменить заказ {code}?</b>\n\n"
            "Место снова станет доступно другим пассажирам. Билет перестанет действовать."
        ),
        "btn_cancel_yes": "Да, отменить заказ",
        "btn_keep": "Сохранить поездку",
        "phone_not_needed": "Номер нужен для бронирования. Нажмите «Найти рейс».",
        "phone_saved": "Номер сохранён ✓",
        "use_buttons": "Воспользуйтесь кнопками ниже или откройте главное меню.",
        "stale": "Эта кнопка устарела. Откройте поиск заново — ваши билеты сохранены.",
        "error_generic": "Не удалось выполнить действие. Проверьте данные или начните поиск заново.",
        "err_SEAT_ALREADY_RESERVED": "Это место уже заняли. Выберите другое — новый заказ не создан.",
        "err_USER_BLOCKED": "Бронирование для этого аккаунта недоступно. Обратитесь в поддержку.",
        "err_RESERVATION_EXPIRED": "Время оформления истекло. Выберите рейс заново.",
        "err_TRIP_NOT_BOOKABLE": "Этот рейс больше недоступен.",
        "err_SEAT_NOT_BOOKABLE": "Это место недоступно. Выберите другое.",
        "err_CITY_NOT_FOUND": "Город не найден.",
        "err_ROUTE_NOT_FOUND": "На этом направлении пока нет рейсов.",
        "err_STALE_BUTTON": "Этот заказ уже изменён. Начните поиск заново.",
        "err_SEAT_WRONG_BUS": "Это место относится к другому автобусу.",
        "err_NO_SEATS": "Сначала выберите место.",
        "err_INVALID_NAME": "Введите имя и фамилию, до 100 символов.",
        "err_TRIP_DEPARTED": "До отправления осталось слишком мало времени. Выберите другой рейс.",
        "err_BOOKING_OWNER_MISMATCH": "Бронь не найдена.",
        "err_RESERVATION_NOT_FOUND": "Бронь не найдена.",
        "err_BOOKING_CLOSED": "Этот заказ уже закрыт. Создайте новый.",
        "err_TICKET_INACTIVE": "Этот билет больше не действует.",
        "err_CANCEL_UNAVAILABLE": "Для отмены этого заказа обратитесь в поддержку.",
        "err_CONTACT_NOT_YOURS": "Поделитесь именно своим номером кнопкой под сообщением.",
        "err_INVALID_PHONE": "Номер некорректен. Поделитесь им ещё раз.",
        "faq": "❓ <b>Частые вопросы</b>\n\nВыберите вопрос. Не нашли ответ — нажмите «Поддержка».",
        "faq_empty": "❓ <b>Вопросы</b>\n\nСписок вопросов пока пуст. Напишите в поддержку — ответим быстро.",
        "btn_faq_back": "← Вопросы",
        "support_intro": (
            "💬 <b>Поддержка</b>\n\nОпишите вопрос — текстом, фото или голосовым. "
            "Ответ оператора придёт в этот чат.\n\nЕсли вопрос по заказу, укажите код брони."
        ),
        "support_offline": "💬 <b>Поддержка</b>\n\nОнлайн-поддержка пока не подключена.",
        "support_contact": "\n\n📞 Контакты: {contact}",
        "support_sent": "✅ Сообщение отправлено оператору. Ответ придёт в этот чат.\n\nМожно дописать ещё или вернуться в меню.",
        "support_reply": "💬 <b>Ответ поддержки</b>",
        "btn_support_done": "✓ Завершить",
        "btn_support_answer": "✍️ Ответить",
        "ticket_caption": (
            "🎫 <b>Ваш билет · {ticket}</b>\n{origin} → {destination}\n{date}, {time} · место {seat}\n{payment}\n\n"
            "Сохраните картинку. Актуальный статус — в разделе «Мои билеты»."
        ),
        "demo_ticket": "\n🧪 Тестовый билет. Недействителен для поездки.",
        "btn_open_booking": "Открыть бронь",
        "btn_open_ticket": "📱 Открыть билет",
        "reminder_day": (
            "⏰ <b>До поездки меньше суток</b>\n\n🚌 {origin} → {destination}\n📅 {date}, {time}\n📍 {boarding}\n\n"
            "Приходите за 20 минут до отправления. Бронь: <code>{code}</code>"
        ),
        "reminder_soon": (
            "🚌 <b>Скоро отправление!</b>\n\n{origin} → {destination}\n📅 {date}, {time}\n📍 {boarding}\n\n"
            "Держите картинку билета под рукой. Бронь: <code>{code}</code>"
        ),
        "boarding_unknown": "Место посадки уточните у перевозчика",
        "inline_desc": "от {price} · купить билет",
        "inline_message": "🚌 <b>{origin} → {destination}</b>\n\nВыберите место в NWay и получите QR-билет в Telegram.",
        "btn_inline_buy": "🎫 Купить билет",
        "inline_open_bot": "🚌 Открыть бота NWay",
    },
}


def t(lang: str, key: str, **values) -> str:
    text = TEXTS.get(lang, TEXTS["uz"]).get(key)
    if text is None:
        text = TEXTS["uz"][key]
    return text.format(**values) if values else text


def has_text(lang: str, key: str) -> bool:
    return key in TEXTS.get(lang, TEXTS["uz"])
