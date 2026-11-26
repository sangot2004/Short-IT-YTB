"""Tạo ảnh đại diện kênh (800x800, YouTube tự cắt tròn). Chạy: .venv/bin/python kenh/anh_dai_dien.py"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ban_tin import MAU, font  # dùng đúng màu và font của video

S = 800
RA = Path(__file__).resolve().parent


def nen():
    img = Image.new("RGBA", (S, S), MAU["nen"] + (255,))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((60, 40, 740, 720), fill=(110, 80, 230, 120))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    d = ImageDraw.Draw(img)
    for y in range(20, S, 40):
        for x in range(20, S, 40):
            d.point((x, y), fill=(255, 255, 255, 22))
    return img


def mau_a():  # khối vuông tím bo góc + "BT", giống logo trong video
    img = nen(); d = ImageDraw.Draw(img)
    d.rounded_rectangle((170, 170, 630, 630), radius=110, fill=MAU["tim"])
    d.text((400, 392), "BT", font=font(250, "dam"), fill="white", anchor="mm")
    return img


def mau_b():  # chữ "IT" lớn + dấu nhắc lệnh, thanh tím bên dưới
    img = nen(); d = ImageDraw.Draw(img)
    d.text((400, 360), ">_IT", font=font(270, "dam"), fill="white", anchor="mm")
    d.rounded_rectangle((200, 520, 600, 590), radius=35, fill=MAU["tim"])
    d.text((400, 556), "BẢN TIN", font=font(46, "dam"), fill="white", anchor="mm")
    return img


def mau_c():  # "BT" trắng trên nền tối, vòng viền tím
    img = nen(); d = ImageDraw.Draw(img)
    d.ellipse((110, 110, 690, 690), outline=MAU["tim"] + (255,), width=26)
    d.text((400, 392), "BT", font=font(270, "dam"), fill="white", anchor="mm")
    return img


def xem_truoc(cac):
    """Ghép các mẫu: mỗi mẫu cắt tròn ở cỡ lớn (220) và cỡ thật trên Shorts (56)."""
    tam = Image.new("RGB", (len(cac) * 300, 360), (245, 245, 245))
    d = ImageDraw.Draw(tam)
    for i, (ten, im) in enumerate(cac):
        for co, (x, y) in [(220, (40, 30)), (56, (122, 270))]:
            nho = im.resize((co, co), Image.LANCZOS)
            mask = Image.new("L", (co, co), 0); ImageDraw.Draw(mask).ellipse((0, 0, co - 1, co - 1), fill=255)
            tam.paste(nho.convert("RGB"), (i * 300 + x, y), mask)
        d.text((i * 300 + 150, 345), ten, font=font(26, "dam"), fill=(30, 30, 30), anchor="mm")
    return tam


if __name__ == "__main__":
    mau_a().convert("RGB").save(RA / "anh-dai-dien.png")  # mẫu đã chọn
    print("Đã lưu", RA / "anh-dai-dien.png")
    if "--ca-ba" not in sys.argv:  # thêm --ca-ba để xuất lại cả 3 mẫu + ảnh xem trước
        sys.exit()
    cac =[("Mẫu A", mau_a()), ("Mẫu B", mau_b()), ("Mẫu C", mau_c())]
    for ten, im in cac:
        im.convert("RGB").save(RA / f"anh-dai-dien-{ten[-1].lower()}.png")
    xem_truoc(cac).save(RA / "xem-truoc.png")
    print("Đã lưu vào", RA)
