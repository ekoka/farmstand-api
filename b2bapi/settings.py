import os
import locale
from collections import namedtuple
import logging
from .config import secrets
from .config import config 
import stripe

SECRET_KEY = secrets.SECRET_KEY
SESSION_COOKIE_SECURE = True
REMEMBER_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = False
REMEMBER_COOKIE_HTTPONLY = False

ALLOWED_ORIGINS_REGEX = config.ALLOWED_ORIGINS_REGEX

# ------------------------- #
# I18N and L10N

stripe.api_key = secrets.STRIPE_KEY
UPDATE_FROM_STRIPE = config.UPDATE_FROM_STRIPE

LOCALES = config.LOCALES
LOCALE = config.LOCALE
locale.setlocale(locale.LC_ALL, LOCALE)

DEFAULT_LANG = config.DEFAULT_LANG
AVAILABLE_LANGS = config.AVAILABLE_LANGS

#BABEL_DOMAIN = 'messages'
BABEL_TRANSLATION_DIRECTORIES = config.BABEL_TRANSLATION_DIRECTORIES

# ------------------------- #

PROJECT_NAME = 'productlist'
# PATHS
SETTINGS_PATH = os.path.realpath(__file__)
APP_PATH = os.path.dirname(SETTINGS_PATH)
PROJECT_PATH = os.path.dirname(APP_PATH)

# logging
LOGGING_PATH = os.path.join(PROJECT_PATH, config.LOGGING_PATH)
#fh = logging.FileHandler(LOGGING_PATH)
#LOGGER = logging.getLogger('mvpb2b')
#LOGGER.setLevel(logging.INFO)
#LOGGER.addHandler(fh)

# static files
STATIC_PATH = os.path.join(PROJECT_PATH, config.STATIC_PATH)

AspectRatio = namedtuple('AspectRatio', 'vertical horizontal')
IMAGE = dict(
    DUMP = config.IMAGE.get('DUMP'),
    MAX_FILESIZE = config.IMAGE.get('MAX_FILESIZE', 10000000), #10mb
    ASPECT_RATIO = AspectRatio(**config.IMAGE.get('ASPECT_RATIO', {
        'vertical': 0.3333,
        'horizontal': 3.0,
    })), # 3:1 (vertical, horizontal)
    WEB_MAX_LENGTH = config.IMAGE.get('WEB_MAX_LENGTH', 900) , # max width/height length
    SUPPORTED_FORMATS = config.IMAGE.get('SUPPORTED_FORMATS', {
        'JPEG': 'jpg', 'JPG': 'jpg', 'PNG': 'png'}),
)

GOOGLE_CLIENT_ID = secrets.GOOGLE_CLIENT_ID
GOOGLE_SECRET = secrets.GOOGLE_SECRET
GOOGLE_REDIRECT_URI = secrets.GOOGLE_REDIRECT_URI

DIGITALOCEAN_ACCESS_TOKEN = secrets.DIGITALOCEAN_ACCESS_TOKEN

THUMBOR_SERVER = secrets.THUMBOR_SERVER
THUMBOR_SECURITY_KEY = secrets.THUMBOR_SECURITY_KEY

MAILER = config.MAILER
MAIL_LOGIN = secrets.MAIL_LOGIN
MAIL_PASSWORD = secrets.MAIL_PASSWORD

PASSCODE_SIGNIN_URL = config.PASSCODE_SIGNIN_URL
ACCOUNT_CONFIRMATION_URL = config.ACCOUNT_CONFIRMATION_URL

connect_string = "{dialect}://{user}:{password}@{host}/{dbname}".format(
    dialect=secrets.DB_DIALECT, user=secrets.DB_USER, 
    password=secrets.DB_PASSWORD, host=secrets.DB_HOST,
    dbname=secrets.DB_NAME)
ident_connect_string = "{dialect}:///{dbname}".format(
    dialect=secrets.DB_DIALECT, dbname=secrets.DB_NAME)
FORCE_DROP_DB_SCHEMA = config.FORCE_DROP_DB_SCHEMA
SQLALCHEMY_DATABASE_URI = connect_string
SQLALCHEMY_ECHO = config.SQLALCHEMY_ECHO

SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_COMMIT_ON_TEARDOWN = True
# SQL ALCHEMY PROFILER
ENABLE_SQL_PROFILE_LOG = False

# Flask development server's config
HOST = config.HOST
HTTP_PORT = config.HTTP_PORT

SERVER_DOMAIN = config.SERVER_DOMAIN

# used in root resources 
API_HOST = config.API_HOST
SUBDOMAIN_HOST_TEMPLATE = config.SUBDOMAIN_HOST_TEMPLATE
ACCOUNT_HOST = config.ACCOUNT_HOST

DEV_MODE = config.DEV_MODE
DEBUG = config.DEBUG
TESTING = config.TESTING
DEMO = config.DEMO

#if DEMO:
#    assert secrets.DB_NAME.startswith('demo_') or secrets.DB_NAME.endswith('_demo')
#
#if TESTING:
#    assert secrets.DB_NAME.startswith('test_') or secrets.DB_NAME.endswith('_test')
#    assert HOST.startswith('test.')
