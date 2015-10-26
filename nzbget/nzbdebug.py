import os

def main():
    dir_root = '/tmp/nzbdebug'
    dir_temp = os.path.join(dir_root, 'temp')

    if not os.path.exists(dir_root): os.makedirs(dir_root)
    if not os.path.exists(dir_temp): os.makedirs(dir_temp)

    os.environ['NZBPP_DIRECTORY'] = dir_root
    os.environ['NZBOP_CONTROLIP'] = '127.0.0.1'
    os.environ['NZBOP_CONTROLPORT'] = '6789'
    os.environ['NZBOP_CONTROLUSERNAME'] = 'admin'
    os.environ['NZBOP_CONTROLPASSWORD'] = 'Secure/(PAD)'
    os.environ['NZBPP_NZBID'] = '0'
    os.environ['NZBOP_TEMPDIR'] = dir_temp

main()
