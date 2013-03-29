#!/usr/bin/env python

from . import Tomcat, TomcatError, TomcatCluster, parse_warfile
from deployer import ClusterDeployer

def deploy_main(args, opts):
    '''
    Deploy a webapp
    '''
    d = ClusterDeployer(opts)
    d.deploy(map(parse_warfile, args))

def tool_main():
    from sys import argv

    tools = { 'deploy': deploy_main }

    # FIXME: Use a proper arguments parsing library
    global_options = {'host': 'localhost', 'user': 'admin', 'passwd': 'admin', 'port': 8080 }
    tool = argv[1]
    if tool not in tools:
        raise ValueError('Usage: tomcat-tool {0} FILE..'.format('|'.join(tools.keys())))

    tools[tool](argv[2:], global_options)

