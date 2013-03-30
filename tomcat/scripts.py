#!/usr/bin/env python

import logging
from optparse import OptionParser
from . import Tomcat, TomcatError, TomcatCluster
from deployer import ClusterDeployer, parse_warfiles

def setup_logging(level, module='pytomcat',
                  fmt='%(asctime)s %(levelname)s %(message)s'):
    log = logging.getLogger(module)
    ch = logging.StreamHandler()
    formatter = logging.Formatter(fmt=fmt)
    ch.setFormatter(formatter)
    log.addHandler(ch)
    log.setLevel(level)

def deploy_main(args, opts):
    '''
    Deploy a webapp
    '''
    d = ClusterDeployer(opts)
    d.deploy(parse_warfiles(args))

def tool_main():
    from sys import argv

    tools = { 'deploy': deploy_main }

    usage = 'usage: %prog [options] {0} args'.format('|'.join(tools.keys()))
    parser = OptionParser(usage=usage)
    parser.add_option("-H", "--host", help="Tomcat server host", default='localhost', dest='host')
    parser.add_option("-p", "--port", help="Tomcat server port", default='8080', dest='port')
    parser.add_option("-U", "--user", help="Tomcat server username", default='admin', dest='user')
    parser.add_option("-P", "--password", help="Tomcat server password", default='admin', dest='password')
    (opts, args) = parser.parse_args(argv)
    global_options = { 'host': opts.host, 'port': opts.port, 'user': opts.user, 'passwd': opts.password }

    #setup_logging(logging.INFO, 'pytomcat.jmxproxy')
    setup_logging(logging.INFO, 'pytomcat')
    #setup_logging(logging.DEBUG, 'pytomcat')

    tool = args[1]
    if tool not in tools:
        raise ValueError('Usage: tomcat-tool {0} FILE..'.format('|'.join(tools.keys())))

    tools[tool](args[2:], global_options)
 
