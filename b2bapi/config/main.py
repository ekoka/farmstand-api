import os

from ..utils import mailer

from .utils import env, get_upper_keys

# path configs currently not used
CONFIG_PATH = os.path.dirname(os.path.realpath(__file__))
APP_PATH = os.path.dirname(CONFIG_PATH)
PROJECT_PATH = os.path.dirname(APP_PATH)
DATA_FILES = os.path.join(APP_PATH, 'data')

ALLOWED_ORIGINS_REGEX = env.string('ALLOWED_ORIGINS_REGEX')

THUMBOR_SERVER = env.string('THUMBOR_SERVER')
MAIL_PROVIDER = env.string('MAIL_PROVIDER')
MAILER = mailer.select(MAIL_PROVIDER)

# I18N and L10N
LOCALES = env.json('LOCALES')
LOCALE = env.string('LOCALE')                   #'fr_CA.UTF-8'
DEFAULT_LANG = env.string('DEFAULT_LANG')       #'en'
AVAILABLE_LANGS = env.json('AVAILABLE_LANGS')   # ['en', 'fr']

#BABEL_DOMAIN = 'messages'
#BABEL_TRANSLATION_DIRECTORIES = 'translations'

# TODO: put in environment
API_NAMESPACE = 'producelist'
API_DOC_URL = 'http://api.producelist.dev:8989/doc/{rel}'

# logging: start with slash for absolute path, otherwise it's relative to
# the project
LOGGING_PATH = env.string('LOGGING_PATH')

# static files
STATIC_PATH = env.string('STATIC_PATH') #'static'

IMAGE = env.json('IMAGE')

PASSCODE_SIGNIN_URL = env.string('PASSCODE_SIGNIN_URL')
ACCOUNT_CONFIRMATION_URL = env.string('ACCOUNT_CONFIRMATION_URL')
SQLALCHEMY_ECHO = env.boolean('SQLALCHEMY_ECHO')
SQLALCHEMY_TRACK_MODIFICATIONS = env.boolean('SQLALCHEMY_TRACK_MODIFICATIONS')
SQLALCHEMY_COMMIT_ON_TEARDOWN = env.boolean('SQLALCHEMY_COMMIT_ON_TEARDOWN')
# SQL ALCHEMY PROFILER
ENABLE_SQL_PROFILE_LOG = env.boolean('ENABLE_SQL_PROFILE_LOG')
FORCE_DROP_DB_SCHEMA = env.boolean('FORCE_DROP_DB_SCHEMA')
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://{user}:{password}@{host}/{dbname}".format(
    dialect='postgresql', user=env.string('DB_USER'),
    password=env.string('DB_PASSWORD'), host=env.string('DB_HOST'),
    dbname=env.string('DB_NAME'))
COMMON_WORDS_FILE = os.path.join(DATA_FILES, 'common_words.json')
RESERVED_WORDS_FILE = os.path.join(DATA_FILES, 'reserved_words.json')

# Flask development server's config
FLASK_HTTP_HOST = env.string('FLASK_HTTP_HOST') #'api.producelist.local'
FLASK_HTTP_PORT = env.num('FLASK_HTTP_PORT')    #8989

INIT_CALLBACKS = env.json('INIT_CALLBACKS')

SERVER_DOMAIN = env.string('SERVER_DOMAIN')

# used in root resources
API_HOST = env.string('API_HOST')
SUBDOMAIN_HOST_TEMPLATE = env.string('SUBDOMAIN_HOST_TEMPLATE')#'http://{domain}.producelist.local:8082 '
ACCOUNT_HOST = env.string('ACCOUNT_HOST') #'http://producelist.local:8081'

DEV_MODE = env.boolean('DEV_MODE')
DEBUG = env.boolean('DEBUG')
TESTING = env.boolean('TESTING')
DEMO = env.boolean('DEMO')

__all__ = get_upper_keys(locals().keys())
