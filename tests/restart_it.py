#!/usr/bin/env python

#__package__ = 'tomcat.tests'

import unittest, os, sys, logging

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from tomcat import TomcatError
from tests import TomcatIntegrationTestCase

class ClusterDeployerIT(TomcatIntegrationTestCase):
    # TODO: validate deployment with http requests against cluster members

    def testSimpleRestartWorks(self):
        self.enable_conditional()
        self.deploy_war('conditional.war', '/conditional')
        self.restart()

    def testMultipleAppRestartWorks(self):
        apps = {}
        self.enable_conditional()
        self.add_war(apps, 'conditional.war',   '/conditional')
        self.add_war(apps, 'goodbye.war', '/multi2')
        self.deploy(apps)
        self.restart()

    def testInvalidWarRaisesError(self):
        self.enable_conditional()
        self.deploy_war('conditional.war', '/conditional')
        self.disable_conditional()
        with self.assertRaises(TomcatError) as context:
            self.restart()

if __name__ == '__main__':
    unittest.main()
