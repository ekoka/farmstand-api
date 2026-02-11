from appsrc.scheduled import scheduler, emails

if __name__=='__main__':
    c = scheduler.Cron()
    c.crontab(job=emails.send_passcode.send)
    c.crontab(job=emails.send_inquiries.send)
    #c.crontab(job=emails.send_password_reset_email.send)
    #c.crontab(job=emails.delete_expired_tokens.send)
    #c.crontab(job=emails.send_activation_email.send)
    c.start()
