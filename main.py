import os
import json
import base64
import threading
import time
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_HORARIA = ZoneInfo("America/Mexico_City")

import gspread
from google.oauth2.service_account import Credentials

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    TypeHandler,
    filters
)

# =========================================
# PERMISOS DE USUARIOS
# =========================================

usuarios_texto = os.getenv("USUARIOS_AUTORIZADOS", "")

USUARIOS_AUTORIZADOS = {
    int(usuario.strip())
    for usuario in usuarios_texto.split(",")
    if usuario.strip()
}

print(f"Usuarios autorizados cargados: {len(USUARIOS_AUTORIZADOS)}")

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
# AUTO-PING PARA EVITAR QUE RENDER SE DUERMA
# ==========================================

def mantener_despierto():
    """Hace una petición HTTP a sí mismo y avisa por Telegram."""
    url_render = os.getenv("RENDER_EXTERNAL_URL")
    token = os.getenv("TOKEN_TELEGRAM")
    
    if not url_render or not token or not USUARIOS_AUTORIZADOS:
        return
    
    admin_id = list(USUARIOS_AUTORIZADOS)[0]
    
    while True:
        try:
            # Recuerda que esto está en 30 para tus pruebas, luego cámbialo a 600
            time.sleep(30)  
            
            # 1. Hace el auto-ping a Render
            req = urllib.request.Request(
                url_render,
                headers={"User-Agent": "AutoPing-KeepAlive"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                estado = response.status
                
                # 2. Si quieres que te avise en el chat cada vez que hace ping con éxito:
                # (Nota: Si lo dejas en 30 segundos, te llegará un mensaje cada 30 segundos).
                mensaje_telegram = f"🔄 Auto-ping exitoso (Estado: {estado})"
                enviar_aviso_telegram(token, admin_id, mensaje_telegram)
                
        except Exception as e:
            # Si hay un error (por ejemplo, si se está despertando), te avisa al chat
            mensaje_error = f"⚠️ Aviso de ping / Despertando: {e}"
            enviar_aviso_telegram(token, admin_id, mensaje_error)

def enviar_aviso_telegram(token, chat_id, texto):
    """Función auxiliar para mandar mensajes desde el hilo secundario."""
    try:
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": texto}).encode("utf-8")
        req = urllib.request.Request(api_url, data=data, method="POST")
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"No se pudo enviar el aviso de Telegram: {e}")

# ==========================================
# NOTIFICACIÓN DE INICIO (DESPERTAR)
# ==========================================

async def notificar_despertar(application: Application):
    """Se ejecuta automáticamente cuando el bot se enciende/despierta."""
    if USUARIOS_AUTORIZADOS:
        # Toma el primer usuario autorizado de la lista para enviarle la alerta
        admin_id = list(USUARIOS_AUTORIZADOS)[0]
        try:
            await application.bot.send_message(
                chat_id=admin_id,
                text="🟢 **¡El bot se ha despertado y está en línea!**\n\nListo para recibir operaciones."
            )
            print("Notificación de encendido enviada con éxito.")
        except Exception as e:
            print(f"No se pudo enviar la notificación de inicio: {e}")

# ==========================================
# FUNCION QUE COMPRUEBA LOS PERMISOS
# ==========================================

async def controlar_acceso(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user

    if usuario and usuario.id not in USUARIOS_AUTORIZADOS:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔ No tienes autorización para utilizar MiaguaBot."
            )

        from telegram.ext import ApplicationHandlerStop
        raise ApplicationHandlerStop

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
# * CONSULTAR VENTAS
# ==========================================


async def consultar_ventas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message

    # Obtener todas las ventas de Google Sheets
    registros = hoja.get_all_records()

    if not registros:
        await mensaje.reply_text(
            "Todavía no hay ventas registradas."
        )
        return

    # Seleccionar las últimas 10 ventas
    ultimas_ventas = registros[-10:]
    ultimas_ventas.reverse()

    respuesta = "📋 ÚLTIMAS VENTAS\n\n"

    for venta in ultimas_ventas:
        fecha = venta.get("Fecha", "Sin fecha")
        cliente = venta.get("Cliente", "Sin cliente")
        garrafones = venta.get("Garrafones", 0)
        total = venta.get("Total", 0)

        respuesta += (
            f"📅 Fecha: {fecha}\n"
            f"👤 Cliente: {cliente}\n"
            f"💧 Garrafones: {garrafones}\n"
            f"💰 Total: ${total}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await mensaje.reply_text(respuesta)

# ==========================================
# * Corte del Día
# ==========================================

async def corte_del_dia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message

    # Obtener las ventas registradas
    registros = hoja.get_all_records()

    # Fecha actual del servidor
    hoy = datetime.now(ZONA_HORARIA).date()

    ventas_hoy = []

    for venta in registros:
        fecha_texto = str(venta.get("Fecha", "")).strip()

        try:
            fecha_venta = datetime.strptime(
                fecha_texto,
                "%d/%m/%Y %H:%M:%S"
            ).date()
        except ValueError:
            continue

        if fecha_venta == hoy:
            ventas_hoy.append(venta)

    # Si no hubo ventas hoy
    if not ventas_hoy:
        await mensaje.reply_text(
            "📊 CORTE DEL DÍA\n\n"
            f"Fecha: {hoy.strftime('%d/%m/%Y')}\n\n"
            "No hay ventas registradas durante el día de hoy."
        )
        return

    # Calcular totales
    cantidad_ventas = len(ventas_hoy)
    total_garrafones = sum(
        int(venta.get("Garrafones", 0) or 0)
        for venta in ventas_hoy
    )
    total_dinero = sum(
        float(venta.get("Total", 0) or 0)
        for venta in ventas_hoy
    )

    # Mostrar resultados
    await mensaje.reply_text(
        "📊 CORTE DEL DÍA\n\n"
        f"📅 Fecha: {hoy.strftime('%d/%m/%Y')}\n"
        f"🧾 Ventas realizadas: {cantidad_ventas}\n"
        f"💧 Garrafones vendidos: {total_garrafones}\n"
        f"💰 Total vendido: ${total_dinero:,.2f}"
    )

# ==========================================
# * Clientes
# ==========================================

async def consultar_clientes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message

    # Obtener las ventas registradas en Google Sheets
    registros = hoja.get_all_records()

    if not registros:
        await mensaje.reply_text(
            "Todavía no hay clientes registrados."
        )
        return

    # Obtener los nombres sin repetirlos
    clientes = set()

    for venta in registros:
        nombre = str(venta.get("Cliente", "")).strip()

        if nombre:
            clientes.add(nombre)

    if not clientes:
        await mensaje.reply_text(
            "Todavía no hay clientes registrados."
        )
        return

    # Ordenar los nombres alfabéticamente
    clientes_ordenados = sorted(
        clientes,
        key=str.casefold
    )

    respuesta = (
        f"👥 CLIENTES REGISTRADOS\n\n"
        f"Total de clientes: {len(clientes_ordenados)}\n\n"
    )

    for numero, nombre in enumerate(clientes_ordenados, start=1):
        respuesta += f"{numero}. {nombre}\n"

    await mensaje.reply_text(respuesta)

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
            datetime.now(ZONA_HORARIA).strftime("%d/%m/%Y %H:%M:%S"),
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

    # Selección de Consultar Ventas    
    if texto == "Consultar Ventas":
        await consultar_ventas(update, context)
        return

    if texto == "Corte del Día":
        await corte_del_dia(update, context)
        return

    if texto == "Clientes":
        await consultar_clientes(update, context)
        return

# ==========================================
# 6. INICIALIZACIÓN DEL BOT
# ==========================================

def main():
    # Lanzar el hilo de auto-ping en segundo plano
    hilo_ping = threading.Thread(target=mantener_despierto, daemon=True)
    hilo_ping.start()
    print("Hilo de auto-ping iniciado correctamente.")

    application = (
        Application.builder()
        .token(TOKEN_TELEGRAM)
        .post_init(notificar_despertar)
        .build()
    )

    application.add_handler(
    TypeHandler(Update, controlar_acceso),
    group=-1
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