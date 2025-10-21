import asyncio
import logging
import os
from datetime import datetime, date

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, BotCommand, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

from db import (
    init_db,
    add_expense,
    get_all_expenses,
    get_expenses_by_date,
    get_month_total,
    get_last_expense,
    delete_expense,
    delete_all_expenses,
)
from utils import parse_expense_message, format_expenses_with_total, format_amount
from keepalive import start_keepalive_server, start_self_ping


router = Router()
WELCOME_STICKER_ID = os.getenv("STICKER_WELCOME_ID")
SUCCESS_STICKER_ID = os.getenv("STICKER_SUCCESS_ID")


def _main_reply_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧾 Hisobot"), KeyboardButton(text="📅 Bugun")],
            [KeyboardButton(text="📆 Oylik"), KeyboardButton(text="↩️ Bekor qilish")],
            [KeyboardButton(text="🗑️ O'chirish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
        selective=False,
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Handle /start command: greet and explain usage."""
    text = (
        "<b>👋 Assalomu alaykum!</b> Men kundalik xarajatlarni yozib boruvchi botman.\n\n"
        "<b>Qanday yoziladi?</b>\n"
        "— Masalan: <b>non 5000</b> yoki <b>qahva 12000</b>\n\n"
        "<b>Hisobotlar:</b>\n"
        "• /hisobot — barcha xarajatlar va jami\n"
        "• /bugun — bugungi xarajatlar va jami\n"
        "• /oylik — joriy oy jami"
    )
    if WELCOME_STICKER_ID:
        try:
            await message.bot.send_sticker(chat_id=message.chat.id, sticker=WELCOME_STICKER_ID)
        except Exception:
            pass
    await message.answer(text, reply_markup=_main_reply_kb())


@router.message(Command("hisobot"))
async def cmd_hisobot(message: Message) -> None:
    """Show all expenses for the user with a total."""
    try:
        user_id = message.from_user.id
        rows = await get_all_expenses(user_id)
        if not rows:
            await message.answer("🧾 Hali hech qanday xarajat kiritilmagan.")
            return
        reply = "\n".join(["<b>🧾 Xarajatlaringiz:</b>", format_expenses_with_total(rows)])
        await message.answer(reply)
    except Exception as exc:
        logging.exception("Failed to build /hisobot: %s", exc)
        await message.answer("Kechirasiz, hisobotni chiqarishda xatolik yuz berdi.")


@router.message(Command("bugun"))
async def cmd_bugun(message: Message) -> None:
    """Show only today's expenses and total for the user."""
    try:
        user_id = message.from_user.id
        today = date.today().strftime("%Y-%m-%d")
        rows = await get_expenses_by_date(user_id, today)
        if not rows:
            await message.answer("🧾 Bugun uchun xarajatlar topilmadi.")
            return
        reply = "\n".join(["<b>🧾 Bugungi xarajatlaringiz:</b>", format_expenses_with_total(rows)])
        await message.answer(reply)
    except Exception as exc:
        logging.exception("Failed to build /bugun: %s", exc)
        await message.answer("Kechirasiz, bugungi hisobotni chiqarishda xatolik yuz berdi.")


@router.message(Command("oylik"))
async def cmd_oylik(message: Message) -> None:
    """Show current month's total expenses for the user (sum only)."""
    try:
        user_id = message.from_user.id
        today = date.today()
        total = await get_month_total(user_id, today.year, today.month)
        await message.answer(f"📅 Joriy oy xarajatlari jami: <b>{format_amount(total)}</b>")
    except Exception as exc:
        logging.exception("Failed to build /oylik: %s", exc)
        await message.answer("Kechirasiz, oylik hisobotni chiqarishda xatolik yuz berdi.")


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    await message.answer("📋 Menyu yangilandi.", reply_markup=_main_reply_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await cmd_start(message)


@router.message(Command("undo"))
async def cmd_undo(message: Message) -> None:
    """Delete the most recently added expense for this user."""
    try:
        user_id = message.from_user.id
        last = await get_last_expense(user_id)
        if not last:
            await message.answer("🗑️ O'chirish uchun yozuv topilmadi.")
            return
        exp_id, item, amount, _dt, _cat = last
        removed = await delete_expense(user_id, exp_id)
        if removed:
            await message.answer(f"🗑️ Oxirgi yozuv o'chirildi: <b>{item}</b> — <b>{format_amount(amount)}</b>")
        else:
            await message.answer("O'chirish amalga oshmadi.")
    except Exception:
        logging.exception("Failed to undo")
        await message.answer("Kechirasiz, o'chirishda xatolik yuz berdi.")


# ReplyKeyboard button text handlers (before generic text handler)
@router.message(F.text.in_({"🧾 Hisobot", "Hisobot"}))
async def rk_hisobot(message: Message) -> None:
    await cmd_hisobot(message)


@router.message(F.text.in_({"📅 Bugun", "Bugun"}))
async def rk_bugun(message: Message) -> None:
    await cmd_bugun(message)


@router.message(F.text.in_({"📆 Oylik", "Oylik"}))
async def rk_oylik(message: Message) -> None:
    await cmd_oylik(message)


@router.message(F.text.in_({"↩️ Bekor qilish", "Bekor qilish"}))
async def rk_cancel(message: Message) -> None:
    # Behaves like undo: remove the last expense
    await cmd_undo(message)


@router.message(F.text.in_({"🗑️ O'chirish", "O'chirish"}))
async def rk_delete(message: Message) -> None:
    await cmd_clear(message)


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    """Clear all expenses for the current user (reset to zero)."""
    try:
        user_id = message.from_user.id
        removed = await delete_all_expenses(user_id)
        if removed:
            await message.answer(f"🗑️ Barcha xarajatlar o'chirildi. Jami: <b>0 so'm</b> (o'chirildi: {removed})")
        else:
            await message.answer("🗑️ O'chirish uchun yozuvlar topilmadi. Jami: <b>0 so'm</b>")
    except Exception:
        logging.exception("Failed to clear")
        await message.answer("Kechirasiz, barcha yozuvlarni o'chirishda xatolik yuz berdi.")


@router.message(F.text)
async def handle_expense_message(message: Message) -> None:
    """Parse 'item amount' text and store it as an expense record."""
    user_id = message.from_user.id
    text = message.text or ""
    try:
        item, amount = parse_expense_message(text)
    except ValueError as e:
        await message.answer(
            (
                "❗ Noto'g'ri format. Iltimos quyidagicha yuboring:\n"
                "masalan: 'non 5000' yoki 'qahva 12000'\n"
                f"Xatolik tafsiloti: {e}"
            )
        )
        return

    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        await add_expense(user_id=user_id, item=item, amount=amount, date_str=today_str)
        if SUCCESS_STICKER_ID:
            try:
                await message.bot.send_sticker(chat_id=message.chat.id, sticker=SUCCESS_STICKER_ID)
            except Exception:
                pass
        await message.answer(
            f"✅ <b>{item}</b> uchun <b>{format_amount(amount)}</b> yozib qo'yildi."
        )
    except Exception as exc:
        logging.exception("Failed to add expense: %s", exc)
        await message.answer("Kechirasiz, ma'lumotni saqlashda xatolik yuz berdi.")


async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="Botdan foydalanish bo'yicha ma'lumot"),
        BotCommand(command="hisobot", description="Barcha xarajatlar va jami"),
        BotCommand(command="bugun", description="Bugungi xarajatlar va jami"),
        BotCommand(command="oylik", description="Joriy oy jami xarajatlar"),
        BotCommand(command="menu", description="Menyuni qayta ko'rsatish"),
        BotCommand(command="help", description="Qisqa yo'riqnoma"),
        BotCommand(command="undo", description="Oxirgi yozuvni o'chirish"),
        BotCommand(command="clear", description="Barcha yozuvlarni o'chirish"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Put it in a .env file.")

    # Start lightweight HTTP server for free-hosting keepalive pings
    try:
        start_keepalive_server()
        keepalive_url = os.getenv("KEEPALIVE_URL")
        if keepalive_url:
            # Optional: self-ping if an external uptime monitor isn't set yet
            start_self_ping(keepalive_url, int(os.getenv("KEEPALIVE_INTERVAL", "300")))
        logging.info("Keepalive HTTP server started. HEALTH: GET /health")
    except Exception:
        logging.exception("Failed to start keepalive server (non-fatal)")

    await init_db()

    bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    await set_bot_commands(bot)
    logging.info("Bot is starting polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped.")
