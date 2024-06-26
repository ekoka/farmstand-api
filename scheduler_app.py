from appsrc import make_app
from appsrc.config import config
from appsrc.scheduled import Cron, emails

app = make_app(config)

if __name__=='__main__':
    c = Cron()
    c.crontab(job=emails.send_passcode.send)
    c.crontab(job=emails.send_inquiries.send)
    #c.crontab(job=emails.send_password_reset_email.send)
    #c.crontab(job=emails.delete_expired_tokens.send)
    #c.crontab(job=emails.send_activation_email.send)
    c.start()
