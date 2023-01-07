from decouple import config

# Database
DATABASE_URI = config("DATABASE_URI")
DATABASE_NAME = config("DATABASE_NAME")
REDIS_URL = config("REDIS_URL")

# Tokens
DBL_TOKEN = config("DBL_TOKEN", default=None)
KOFI_TOKEN = config("KOFI_TOKEN", default=None)

# Discord OAUTH
CLIENT_ID = config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")
ALGORITHM = config("ALGORITHM")
REDIRECT_URL = config("REDIRECT_URL")
SECRET = config("SECRET")
