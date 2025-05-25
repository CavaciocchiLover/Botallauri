#!/usr/bin/env python
import logging
import json
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)
import datetime
from calendar import monthrange

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

START_ROUTES, END_ROUTES = range(2)

mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno", "", "", "Settembre", "Ottobre", "Novembre",
        "Dicembre"]
giorni = ["lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato"]

jsonA = {}
jsonB = {}
settimaneA = {}
settimaneB = {}
try:
    with open("orario_A.json") as f:
        jsonA = json.load(f)
    with open("orario_B.json") as f:
        jsonB = json.load(f)
    with open("settimane_A.json") as f:
        settimaneA = json.load(f)
    with open("settimane_B.json") as f:
        settimaneB = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError("non ho trovato i file.json necessari")


async def cerca(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.split(" ")
    if not (len(message) == 2 and len(message[1]) == 5):
        await update.message.reply_text("Devi scrivere la classe così /cerca 1CINF")
    else:
        oggi = datetime.datetime.now()
        if oggi.weekday() == 6:
            oggi = oggi + datetime.timedelta(days=1)

        monday = oggi.day if oggi.weekday() == 0 else (oggi - datetime.timedelta(days=oggi.weekday())).day
        sunday = oggi.day if oggi.weekday() == 5 else (oggi + datetime.timedelta(days=5 - oggi.weekday())).day

        await mandoElenco(update=update, mese=mesi[oggi.month - 1], periodo=str(monday) + "-" + str(sunday),
                          giorno=giorni[oggi.weekday()], classe=message[1], giornoSpecifico=False, context=context)


async def mandoElenco(update: Update, mese: str, periodo: str, giorno: str, classe: str, giornoSpecifico: bool, context: ContextTypes.DEFAULT_TYPE) -> None:
    sezione = {}
    try:
        vacanza = False
        if "1" in classe and "LIC" not in classe:
            if settimaneB[mese][periodo] == "B":
                sezione = jsonB[classe][giorno]
            elif settimaneB[mese][periodo] == "N/A":
                vacanza = True
            else:
                sezione = jsonA[classe][giorno]
        else:
            if settimaneA[mese][periodo] == "B":
                sezione = jsonB[classe][giorno]
            elif settimaneA[mese][periodo] == "N/A":
                vacanza = True
            else:
                sezione = jsonA[classe][giorno]

        if vacanza:
            await update.message.reply_text("Oggi la scuola non è aperta")
        else:
            if giornoSpecifico:
                for i in range(0, 6):
                    await context.bot.send_message(
                        chat_id=update.callback_query.message.chat.id,
                        text=
                        "Materia: \"" + sezione["materie"][i] + "\" - Professorə: \"" + sezione["professori"][
                            i] + "\" - Aula: \"" + sezione["aule"][i] + "\"")
            else:
                for i in range(0, 6):
                    await update.message.reply_text(
                        "Materia: \"" + sezione["materie"][i] + "\" - Professorə: \"" + sezione["professori"][
                            i] + "\" - Aula: \"" + sezione["aule"][i] + "\"")
    except KeyError:
        if giornoSpecifico:
            await update.callback_query.edit_message_text(text="Classe non trovata")
        else:
            await update.message.reply_text("Classe non trovata")


async def domani(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message.text.split(" ")
    if not (len(message) == 2 and len(message[1]) == 5):
        await update.message.reply_text("Devi scrivere la classe così /domani 1CINF")
    else:
        oggi = datetime.datetime.now()

        if oggi.weekday() == 5:
            oggi = oggi + datetime.timedelta(days=2)
        else:
            oggi = oggi - datetime.timedelta(days=1)

        monday = oggi.day if oggi.weekday() == 0 else (oggi - datetime.timedelta(days=oggi.weekday())).day
        sunday = oggi.day if oggi.weekday() == 5 else (oggi + datetime.timedelta(days=5 - oggi.weekday())).day

        await mandoElenco(update=update, mese=mesi[oggi.month - 1], periodo=str(monday) + "-" + str(sunday),
                          giorno=giorni[oggi.weekday()], classe=message[1], giornoSpecifico=False, context=context)


async def giornospecifo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.message.text.split(" ")
    if not (len(message) == 2 and len(message[1]) == 5):
        await update.message.reply_text("Devi scrivere la classe così /giornospecifico 1CINF")
        return 0
    else:
        keyboard = [[]]
        k = 0
        mese = datetime.datetime.today().month
        ultimo_n_mese = monthrange(2025, mese)[1]
        for i in range(ultimo_n_mese):
            if i % 3 == 0:
                keyboard.append(
                    [InlineKeyboardButton(str(i + 1), callback_data=message[1] + "|" + str(i + 1) + "|" + str(mese))])
                k = k + 1
            else:
                keyboard[k].append(
                    InlineKeyboardButton(str(i + 1), callback_data=message[1] + "|" + str(i + 1) + "|" + str(mese)))
        if ultimo_n_mese == 30:
            keyboard.append(
                [InlineKeyboardButton("Mese prima", callback_data=message[1] + "|" + str(mese) + "|" + "prima")])
            k = k + 1
            keyboard[k].append(
                InlineKeyboardButton("Mese dopo", callback_data=message[1] + "|" + str(mese) + "|" + "dopo"))
        else:
            keyboard[k].append(
                InlineKeyboardButton("Mese prima", callback_data=message[1] + "|" + str(mese) + "|" + "prima"))
            keyboard[k].append(
                InlineKeyboardButton("Mese dopo", callback_data=message[1] + "|" + str(mese) + "|" + "dopo"))
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Scegli un giorno", reply_markup=reply_markup)
        return START_ROUTES


async def giorno(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    dati = query.data.split("|")
    await query.answer()
    data = datetime.datetime.strptime(dati[1] + "/" + dati[2] + "/" + str(2025) if int(dati[2]) <= 6 else str(2024),
                                      "%d/%m/%Y")
    if data.weekday() == 6:
        data = data + datetime.timedelta(days=1)
    monday = data.day if data.weekday() == 0 else (data - datetime.timedelta(days=data.weekday())).day
    sunday = data.day if data.weekday() == 5 else (data + datetime.timedelta(days=5 - data.weekday())).day


    await mandoElenco(update=update, mese=mesi[data.month - 1], periodo=str(monday) + "-" + str(sunday),
                      giorno=giorni[data.weekday()], classe=dati[0], giornoSpecifico=True, context=context)
    return END_ROUTES


async def cambio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    dati = query.data.split("|")
    await query.answer()

    keyboard = [[]]
    k = 0
    mese = int(dati[1])
    if dati[2] == "prima":
        if mese == 1:
            mese = 12
        else:
            mese = mese - 1
    else:
        if mese == 12:
            mese = 1
        else:
            mese = mese + 1
    ultimo_n_mese = monthrange(2025, mese)[1]
    for i in range(ultimo_n_mese):
        if i % 3 == 0:
            keyboard.append(
                [InlineKeyboardButton(str(i + 1), callback_data=dati[0] + "|" + str(i + 1) + "|" + str(mese))])
            k = k + 1
        else:
            keyboard[k].append(
                InlineKeyboardButton(str(i + 1), callback_data=dati[0] + "|" + str(i + 1) + "|" + str(mese)))
    if ultimo_n_mese == 30:
        keyboard.append(
            [InlineKeyboardButton("Mese prima", callback_data=dati[0] + "|" + str(mese) + "|" + "prima")])
        k = k + 1
        keyboard[k].append(
            InlineKeyboardButton("Mese dopo", callback_data=dati[0] + "|" + str(mese) + "|" + "dopo"))
    else:
        keyboard[k].append(
            InlineKeyboardButton("Mese prima", callback_data=dati[0] + "|" + str(mese) + "|" + "prima"))
        keyboard[k].append(
            InlineKeyboardButton("Mese dopo", callback_data=dati[0] + "|" + str(mese) + "|" + "dopo"))
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="Scegli un giorno", reply_markup=reply_markup
    )
    return START_ROUTES

async def fine(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return ConversationHandler.END

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if token is None:
        print("BOT_TOKEN environment variable not set")
    else:
        application = Application.builder().token(token).build()
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("giornospecifico", giornospecifo)],
            states={
                START_ROUTES: [
                    CallbackQueryHandler(giorno, pattern=r"^(\w{5})\|[0-9]{1,2}\|[0-9]{1,2}"),
                    CallbackQueryHandler(cambio, pattern=r"^(\w{5})\|[0-9]{1,2}\|[a-z]{4,5}"),

                ],
                END_ROUTES: [
                    CallbackQueryHandler(fine)
                ],
            },
            fallbacks=[CommandHandler("giornospecifico", giornospecifo)]
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("cerca", cerca))
        application.add_handler(CommandHandler("domani", domani))

        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
