#!/usr/bin/env python
'''
This agent subscribes eye_tracking usybus events. It logs it to console and record it to filesystem.
Records can be used to compare eye_tracking sets and subscribed uvybus data
'''
import getopt
import os
import string
import sys

from ivy.std_api import *

IVYAPPNAME = 'eye_tracking_usybus_subscriber'


def lprint(fmt, *arg):
    print(IVYAPPNAME + ': ' + fmt % arg)


def usage(scmd):
    lpathitem = string.split(scmd, '/')
    fmt = '''Usage: %s [-h] [-b IVYBUS | --ivybus=IVYBUS]
    where
    \t-h provides the usage message;
    \t-b IVYBUS | --ivybus=IVYBUS allow to provide the IVYBUS string in the form
    \t adresse:port eg. 127.255.255.255:2010
    '''
    print(fmt % lpathitem[-1])


def oncxproc(agent, connected):
    if connected == IvyApplicationDisconnected:
        lprint('Ivy application %r was disconnected', agent)
    else:
        lprint('Ivy application %r was connected', agent)
    lprint('currents Ivy application are [%s]', IvyGetApplicationList())


def ondieproc(agent, _id):
    lprint('received the order to die from %r with id = %d', agent, _id)


def on_ub2_msg(agent, *larg):
    usy_type = larg[0]
    source = larg[1]
    data=larg[2].split(';')
    data_out={}

    # no check on data format => done using subscribed regexp
    
    #remove first item
    data = data[1:]
     
    for elem in data :
        ops = elem.split('=')
        data_out[ops[0]] = ops[1]

    lprint('UB2 msg : received from %r\n  >UB2 type %s \n  >UB2 data %s  ', agent, usy_type, data_out)
    
    if usy_type == 'eyetracking:point' :
        with  open('gaze_from_ub.csv', 'a') as gaze_from_ub_file :
            gaze_from_ub_file.write('{},{}\n'.format(floatToString(float(data_out['x'])), floatToString(float(data_out['y']))))

def on_all_msg(agent, *larg):
    lprint('Received from %r: [%s] ', agent, larg[0])

'''
Useful methods
'''
def floatToString(inputValue):
    return ('%.17f' % inputValue).rstrip('0').rstrip('.')

if __name__ == '__main__':
    # initializing ivybus and isreadymsg
    sivybus = ''
    sisreadymsg = '[%s is ready]' % IVYAPPNAME
    # getting option
    try:
        optlist, left_args = getopt.getopt(sys.argv[1:], 'hb:', ['ivybus='])
    except getopt.GetoptError:
        # print help information and exit:
        usage(sys.argv[0])
        sys.exit(2)
    for o, a in optlist:
        if o in ('-h', '--help'):
            usage(sys.argv[0])
            sys.exit()
        elif o in ('-b', '--ivybus'):
            sivybus = a
    if sivybus:
        sechoivybus = sivybus
    elif 'IVYBUS' in os.environ:
        sechoivybus = os.environ['IVYBUS']
    else:
        sechoivybus = 'ivydefault'
    lprint('Ivy will broadcast on %s ', sechoivybus)

    # initialising the bus
    IvyInit(IVYAPPNAME,     # application name for Ivy
            sisreadymsg,    # ready message
            0,              # main loop is local (ie. using IvyMainloop)
            oncxproc,       # handler called on connection/disconnection
            ondieproc)      # handler called when a <die> message is received

    # starting the bus
    # Note: env variable IVYBUS will be used if no parameter or empty string
    # is given ; this is performed by IvyStart (C)
    IvyStart(sivybus)
    # binding to every message
    IvyBindMsg(on_ub2_msg, 'UB2;type=([^;]+);from=([^;]+)((;[^;]+=[^;]+)*)')
    #IvyBindMsg(on_all_msg, '(.*)')
    
    lprint('%s doing IvyMainLoop', IVYAPPNAME)
    IvyMainLoop()
