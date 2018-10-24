from spcadmin.config import config
from spcadmin import make_app
app = make_app(config)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.HTTP_PORT, debug=config.DEBUG)
