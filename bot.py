import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from agent import run_agent


TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 ¡Hola! Escribe /receta para obtener una recomendación.")


async def receta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🍳 Pensando qué puedes cocinar hoy...")

    try:
        result = run_agent()
        await update.message.reply_text(result)

    except Exception as e:
        await update.message.reply_text("❌ Error al generar la receta")
        print(e)


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("receta", receta))

    print("🤖 Bot de Telegram en ejecución...")
    app.run_polling()


if __name__ == "__main__":
    main()
