"""Render actual ticket data and its verification token into a shareable PNG."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import qrcode


@dataclass(frozen=True)
class TicketImageData:
    public_id: str
    booking_code: str
    qr_token: str
    origin: str
    destination: str
    departure_date: str
    departure_time: str
    arrival_time: str
    passenger: str
    seat: str
    bus: str
    boarding: str
    price: str
    payment: str = "Оплата при посадке"
    status: str = "БРОНЬ ПОДТВЕРЖДЕНА"
    demo: bool = False


def font(size: int, bold: bool = False):
    names = (
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"C:/Windows/Fonts/arial{'bd' if bold else ''}.ttf",
    )
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default(size=size)


def render_ticket(data: TicketImageData) -> bytes:
    width, height = 1080, 1550
    image = Image.new("RGB", (width, height), "#E7EEE9")
    draw = ImageDraw.Draw(image)
    ink, muted, teal = "#142F2A", "#60756F", "#16735D"
    draw.rounded_rectangle((36, 28, 1044, 1522), radius=36, fill="#FFFEF8")
    draw.rounded_rectangle((36, 28, 1044, 396), radius=36, fill=ink)
    draw.rectangle((36, 300, 1044, 396), fill=ink)

    def label(text, xy, size=24, color=muted, bold=False, max_width=900):
        selected = font(size, bold)
        while draw.textlength(text, font=selected) > max_width and size > 17:
            size -= 1
            selected = font(size, bold)
        if draw.textlength(text, font=selected) > max_width:
            while text and draw.textlength(text + "…", font=selected) > max_width:
                text = text[:-1]
            text += "…"
        draw.text(xy, text, fill=color, font=selected)

    label("nway", (86, 60), 58, "#FFFFFF", True)
    label("ВАШ ПУТЬ. ВАШЕ МЕСТО.", (88, 132), 18, "#A7C9B6")
    draw.rounded_rectangle((750, 70, 994, 116), radius=23, fill="#D6EDAE")
    label("ЭЛЕКТРОННЫЙ БИЛЕТ", (769, 84), 16, ink, True, 210)
    label(data.origin, (86, 196), 53, "#FFFFFF", True, 890)
    label("↓", (88, 260), 35, "#D6EDAE")
    label(data.destination, (86, 306), 53, "#FFFFFF", True, 890)

    label("ОТПРАВЛЕНИЕ", (86, 439), 20)
    label(data.departure_time, (82, 470), 80, ink, True, 490)
    label(data.departure_date, (88, 569), 27, ink)
    label("МЕСТО", (775, 439), 20)
    draw.rounded_rectangle((748, 476, 994, 604), radius=25, fill="#E7F0DA")
    label(data.seat, (790, 488), 82, ink, True, 170)
    label(f"Прибытие {data.arrival_time}  ·  Время местное", (88, 631), 22)
    draw.line((86, 687, 994, 687), fill="#DCE5DD", width=2)

    label("ПАССАЖИР", (88, 724), 20)
    label(data.passenger, (86, 759), 38, ink, True, 902)
    label("АВТОБУС", (88, 831), 20)
    label(data.bus, (88, 864), 29, ink, max_width=902)
    label("ПОСАДКА", (88, 924), 20)
    label(data.boarding, (88, 957), 28, ink, max_width=902)
    label(data.price, (88, 1024), 40, ink, True, 500)
    label(data.payment, (88, 1083), 25, teal, True, 550)

    for x in range(65, 1020, 24):
        draw.line((x, 1150, x + 12, 1150), fill="#B9CCC1", width=2)
    draw.ellipse((13, 1128, 59, 1174), fill="#E7EEE9")
    draw.ellipse((1021, 1128, 1067, 1174), fill="#E7EEE9")

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=7, border=4)
    qr.add_data(data.qr_token)
    qr.make(fit=True)
    qr.box_size = max(1, 310 // (qr.modules_count + 2 * qr.border))
    code = qr.make_image(fill_color=ink, back_color="#FFFEF8").convert("RGB")
    # Integer QR modules preserve sharp edges for phone cameras.
    image.paste(code, (77, 1192))
    label(data.status, (425, 1200), 22, teal, True, 565)
    label(data.public_id, (422, 1242), 37, ink, True, 565)
    label(f"Заказ {data.booking_code}", (425, 1302), 26, ink, max_width=565)
    label("Покажите QR при посадке.", (425, 1359), 22, muted, max_width=565)
    label("Приезжайте за 20 минут до рейса.", (425, 1393), 22, muted, max_width=565)
    if data.demo:
        label("ДЕМО • ТЕСТОВЫЙ РЕЙС • НЕ ДЛЯ ПРОЕЗДА", (425, 1460), 17, "#A15821", True, 565)
    else:
        label("Сохраните билет, он доступен без интернета.", (425, 1460), 17, muted, max_width=565)
    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
