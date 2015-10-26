import time

def retry(callback, max_retries=3, seconds=0.1, pushout=True):
    count = 0

    while count < max_retries:
        try:
            return callback()
        except Exception as e:
            print('Retry failed due to %s (%s/%s).' % (e, count, max_retries))
            sleep_time = seconds * count if pushout else seconds
            time.sleep(sleep_time)
            count += 1

    raise IOError('Retry failed after %s tries.' % max_retries)
