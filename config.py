from decouple import config

# Database
DATABASE_URI = config("DATABASE_URI")
DATABASE_NAME = config("DATABASE_NAME")
REDIS_URL = config("REDIS_URL")

DBL_TOKEN = config("DBL_TOKEN", default=None)
