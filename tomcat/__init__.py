#!/usr/bin/env python

import re, os, logging, time
from multiprocessing.pool import ThreadPool
from multiprocessing.sharedctypes import Value
from error import TomcatError
from jmxproxy import JMXProxyConnection
from manager import ManagerConnection

class Tomcat:
    progress_callback = None

    def __init__(self, host, user = 'admin', passwd = 'admin', port = 8080):
        (self.host, self.port) = (host, port)
        self.log = logging.getLogger('pytomcat.Tomcat')
        self.name = 'Tomcat at {0}:{1}'.format(host,port)
        self.jmx = JMXProxyConnection(host, user, passwd, port)
        self.mgr = ManagerConnection(host, user, passwd, port)

    def memory_info(self):
        '''
        Get memory pools, sizes and allocation information

        >>> t.memory_info()
        { 'HeapMemory': {'max': 129957888, 'init': 0, 'used': 16853056, 'committed': 85000192}, ... }
        '''
        data = self.jmx.query('java.lang:type=Memory*,*')
        meminfo = {}

        generic = data.pop('java.lang:type=Memory')
        for k in [ 'NonHeapMemoryUsage', 'HeapMemoryUsage' ]:
            meminfo.update({ k.replace('Usage',''): generic[k] })

        for k, v in data.iteritems():
            if k.startswith('java.lang:type=MemoryPool,'):
                name = k.replace('java.lang:type=MemoryPool,name=','')
                meminfo.update({ name: v['Usage']})

        return meminfo

    def memory_usage(self):
        '''
        Get memory pool usage as percentage of allowed maximum.

        >>> t.memory_usage()
        { 'HeapMemory': 10, 'NonHeapMemory': 15, ... }
        '''
        usage = {}
        for k, v in self.memory_info().iteritems():
            usage[k] = 100 * v['used'] / v['max']

        return usage
        
    def find_pools_over(self, percentage):
        return list(k for k, v in self.memory_usage().iteritems() if v > percentage)

    def run_gc(self):
        '''
        Invoke Garbage Collector to (hopefully) reclaim memory
        '''
        return self.jmx.invoke('java.lang:type=Memory', 'gc')

    def dump_all_threads(self):
        return self.jmx.invoke('java.lang:type=Threading', 'dumpAllThreads', 'true', 'true')

    def vhosts(self):
        '''
        Return configured vhosts

        >>> for k, v in t.vhosts().items():
        ...     print 'Host: {0}'.format(v['name'])
        ...
        Host: localhost
        >>>
        '''
        return self.jmx.query('Catalina:type=Host,*')

    def deployers(self):
        '''
        Return available application deployers (each configured vhost
        has its own deployer)
        '''
        return self.jmx.query('Catalina:type=Deployer,*')

    def has_cluster(self):
        '''
        Return true if this instance of Tomcat is member of a cluster
        '''
        return len(self.jmx.query('Catalina:type=Cluster')) > 0

    def server_status(self):
        '''
        Return the state name of the Tomcat server component.

        >>> t.server_status()
        'STARTED'

        See Also:
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/Lifecycle.html
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/LifecycleState.html
        '''
        return self.jmx.get('Catalina:type=Server', 'stateName')

    @property
    def _restarter(self):
        try:
            return self._restarter_obj
        except AttributeError:
            self._restarter_obj = self._find_restarter()
            return self._restarter_obj

    def _find_restarter(self):
        restarters = [ _JSWRestarter(self), _YAJSWRestarter(self) ]
        for r in restarters:
            if r.detect():
                return r
        return None

    def can_restart(self):
        '''
        Return true is this instance of Tomcat can be restarted remotely.
        This will only work if Tomcat is launched by a supported wrapper
        which exposes this functionality via JMX.
        e.g. Java Service Wrapper http://wrapper.tanukisoftware.com or
        Yet Another Java Service Wrapper http://yajsw.sourceforge.net/

        >>> t.can_restart()
        True
        '''
        return self._restarter != None

    def restart(self, timeout=600):
        '''
        Restart this instance of Tomcat.
        Restarting will only work if Tomcat is launched by a supported wrapper
        which exposes restarting functionality via JMX.

        >>> t.restart()
        '''
        def started():
            try:
                return self.server_status() == 'STARTED'
            except: 
                return False
        def apps_started(apps):
            try:
                all_restarted = False
                max_attempts = 5
                attempts = 0
                while not all_restarted:
                    current_apps = map(lambda x: (x['baseName'], x['stateName']=='STARTED') ,self.list_webapps().values())
                    original_apps = map(lambda x: (x, True), apps)
                    all_restarted = all_restarted or set(original_apps).issubset(set(current_apps))
                    attempts += 1
                    if attempts >= max_attempts:
                        break
                return all_restarted
            except:
                return False
        apps = map(lambda x: x['baseName'], self.list_webapps().values())
        if not self.can_restart():
            raise TomcatError('{0} does not support remote restarting'
                              .format(self.name))
        self._restarter.restart()
        if not wait_until(lambda: not started(), timeout):
            raise TomcatError('Timed out waiting for {0} to shut down'
                              .format(self.name))
        if not wait_until(started, timeout):
            raise TomcatError('Timed out waiting for {0} to boot up'
                              .format(self.name))
        if not wait_until(lambda: apps_started(apps), timeout):
            raise TomcatError('Timed out waiting for applications ({0}) to boot up'
                              .format(apps))

    def cluster_name(self):
        '''
        Return the name of the cluster
        '''
        return self.jmx.get('Catalina:type=Cluster', 'clusterName')

    def cluster_members(self):
        '''
        Return all members of the cluster

        >>> map(lambda x: x['hostname'], t.cluster_members().values())
        ['192.168.56.101', '192.168.56.102', '192.168.56.103']
        '''
        invalid_ips = [ '0.0.0.0', '255.255.255.255' ]
        def is_valid(m):
            return ( m['hostname'] not in invalid_ips )
        m = self.jmx.query('Catalina:type=Cluster,component=Member,*')
        return dict((k, v) for k, v in m.iteritems() if is_valid(v))

    def active_members(self):
        '''
        Return only active members of the cluster
        '''
        def is_active(m):
            return ( m['ready'] and not m['failing'] and not m['suspect'] )

        m = self.cluster_members()
        return dict((k, v) for k, v in m.iteritems() if is_active(v))

    def list_webapps(self, app='*', vhost='*'):
        '''
        List webapps running on the specified host

        >>> for v in t.list_webapps().values():
        ...     print '{baseName:<20} {path:<20} {stateName}'.format(**v)
        ...
        manager              /manager             STARTED
        docs                 /docs                STARTED
        ROOT                 None                 STARTED
        examples             /examples            STARTING
        host-manager         /host-manager        STOPPED
        >>>

        See Also:
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/Lifecycle.html
        http://tomcat.apache.org/tomcat-7.0-doc/api/org/apache/catalina/LifecycleState.html
        '''
        def sanitize_name(name):
            return '/' if name == None else name
        rv = self.jmx.query(
                   'Catalina:j2eeType=WebModule,name=//{0}/{1},*'
                   .format(vhost, re.sub('^/', '', app)))
        return dict((sanitize_name(v['name']),v) for k, v in rv.iteritems())

    def find_managers(self, app='*', vhost='*'):
        '''
        TODO
        '''
        def extract_context(mgr_id):
            # FIXME: depends on the exact ordering of parts in the object ID
            return re.match(
                       '^Catalina:type=Manager,context=(.+?),host=(.+?)',
                       mgr_id).group(1)
        rv = self.jmx.query(
                   'Catalina:type=Manager,context={0},host={1}'
                   .format(app, vhost))
        return dict((extract_context(k),v) for k, v in rv.iteritems())

    def _list_session_ids(self, mgr_obj_id):
        ids = self.jmx.invoke(mgr_obj_id, 'listSessionIds')
        if ids == None:
            return []
        else:
            return ids.rstrip().split(' ')

    def list_sessions(self, app='*', vhost='*'):
        '''
        TODO
        '''
        rv = {}
        for k, v in self.find_managers(app, vhost).iteritems():
            if v['activeSessions'] > 0:
                rv[k] = self._list_session_ids(v['objectName'])
            else:
                rv[k] = []
        return rv

    def undeploy_old_versions(self, vhost=None):
        '''
        Invoke 'checkUndeploy' on 'Catalina:type=Deployer' to undeploy old
        versions of webapps that share the same path. The distinction is made
        by comparing the 'webappVersion' property. Webapps must have no active
        sessions in order to be undeployed by this call.

        NB! As of Tomcat 7.0.37 versions are compared as strings
            thus 2 > 10, however 02 < 10

        >>> t.undeploy_old_versions('localhost') # Undeploy from localhost
        >>> t.undeploy_old_versions() # Undeploy from all configured vhosts
        '''
        if vhost == None:
            deployers = self.deployers().keys()
        else:
            deployers = [ 'Catalina:type=Deployer,host={0}'.format(vhost) ]

        for d in deployers:
            self.jmx.invoke(d, 'checkUndeploy', timeout=20)

    def find_connectors(self):
        '''
        Return the list of active Tomcat connector names.

        >>> t.find_connectors()
        ['Connector[HTTP/1.1-8080]', 'Connector[AJP/1.3-8009]']
        '''
        return self.jmx.invoke('Catalina:type=Service', 'findConnectors')

    def max_heap(self):
        return self.jmx.get('java.lang:type=Memory', 'HeapMemoryUsage', 'max')

    def max_nonheap(self):
        return self.jmx.get('java.lang:type=Memory', 'NonHeapMemoryUsage', 'max')

    def deploy(self, filename, context=None, vhost='localhost'):
        '''
        Deploy a Web application archive (WAR)

        >>> t.deploy('/tmp/myapp.war')
        '''
        (ctx, path, version) = parse_warfile(filename)
        if context == None:
            context = ctx
        return self.mgr.deploy(filename, context, vhost)

    def undeploy(self, context, vhost='localhost'):
        '''
        Remove a web application from the server

        >>> t.undeploy('/myapp')
        '''
        self.mgr.undeploy(context, vhost)

    def _expire_session(self, mgr_obj_id, session_id):
        self.jmx.invoke(mgr_obj_id, 'expireSession', session_id)

    def expire_sessions(self, app, vhost = '*'):
        '''
        Forcefully expire ALL active sessions in a webapp

        >>> t.expire_sessions('/manager')
        '''
        sessions = self.list_sessions(app, vhost)
        if len(sessions) <= 0:
            raise TomcatError("Unable to find context '{0}' from vhost '{1}'"
                              .format(app, vhost))

        mgrs = self.find_managers(app, vhost)
        for ctx, ids in sessions.iteritems():
            for id in ids:
                if not ctx in mgrs:
                    raise TomcatError(
                              "Unable to find manager for context '{0}' from vhost '{1}'"
                              .format(app, vhost))
                self._expire_session(mgrs[ctx]['objectName'], id)

    def set_progress_callback(self, callback):
        self.progress_callback = callback
        self.mgr.progress_callback = callback

class _JSWRestarter:
     name = 'org.tanukisoftware.wrapper:type=WrapperManager'
     def __init__(self, tomcat):
         self.jmx = tomcat.jmx
         self.log = logging.getLogger('pytomcat._JSWRebooter')

     def detect(self):
         try:
             rv = self.jmx.get(self.name, 'ControlledByNativeWrapper')
             self.log.debug("Tanuki Java Service Wrapper detected")
             if not rv:
                 self.log.warn("JSW not controlled by Native Wrapper, restarting disabled")
             return rv
         except:
             return False

     def restart(self):
         self.log.debug("Requesting a restart from Java Service Wrapper")
         return self.jmx.invoke(self.name, 'restart')

class _YAJSWRestarter:
     def __init__(self, tomcat):
         self.jmx = tomcat.jmx
         self.log = logging.getLogger('pytomcat._YAJSWRebooter')

     def detect(self):
         beans = self.jmx.query('Wrapper:name=*').keys()
         if len(beans) <= 0:
             return False
         if len(beans) > 1:
             self.log.warn("Found more than one YAJSW MBean %s", beans)
         self.name = beans.pop()
         rv = self.jmx.get(self.name, 'ControlledByWrapper')
         if not rv:
             self.log.warn("YAJSW not controlled by Wrapper, restarting disabled")
         return rv
     def restart(self):
         self.log.debug("Requesting a restart from YAJSW")
         return self.jmx.invoke(self.name, 'restart')

def parse_warfile(filename):
    m = re.match('^(?P<ctx>(?P<path>.+?)(##(?P<ver>.+?))?)\\.war$',
                 '/' + os.path.basename(filename), flags=re.I)
    if m == None:
        raise TomcatError("Invalid WAR file name: '{0}'".format(filename))
    return ( m.group('ctx'), m.group('path'), m.group('ver') )

def wait_until(predicate, timeout, poll_interval=5):
    end_time = time.time() + timeout
    while time.time() < end_time:
        if predicate(): return True
        time.sleep(poll_interval)
    return False

class TomcatCluster:
    max_threads = 20
    members = {}
    progress_callback = None
    active_only = False

    def __init__(self, host = None, user = None, passwd = None, port = 8080):
        self.log = logging.getLogger('pytomcat.TomcatCluster')
        (self.user, self.passwd, self.port) = (user, passwd, port)
        if host != None:
            self._discover(Tomcat(host, user, passwd, port))

    def _discover(self, t):
        if self.active_only:
            members = t.active_members().values()
        else:
            members = t.cluster_members().values()
        for h in map(lambda x: x['hostname'], members):
            member_id = '{0}:{1}'.format(h, self.port)
            if not member_id in self.members:
                self.log.info("Autodiscovered cluster member '%s'", h)
                self.add_member(Tomcat(h, self.user, self.passwd, self.port))
                self._discover(self.members[member_id])
        self.set_progress_callback(self.progress_callback)

    def _run_progress_callback(self, **args):
        if self.progress_callback != None:
            try:
                self.progress_callback(**args)
            except Exception as e:
                self.log.error('running progress callback: %s', e)

    def member_count(self):
        return len(self.members)

    def add_member(self, t):
        member_id = '{0}:{1}'.format(t.host, t.port)
        if member_id in self.members:
            raise TomcatError('{0} already exists'.format(member_id))
        self.members[member_id] = t

    def run_command(self, command, *args, **opts):
        if len(self.members) <= 0:
            raise TomcatError("Cluster has no members")
        hosts = opts.setdefault('hosts', self.members.keys())
        threads = opts.setdefault('threads',
                      min(self.member_count(), self.max_threads))
        abort_on_error = opts.setdefault('abort_on_error', False)
        if abort_on_error:
            abort = Value('b', 0)

        def run_cmd(host):
            try:
                if abort_on_error and abort.value:
                    raise TomcatError('Aborted')
                self.log.debug("Performing %s%s on %s", command, args, host)
                self._run_progress_callback(event=events.CMD_START,
                        command=command, args=args, node=host)

                rv = getattr(self.members[host], command)(*args)

                self._run_progress_callback(event=events.CMD_END,
                        command=command, args=args, node=host)
            except Exception as e:
                if abort_on_error:
                    abort.value = True
                rv = e
            return (host, rv)

        pool = ThreadPool(processes=threads)
        return ClusterCommandResults(pool.map(run_cmd, hosts))

    def set_progress_callback(self, callback):
        self.progress_callback = callback
        for t in self.members.values():
            t.set_progress_callback(callback)
    
    def webapp_status(self, app='*', vhost='*', latest=False):
        '''
        Perform a cluster-wide discovery to find webapps that match the filter.

        >>> c.webapp_status('/manager')
        {'/manager': {'coherent': True, 'stateName': 'STARTED', 'presentOn': ['10.1.6.1'], ... }}
        '''
        interesting_keys = [ 'stateName', 'path', 'webappVersion' ]
        app_versions = []

        def new_stats():
            rv = {
                'presentOn': [],
                'coherent': True,
                'clusterDetails': dict((k,{}) for k in interesting_keys)
            }
            rv.update(dict((k,None) for k in interesting_keys))
            return rv

        def populate_interesting(stats):
            for key in interesting_keys:
                cd = stats['clusterDetails']
                cd[key].update({ host: v[app][key] })
                if key == 'webappVersion' and v[app][key] is not None:
                    app_versions.append(v[app][key])

        def consolidate_interesting(stats):
            for key in interesting_keys:
                d = stats['clusterDetails'][key]
                unique = set(i for i in d.values())
                if len(unique) == 1:
                    stats[key] = unique.pop()
                else:
                    stats['coherent'] = False

        def remove_old_version():
            app_versions.sort(reverse=True)
            for k, a in rv.items():
                if a['webappVersion'] != app_versions[0]:
                    del rv[k]

        # TODO: report failed commands
        apps = self.run_command('list_webapps', app, vhost).results
        all_keys = set.union(*map(set, apps.values()))
        rv = {}
        for app in all_keys:
            stats = new_stats()
            for host, v in apps.iteritems():
                if app in v:
                    stats['presentOn'].append(host)
                    populate_interesting(stats)
            consolidate_interesting(stats)
            if len(stats['presentOn']) != len(self.members):
                stats['coherent'] = False
            rv[app] = stats
        if latest is True:
            remove_old_version()
        return rv

class ClusterCommandResults:
    '''
    Encapsulates the results of a cluster-wide command
    '''
    def __init__(self, rv):
        def success((k,v)):
            return not isinstance(v, Exception)
        self._failed = filter(lambda x: not success(x), rv)
        self._succeeded = filter(success, rv)

    @property
    def has_failures(self):
        return len(self._failed) > 0

    @property
    def results(self):
        '''
        Returns a dict of successful results
        '''
        return dict(self._succeeded)

    @property
    def failures(self):
        '''
        Returns a dict of failures
        '''
        return dict(self._failed)

    @property
    def all_results(self):
        '''
        Returns a dict of all results
        '''
        return dict(self._succeeded + self._failed)

