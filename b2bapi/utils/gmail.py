import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import contextlib
#from email.MIMEMultipart import MIMEMultipart
#from email.MIMEText import MIMEText

class Mailer(object):
    def __init__(self, login, password, subject=None, message=None, 
                 recipients=None, expected_charset=None):

        self.charset = expected_charset

        self.login = self.utf8_encode(login)
        self.password = self.utf8_encode(password)

        # specifies the charset of strings it will be receiving
        self.charset = expected_charset

        if subject:
            self.subject = subject

        if message:
            self.message = message

        if recipients:
            self.recipients = recipients


    def utf8_encode(self, string):
        """ ensures conversion to utf-8 """
        if self.charset:
            try:
                string = string.decode(self.charset)
            except:
                raise Exception('Mailer object expects to work with {} strings.'
                                .format(self.charset))
        return string.encode('utf-8')

    def iterate_recipients(self, recipients):
        try:
            return ((k,v) for k,v in recipients.iteritems())  
        except:
            return ((k, None) for k in recipients)


    def send_all(self, sender=None, recipients=None, subject=None, 
                 message=None):
        sender = sender or self.login
        recipients = recipients or getattr(self, 'recipients', [])
        subject = subject or getattr(self, 'subject', '')
        message = message or getattr(self, 'message', '')
        msgs = []
        for recipient, config in self.iterate_recipients(recipients):
            _sender = config.get('sender', sender) if config else sender
            _subject = config.get('subject', subject) if config else subject
            _message = config.get('message', message) if config else message
            html = plain = None
            msg = MIMEMultipart('alternative')
            try:
                _html = _message.get('html')
                _plain = _message.get('plain')
            except AttributeError:
                _html = None
                _plain = _message
                
            try:
                _recipient = self.utf8_encode(recipient)
                _sender = self.utf8_encode(_sender)
                _subject = self.utf8_encode(_subject)
                if _plain:
                    _plain = self.utf8_encode(_plain)
                    _plain_text = MIMEText(_plain, 'plain', 'utf-8') 
                    msg.attach(_plain_text)
                if _html:
                    _html = self.utf8_encode(_html)
                    _html_text = MIMEText(_html, 'html', 'utf-8')
                    msg.attach(_html_text)
            except:
                raise
                raise Exception('Gmail object only works with Unicode data.')

            msg['Subject'] = Header(_subject, 'utf-8')
            msg['From'] = Header(_sender, 'utf-8') 
            msg['To'] = ','.join([_recipient])
            msgs.append(msg)
                
        with self.connection(True) as conn:
            [conn.sendmail(msg['From'], msg['To'], msg.as_string()) 
             for msg in msgs]

class Gmail(Mailer):

    @contextlib.contextmanager
    def connection(self, debug=False):
        conn = smtplib.SMTP('smtp.gmail.com', 587)
        conn.set_debuglevel(debug)
        conn.starttls()
        conn.login(self.login, self.password)
        yield conn
        conn.quit()
