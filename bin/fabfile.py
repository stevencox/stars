#############################################################x############
##
## Cluster installer
##
##    * In general we try to make operations idempotent and reversible.
##
##    * Idempotency: Running an operation once should have the same
##      effect as running it ten times.
##
##    * Reversibility: Each operation implements install and clean 
##      sub-operations. The default is to install and clean can be 
##      specified to reverse the ordinary operation.
##
#########################################################################

import os
import socket
import sys
import StringIO

from string import Template

from fabric.api import cd
from fabric.api import env
from fabric.api import execute
from fabric.api import hosts
from fabric.api import local
from fabric.api import parallel
from fabric.api import put
from fabric.api import run
from fabric.api import settings
from fabric.api import sudo
from fabric.api import task
from fabric.contrib.files import exists
import stars_util as su
from importlib import import_module

from fabric.state import output
output['warnings'] = False
output['status'] = False
output['running'] = False

sys.path.append('.')
sys.path.append (os.path.join (os.environ['STARS_HOME'], 'bin'))

app = import_module (os.environ ['app'])
env.user = app.env.user
cluster_nodes   = su.concat ([ app.env.head_nodes, app.env.work_nodes, app.env.db_nodes ])

# Git repositories
orchestration_app_git_uri = "https://github.com/stevencox/orchestration.git"

##################################################################
##
## Targets
##
##################################################################

''' configure the web server '''
@task
def web (mode="install"):
    def install ():
        ''' Install nginx '''
        local (get_yum_command (sudo=True) % ("nginx", "nginx"))

        ''' Install basic apps '''
        for app in base_apps:
            local (get_yum_command (sudo=True) % (app, base_apps[app]))

        ''' Configure iptables '''
        sudo ('if [ ! -f /etc/sysconfig/iptables.orig ]; then cp /etc/sysconfig/iptables /etc/sysconfig/iptables.orig; fi')
        sudo ('cp %s/iptables.web /etc/sysconfig/iptables' % app.env.conf)
        sudo ('service iptables restart')
        sudo ('service iptables status')

        ''' Configure proxy '''
        local ('sudo cp %s/nginx/nginx.conf /etc/nginx' % app.env.conf)
        local ('sudo cp -r %s/nginx/conf.d /etc/nginx' % app.env.conf)
        local ('sudo service nginx stop')
        local ('sudo service nginx start')
        local ('sudo service nginx status')

    def clean ():
        local (get_yum_command(sudo=True, install=False) % ("nginx", "nginx"))
        local (get_yum_command(sudo=True, install=False) % ("nginx-filesystem", "nginx-filesystem"))
        local ('sudo rm -rf /etc/nginx')
        for app in base_apps:
            local (get_yum_command (sudo=True, install=False) % (app, base_apps[app]))
    return su.execute_op (mode, install, clean)

''' Configure head nodes '''        
@task
@hosts(app.env.head_nodes)
def head (mode="install"):
    mesosphere_repo (mode)
    base (mode)
    zoo (mode)
    def install ():
        sudo ('sh -c "echo IP=$(hostname -I) > /etc/network-environment" ')
        firewall (mode)
        mesos (mode)
        marathon (mode)
        chronos (mode)
        orchestration (mode)
        configure_mesos_services (mode)
    def clean ():
        orchestration (mode)
        chronos (mode)
        marathon (mode)
        mesos (mode)
        firewall (mode)
    return su.execute_op (mode, install, clean)

@task
@parallel
@hosts(app.env.head_nodes)
def marathon (mode="install"):
    def install ():
        su.yum_install (mode, "marathon-", "marathon")
        run ('gem install marathon_client')
    def clean ():
        run ('gem uninstall --quiet --executables marathon_client')
        su.yum_install (mode, "marathon-", "marathon")
    return su.execute_op (mode, install, clean)
        
@task
@parallel
@hosts(app.env.head_nodes)
def chronos (mode="install"):
    def install ():
        su.yum_install (mode, "chronos-", "chronos")
        su.configure_service (mode, 'chronos')
    def clean ():
        su.configure_service (mode, 'chronos')
        su.yum_install (mode, "chronos-", "chronos")
    return su.execute_op (mode, install, clean)

@task
@hosts(app.env.head_nodes)
def mesos (mode="install"):
    mesos_21 (mode)

@task
@parallel
@hosts(app.env.head_nodes)
def mesos_24(mode="install"):
    def install ():
        su.yum_install (mode, "mesos-", "mesos")
        sudo ('rm -rf /etc/mesos-master/quorum.rpm*')
        sudo ('echo 2 > /etc/mesos-master/quorum')
        mkdir_mine ('/var/log/mesos', env.user)
        mkdir_mine ('/var/lib/mesos', env.user)
        sudo ('cp %s/mesos/mesos-master.service /usr/lib/systemd/system/' % app.env.conf)
        su.configure_service (mode, 'mesos-master')
    def clean ():
        su.configure_service (mode, 'mesos-master')
        sudo ('rm -rf /etc/mesos-master/quorum')
        sudo ('rm -f /usr/lib/systemd/system/mesos-master.service')
        su.yum_install (mode, "mesos-", "mesos")
    return su.execute_op (mode, install, clean)

def mesos_21_install (mode):
    def install ():
        sudo ('rm -rf /usr/lib/systemd/system/mesos-master.service')
        with settings(warn_only=True):
            libs = ' '.join ([ 'apache-maven python-devel java-1.7.0-openjdk-devel zlib-devel libcurl-devel',
                               'openssl-devel cyrus-sasl-devel cyrus-sasl-md5 apr-devel subversion-devel apr-util-devel' ])
            su.yum_install_all (mode, libs) 
        with cd (su.opt):
            sudo ('rm -rf mesos')
            sudo ('mkdir -p mesos')
            sudo ('chown %s mesos' % env.user)
            run ('mkdir -p mesos')
            with cd ('mesos'):
                run ('tar xzf %s/mesos-renci-0.21.0.tar.gz' % su.dist)
                with cd ('mesos-0.21.0'):
                    sudo ('make install 2>&1 > mesos-install.log')
    def clean ():
        sudo ('rm -rf %/mesos' % su.opt)
    return su.execute_op (mode, install, clean)

@hosts(app.env.head_nodes)
def mesos_21(mode="install"):
    def install ():
        mesos_21_install (mode)
        ip_addr = run ('hostname -I')
        zk_string = run ('cat /etc/mesos/zk')
        su.generate_config (
            template='%s/mesos/mesos-master.service.custom' % app.env.conf,
            context={
                'EXE'      : '%s/mesos/mesos-0.21.0/bin/mesos-master.sh' % su.opt,
                'IP'       : ip_addr,
                'ZK'       : zk_string,
                'LOGLEVEL' : 'WARNING',
                'LOGDIR'   : '/var/log/mesos',
                'QUORUM'   : 2
            },
            output='/usr/lib/systemd/system/mesos-master.service',
            use_sudo=True)
        sudo ('rm -rf /etc/mesos-master/quorum.rpm*')
        sudo ('echo 2 > /etc/mesos-master/quorum')
        mkdir_mine ('/var/log/mesos', env.user)
        mkdir_mine ('/var/lib/mesos', env.user)
        su.configure_service (mode, 'mesos-master')
    def clean ():
        su.configure_service (mode, 'mesos-master')
        sudo ('rm -rf /etc/mesos-master/quorum')
        sudo ('rm -f /usr/lib/systemd/system/mesos-master.service')
        su.yum_install (mode, "mesos-", "mesos")
    return su.execute_op (mode, install, clean)

@task
@parallel
@hosts(app.env.head_nodes)
def head_restart ():
    services = [ 'orchestration', 'chronos', 'marathon', 'mesos-master', 'zookeeper' ]
    map (lambda s : sudo ('service %s stop' % s), services)
    map (lambda s : sudo ('service %s start' % s), reversed (services))

''' Configure head node systemD services '''
@task
@parallel
@hosts(app.env.head_nodes)
def services (mode="install"):
    def install ():
        sudo ('cp %s/marathon/marathon.service  /usr/lib/systemd/system/' % app.env.conf)
    def clean ():
        sudo ('rm -f /usr/lib/systemd/system/marathon.service')
        sudo ('rm -f /usr/lib/systemd/system/chronos/chronos.service')
        sudo ('rm -f /usr/lib/systemd/system/chronos/orchestration.service')
    su.configure_service (mode, 'mesos-master')
    su.configure_service (mode, 'marathon')
    su.configure_service (mode, 'chronos')
    return su.execute_op (mode, install, clean)

''' Configure orchestration server '''
@task
@parallel
@hosts(app.env.head_nodes)
def orchestration (mode="install"):
    def install ():
        su.yum_install (mode, 'haproxy-', 'haproxy')
        mkdir_mine ('/opt/app', env.user)
        mkdir_mine ('/var/log/orchestration', env.user)
        mkfile_mine ('/etc/haproxy/haproxy.auto.cfg', env.user)
        with cd (su.opt):
            sudo ('rm -rf orchestration')
            run ('git clone --quiet %s' % orchestration_app_git_uri)
        with cd (su.orchestration_path):
            run ('cp %s/orchestration/local_config.json %s/etc' % (app.env.conf, su.orchestration_path))
            sudo ('cp %s/orchestration/orchestration.service /usr/lib/systemd/system' % app.env.conf)
        sudo ('service haproxy stop')
        su.configure_service (mode, 'orchestration')
    def clean ():
        su.configure_service (mode, 'orchestration')
        su.configure_service (mode, 'haproxy')
        su.yum_install (mode, 'haproxy-', 'haproxy')
        sudo ('rm -rf /var/log/orchestration')
        sudo ('rm -rf /opt/app/orchestration')
    return su.execute_op (mode, install, clean)

''' Configure head node firewall ''' 
@task
@parallel
@hosts(app.env.head_nodes)
def firewall (mode="install"):
    def install ():
        sudo ('if [ ! -f /etc/sysconfig/iptables.orig ]; then cp /etc/sysconfig/iptables /etc/sysconfig/iptables.orig; fi')
        sudo ('cp %s/iptables.headnode /etc/sysconfig/iptables' % app.env.conf)
        sudo ('service iptables stop') # spark assigns random ports for driver/worker communication.
    def clean ():
        sudo ('cp /etc/sysconfig/iptables.orig /etc/sysconfig/iptables')
        sudo ('service iptables stop')
        sudo ('service iptables status')
    return su.execute_op (mode, install, clean)

@task
@parallel
@hosts(app.env.work_nodes)
def work (mode="install"):
    work_21 (mode)

''' Applies to every worker node. Configure worker and firewall. '''
@task
@parallel
@hosts(app.env.work_nodes)
def work_24 (mode="install"):
    mesosphere_repo (mode)
    # Needed by evry app
    su.yum_install (mode, 'postgresql-devel', 'postgresql-devel')
    base (mode)
    def install ():
        su.yum_install (mode, "mesos-", "mesos")
        sudo ("systemctl enable mesos-slave")
        sudo ("service mesos-slave restart")
        sudo ("service mesos-slave status")
        sudo ('service iptables stop')
        # Support application installation
        mkdir_mine (su.opt, env.user)
    def clean ():
        with settings(warn_only=True):
            sudo ('service iptables start')
            sudo ('service iptables status') 
            sudo ("systemctl disable mesos-slave")
            sudo ("service mesos-slave stop")
            su.yum_install (mode, "mesos-", "mesos")
    return su.execute_op (mode, install, clean)

@task
@parallel
@hosts(app.env.work_nodes)
def work_21 (mode="install"):
    sudo ('rm -rf /opt/app/mesos/mesos-0.21.0/src/')
    sudo ('yum clean all')
    mesos_21_install (mode)
    mesosphere_repo (mode)
    # Needed by evry app
    su.yum_install (mode, 'postgresql-devel', 'postgresql-devel')
    base (mode)
    def install ():
        zk_string = run ('cat /etc/mesos/zk')
        su.generate_config (
            template='%s/mesos/mesos-slave.service.custom' % app.env.conf,
            context={
                'EXE'      : '%s/mesos/mesos-0.21.0/bin/mesos-slave.sh' % su.opt,
                'ZK'       : zk_string,
                'LOGDIR'   : '/var/log/mesos'
            },
            output='/usr/lib/systemd/system/mesos-slave.service',
            use_sudo=True)
        sudo ("systemctl enable mesos-slave")
        sudo ("service mesos-slave restart")
        sudo ("service mesos-slave status")
        sudo ('service iptables stop')
        # Support application installation
        mkdir_mine (su.opt, env.user)
    def clean ():
        with settings(warn_only=True):
            sudo ('service iptables start')
            sudo ('service iptables status') 
            sudo ("systemctl disable mesos-slave")
            sudo ("service mesos-slave stop")
            su.yum_install (mode, "mesos-", "mesos")
    return su.execute_op (mode, install, clean)    

''' Applies to every machine '''
@task
@parallel
@hosts(cluster_nodes)
def base (mode="install"):
    def install ():
        # Deploy base apps everywhere.
        su.install_base_apps (mode)
        # Deploy standard bashrc to all worker nodes (controlling user environment).
        sudo ('cp %s/%s.bashrc /home/%s/.bashrc' % (app.env.conf, env.user, env.user))
        sudo ('if [ "$(grep -c stars ~/.bashrc)" -eq 0 ]; then echo source %s/env.sh >> ~/.bashrc; fi' % app.env.conf)
        # Deploy zookeeper configuration (identifying quorum hosts) to all nodes.
        addr = local ("ping -c 1 %s | awk 'NR==1{gsub(/\(|\)/,\"\",$3);print $3}'" % zookeeper_nodes, capture=True)
        print "zookeeper hosts: %s" % addr
        text = "%s:2181" % addr
        sudo ('sh -c "if [ -d /etc/mesos ]; then echo zk://%s/mesos > /etc/mesos/zk; fi" ' % text)
    def clean ():
        sudo ('rm -rf /etc/mesos/zk')
        su.install_base_apps (mode)
    return su.execute_op (mode, install, clean)

''' Configure zookeeper cluster '''
@task
@parallel
@hosts(app.env.zookeeper_nodes)
def zoo (mode="install"):
    def install ():
        su.yum_install (mode, 'mesosphere-zookeeper', 'mesosphere-zookeeper')
        addr = socket.gethostbyname (app.env.head_nodes [0])
        su.generate_config (template="%s/zoo.cfg" % app.env.conf,
                            context={ 'IPADDR' : addr },
                            output='/etc/zookeeper/conf/zoo.cfg',
                            use_sudo=True)
        su.configure_service (mode, 'zookeeper')
    def clean ():
        su.configure_service (mode, 'zookeeper')
        su.yum_install (mode, 'mesosphere-zookeeper', 'mesosphere-zookeeper')
        sudo ('rm -rf /var/lib/zookeeper')
        sudo ('rm -rf /var/log/zookeeper')
        sudo ('rm -rf /etc/zookeeper')
    return su.execute_op (mode, install, clean)
        
''' Configure general tools underlying the cluster '''
@task
@parallel
@hosts(app.env.zookeeper_nodes)
def core (mode="install"):
    run('mkdir -p %s' % su.dist)
    run('mkdir -p %s' % su.stack)
    run('mkdir -p %s' % su.app)
    with cd (su.dist):
        run ("""wget --quiet --timestamping --no-cookies --no-check-certificate \
                     --header "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie" \
                     "http://download.oracle.com/otn-pub/java/jdk/8u60-b27/jdk-8u60-linux-x64.tar.gz" """)
    with cd (su.stack):
        spark (mode)
        maven (mode)
        su.deploy_tar     (mode, 'jdk')
        su.deploy_uri_tar (mode, 'scala')
        su.deploy_uri_tar (mode, 'node')
        su.deploy_uri_tar (mode, 'mongodb')
        su.deploy_uri_tar (mode, 'hadoop')
        su.deploy_uri_tar (mode, 'tachyon')

@task
@hosts(app.env.zookeeper_nodes)
def maven (mode="install"):
    su.deploy_uri_tar (mode, 'maven')
    run ('cp %s/maven/settings.xml %s/maven/current/conf' % (app.env.conf, su.stack))

@task
@hosts(app.env.zookeeper_nodes)
def spark (mode="install"):
    su.deploy_uri_tar (mode, 'spark')
    su.generate_config (
        template='%s/spark/spark-env.sh' % app.env.conf,
        context={
            'STARS_CONF' : app.env.conf,
            'STARS_DIST' : su.dist
        },
        output='%s/spark/current/conf/spark-env.sh' % su.stack)

@task
def all (mode="install"):
    execute (base,  mode=mode,  hosts=cluster_nodes)
    execute (core,  mode=mode,  hosts=app.env.work_nodes)
    execute (head,  mode=mode,  hosts=app.env.head_nodes)
    execute (work,  mode=mode,  hosts=app.env.work_nodes)

@task
@parallel
@hosts(cluster_nodes)
def status ():
    run ('free -h')
    run ('vmstat')
    app.status ()

@task
@hosts(app.env.head_nodes[0])
def backup ():
    run ('%s/evry/bin/backup backup' % su.app)
