"""FAQ content shared by the bot, the Mini App and the admin panel."""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.faq import FaqItem

LANGS = ("uz", "ru")

# Starter content. Operators edit it in the admin panel; it is only inserted
# into an empty table, so later edits and deletions are never overwritten.
DEFAULT_FAQ: dict[str, list[tuple[str, str, str]]] = {
    "uz": [
        ("booking", "Chiptani qanday sotib olaman?",
         "Botda «Chipta sotib olish» tugmasini bosing. Yo‘nalish, sana va joyni tanlang, ismingiz va raqamingizni kiriting, bronni tasdiqlang. QR-chipta shu chatga rasm bo‘lib keladi."),
        ("payment", "To‘lov qanday amalga oshiriladi?",
         "Hozircha to‘lov avtobusga chiqishda naqd pul bilan qilinadi. Bron qilishda pul yechilmaydi. Payme, Click va karta orqali to‘lov tez orada ulanadi."),
        ("booking", "Joy qancha vaqt saqlanadi?",
         "Tanlangan joy rasmiylashtirish uchun 10 daqiqa saqlanadi. Tasdiqlangan bron jo‘nashgacha amal qiladi."),
        ("booking", "4 va undan ko‘p joy olsam-chi?",
         "Katta guruh uchun bronni operator tasdiqlaydi: u ko‘rsatilgan raqamga qo‘ng‘iroq qiladi. Tasdiqlangach, chiptalar chatga keladi."),
        ("tickets", "Chipta kelmadi. Nima qilay?",
         "«Chiptalarim» bo‘limini oching, bronni tanlang va «Chiptani rasm qilib olish» tugmasini bosing. Botni bloklamaganingizni tekshiring."),
        ("tickets", "Bronni qanday bekor qilaman?",
         "«Chiptalarim» → bron → «Safarni bekor qilish». To‘lanmagan bronni jo‘nashgacha bekor qilish mumkin. Joy boshqa yo‘lovchilarga bo‘shaydi, QR-chipta amal qilmay qoladi."),
        ("trip", "Qachon kelishim kerak?",
         "Jo‘nashdan kamida 20 daqiqa oldin keling. Vaqt jo‘nash shahri bo‘yicha ko‘rsatiladi. Chiqish joyi chiptada yozilgan."),
        ("trip", "Haydovchiga nimani ko‘rsataman?",
         "Chipta rasmidagi QR-kodni yoki bron kodini ko‘rsating. Internet bo‘lmasa ham rasm yetarli."),
        ("trip", "Ayollar uchun joylar nima?",
         "Salon sxemasida 🌸 belgisi bilan ko‘rsatilgan joylar faqat ayol yo‘lovchilar uchun."),
    ],
    "ru": [
        ("booking", "Как купить билет?",
         "Нажмите в боте «Купить билет». Выберите направление, дату и место, укажите имя и номер, подтвердите бронь. QR-билет придёт в этот чат картинкой."),
        ("payment", "Как оплатить поездку?",
         "Пока оплата наличными при посадке в автобус. При бронировании деньги не списываются. Оплата через Payme, Click и карту скоро появится."),
        ("booking", "Сколько держится место?",
         "Выбранное место держится 10 минут на оформление. Подтверждённая бронь действует до отправления."),
        ("booking", "Что если нужно 4 места и больше?",
         "Бронь для группы подтверждает оператор: он позвонит на указанный номер. После подтверждения билеты придут в чат."),
        ("tickets", "Билет не пришёл. Что делать?",
         "Откройте «Мои билеты», выберите бронь и нажмите «Получить билет картинкой». Проверьте, что вы не заблокировали бота."),
        ("tickets", "Как отменить бронь?",
         "«Мои билеты» → бронь → «Отменить поездку». Неоплаченную бронь можно отменить до отправления. Место освободится, QR-билет перестанет действовать."),
        ("trip", "Когда приходить на посадку?",
         "Приходите минимум за 20 минут до отправления. Время указано по городу отправления. Место посадки написано в билете."),
        ("trip", "Что показать водителю?",
         "QR-код с картинки билета или код брони. Интернет не нужен — достаточно картинки."),
        ("trip", "Что такое места для женщин?",
         "Места с отметкой 🌸 на схеме салона предназначены только для пассажирок."),
    ],
}


def normalize_lang(value: str | None) -> str:
    return value if value in LANGS else "uz"


async def list_faq(session: AsyncSession, lang: str, *, active_only: bool = True) -> list[FaqItem]:
    query = select(FaqItem).where(FaqItem.lang == normalize_lang(lang))
    if active_only:
        query = query.where(FaqItem.active.is_(True))
    return list((await session.scalars(query.order_by(FaqItem.position, FaqItem.created_at))).all())


async def ensure_default_faq(session: AsyncSession) -> int:
    if await session.scalar(select(func.count()).select_from(FaqItem)):
        return 0
    added = 0
    for lang, items in DEFAULT_FAQ.items():
        for position, (category, question, answer) in enumerate(items):
            session.add(FaqItem(lang=lang, category=category, question=question, answer=answer, position=position * 10))
            added += 1
    await session.commit()
    return added
