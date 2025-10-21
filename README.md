# Hisobchi Bot (aiogram 3.x + SQLite3)

Telegram boti kundalik xarajatlarni yozib boradi, hisobotlarni ko'rsatadi.

## Xususiyatlar

- `aiogram` 3.x asosida asinxron bot
- `sqlite3` bilan avtomatik DB yaratish
- `.env` orqali `BOT_TOKEN` yuklash
- HTML format bilan <b>qalin</b> matn va ixtiyoriy stikerlar
- Buyruqlar: `/start`, `/hisobot`, `/bugun`, `/oylik`
- Qo'shimcha buyruqlar: `/help`, `/undo`, `/stat`, `/export`
- Xabar formatini tekshirish, foydali xatoliklar

## O'rnatish

1) Python 3.10+ o'rnating.

2) Kutubxonalarni o'rnating:

```
pip install -r requirements.txt
```

3) `.env` faylini yarating (namuna `.env.example`):

```
BOT_TOKEN=1234567890:REPLACE_WITH_YOUR_BOT_TOKEN
# DB_PATH=expenses.db  # ixtiyoriy
# STICKER_WELCOME_ID=...  # ixtiyoriy
# STICKER_SUCCESS_ID=...  # ixtiyoriy
# --- Keepalive (bepul hosting) ---
# PORT=8080                 # PaaS belgilasa avtomatik olinadi
# KEEPALIVE_PORT=8080       # PORT bo'lmasa shu ishlatiladi
# KEEPALIVE_URL=https://app-url.example.com/health
# KEEPALIVE_INTERVAL=300    # soniya (default 300)
```

4) Botni ishga tushiring:

```
python bot.py
```

## Foydalanish

- `/start` — foydalanish bo'yicha qisqacha ma'lumot
- Xarajat qo'shish: `mahsulot summa` (masalan: `non 5000`)
- `/hisobot` — barcha yozuvlar va jami
- `/bugun` — bugungi yozuvlar va jami
- `/oylik` — joriy oy xarajatlari ro‘yxati va jami
- `/undo` — oxirgi kiritilgan yozuvni o'chirish
- `/stat` — joriy oy bo'yicha toifalar kesimida statistikalar
- `/export` — barcha yozuvlarni CSV fayl sifatida yuklab olish
  - Yangi yozuvdan so‘ng inline tugmalar chiqadi: 🧾 Hisobot, 📅 Bugun, 📆 Oylik, ↩️ Bekor qilish

## Ma'lumotlar bazasi

- Fayl: `expenses.db` (yoki `DB_PATH` orqali o'zgartiring)
- Jadval: `expenses (id, user_id, item, amount, date, category)`
- `date` qiymati `YYYY-MM-DD` formatida saqlanadi

## Bepul hostingda "uxlab qolmaslik" (keepalive)

- Kod ichiga minimal HTTP server qo'shildi: `GET /health` uchun `200 OK` qaytaradi.
- PaaS odatda `PORT` muhit o'zgaruvchisini beradi — server shu portda tinglaydi.
- Agar `.env` ichida `KEEPALIVE_URL` ko'rsatsangiz, bot ushbu URL'ni `KEEPALIVE_INTERVAL` bo'yicha o'zi ping qilib turadi.
- Tavsiya: UptimeRobot yoki PaaS healthcheck bilan `https://<sizning-app-urlingiz>/health` manzilini 5 daqiqada bir ping qiling.

Misol (`.env`):

```
KEEPALIVE_URL=https://your-app.onrender.com/health
KEEPALIVE_INTERVAL=300
```

## Yozish formati va toifalar

- Oddiy: `non 5000`
- Toifa bilan: `non 5000 #ovqat`
- Summani bo'lish belgilari bilan ham yozish mumkin: `12 000`, `12,000`, `12000 so'm`

## Stiker file_id olish

- Botga istalgan stiker yuboring — u sizga `file_id` qaytaradi.
- Shu `file_id`ni `.env` ichida `STICKER_WELCOME_ID` yoki `STICKER_SUCCESS_ID` ga yozing.

## Eslatmalar

- Bot tokenini xavfsiz saqlang; hech qayerda oshkor qilmang.
- SQLite operatsiyalari `asyncio.to_thread` orqali ishga tushiriladi, shuning uchun bot javob berishda bloklanmaydi.
