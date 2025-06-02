import os
import asyncio
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import nest_asyncio

nest_asyncio.apply()

BOT_TOKEN = '7854713596:AAGkcMu9WqryOwn--RtM62Ccayu0RsBZv7Y'

# === Пользовательские данные ===
user_name_map = {
    186142796: "Андрей",
    #338387117: "Анна"
}

# === Опросники ===
survey_configs = {
    "survey1": {
        "questions": {
            186142796: "Hi. Rate your condition, please?Привет, поставь оценку состояния, пожалуйста.",
            #338387117: "Hi. Rate your condition, please?"
        },
        "image_map": {
            186142796: 2,
            #338387117: 2
        },
        "image_paths": [
            "images/1.jpg",
            "images/2.jpg",
            "images/3.jpg"
        ],
        "excel_file": "responses_survey1.xlsx"
    },
    "survey2": {
        "questions": {
            186142796: "Rate your condition after session, pleaseПоставь оценку после нагрузки, пожалуйста",
            #338387117: "Rate your condition after session, please."
        },
        "image_map": {
            186142796: 2,
            #338387117: 2
        },
        "image_paths": [
            "images/4.jpg",
            "images/5.jpg",
            "images/6.jpg"
        ],
        "excel_file": "responses_survey2.xlsx"
    },
}

# === Вспомогательные переменные ===
responses = {
    "survey1": {},
    "survey2": {},

}

pending_reminders = {
    "survey1": {},
    "survey2": {},

}


# === Кнопки ===
def get_keyboard(survey_key: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(str(i), callback_data=f"{survey_key}|{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"{survey_key}|{i}") for i in range(6, 11)]
    ])



# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name or 'друг'}! Твой Telegram ID: {user.id}"
    )


def create_survey_handler(survey_key: str):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        config = survey_configs[survey_key]
        for uid in user_name_map:
            name = user_name_map[uid]
            question = config["questions"].get(uid, "Поставь оценку.")
            img_index = config["image_map"].get(uid, 1) - 1
            img_path = config["image_paths"][img_index]

            await context.bot.send_message(chat_id=uid, text=question)

            if os.path.exists(img_path):
                with open(img_path, 'rb') as img:
                    await context.bot.send_photo(chat_id=uid, photo=img)
            else:
                await context.bot.send_message(chat_id=uid, text="(Изображение не найдено)")

            await context.bot.send_message(
                chat_id=uid,
                text="Выбери от 1 до 10:",
                reply_markup=get_keyboard(survey_key)
            )


            if uid not in responses[survey_key]:
                task = asyncio.create_task(schedule_reminder(context, uid, survey_key))
                pending_reminders[survey_key][uid] = task

        await update.message.reply_text("Опрос отправлен.")
    return handler


async def schedule_reminder(context: ContextTypes.DEFAULT_TYPE, user_id: int, survey_key: str):
    await asyncio.sleep(180)
    if user_id not in responses[survey_key]:
        await context.bot.send_message(chat_id=user_id, text="Пожалуйста, не забудьте поставить оценку!")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    try:
        survey_key, score = data.split("|")
        score = int(score)
    except ValueError:
        await query.edit_message_text("Неверный формат ответа.")
        return

    if user_id in responses[survey_key]:
        await query.edit_message_text(text="Вы уже ответили.")
        return

    responses[survey_key][user_id] = score
    await query.edit_message_text(text=f"Спасибо! Вы поставили оценку {score}")

    if user_id in pending_reminders[survey_key]:
        pending_reminders[survey_key][user_id].cancel()
        del pending_reminders[survey_key][user_id]

    save_response_to_excel(
        survey_configs[survey_key]["excel_file"],
        user_name_map.get(user_id, str(user_id)),
        score
    )


# === Сохранение в Excel ===
def save_response_to_excel(filepath: str, name: str, score: int):
    try:
        if os.path.exists(filepath):
            df = pd.read_excel(filepath, index_col=0)
        else:
            df = pd.DataFrame(columns=["Оценка"])

        df.loc[name] = score
        df.sort_index(inplace=True)
        df.to_excel(filepath)
        print(f"✔️ Сохранили: {name} → {score}")
    except Exception as e:
        print(f"❌ Ошибка при записи в Excel: {e}")


# === Запуск ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("survey1", create_survey_handler("survey1")))
    app.add_handler(CommandHandler("survey2", create_survey_handler("survey2")))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Бот запущен.")
    await app.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        import sys
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.create_task(main())
        loop.run_forever()
