from setuptools.command.install import install
from subprocess import call

class CustomInstall(install):

    def run(self):
        install.run(self)
        print("running custom install steps...")
        call(["wget", "-P", "/tmp", "http://archive.apache.org/dist/tomcat/tomcat-7/v7.0.62/bin/apache-tomcat-7.0.62.tar.gz"])
        call(["tar", "-xzf", "/tmp/apache-tomcat-7.0.62.tar.gz", "-C", "/tmp"])
