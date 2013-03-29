#!/usr/bin/env python

from . import TomcatError, TomcatCluster

class ClusterDeployer:
    required_memory = 50
    check_memory = True
    undeploy_on_error = True
    kill_sessions = False
    auto_reboot = False
    port = 8080

    def __init__(self, opts):
        for k, v in opts.items():
            setattr(self, k, v)
        self.c = TomcatCluster(self.host, self.user, self.passwd, self.port)

    def _get_webapps(self, vhost='*'):
        stats = self.c.webapp_status('*', vhost)
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
                c.run_command('expire_sessions', app, vhost)
        self.c.run_command('undeploy_old_versions', vhost)
        (stats, paths, all_paths) = self._get_webapps(vhost)
        if len(paths[path]) > 1:
            raise TomcatError(
                      "Path '{0}' is served by more than one version ({1})"
                      .format(path, ' and '.join(paths[path])))

    def _clean_old_apps(self, new_apps, vhost='*'):
        (stats, paths, all_paths) = self._get_webapps(vhost)
        for ctx, path, ver in new_apps:
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
                        self._undeploy_old_versions(path, paths[path], vhost)

    def _check_memory(self):
        rv = self.c.run_command('check_memory', 100 - self.required_memory)
        if False in rv.values():
            tmp_str = ' and '.join(k for k, v in rv.items() if v == False)
            raise TomcatError("Node(s) {0} is low on memory".format(tmp_str))

    def deploy(self, new_apps, vhost='localhost'):
        '''
        Perform a cluster-wide deployment of a webapp
        Before deployment, the following tasks will be executed:
          - check that the path will not conflict with any other app in cluster
          - if the app is versioned, expire old versions before proceeding
          - check that there is enough memory available on every node
          - optionally reboot nodes to reclaim memory

        >>> from tomcat import parse_warfile
        >>> d.deploy([ parse_warfile('/tmp/test.war') ])
        '''
        self._clean_old_apps(new_apps, vhost)
        if self.check_memory:
            self._check_memory()
        # TODO
