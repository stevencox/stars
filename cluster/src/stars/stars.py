import argparse
import chronos
import json
import glob
import logging
import re
import os
import sys
import traceback
from pprint import pprint
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
from collections import namedtuple
from kazoo.client import KazooClient
from marathon import MarathonClient
from marathon import MarathonApp

class LoggingUtil(object):
    @staticmethod
    def init_logging (name):
        FORMAT = '%(asctime)-15s %(filename)s %(funcName)s %(levelname)s: %(message)s'
        logging.basicConfig(format=FORMAT, level=logging.INFO)
        return logging.getLogger(name)
logger = LoggingUtil.init_logging (__file__)

class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """
    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for retrieval later
        """
        host = result._host
        value = result._result
        if 'msg' in value and len(value['msg']) > 0:
            logger.info ("%s(chg=%s): %s", result._host, value['changed'], value['msg'])
        else:
            output = False
            if 'stdout' in value and len(value['stdout']) > 0:
                output = True
                logger.info ("%s(chg=%s)(stdout): %s", result._host, value['changed'], value['stdout'])
            if 'stderr' in value and len(value['stderr']) > 0:
                output = True
                logger.info ("%s(chg=%s)(stderr): %s", result._host, value['changed'], value['stderr'])
#            if not output:
#                logger.info ("%s(chg=%s)(stderr): %s", result._host, value['changed'], json.dumps (value, indent=2))


class Automator (object):
    def __init__(self, play_name, vault_password_file):
        self.play_name = play_name
        self.vault_password_file = vault_password_file

    def execute (self, hosts, environment, module="shell", command="ls"):
        Options = namedtuple('Options', ['connection', 'module_path', 'forks', 'become', 'become_method', 'become_user', 'check'])
        # initialize needed objects
        variable_manager = VariableManager()
        loader = DataLoader()
        options = Options(connection='ssh', module_path=None, forks=10, become=None, become_method=None, become_user=None, check=False)
        passwords={}
        if self.vault_password_file:
            passwords = dict(vault_pass=open(os.path.expanduser(self.vault_password_file), 'r').read ().strip ())
            loader.set_vault_password (passwords['vault_pass'])

        # Instantiate our ResultCallback for handling results as they come in
        results_callback = ResultCallback()

        # create inventory and pass to var manager
        inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=environment)
        variable_manager.set_inventory(inventory)

        # create play with tasks
        play_source =  dict(
            name = self.play_name,
            hosts = hosts,
            gather_facts = 'no',
            tasks = [
                dict(action=dict(module=module, args=command), register='shell_out'),
                dict(action=dict(module='debug', args=dict(msg='{{shell_out.stdout}}')))
            ]
        )
        play = Play().load(play_source, variable_manager=variable_manager, loader=loader)
        
        # actually run it
        tqm = None
        try:
            logger.info ("Executing: command [%s] in play %s on hosts %s in environment %s", command, self.play_name, hosts, environment)
            tqm = TaskQueueManager(
                inventory=inventory,
                variable_manager=variable_manager,
                loader=loader,
                options=options,
                passwords=passwords,
                stdout_callback=results_callback,  # Use our custom callback instead of the ``default`` callback plugin
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

class Configuration (object):
    # https://kazoo.readthedocs.io/en/latest/index.html
    def __init__(self, zookeeper_hosts):
        self.zookeeper_hosts = zookeeper_hosts
        self.zk = KazooClient(hosts=self.zookeeper_hosts) 
        self.zk.start ()
    def listr (self, path, pattern=None, result=[]):
        children = self.zk.get_children (path)
        for child in children:
            if pattern != None and re.match (pattern, child) == None:
                continue
            result.append ("{0}/{1}".format (path, child))
            self.listr ("{0}/{1}".format (path, child), pattern=pattern, result=result)
        return result
    def rmr (self, pattern):
        full = self.listr ("/")
        for i in full:
            if re.match (pattern, i):
                logger.debug (" --- {0}".format (i))
                try:
                    self.zk.delete(i, recursive=True)
                except:
                    pass
                    #traceback.print_exc ()

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')
class Names(object):
    @staticmethod
    def snake_case(name):
        result = None
        if isinstance (name, dict):
            result = { Names.snake_case (k): v for k, v in name.items ()}
        elif isinstance (name, str):
            s1 = first_cap_re.sub(r'\1_\2', name)
            result = all_cap_re.sub(r'\1_\2', s1).lower()
        else:
            result = name
        return result

class Services (object):
    def __init__(self, endpoints):
        self.marathon = MarathonClient (endpoints)
    def list (self):
        return self.marathon.list_apps()
    def clean (self, pattern=None):
        apps = self.list ()
        for app in apps:
            try:
                if pattern==None or re.match (pattern, app.id) != None:
                    logging.info ("Deleting app: %s", app.id)
                    self.marathon.delete_app (app.id, force=True)
                else:
                    logging.info ("Ignoring app %s. Did not match pattern %s", app.id, pattern)
            except:
                logger.info ("Unable to delete app %s", app.id)
                traceback.print_exc ()
    def register_services (self, service_registry="conf/marathon"):
        for app_def in glob.glob (os.path.join (service_registry, "*json")):
            with open (app_def, "r") as stream:
                args = json.loads (stream.read ())
                app_id = args['id']
                args = Names.snake_case (args)
                logger.debug ("Creating service: %s", json.dumps (args, indent=2))
                args['tasks'] = []
                app = MarathonApp (**args)
                try:
                    logging.info ("Creating app [id=>{0}]".format (app_id))
                    self.marathon.create_app (app_id, app)
                except:
                    traceback.print_exc ()

class Scheduler (object):
    def __init__(self, endpoints, proto="http"):
        self.client = chronos.connect(endpoints, proto="https")
    def list (self):
        return self.client.list()
    def run_all (self):
        for j in jobs:
            self.run (j['name'])
    def run (self, job_id):
        logger.debug ("Running job %s", job_id)
        self.client.run (job_id)

class System (object):
    def __init__(self, services_endpoints, scheduler_endpoints, vault_password_file):
        self.services  = Services (endpoints=services_endpoints)
        self.scheduler = Scheduler (endpoints=scheduler_endpoints, proto="https")
        self.automator = Automator (play_name="RENCI_Stars_Auto", vault_password_file=vault_password_file)

class Stars (System):
    def __init__(self, services_endpoints, scheduler_endpoints, vault_password_file):
        super (Stars, self).__init__(services_endpoints, scheduler_endpoints, vault_password_file)
        self.services = {
            'masters' : [ "mesos-dns", "marathon", "mesos-master", "zookeeper" ],
            'workers' : [ "mesos-slave", "docker" ]
        }
    def service (self, hosts="workers", env="staging", cmd="stop"):
        if hosts in self.services:
            services = self.services [hosts]
            if cmd=='start':
                services = reversed (services)
            for service in services:
                self.automator.execute (hosts=hosts, environment=env, command="sudo service {0} {1}".format (service, cmd)) 

def x ():
    print ("services: {0}".format (list (map (lambda s : s.id, system.services.list ()))))
    system.services.clean () #delete_by_pattern (".*-auto$")
    system.services.register_services ()


def main ():
    parser = argparse.ArgumentParser ()
    parser.add_argument ("--env",     help="Environment - an inventory of hosts")
    parser.add_argument ("--hosts",   help="Group of hosts to run on")
    parser.add_argument ("--module",  help="Ansible module to run", default="shell")
    parser.add_argument ("--cmd",     help="Module command to run", default="ls")
    parser.add_argument ("--vault",   help="Vault password file", default="~/.vault_password.txt")
    parser.add_argument ("--run",     help="Execute command", action='store_true')
    parser.add_argument ("--service", help="Send command to services")
    args = parser.parse_args ()

    system = Stars (services_endpoints  = [ "https://stars-app.renci.org/marathon"],
                    scheduler_endpoints = [ "stars-app.renci.org/chronos" ],
                    vault_password_file = args.vault)

    if args.service:
        system.service (hosts=args.hosts,
                        env=args.env,
                        cmd=args.service)
        
    elif args.cmd:
        system.automator.execute (hosts=args.hosts,
                                  environment=args.env,
                                  module=args.module,
                                  command=args.cmd)
#main ()

config = Configuration ('stars-dc0.edc.renci.org:2181,stars-dc1.edc.renci.org:2181,stars-dc2.edc.renci.org:2181')
#pprint (config.listr ('marathon'))

config.rmr (".*auto$")
for k in config.listr ("/"):
    print ("  {0}".format (k))
for k in config.listr ("/", pattern=".*auto$"):
    print ("(l)  {0}".format (k))


def pretty(d, indent=0):
   for key, value in d.items():
      print('\t' * indent + str(key))
      if isinstance(value, dict):
         pretty(value, indent+1)
      else:
         print('\t' * (indent+1) + str(value))

# python ../bin/restore.py --run --hosts workers --env staging --cmd "sudo service docker status"



