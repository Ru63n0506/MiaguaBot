
import os
import json
import base64
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# ==========================================
# 1. CREDENCIALES DE GOOGLE SHEETS
# ==========================================

contenido = os.getenv("GOOGLE_CREDENTIALS_BASE64")

if not contenido:
    raise RuntimeError(
        "Falta configurar GOOGLE_CREDENTIALS_BASE64 en Render."
    )

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

cliente_sheets = gspread.authorize(credenciales)

hoja = cliente_sheets.open(
    "Miagua - Registro de Ventas"
).worksheet("Ventas")


# ==========================================
# 2. CONFIGURACIÓN DEL BOT
# ==========================================

TOKEN_TELEGRAM = os.getenv("TOKEN_TELEGRAM")

if not TOKEN_TELEGRAM:
    raise RuntimeError(
        "Falta configurar TOKEN_TELEGRAM en Render."
    )

URL_RENDER = os.getenv("RENDER_EXTERNAL_URL")

if not URL_RENDER:
    raise RuntimeError(
        "No se encontró RENDER_EXTERNAL_URL en Render."
    )

PUERTO = int(os.getenv("PORT", "10000"))


# ==========================================
# 3. COMANDO /start Y /help
# ==========================================

async def send_welcome(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    teclado = [
        ["Registrar Venta", "Consultar Ventas"],
        ["Corte del Día", "Clientes"]
    ]

    menu = ReplyKeyboardMarkup(
        teclado,
        resize_keyboard=True
    )

    await update.effective_message.reply_text(
        "Bienvenido al bot de Miagua\n\n"
        "¿Qué deseas hacer?",
        reply_markup=menu
    )


# ==========================================
# 4. COMANDO /hola
# ==========================================

async def send_hola(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.effective_message.reply_text(
        "¡Hola! ¿Cómo estás?"
    )


# ==========================================
# 5. PROCESAMIENTO DE MENSAJES
# ==========================================

async def manejar_texto(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    mensaje = update.effective_message
    texto = mensaje.text.strip()

    # Si el usuario está registrando una venta
    if context.user_data.get("esperando_venta"):

        datos = texto.split(maxsplit=2)

        if len(datos) != 3:
            await mensaje.reply_text(
                "Formato incorrecto.\n\n"
                "Escribe:\n"
                "Garrafones Cliente Total\n\n"
                "Ejemplo:\n"
                "5 Juan Pérez 100"
            )
            return

        cantidad_texto = datos[0]
        nombre_cliente = datos[1]
        total_texto = datos[2]

        try:
            cantidad = int(cantidad_texto)
            total = float(total_texto)

            if cantidad <= 0 or total < 0:
                raise ValueError

        except ValueError:
            await mensaje.reply_text(
                "La cantidad debe ser un entero positivo "
                "y el total debe ser un número válido.\n\n"
                "Ejemplo:\n"
                "5 Juan Pérez 100"
            )
            return

        # Guardar la venta en Google Sheets
        hoja.append_row([
            "",
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            nombre_cliente,
            cantidad,
            total
        ])

        context.user_data["esperando_venta"] = False

        await mensaje.reply_text(
            "¡Venta registrada!\n\n"
            f"Garrafones: {cantidad}\n"
            f"Cliente: {nombre_cliente}\n"
            f"Total: ${total:.2f}"
        )

        return

    # Selección de Registrar Venta
    if texto == "Registrar Venta":

        context.user_data["esperando_venta"] = True

        await mensaje.reply_text(
            "Nueva Venta\n\n"
            "Escribe los datos en este formato:\n\n"
            "Garrafones Cliente Total\n\n"
            "Ejemplo:\n"
            "5 Juan Pérez 100"
        )

        return

    # Opciones pendientes de implementar
    if texto in [
        "Consultar Ventas",
        "Corte del Día",
        "Clientes"
    ]:

        await mensaje.reply_text(
            "Esta opción todavía está en desarrollo."
        )


# ==========================================
# 6. INICIALIZACIÓN DEL BOT
# ==========================================

def main():

    application = (
        Application.builder()
        .token(TOKEN_TELEGRAM)
        .build()
    )

    application.add_handler(
        CommandHandler(
            ["start", "help"],
            send_welcome
        )
    )

    application.add_handler(
        CommandHandler(
            "hola",
            send_hola
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            manejar_texto
        )
    )

    print("MiaguaBot iniciado con webhooks")

    # Render recibe las actualizaciones mediante HTTPS
    application.run_webhook(
        listen="0.0.0.0",
        port=PUERTO,
        url_path="telegram",
        webhook_url=f"{URL_RENDER.rstrip('/')}/telegram",
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()