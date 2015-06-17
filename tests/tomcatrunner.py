#!/usr/bin/python

#__package__ = 'tomcat.tests'

import os, sys, random, tempfile, shutil, subprocess, logging
from tomcat import Tomcat, TomcatCluster, wait_until
from tomcat.deployer import ClusterDeployer

class TomcatRunner:
    port_names = [ 'SHUTDOWN_PORT', 'HTTP_PORT', 'CLUSTER_PORT' ]
    timeout = 1

    def __init__(self, tomcat_dir, node_count = 2, user='admin', passwd='admin'):
        self.log = logging.getLogger('pytomcat.TomcatRunner')
        self.user = user
        self.passwd = passwd

        self.tomcat_dir = os.path.abspath(tomcat_dir)
        self.__validate_tomcat_installation()

        self.nodes = [ {} for i in range(node_count) ]
        self.deployer = ClusterDeployer(host=None, user=user, passwd=passwd)
        self.cluster = self.deployer.c

    def __enter__(self):
        self.start()

    def __exit__(self, type, value, traceback):
        self.stop()

    def start(self):
        self.__allocate_ports()
        self.__create_homes()
        self.__start_servers()

    def stop(self):
        self.__stop_servers()
        self.__remove_homes()

    def restart(self):
        self.__stop_servers()
        self.__start_servers()

    def __validate_tomcat_installation(self):
        for f in [ 'bin/catalina.sh', 'lib/catalina.jar' ]:
            if not os.path.exists(os.path.join(self.tomcat_dir, f)):
                msg = 'Unpack tomcat to {0}'.format(self.tomcat_dir)
                raise AssertionError(msg)

    def __create_homes(self):
        for node in self.nodes:
            node['CATALINA_HOME'] = self.__create_catalina_home()
            self.__generate_config(node)

    def __remove_homes(self):
        map(lambda n: shutil.rmtree(n['CATALINA_HOME']), self.nodes)

    def __start_servers(self):
        procs = map(self.__start_server, self.nodes)
        map(subprocess.Popen.wait, procs)
        self.__wait_until_booted()

    def __stop_servers(self):
        procs = map(self.__stop_server, self.nodes)
        map(subprocess.Popen.wait, procs)

    def __start_server(self, node):
        return self.__run_catalina(node, 'start')

    def __stop_server(self, node):
        return self.__run_catalina(node, 'stop 1 -force')

    def __wait_until_booted(self):
        def all_started():
            r = self.cluster.run_command('server_status').all_results
            return len(filter(lambda x: x != 'STARTED', r.values())) == 0
        wait_until(all_started, 10, 0.5)

    def check_status(self):
        return self.cluster.run_command('list_webapps').all_results

    def __run_catalina(self, node, args):
        # TODO: Support catalina.bat on windows
        exe = os.path.join(node['CATALINA_HOME'], 'bin', 'catalina.sh')
        pidf = os.path.join(node['CATALINA_HOME'], 'logs', 'catalina.pid')
        cmdline = '{0} {1}'.format(exe, args)
        return subprocess.Popen(cmdline, shell=True,
            env={ 'CATALINA_PID': pidf }, stdout=subprocess.PIPE)

    def __create_catalina_home(self):
        home = tempfile.mkdtemp('.tomcat')

        shutil.copytree(os.path.join(self.tomcat_dir, 'conf'),
                        os.path.join(home, 'conf'))

        for l in ['bin', 'lib']:
            # TODO: Support systems without symlinks (e.g. Windows)
            os.symlink(os.path.join(self.tomcat_dir, l), os.path.join(home, l))

        for d in [ 'logs', 'temp', 'webapps', 'work' ]:
            os.mkdir(os.path.join(home, d))

        src_dir = os.path.join(self.tomcat_dir, 'webapps')
        dst_dir = os.path.join(home, 'webapps')
        for app in [ 'manager', 'host-manager' ]:
            src = os.path.join(src_dir, app)
            dst = os.path.join(dst_dir, app)
            shutil.copytree(src, dst)

        return home

    def __allocate_ports(self):
        nports = len(self.port_names)
        universe = range(10000, 65500)
        rnd_ports = random.sample(universe, len(self.nodes) * nports)
        # TODO: Validate if generated ports are available

        for (n, node) in enumerate(self.nodes):
            new_ports = dict(zip(self.port_names, rnd_ports[n*nports:]))
            node.update(new_ports)
            t = Tomcat('localhost', self.user, self.passwd, node['HTTP_PORT'])
            t.mgr.timeout = t.jmx.timeout = self.timeout
            self.cluster.add_member(t)

    def __generate_config(self, node):
        users_cfg = os.path.join(node['CATALINA_HOME'], 'conf', 'tomcat-users.xml')
        with open(users_cfg, 'w') as f:
            f.write(self.__users_xml_tpl.format(user=self.user,passwd=self.passwd))

        other_nodes = filter(lambda x: x != node, self.nodes)
        members_xml = '\n'.join(
            map(lambda x: self.__member_xml_tpl.format(**x), other_nodes))
        xml = self.__server_xml_tpl.format(MEMBERS=members_xml, **node)
        server_cfg = os.path.join(node['CATALINA_HOME'], 'conf', 'server.xml')
        with open(server_cfg, 'w') as f:
            f.write(xml)

    __users_xml_tpl = '''<?xml version='1.0' encoding='utf-8'?>
    <tomcat-users>
      <user username="{user}" password="{passwd}" roles="manager-gui,manager-script,manager-jmx"/>
    </tomcat-users>
    '''

    __member_xml_tpl = '''
        <Member className="org.apache.catalina.tribes.membership.StaticMember"
                port="{CLUSTER_PORT}" host="127.0.0.1" domain="pytomcat-test" />
    '''

    __server_xml_tpl = '''<?xml version='1.0' encoding='utf-8'?>
    <Server port="{SHUTDOWN_PORT}" shutdown="SHUTDOWN">
      <Listener className="org.apache.catalina.core.AprLifecycleListener" SSLEngine="on" />
      <Listener className="org.apache.catalina.core.JasperListener" />
      <Listener className="org.apache.catalina.core.JreMemoryLeakPreventionListener" />
      <Listener className="org.apache.catalina.mbeans.GlobalResourcesLifecycleListener" />
      <Listener className="org.apache.catalina.core.ThreadLocalLeakPreventionListener" />

      <GlobalNamingResources>
        <Resource name="UserDatabase" auth="Container"
                  type="org.apache.catalina.UserDatabase"
                  description="User database that can be updated and saved"
                  factory="org.apache.catalina.users.MemoryUserDatabaseFactory"
                  pathname="conf/tomcat-users.xml" />
      </GlobalNamingResources>

      <Service name="Catalina">
        <Connector port="{HTTP_PORT}" protocol="HTTP/1.1"
                   connectionTimeout="20000" />

        <Engine name="Catalina" defaultHost="localhost">
          <Cluster className="org.apache.catalina.ha.tcp.SimpleTcpCluster"
                   channelSendOptions="8" channelStartOptions="3">
            <Manager className="org.apache.catalina.ha.session.DeltaManager"
                     expireSessionsOnShutdown="false"
                     notifyListenersOnReplication="true"
                     stateTransferTimeout="20" />
            <Channel className="org.apache.catalina.tribes.group.GroupChannel">
              <Receiver className="org.apache.catalina.tribes.transport.nio.NioReceiver"
                        address="127.0.0.1" port="{CLUSTER_PORT}" autoBind="9"
                        selectorTimeout="5000" maxThreads="6" />
              <Sender className="org.apache.catalina.tribes.transport.ReplicationTransmitter">
                <Transport className="org.apache.catalina.tribes.transport.nio.PooledParallelSender" />
              </Sender>
              <Interceptor className="org.apache.catalina.tribes.group.interceptors.TcpPingInterceptor" />
              <Interceptor className="org.apache.catalina.tribes.group.interceptors.TcpFailureDetector" />
              <Interceptor className="org.apache.catalina.tribes.group.interceptors.MessageDispatch15Interceptor" />
              <Interceptor className="org.apache.catalina.tribes.group.interceptors.StaticMembershipInterceptor">
                  {MEMBERS}
              </Interceptor>
            </Channel>
            <Valve className="org.apache.catalina.ha.tcp.ReplicationValve"
                   filter=".*\.gif|.*\.js|.*\.jpeg|.*\.jpg|.*\.png|.*\.htm|.*\.html|.*\.css|.*\.txt"/>
            <Valve className="org.apache.catalina.ha.session.JvmRouteBinderValve" />
            <ClusterListener className="org.apache.catalina.ha.session.JvmRouteSessionIDBinderListener" />
            <ClusterListener className="org.apache.catalina.ha.session.ClusterSessionListener" />
          </Cluster>

          <Realm className="org.apache.catalina.realm.LockOutRealm">
            <Realm className="org.apache.catalina.realm.UserDatabaseRealm"
                   resourceName="UserDatabase"/>
          </Realm>

          <Host name="localhost"  appBase="webapps"
                unpackWARs="true" autoDeploy="true">
            <Valve className="org.apache.catalina.valves.AccessLogValve" directory="logs"
                   prefix="localhost_access_log." suffix=".txt"
                   pattern="%h %l %u %t &quot;%r&quot; %s %b" />
          </Host>
        </Engine>
      </Service>
    </Server>
    '''
