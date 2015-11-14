import time

def Retry(callback, max_retries=3, seconds=0.5, pushout=True):
    count = 0
    exception = None

    while count < max_retries:
        try:
            return callback()
        except Exception as e:
            exception = e
            sleep_time = seconds * count if pushout else seconds
            time.sleep(sleep_time)
            count += 1

    raise exception
