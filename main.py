import telebot
from telebot import types
import mysql.connector

bot = telebot.TeleBot("8849822777:AAHmsM5lCkXzY-5roWkTl2HGIvRj0phKRVY")

esperando_venta = set()

conexion = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Reyes41879!123",
    database="miagua"
)



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

    cursor = conexion.cursor()

    sql = """
    INSERT INTO ventas (num_garrafones, cliente, total)
    VALUES (%s, %s, %s)
    """

    valores = (cantidad, cliente, total)

    cursor.execute(sql, valores)

    conexion.commit()

    cursor.close()

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
