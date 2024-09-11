from datetime import datetime
import time


def write_schedule(schedule_json, schedule, job):
    context = schedule_json['context']
    if context == 'mins':
        period = schedule_json['every']
        if 60 % period != 0:
            raise Exception("""
                context: mins\n60 % schedule_json['every'] != 0\n
                Message: mins must round to hour!
            """)
        next_time = 0
        while next_time < 60:
            t = ":{}".format(next_time) if next_time >= 10 \
                else ":0{}".format(next_time)
            schedule.every().hour.at(t).do(job)
            next_time += period
    elif context == 'hours':
        period = schedule_json['every']
        if 24 % period != 0:
            raise Exception("""
                context: hours\n24 % schedule_json['every'] != 0\n
                Message: hours must round to day!
            """)
        next_time = 0
        while next_time < 24:
            t = "{}:00".format(next_time) if next_time >= 10 \
                else "00:0{}".format(next_time)
            schedule.every().day.at(t).do(job)
            next_time += period


def edit_schedule(schedule_json, schedule, job):
    schedule.clear()
    write_schedule(schedule_json, schedule, job)


def start_schedule(schedule):
    while True:
        next_run = schedule.next_run()
        now = datetime.now()
        diff = next_run - now
        print('now: {}, next_run: {}, diff: {}'.format(now, next_run, diff))
        seconds_till_next = diff.total_seconds()

        while seconds_till_next < 0:
            skip_job = min(schedule.jobs)
            print('Task taking too long! Skipping job:', skip_job)
            skip_job._schedule_next_run()

            next_run = schedule.next_run()
            now = datetime.now()
            diff = next_run - now
            print('now: {}, next_run: {}, diff: {}'.format(
                now, next_run, diff))
            seconds_till_next = diff.total_seconds()

        if seconds_till_next > 0.2:
            print('wait', seconds_till_next - 0.2)
            time.sleep(seconds_till_next - 0.2)
        else:
            time.sleep(0.2)

        schedule.run_pending()
