import dramatiq
from datetime import datetime
from b2bapi.db.models.accounts import Signin
from b2bapi.db.models.inquiries import Inquiry
from b2bapi.db import db
from b2bapi.utils.uuid import clean_uuid
from jinja2 import Environment, FileSystemLoader, select_autoescape

env = Environment(
    loader=FileSystemLoader('b2bapi/scheduled/templates'),
    autoescape=select_autoescape('html'),
)

def send(subject, to, content=None, html_content=None):
    #TODO: make a single reusable instance of mailer
    config = dramatiq.flask_app.config
    Mailer = config['MAILER']
    login = config['MAIL_LOGIN']
    password = config['MAIL_PASSWORD']
    m = Mailer(login, password, subject=subject, to=to, 
               content=content, html_content=html_content,)
    return m.send()

@dramatiq.actor(actor_name='productlist.send_passcode')
def send_passcode():
    config = dramatiq.flask_app.config
    signins = Signin.query.filter_by(sent=False).all()
    for s in signins:
        s.passcode_timestamp = datetime.utcnow()
        lang = 'en'
        url_template = config['PASSCODE_SIGNIN_URL']
        url = url_template.format(
            passcode=s.passcode, lang=lang, signin_id=clean_uuid(s.signin_id))
        content = f"One-time access code: {url}"
        to = s.email
        try: 
            send(subject="One-time access code", content=content, to=to)
            s.sent = True
            db.session.commit()
        except:
            db.session.rollback()
            raise
    return True

@dramatiq.actor(actor_name='productlist.send_inquiries')
def send_inquiries():
    app = dramatiq.flask_app
    unsent = {'email': {'sent':False}}
    inquiries = Inquiry.query.filter(Inquiry.data.comparator.contains(unsent))
    for i in inquiries:
        admin = i.domain.admins[0]
        inquiry = prep_inquiry_data(i)
        # TODO: ensure that there's always at least one admin
        html_content = load_inquiry_template(inquiry)
        to = admin.email
        try: 
            send(subject="New inquiry from your Productlist",
                 html_content=html_content, to=to)
            i.data['email'] = {
                'sent': True,
                'timestamp': datetime.utcnow().timestamp()
            }
            db.session.commit()
        except:
            db.session.rollback()
            raise

def prep_inquiry_data(inquiry):
    user = inquiry.account
    products = []
    for p in  inquiry.products:
        products.append({
            'name': get_field(p.product, 'name', inquiry.data['lang']),
            'number': get_field(p.product, 'number', inquiry.data['lang']),
            'url': 'https://someplaceholder.com/url',
            'admin_url': 'https://someplaceholder.com/admin_url',
            'quantity': p.quantity,
            'comments': p.data.get(
                'messages', [{}])[0].get('comments', '') or '',
        })
    comments = inquiry.data.get('messages', [{}])[0].get('comments', '') or ''
    return dict(user=user, products=products, comments=comments)

def load_inquiry_template(inquiry):
    t = env.get_template('inquiry.html')
    return t.render(**inquiry)

def get_field(record, name, lang):
    for f in record.fields.get('fields', []):
        if f.get('name')==name:
            if f.get('localized'): 
                return f.get('value', {}).get(lang) 
            else:
                return f.get('value')

#@dramatiq.actor(actor_name='productlist.send_activation_email')
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
#                   f"Productlist.io. Click here to activate your account "
#                   f"{activation_url}")
#
#        content = (f"You've recently signed up to a new service with Productlist."
#                   f" Click the following link to activate your account "
#                   f"{activation_url}")
#        to = s.email
#
#        try:
#            send(subject='Productlist Account Activation', 
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

#@dramatiq.actor(actor_name='productlist.send_password_reset_email')
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

