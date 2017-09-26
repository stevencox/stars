# Stars

## What Is It?

Stars automates data science stacks.

Stars' end game is to be able to compose data science stacks with predictability and reproducibility.

Here, in overview form is a summary of the capabilities Stars includes and some of the systems it uses to achieve them:

### **Applications**:

* **Analytics**: Mapreduce, streaming, graph, machine learning, and SQL at scale.
* **Notebooks**: Connect the best in notebook computing to enable scalability and collaboration.
* **Visualization**: Service for generating visualizations suitable for embedding in data science notebooks.

| System        | Version  |     Role      | Description                                  |
| --------------|----------|---------------|----------------------------------------------|
| Zeppelin      | 0.7.x    | Notebooks     | Collaborative notebook computing interface.  |
| Ligthning     | 1.0.1    | Visualization | Lightweight visualization server.            |
| Livy          | 0.4.0    | Notebooks     | Allows Jupyter Lab to connect to Spark.      |
| Blazegraph    | 2.1.4    | Analytics     | RDF database and SPARQL endpoint.            |
| Spark         | 1.2.2    | Analytics     | Mapreduce, Graph, ML, Streaming engine.      |

### **Platform**

* **Discovery**: Services are discovered and routed automatically via DNS.
* **Services**: Long running services are managed with Marathon.
* **Scheduler**: Scheduled tasks are managed with Chronos.
* **Orchestration**: Delegate data center management to a scalable orchestrator like Mesos

| System        | Version  |     Role      | Description                                  |
| --------------|----------|---------------|----------------------------------------------|
| Mesos-DNS     | 0.6.0    | Discovery     | DNS name resolution for launched contaiers.  |
| Chronos       | 3.0.0    | Scheduler     | Scheduled hierarchical tasks for Mesos.      |
| Marathon      | 1.4.7    | Services      | Long running service manager for Mesos.      |
| Mesos         | 1.3.x    | Orchestration | Container orchestration and data center OS.  |
| Zookeeper     | 3.4.6    | Configuration | Distributed configuration management.        |

### **Tools**

* **Languages/Compilers**: Suites of commonly used programming tools.

| System        | Version  |     Role      | Description                                  |
| --------------|----------|---------------|----------------------------------------------|
| Java JDK      | 1.8.0    | Languages     | Required by many modern big data stacks.     |
| Maven         | 3.3.9    | Languages     | Build and artifact management for Java.      |
| Python        | 3.6      | Languages     | Among the most common data science languages.|

### **DevOps**

* **DevOps**: Automate core system architecture components with Ansible
* **Containers**: Automate application level data science stacks with Docker and Ansible.

| System        | Version  |     Role      | Description                                  |
| --------------|----------|---------------|----------------------------------------------|
| Docker        | 1.12.6   | Containers    | Compose, share custom machine environments.  |
| Ansible       | 2.2.0.0  | Automation    | Automate infrastructure architecture.        |

### **Cloud**

Stars is going to the cloud. More on this soon.

## How Do I Interact With It?

Management of services within the container orchestrator uses Marathon. The interface makes it easy to control resource allocation to applications including CPUs, memory, and number of instances. It also takes care of restarting failed instances, supports Docker containers, and several sophisticated service deployment scenarios to support micro-services and continuous deployment.

![Marathon UI](https://mesostars.files.wordpress.com/2017/09/marathon.png)

The Mesos interface shows individual tasks started by frameworks. It also lets users navigate to each tasks' sandbox, or output area:

![Mesos UI](https://mesostars.files.wordpress.com/2017/09/mesos1-3-0.png)

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

