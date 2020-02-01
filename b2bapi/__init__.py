import os
import locale
import functools

from werkzeug import ImmutableDict, exceptions as exc
from flask import (
    Flask, request, g, session, current_app, logging as flask_logging,
    ctx)
import dramatiq
from flask_sqlalchemy import SQLAlchemy
from flask_babelex import Babel

from .api import bp as api_blueprint
from .utils.gmail import Gmail

from .db import db

def make_app(config_obj=None):
    # Let's make sure to override the static_folder default value ('static'),
    # to avoid conflicts with blueprints that might also use 'static' as
    # a static folder. We might wanna do the same for templates.

    app = Flask(
        import_name=__name__, static_folder='../static', 
        static_url_path='/static', )
    app.config.from_object(config_obj)

    dramatiq.flask_app = app

    # Babel: i10n & i18n
    babel = Babel(app)
    @babel.localeselector
    def get_locale():
        return getattr(g, 'lang', app.config['DEFAULT_LANG'])

    if app.config['ENABLE_SQL_PROFILE_LOG']:
        enable_sql_profiling(app.config['LOGGER'])

    langs = ','.join(app.config['AVAILABLE_LANGS'])
    url_prefix = '/api/v1'
    app.register_blueprint(api_blueprint, url_prefix=url_prefix)

    # DATABASE
    db.init_app(app)
    db.app = app
    if app.config.get('FORCE_DROP_DB_SCHEMA'):
        db.drop_all()
    with app.app_context():
        db.create_all()

    #app.mailer = Gmail(app.config['GMAIL_LOGIN'], app.config['GMAIL_PASSWORD'])

    #@app.before_request
    #def set_current_domain():
    #    g.domain = get_domain(request)


    # english is the default
    default_lang = app.config.get('DEFAULT_LANG', 'en')

    @app.before_request
    def set_content_lang():
        # TODO: this config should be set with values from the db, provided
        # by the domain admin. 
        g.enabled_langs = ['en', 'fr']

        # data lang is set in the qs as 'lang'
        lang = request.args.get('lang', default_lang)
        if lang not in g.enabled_langs:
            lang = g.enabled_langs[0]
        g.lang = lang

    @app.url_defaults
    def set_lang(endpoint, values):
        if 'lang' in values or not getattr(g, 'lang', None):
            return
        if app.url_map.is_endpoint_expecting(endpoint, 'lang'):
            values['lang'] = g.lang

    @app.after_request
    def call_after_request_callbacks(response):
        callbacks = getattr(g,'after_request_callbacks', [])
        for cb in callbacks:
            cb(response)
        return response

    enable_file_logging(app)

    return app

def enable_file_logging(app):
    import logging
    path = app.config['LOGGING_PATH']

    class DebugFileHandler(logging.FileHandler):
        def emit(self, record):
            if app.debug and app.logger.level==logging.DEBUG:
                super(DebugFileHandler, self).emit(record)
    app.logger.addHandler(DebugFileHandler(path))

def get_domain(request):
    domain = current_app.config['SERVER_DOMAIN']
    try:
        subdomain = request.host.rpartition(domain)[0].strip('.') or 'www'
    except:
        subdomain = 'www'

    t = db.session.execute(
        'select domain_id from domains where name = :name', 
        {'name':subdomain}).fetchone()

    if t is None:
        raise exc.NotFound(u'Domain Not Found')

    rv = dict(domain_id=t.domain_id, domain=subdomain, IMAGE_PATH={})
    #domain['STATIC_PATH'] = os.path.join(config['STATIC_PATH'], domain['domain'])
    #for k,v in config['IMAGE_PATH'].items():
    #    path = os.path.join(domain['STATIC_PATH'], v)
    #    if not os.path.exists(path):
    #        os.makedirs(path)
    #    domain['IMAGE_PATH'][k] = path

    return rv

def enable_sql_profiling(logger):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    import time

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement,
                            parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
        logger.debug("Start Query: %s", statement)

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement,
                            parameters, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop(-1)
        logger.debug("Query Complete!")
        logger.debug("Total Time: %f", total)
