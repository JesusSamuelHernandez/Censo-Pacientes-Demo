"""Limitador de tasa compartido para endpoints públicos (sin autenticación).

Separado de app.main para que los routers puedan importar `limiter` sin crear
un import circular con la app FastAPI.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
