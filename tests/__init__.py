#!/usr/bin/env python

import unittest, os, sys, logging
from tomcatrunner import TomcatRunner
from tomcat.deployer import ClusterDeployer
from tomcat import *

class TomcatIntegrationTestCase(unittest.TestCase):
    # TODO: Save appserver and pytomcat logs

    tomcat_dir = '/tmp/apache-tomcat-7.0.39'
    war_dir = os.path.join(os.path.dirname(__file__), 'test_wars')

    @classmethod
    def setUpClass(cls):
        #logging.basicConfig(filename='example.log', filemode='w', level=logging.DEBUG)
        logging.basicConfig(level=100)
        cls.tr = TomcatRunner(cls.tomcat_dir)
        cls.tr.start()

    @classmethod
    def tearDownClass(cls):
        cls.tr.stop()

    def add_war(self, apps, fname, path=None, ver=None):
        if path == None:
            (_, path, ver) = parse_warfile(fname)
        ctx = (path if ver == None else '{0}##{1}'.format(path, ver))
        apps.update({os.path.join(self.war_dir, fname): (ctx, path, ver)})

    def deploy_war(self, fname, path=None, ver=None):
        apps = {}
        self.add_war(apps, fname, path, ver)
        self.deploy(apps)

    def deploy(self, apps):
        self.tr.deployer.deploy(apps)

