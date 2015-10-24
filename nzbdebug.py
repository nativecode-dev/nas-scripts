import os

def main():
    os.environ['NZBOP_CONTROLIP'] = '127.0.0.1'
    os.environ['NZBOP_CONTROLPORT'] = '6789'
    os.environ['NZBOP_CONTROLUSERNAME'] = 'admin'
    os.environ['NZBOP_CONTROLPASSWORD'] = 'Secure/(PAD)'
    os.environ['NZBPP_NZBID'] = '0'
    os.environ['NZBOP_TEMPDIR'] = '/tmp'

main()
