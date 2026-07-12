import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from datetime import datetime, timedelta
import re

# ====== НАСТРОЙКИ ======
BOT_TOKEN = "8874942259:AAFr1tjVSHMGIRKZT9ZV7oJ2gsAfdi0vIVs"
CHANNEL_ID = "@morich_z"  # или числовой ID (-100...)
DEFAULT_DELAY_MINUTES = 120  # время до замены (можно менять командой)
TEMPLATE_TEXT = "💁 Задание закончилось! Дождитесь нового поста, чтобы откликнуться Не успеваете брать задания? Включите уведомления и получайте их первыми!"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище задач на замену
scheduled_tasks = {}

async def replace_message_later(chat_id, message_id, delay_seconds, new_text):
    """Заменяет текст сообщения через указанное время"""
    await asyncio.sleep(delay_seconds)
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=new_text
        )
        print(f"[✅] Сообщение {message_id} заменено на шаблон")
    except Exception as e:
        print(f"[❌] Ошибка замены: {e}")

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "📢 Как работать:\n"
        "1. Отправьте текст для публикации\n"
        "2. Бот опубликует его в канале\n"
        "3. Через заданное время заменит на шаблон\n\n"
        "Команды:\n"
        "/settime 15 — установить задержку (минут)\n"
        "/template Текст — установить шаблон\n"
        "/cancel — отменить последнюю задачу"
    )

@dp.message(Command("settime"))
async def set_time(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("❌ Используйте: /settime 15")
        return
    global DEFAULT_DELAY_MINUTES
    DEFAULT_DELAY_MINUTES = int(args[1])
    await message.answer(f"⏱ Задержка установлена: {DEFAULT_DELAY_MINUTES} мин.")

@dp.message(Command("template"))
async def set_template(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Укажите текст шаблона")
        return
    global TEMPLATE_TEXT
    TEMPLATE_TEXT = args[1]
    await message.answer(f"✅ Шаблон обновлён:\n{TEMPLATE_TEXT}")

@dp.message(Command("cancel"))
async def cancel_last(message: Message):
    user_id = message.from_user.id
    if user_id in scheduled_tasks:
        scheduled_tasks[user_id].cancel()
        del scheduled_tasks[user_id]
        await message.answer("❌ Последняя задача отменена")
    else:
        await message.answer("Нет активных задач")

@dp.message()
async def publish_and_schedule(message: Message):
    # Игнорируем команды
    if message.text and message.text.startswith("/"):
        return
    
    user_id = message.from_user.id
    text_to_publish = message.text

    # 1. Публикуем в канал
    try:
        sent = await bot.send_message(
            chat_id=CHANNEL_ID,
            text=text_to_publish
        )
        await message.answer(f"✅ Опубликовано в канале!\nID: {sent.message_id}")
    except Exception as e:
        await message.answer(f"❌ Ошибка публикации: {e}\nПроверьте, что бот — админ канала.")
        return

    # 2. Отменяем старую задачу пользователя, если есть
    if user_id in scheduled_tasks:
        scheduled_tasks[user_id].cancel()

    # 3. Создаём новую задачу на замену
    delay = DEFAULT_DELAY_MINUTES * 60
    task = asyncio.create_task(
        replace_message_later(
            CHANNEL_ID,
            sent.message_id,
            delay,
            TEMPLATE_TEXT
        )
    )
    scheduled_tasks[user_id] = task

    # Вычисляем время замены
    replace_time = datetime.now() + timedelta(minutes=DEFAULT_DELAY_MINUTES)
    await message.answer(
        f"⏳ Замена через {DEFAULT_DELAY_MINUTES} мин.\n"
        f"⏰ Примерно: {replace_time.strftime('%H:%M:%S')}"
    )

async def main():
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())