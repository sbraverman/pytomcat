#!/usr/bin/env python

import logging
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

    # FIXME: Use a proper arguments parsing library
    global_options = {'host': 'localhost', 'user': 'admin', 'passwd': 'admin', 'port': 8080 }
    #setup_logging(logging.INFO, 'pytomcat.jmxproxy')
    setup_logging(logging.INFO, 'pytomcat')
    tool = argv[1]
    if tool not in tools:
        raise ValueError('Usage: tomcat-tool {0} FILE..'.format('|'.join(tools.keys())))

    tools[tool](argv[2:], global_options)

