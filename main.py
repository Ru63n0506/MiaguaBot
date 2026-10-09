import telebot
from telebot import types
from datetime import datetime

import os
import json
import base64

import gspread
from google.oauth2.service_account import Credentials

if os.getenv("GOOGLE_CREDENTIALS_BASE64"):
    contenido = os.getenv("GOOGLE_CREDENTIALS_BASE64")

    datos_credenciales = json.loads(
        base64.b64decode(contenido).decode("utf-8")
    )

    credenciales = Credentials.from_service_account_info(
        datos_credenciales,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

else:
    credenciales = Credentials.from_service_account_file(
        "miaguabottele-5937ab6909da.json",
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
    )

cliente = gspread.authorize(credenciales)

hoja = cliente.open("Miagua - Registro de Ventas").worksheet("Ventas")

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")

bot = telebot.TeleBot(TOKEN_TELEGRAM)

esperando_venta = set()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):

    teclado = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    btnVenta = types.KeyboardButton('Registrar Venta')
    btnVentas = types.KeyboardButton('Consultar Ventas')
    btnCorte = types.KeyboardButton('Corte del Día')
    btnClientes = types.KeyboardButton('Clientes')

    teclado.add(btnVenta, btnVentas, btnCorte, btnClientes)

    bot.send_message(
        message.chat.id,
        "Bienvenido al bot de Miagua\n\n¿Qué deseas hacer?",
        reply_markup=teclado
    )

@bot.message_handler(func=lambda message: message.text == 'Registrar Venta')
def registrar_venta(message):

    esperando_venta.add(message.chat.id)

    bot.reply_to(
        message,
        "Nueva Venta\n\n"
        "Escribe los datos de la venta en este formato:\n\n"
        "#Garrafones Cliente Total\n\n"
        "Ejemplo:\n"
        "5 Juan 100"
    )

@bot.message_handler(func=lambda message: message.chat.id in esperando_venta)
def recibir_venta(message):

    datos = message.text.split()

    if len(datos) != 3:
        bot.reply_to(
            message,
            "Formato incorrecto.\n\n"
            "Usa:\n"
            "#Garrafones Cliente Total\n\n"
            "Ejemplo:\n"
            "5 Juan 100"
        )
        return

    cantidad = datos[0].strip()
    cliente = datos[1].strip()
    total = datos[2].strip()

    hoja.append_row([
    "", 
    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    cliente,
    int(cantidad),
    float(total)
    ])

    esperando_venta.remove(message.chat.id)

    bot.reply_to(
        message,
        f"Venta registrada:\n\n"
        f"Garrafones: {cantidad}\n"
        f"Cliente: {cliente}\n"
        f"Total: {total}"
    )

@bot.message_handler(commands=['hola'])
def send_hola(message):
    bot.reply_to(message, "¡Hola! ¿Cómo estás?")

bot.infinity_polling()
