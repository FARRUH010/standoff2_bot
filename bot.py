import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
TOKEN = "8938746737:AAHQHn_fDWqOZ9wKPs6SQZ8Rg3wbVp4Vgv0"
ADMIN_ID = 5489027008
RATE_PER_GOLD = 0.12  # Курс: 1 Gold = 0.12 сомони

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СОСТОЯНИЯ (FSM) ---
class WithdrawState(StatesGroup):
    waiting_for_amount = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
    """)
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> float:
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 0.0))
        conn.commit()
        balance = 0.0
    else:
        balance = row[0]
    conn.close()
    return balance

def update_balance(user_id: int, amount: float):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", (user_id, amount, amount))
    conn.commit()
    conn.close()

# --- КЛАВИАТУРЫ ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👤 Мой кабинет"), KeyboardButton(text="💳 Пополнить Gold")],
        [KeyboardButton(text="🛒 Купить Gold"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

contact_admin_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📲 Отправить чек/скриншот админу", url="https://t.me/standoff2shop_tj_admin")]
    ]
)

# --- ОБРАБОТЧИКИ СООБЩЕНИЙ ---

@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    get_balance(message.from_user.id)
    await message.answer(
        f"👋 Салом, {message.from_user.first_name}!\n\n"
        f"Добро пожаловать в **Standoff2Shop_TJ** 🇹🇯\n"
        f"Здесь вы можете купить и мгновенно выводить **Gold** в Standoff 2!",
        reply_markup=main_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "👤 Мой кабинет")
async def profile_handler(message: types.Message, state: FSMContext):
    await state.clear()
    balance = get_balance(message.from_user.id)
    await message.answer(
        f"👤 **Ваш профиль:**\n\n"
        f"🆔 Ваш ID: `{message.from_user.id}`\n"
        f"💰 Ваш баланс: **{balance} G**",
        parse_mode="Markdown"
    )

@dp.message(F.text == "💳 Пополнить Gold")
async def deposit_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 Введите количество **Gold**, которое хотите приобрести (например, `100`):",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🛒 Купить Gold")
async def buy_handler(message: types.Message, state: FSMContext):
    balance = get_balance(message.from_user.id)
    if balance <= 0:
        await message.answer("❌ На вашем балансе недостаточно Gold! Сначала пополните счет.")
        return
    
    await state.set_state(WithdrawState.waiting_for_amount)
    await message.answer(
        f"🛒 **Вывод Gold**\n\n"
        f"Доступный баланс: **{balance} G**\n"
        f"Введите количество **Gold**, которое хотите вывести в игру:",
        parse_mode="Markdown"
    )

@dp.message(WithdrawState.waiting_for_amount)
async def process_withdrawal(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите корректное число.")
        return
    
    desired_gold = float(message.text)
    balance = get_balance(message.from_user.id)

    if desired_gold <= 0:
        await message.answer("Число должно быть больше 0.")
        return

    if desired_gold > balance:
        await message.answer(f"❌ У вас недостаточно Gold! Доступно: **{balance} G**.")
        return

    # Комиссия рынка Standoff 2 — 20%
    market_price = round(desired_gold / 0.8, 2)
    
    await state.clear()

    caption = (
        f"✨ Для получения голды выставьте на рынок **USP CORRODE** С НАКЛЕЙКОЙ за "
        f"**{market_price}G**, чтобы вам пришло **{desired_gold}G** - это количество голды, "
        f"которое вы хотите вывести (комиссия рынка на мне).\n\n"
        f"📝 Далее нажмите на «Только мои запросы», сделайте скриншот и отправьте в бота / админу.\n\n"
        f"❗️ Пожалуйста, не меняйте аватарку и цену скина, пока выводится голда."
    )

    PHOTO_URL = "https://raw.githubusercontent.com/FARRUH010/standoff2_bot/main/guide.jpg"
    
    try:
        await message.answer_photo(
            photo=PHOTO_URL,
            caption=caption,
            reply_markup=contact_admin_kb,
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer(
            caption,
            reply_markup=contact_admin_kb,
            parse_mode="Markdown"
        )

@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "ℹ️ **Служба поддержки**\n\n"
        "По всем вопросам оплаты, пополнения и получения Gold обращайтесь к администратору:",
        reply_markup=contact_admin_kb,
        parse_mode="Markdown"
    )

@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def process_amount(message: types.Message):
    gold = int(message.text)
    if gold <= 0:
        await message.answer("Пожалуйста, введите число больше 0.")
        return
    
    price_somoni = round(gold * RATE_PER_GOLD, 2)
    await message.answer(
        f"💳 **СЧЕТ НА ОПЛАТУ**\n\n"
        f"⚙️ Вы получаете: **{gold} G**\n"
        f"💵 К оплате: **{price_somoni} TJS**\n\n"
        f"Оплатите указанную сумму по реквизитам и отправьте чек администратору для зачисления:",
        reply_markup=contact_admin_kb,
        parse_mode="Markdown"
    )

@dp.message(Command("pay"))
async def pay_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        args = message.text.split()
        target_id = int(args[1])
        gold_amount = float(args[2])

        update_balance(target_id, gold_amount)
        await message.answer(
            f"✅ Пользователю `{target_id}` начислено **{gold_amount} G**.",
            parse_mode="Markdown"
        )
        await bot.send_message(
            target_id, 
            f"🎉 Ваш баланс пополнен на **{gold_amount} G**!", 
            parse_mode="Markdown"
        )
    except Exception:
        await message.answer(
            "Ошибка! Формат: `/pay <ID> <количество_голды>`\nПример: `/pay 123456789 500`",
            parse_mode="Markdown"
        )

# --- ЗАПУСК ---
async def main():
    init_db()
    print("Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
