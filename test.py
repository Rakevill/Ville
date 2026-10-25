from config import Config
from commands import CommandRegistry
r = CommandRegistry(Config.load())
print(r.execute('/calc 2+2'))
print(r.execute('/openset \"C:\\Temp\" temp'))
print(r.execute('/openlist'))
print(r.execute('/opendel temp'))