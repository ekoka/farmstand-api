from .utils import env, get_upper_keys

SECRET_KEY = env.binstring('SECRET_KEY')
DIGITALOCEAN_ACCESS_TOKEN = env.string('DIGITALOCEAN_ACCESS_TOKEN')

THUMBOR_SECURITY_KEY = env.string('THUMBOR_SECURITY_KEY')

STRIPE_DEV_KEY = env.string('STRIPE_DEV_KEY')
STRIPE_KEY = STRIPE_DEV_KEY

MAIL_LOGIN = env.string('MAIL_LOGIN')
MAIL_PASSWORD = env.string('MAIL_PASSWORD')

__all__ = get_upper_keys(locals().keys())
