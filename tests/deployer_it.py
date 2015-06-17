#!/usr/bin/env python

#__package__ = 'tomcat.tests'

import unittest, os, sys, logging

parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from tomcat import TomcatError
from tests import TomcatIntegrationTestCase

class ClusterDeployerIT(TomcatIntegrationTestCase):
    # TODO: validate deployment with http requests against cluster members

    def testSimpleDeployWorks(self):
        self.deploy_war('blank.war', '/simple')

    def testMultipleDeployWorks(self):
        apps = {}
        self.add_war(apps, 'hello.war',   '/multi1')
        self.add_war(apps, 'goodbye.war', '/multi2')
        self.deploy(apps)

    def testVersionedDeployWorks(self):
        self.deploy_war('blank.war',   '/versioned', '0001')
        self.deploy_war('hello.war',   '/versioned', '0002')
        self.deploy_war('goodbye.war', '/versioned', '0003')

    def testInvalidWarRaisesError(self):
        with self.assertRaises(TomcatError) as context:
            self.deploy_war('corrupt.war')

    def testSlowlyDeployingWarWorks(self):
        self.deploy_war('slow.war',    '/slow1', '0001')
        self.deploy_war('hello.war',   '/slow1', '0002')
        self.deploy_war('goodbye.war', '/slow1', '0003')

    def testSimpleRestartWorks(self):
        self.enable_conditional()
        self.deploy_war('conditional.war', '/simplerestart')
        self.restart()
        for servers,wars in self.status().iteritems():
            self.assertEqual(wars['/simplerestart']['stateName'], "STARTED") 

    def testMultipleAppRestartWorks(self):
        apps = {}
        self.enable_conditional()
        self.add_war(apps, 'hello.war',   '/multirestart1')
        self.add_war(apps, 'goodbye.war', '/multirestart2')
        self.deploy(apps)
        self.restart()
        for servers,wars in self.status().iteritems():
            self.assertEqual(wars['/multirestart1']['stateName'], "STARTED") 
            self.assertEqual(wars['/multirestart2']['stateName'], "STARTED") 

    def testInvalidWarRaisesErrorRestart(self):
        self.enable_conditional()
        self.deploy_war('conditional.war', '/conditional')
        for servers,wars in self.status().iteritems():
            self.assertEqual(wars['/conditional']['stateName'], "STARTED") 
        self.disable_conditional()
        self.restart()
        for servers,wars in self.status().iteritems():
            self.assertEqual(wars['/conditional']['stateName'], "STOPPED") 

if __name__ == '__main__':
    unittest.main()
