import gspread
from google.oauth2.service_account import Credentials

credenciales = Credentials.from_service_account_file(
    "miaguabottele-5937ab6909da.json",
    scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
)

cliente = gspread.authorize(credenciales)

hoja = cliente.open("Miagua - Registro de Ventas").worksheet("Ventas")

print("Conexión exitosa")

hoja.append_row([1, "08/10/2026", "Cliente Prueba", 3, 45])