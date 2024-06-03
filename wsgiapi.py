from appsrc.config import config
from appsrc import make_app

app = make_app(config)

if __name__ == '__main__':
    app.run(
        host=config.FLASK_HTTP_HOST,
        port=config.FLASK_HTTP_PORT,
        debug=config.DEBUG,
    )
