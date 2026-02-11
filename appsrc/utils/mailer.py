import smtplib
from email.message import EmailMessage
from contextlib import contextmanager
from functools import partial

class Mailer:
    def __init__(self, login, password, sender=None, to=None, subject=None, content=None,
                 html_content=None,):
        self.login = login
        self.password = password
        message = EmailMessage()
        if sender is None:
            sender = login
        message['From'] = sender
        if content is not None:
            message.set_content(content, subtype='plain')
            add_html = partial(message.add_alternative, subtype='html')
        else:
            add_html = partial(message.set_content, subtype='html')
        if html_content is not None:
            add_html(html_content)
        if subject is not None:
            message['Subject'] = subject
        if to is not None:
            if isinstance(to, str):
                to = [to]
            message['To'] = ', '.join(to)
        self.message = message

    def send(self, debug=False):
        with self.connection(debug=debug) as conn:
            conn.sendmail(
                self.message['From'],
                self.message['To'],
                self.message.as_string())

    @contextmanager
    def connection(self, debug=False):
        conn = self.Connection(self.SERVER, self.PORT)
        conn.set_debuglevel(debug)
        # give a chance to subclass to customize connection
        self.customize(conn)
        conn.login(self.login, self.password)
        yield conn
        conn.quit()

    def customize(self, conn): pass


class Gmail(Mailer):
    SERVER = 'smtp.gmail.com'
    PORT = 587
    Connection = smtplib.SMTP

    def customize(self, conn):
        conn.starttls()


#class Fastmail(Mailer):
#    SERVER = 'smtp.fastmail.com'
#    PORT = 465
#    Connection = smtplib.SMTP_SSL

class Fastmail(Mailer):
    SERVER = 'smtp.fastmail.com'
    PORT = 587
    Connection = smtplib.SMTP

    def customize(self, conn):
        conn.starttls()

class Zoho(Mailer):
    SERVER = 'smtp.zoho.com'
    PORT = 465
    Connection = smtplib.SMTP_SSL


def select(mailer):
    if mailer.lower()=='zoho':
        return Zoho
    if mailer.lower()=='gmail':
        return Gmail
    if mailer.lower()=='fastmail':
        return Fastmail
