# Stars
Stars automates the installation and configuration of the software stack needed to run big data applications on the Berkeley Data Analytics Stack (BDAS)

**Current Status**: Installs Java, Python, Maven, Docker, Zookeeper, Mesos, Marathon, and Chronos to a cluster. We still haven't settled on an orchestration approach so it's not ready for prime time. But Marathon can now pull, run, and scale docker images on Mesos.

It installs common compiler and interpreter infrastructure including:
- Java
- Maven
- Python3

It then installs distributed computing cluster infrastructure:
- Apache Zookeeper
- Apache Mesos
- Mesosphere Marathon
- AirBnB Chronos
- Apache Mesos
- Apache Zeppelin

The installation and configuration is automated with Ansible.

## Tools
The Stars cluster module contains scripts for
- Assembling required Ansible roles
- Executing those roles
- Currently, we have to run some additional, non-Ansible configuration
  - This will be generalized via Ansible

In the structure:
```
.
├── bin
│   ├── clone-roles
│   ├── connect
│   └── diff-repos
├── conf
│   ├── marathon
│   │   └── marathon.service
│   ├── mesos
│   │   ├── mesos-master.service
│   │   ├── mesos-master.service.0
│   │   ├── mesos-master.service.1
│   │   └── mesos-slave.service
│   └── zookeeper
│       └── zoo.cfg
```
The bin directory contains scripts to:
- clone-roles: Clone GitHub repos containing needed roles.
- connect: Non-Ansible managed configurations.
- diff-repos: Tool for diffing roles from cloned repos.

## Running

1. **Clone Roles** There are a few roles that are in the cluster module itself. They include the common role and, currently, the mesos-dns roles. Others are assembled from external GitHub repos by the clone-roels script.
To clone github repositories containing ansible roles we depend on, execute:

```
bin/clone-roles
```

When that's done, you should have a directory structure like this:
```
└── system
    ├── group_vars
    │   ├── all
    │   ├── master
    │   └── workers
    ├── host_vars
    │   ├── hostname1
    │   ├── stars-dc0.edc.renci.org
    │   └── stars-dc1.edc.renci.org
    ├── log.txt
    ├── masters.retry
    ├── masters.yml
    ├── production
    ├── README.md
    ├── repo-diffs.txt
    ├── roles
    │   ├── chronos
    │   ├── common
    │   ├── docker
    │   ├── jeffhung.java-se
    │   ├── jeffhung.localrepo
    │   ├── marathon
    │   ├── maven
    │   ├── mesos
    │   ├── mesos-dns-client
    │   ├── mesos-dns-server
    │   ├── nginx
    │   ├── spark
    │   ├── zeppelin
    │   └── zookeeper
    ├── site.retry
    ├── site.yml
    ├── staging
    ├── webservers.yml
    ├── workers.yml
    └── zookeeper.yml
```
2. **Masters**: Run the Ansible playbook to install and configure masters:
```
ansible-playbook masters.yml -i production --limit masters
```

3. **Workers**: Configure Mesos workers
```
ansible-playbook workers.yml -i production --limit workers
```

4. **Webservers**: Configure webservers
```
ansible-playbook webservers.yml -i production --limit webservers
```

5. **Connect**: Until we integrate these changes into Ansible roles, we run a script that configures a few specific things:
```
bin/connect
```

