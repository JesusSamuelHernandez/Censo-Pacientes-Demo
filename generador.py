import random
import string

def generar_password():
    caracteres = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(caracteres) for _ in range(8))

print(generar_password())