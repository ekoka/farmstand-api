from appsrc import make_app
from appsrc.config import config
from appsrc.db import db
from appsrc.db.models.accounts import Account
import click

app = make_app(config)

@app.cli.command("update-password")
@click.argument("email")
@click.argument("password")
def create_user(email, password):
    account = Account.query.filter_by(email=email).one()
    account.password = password
    db.session.commit()
