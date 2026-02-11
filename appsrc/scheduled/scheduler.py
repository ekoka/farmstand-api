from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

class Cron:
    def __init__(self):
        self.scheduler = BlockingScheduler()
        
    def crontab(self, job, crontab='* * * * *'): 
        self.scheduler.add_job(job, CronTrigger.from_crontab(crontab))

    def start(self):
        try:
            self.scheduler.start()
        except KeyboardInterrupt as e:
            self.scheduler.shutdown()
