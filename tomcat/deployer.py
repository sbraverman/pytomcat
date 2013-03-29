#!/usr/bin/env python

import time, logging
from . import TomcatError, TomcatCluster, parse_warfile

def parse_warfiles(warfiles):
    return dict((f, parse_warfile(f)) for f in warfiles)

class ClusterDeployer:
    required_memory = 50
    check_memory = True
    undeploy_on_error = True
    kill_sessions = False
    auto_reboot = False
    port = 8080
    poll_interval=5
    deploy_wait_time=10

    def __init__(self, opts):
        self.log = logging.getLogger('pytomcat.deployer')
        for k, v in opts.items():
            setattr(self, k, v)
        self.c = TomcatCluster(self.host, self.user, self.passwd, self.port)

    def _get_webapps(self, vhost='*'):
        stats = self.c.webapp_status('*', vhost)
        self.log.debug("Received cluster-wide application status: %s", stats)
        all_paths = {}
        paths = {}
        for a, d in stats.items():
            for k, v in d['clusterDetails']['path'].items():
                all_paths.setdefault(v, []).append(k)
            paths.setdefault(d['path'], []).append(a)
        return (stats, paths, all_paths)

    def _undeploy_old_versions(self, path, apps, vhost):
        if self.kill_sessions:
            for app in apps:
                self.log.info('Forcefully expiring sessions for %s', app)
                self.c.run_command('expire_sessions', app, vhost)
        self.log.info('Attempting to undeploy old versions across the cluster')
        self.c.run_command('undeploy_old_versions', vhost)
        (stats, paths, all_paths) = self._get_webapps(vhost)
        if len(paths[path]) > 1:
            raise TomcatError(
                      "Path '{0}' is served by more than one version ({1})"
                      .format(path, ' and '.join(paths[path])))
        self.log.info('Old versions successfully undeployed')

    def _clean_old_apps(self, new_apps, vhost='*'):
        (stats, paths, all_paths) = self._get_webapps(vhost)
        for ctx, path, ver in new_apps.values():
            if ctx in stats:
                raise TomcatError(
                        'There is already a context {0} on {1}'
                        .format(ctx, ' and '.join(stats[ctx]['presentOn'])))
            if path in all_paths:
                if ver == None:
                    raise TomcatError(
                        'There is already a webapp deployed to {0} on {1}'
                        .format(path, ' and '.join(paths[path])))
                elif path not in paths:
                    raise TomcatError(
                        'Webapp {0} is deployed only to a subset of nodes ({1})'
                        .format(path, ' and '.join(paths[path])))
                else:
                    if len(paths[path]) > 1:
                        # TODO: Check if any existing version is newer than the one
                        #       we are attempting to deploy
                        self._undeploy_old_versions(path, paths[path], vhost)

    def _check_memory(self):
        self.log.info("Checking that all cluster nodes have at least %s%% of free memory",
                      self.required_memory)
        rv = self.c.run_command('check_memory', 100 - self.required_memory)
        if False in rv.values():
            tmp_str = ' and '.join(k for k, v in rv.items() if v == False)
            raise TomcatError("Node(s) {0} is low on memory".format(tmp_str))

    def _wait_for_apps(self, new_apps, vhost='*'):
        ctx_list = [ ctx for ctx, path, ver in new_apps.values() ]
        wait_total = 0
        self.log.info("Waiting for webapps to become available on all nodes")
        while wait_total < self.deploy_wait_time:
            cluster_ok = True
            stats = self.c.webapp_status('*', vhost)
            failed_apps = []
            for ctx in ctx_list:
                try:
                    cs = stats[ctx]
                    self.log.info("\t%s - %s", ctx, cs['clusterDetails']['stateName'])
                    if cs['coherent'] == False or cs['stateName'] != 'STARTED':
                        cluster_ok = False
                        failed_apps.append(ctx)
                except KeyError:
                        cluster_ok = False
                        failed_apps.append(ctx)
            if cluster_ok == True:
                break
            wait_total += self.poll_interval
            time.sleep(self.poll_interval)

        return failed_apps

    def _deploy(self, new_apps, vhost='localhost'):
        rv = {}
        for fn, (ctx, path, ver) in new_apps.items():
            rv[ctx] = self.c.run_command('deploy', fn, ctx, vhost)
        return rv

    def deploy(self, new_apps, vhost='localhost'):
        '''
        Perform a cluster-wide deployment of a webapp
        Before deployment, the following tasks will be executed:
          - check that the path will not conflict with any other app in cluster
          - if the app is versioned, expire old versions before proceeding
          - check that there is enough memory available on every node
          - optionally reboot nodes to reclaim memory

        >>> from tomcat.deployer import parse_warfiles
        >>> d.deploy(parse_warfiles([ '/tmp/test.war' ]))
        '''
        self._clean_old_apps(new_apps, vhost)
        if self.check_memory:
            self._check_memory()
        rv = self._deploy(new_apps, vhost)
        self.log.debug("Deployment results %s", rv)
        # TODO: Check the results for errors
        failed = self._wait_for_apps(new_apps, vhost)
        if len(failed) > 0:
            errstr = "Deployment of %s failed".format(' and '.join(failed))
            self.log.error(errstr)
            if self.undeploy_on_error:
                ctx_names = [ ctx for ctx, path, ver in new_apps.values() ]
                rv = self.undeploy(ctx_names, vhost)
            raise TomcatError(errstr)

    def undeploy(self, context_names, vhost='localhost'):
        '''
        Perform a cluster-wide undeploy of specified contexts

        >>> d.undeploy([ '/test1', '/test2' ])
        '''
        rv = {}
        for ctx in context_names:
            self.log.info("Performing a cluster-wide undeploy of %s", ctx)
            rv[ctx] = self.c.run_command('undeploy', ctx, vhost)
        return rv

