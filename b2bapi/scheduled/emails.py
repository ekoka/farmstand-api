import dramatiq
from datetime import datetime
from b2bapi.db.models.signins import Signin
from b2bapi.db import db
from b2bapi.utils.mailer import Gmail as Mailer
from b2bapi.utils.randomstr import randomstr
from b2bapi.utils.uuid import clean_uuid

def send(subject, content, to):
    config = dramatiq.flask_app.config
    login = config['MAIL_LOGIN']
    password = config['MAIL_PASSWORD']
    m = Mailer(login, password, subject=subject, content=content, to=to)
    return m.send()

@dramatiq.actor(actor_name='simpleb2b.send_passcode')
def send_passcode():
    app = dramatiq.flask_app
    signins = Signin.query.filter_by(sent=False).all()
    for s in signins:
        code = randomstr(4, ucase=False, lcase=True, digits=True)
        s.passcode = code
        s.passcode_timestamp = datetime.utcnow()
        lang = 'en'
        url_type = 'PASSCODE_SIGNIN_URL'
        url_template = dramatiq.flask_app.config[url_type]
        url = url_template.format(
            passcode=s.passcode, lang=lang, signin_id=clean_uuid(s.signin_id))
        content = f"One-time access code: {url}"
        to = s.email
        try: 
            send(subject="One-time access code", content=content, to=to)
            s.sent = True
            db.session.commit()
        except:
            raise
    return True



#@dramatiq.actor(actor_name='simpleb2b.send_activation_email')
#def send_activation_email():
#    app = dramatiq.flask_app
#    token_expr = {"tokens": [{"type": "activation_token", 
#                              "status": "new"}]}
#    new_signins = Signin.query.filter(
#        Signin.meta.comparator.contains(token_expr)).all()
#
#
#    for s in new_signins:
#        for t in s.meta['tokens']:
#            if t['type']=='activation_token' and t['status']=='new':
#                token = t
#                break
#        # TODO: move activation_url_template in config and set lang inside 
#        # activation token
#        lang = token.get('lang', 'en')
#        activation_url = dramatiq.flask_app.config['ACTIVATION_URL']
#        activation_url = activation_url.format(token=token['token'], lang=lang)
#        content = (f"Your e-mail address was recently used to sign-up to "
#                   f"SimpleB2B.app. Click here to activate your account "
#                   f"{activation_url}")
#
#        content = (f"You've recently signed up to a new service with SimpleB2B."
#                   f" Click the following link to activate your account "
#                   f"{activation_url}")
#        to = s.email
#
#        try:
#            send(subject='SimpleB2B Account Activation', 
#                 content=content, to=to)
#            # activate token
#            #s.meta['tokens'][i]['status'] = 'active'
#            token['status'] = 'pending'
#            db.session.commit()
#        except:
#            raise
#            pass
#
#    return True

#@dramatiq.actor(actor_name='simpleb2b.send_password_reset_email')
#def send_password_reset_email():
#    token_expr = {"tokens": [{"type": "reset_token", 
#                              "status": "new"}]}
#    new_signins = Signin.query.filter(
#        Signin.meta.comparator.contains(token_expr)).all()
#
#    for s in new_signins:
#        for i, t in enumerate(s.meta['tokens']):
#            if t['type']=='reset_token' and t['status']=='new':
#                token = t
#                break
#        lang = token['lang']
#        reset_url = token['reset_url_template'].format(
#            token=token['token'], lang=lang)
#        content = (f"You've requested a password change."
#                   f" Click here to change your password {reset_url}")
#        to = s.email
#
#        try:
#            send(subject='Password Reset', content=content, to=to)
#            # activate token
#            s.meta['tokens'][i]['status'] = 'active'
#            db.session.commit()
#        except:
#            pass
#
#    return True

