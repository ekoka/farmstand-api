from b2bapi.config import config
from b2bapi import make_app
app = make_app(config)

if __name__ == '__main__':
    app.run(host=config.HOST, port=config.HTTP_PORT, debug=config.DEBUG)
