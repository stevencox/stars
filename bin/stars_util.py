#########################################################################
##
## Cluster installer library
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
from fabric.api import settings
from fabric.api import run
from fabric.api import sudo
from fabric.contrib.files import exists
from importlib import import_module

root = os.environ ['STARS_HOME']

if not os.path.isdir (root):
    raise ValueError ("STARS_HOME must be set to the root directory of the stars installation. value[%s]" % root)

app = '%s/app' % root
stack = '%s/stack' % root
var = '%s/var' % root
dist = '%s/dist' % root
opt = '/opt/app'
orchestration = '%s/orchestration' % opt

''' Concatenate lists of tuples '''
def concat (T):
    A = []
    for element in T:
        if isinstance(element, basestring):
            A.append (element)
        elif isinstance (element, tuple):
            for i in element:
                A.append (i)
    return tuple (A)

# Third party libraries to install
dist_map = {
    'spark'      : 'http://apache.arvixe.com/spark/spark-1.5.0/spark-1.5.0-bin-hadoop2.6.tgz',
    'scala'      : 'http://www.scala-lang.org/files/archive/scala-2.10.4.tgz',    
    'jdk'        : 'jdk-8u60-linux-x64.tar.gz',
    'maven'      : 'http://apache.mirrors.lucidnetworks.net/maven/maven-3/3.3.3/binaries/apache-maven-3.3.3-bin.tar.gz',
    'mongodb'    : 'https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-rhel70-3.0.6.tgz',
    'node'       : 'https://nodejs.org/dist/v0.12.7/node-v0.12.7-linux-x64.tar.gz',
    'hadoop'     : 'http://apache.arvixe.com/hadoop/common/hadoop-2.6.0/hadoop-2.6.0.tar.gz',
    'tachyon'    : 'http://tachyon-project.org/downloads/files/0.7.1/tachyon-0.7.1-bin.tar.gz'
}

def get_env ():
    env_module = os.environ ['env']
    result = None
    if env_module:
        result = import_module (env_module)
    else:
        raise NameError ("The 'env' environment variable must be specified and must resolve to the name of a python module.")
    return result 

def add_dist (name, source):
    dist_map[name] = source

# Apps we want on all machines
base_apps = {
    'python-virtualenv' : 'python-virtualenv',
    'git-'              : 'git',
    'emacs-24'          : 'emacs'
}

def add_base_app (name, package_name):
    base_apps[name] = package_name

def install_base_apps (mode="install"):
    for app in base_apps:
        su.yum_install (mode, app, base_apps[app])

##################################################################
##
## Utilities
##
##################################################################

''' uniformly select install or clean operation based on the mode parameter '''
def execute_op (mode, install, clean):
    installed = True
    if mode == "install":
        install ()
    elif mode == "clean":
        clean ()
        installed = False
    return installed

# File permissions

''' Make a directory owned by the env user '''
def mkdir_mine (d, user):
    sudo ('mkdir -p %s' % d)
    sudo ('chown %s %s' % (user, d))

''' Make a file owned by the env user '''
def mkfile_mine (f, user):
    sudo ('touch %s' % f)
    sudo ('chown %s %s' % (user, f))
    
# Tar

''' Untar a file and create a symbolic link called current to the extracted folder '''
def untar_and_link (name, file_name):
    run ('if [[ ! -h current ]]; then tar xzf %s/%s; fi' % (dist, file_name))
    run ('if [[ ! -h current ]]; then ln -s *%s* current; fi' % name)
    run ('ls -lisa')

''' Deploy a tar based on a URI '''
def deploy_uri_tar (mode, name):
    path = "%s/%s" % (stack, name)
    def install ():
        uri = dist_map [name]
        with cd (dist):
            run ('wget --timestamping --quiet %s' % uri)
        run ('mkdir -p %s' % path)
        with cd (path):
            untar_and_link (name, os.path.basename (uri))
    def clean ():
        run ('rm -rf %s' % path)
    return execute_op (mode, install, clean)

''' Deploy an RPM based on a URI '''
def deploy_uri_rpm (mode, name):
    def install ():
        yum_install (mode, name, dist_map [name])
    def clean ():
        yum_install (mode, name, name)
    return execute_op (mode, install, clean)

''' Deploy a tar '''
def deploy_tar (mode, name):
    path = "%s/%s" % (stack, name)
    def install ():
        run ('mkdir -p %s' % path)
        with cd (path):
            untar_and_link (name, dist_map [name])
    def clean ():
        run ('rm -rf %s' % path)
    return execute_op (mode, install, clean)

# Yum

''' Add the MesoSphere Repo '''
def mesosphere_repo (mode="install"):
    def install ():
        mesosphere_repo='http://repos.mesosphere.com/el/7/noarch/RPMS/mesosphere-el-repo-7-1.noarch.rpm'
        sudo ('if [ -z "$( rpm -qa | grep mesosphere-el-repo )" ]; then yum install --assumeyes --quiet %s; fi' % mesosphere_repo)
    def clean ():
        yum_install (mode, "mesosphere-el-repo", "mesosphere-el-repo")
    return execute_op (mode, install, clean)

''' Determine if a package is installed '''
def yum_installed (package):
    return 'if [ "$(rpm -qa | grep -c %s)" -gt 0  ]; then true; fi' % package

''' Get a yum command ''' 
def get_yum_command (sudo=True, install=True):
    command = Template('if [ "$$(rpm -qa | grep -c %s)" $compareop 0  ]; then $yum $command --assumeyes --quiet %s; fi')
    yum = "sudo yum" if sudo else "yum"
    if install:
        command = command.substitute (yum=yum, compareop='==', command='install')
    else:
        command = command.substitute (yum=yum, compareop='-gt', command='remove')
    return command

''' Invoke yum '''
def yum_install (mode, query, package):
    def install ():
        sudo (get_yum_command () % (query, package))
    def clean ():
        sudo (get_yum_command(install=False) % (query, package))
    return execute_op (mode, install, clean)

def yum_install_all (mode, packages):
    packages = packages.split (' ')
    for p in packages:
        yum_install (mode, p, p)

# SystemD

''' Configure a systemd service ''' 
def configure_service (mode, service):
    def install ():
        sudo ('systemctl enable %s' % service)
        sudo ('systemctl restart %s' % service)
        sudo ('systemctl status %s' % service)
    def clean ():
        with settings(warn_only=True):
            sudo ('systemctl stop %s' % service)
            sudo ('systemctl disable %s' % service)
    return execute_op (mode, install, clean)

def generate_config (template, context, output=None, use_sudo=False):
    result = None
    with open (template) as stream:
        template_obj = Template (stream.read ())
        result = template_obj.safe_substitute (context)
    if output:
        put (StringIO.StringIO (result), output, use_sudo=use_sudo, temp_dir='/tmp')
    return result
