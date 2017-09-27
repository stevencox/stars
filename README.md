# Stars

## What Is It?

Stars automates data science stacks.

Stars' end game is composing scalable data science stacks with predictability and reproducibility.

What follows is an overview introducing Stars' capabilities. Each section also lists, by way of example, specific components and their roles in achieving the system's overall goals.

### **Applications**:

Stars is used to deliver best in class data science solutions. It has been used in multiple federally funded research projects for several years. Our team does semantic web analytics using graph databases like Blazegraph in the bioinformatics domain. We've used Spark to parallelize generation of Gensim word2vec models over a corpus of medical literature. We share computing notebooks via Zeppelin with collaborators at federal agencies and other partner institutions. To do this work, we use:

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

Underlying applications is a highly scalable container orchestration platform with support for long running tasks, scheduled jobs, and support of dynamic service discovery.

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

For all of this to be useful, there need to be programming tools. We have found a small set adequate for the needs of the communities we work with but will soon be adding more. Scala and R are top of the list.

* **Languages/Compilers**: Suites of commonly used programming tools.

| System        | Version  |     Role      | Description                                  |
| --------------|----------|---------------|----------------------------------------------|
| Java JDK      | 1.8.0    | Languages     | Required by many modern big data stacks.     |
| Maven         | 3.3.9    | Languages     | Build and artifact management for Java.      |
| Python        | 3.6      | Languages     | Among the most common data science languages.|

### **DevOps**

DevOps is the merger of software development and operations. We will make infrastructure code. We now manage the entire architecture of Stars as repeatable rules encoded in software.

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

## Usage

### Get the Code

Get the code...

```
pip install ansible=2.2.0.0
git clone git@github.com:stevencox/stars.git
cd stars/cluster/system
```
## Configuration

### Provisioning Compute and Storage Infrastructure

At this point you'll want to provision some master nodes and some workers.

Three masters is a good number for an HA system. Zookeeper uses a protocol that requires a concensus so there are numbers of machines that just don't make a lot of sense. One is fine for testing. Three is good for production.

The number of workers is entirely up to your usage scenario.
It's a good idea to:
* Make the /var partition 50GB or greater. Docker uses this as its storage.
* Launch docker containers with the "--rm" option to remove containers.

Stars has been tested on CentOS 7.

### Structure

1. **Vault**: Create an Ansible vault to hold secrets:
   * Follow instructions here to [create a vault](http://docs.ansible.com/ansible/latest/playbooks_vault.html)
   * Be sure to name the vault password file **~/.vault_password.txt** 
2. **Variables**: Set variables appropriately for each machine role in cluster/system/group_vars
3. **Staging**: Add staging machines to cluster/system/staging
4. **Production**: Add production machines to cluster/system/production

```
└── system
    ├── ci.yml
    ├── conf
    │   ├── chronos
    │   └── marathon
    ├── group_vars
    │   ├── all
    │   ├── ci
    │   ├── masters
    │   └── workers
    ├── host_vars
    │   └── hostname1
    ├── masters.yml
    ├── production
    ├── README.md
    ├── roles
    │   ├── blazegraph
    │   ├── common
    │   ├── docker
    │   ├── java-se
    │   ├── jeffhung.java-se
    │   ├── jeffhung.localrepo
    │   ├── jenkins
    │   ├── lightning
    │   ├── livy
    │   ├── localrepo
    │   ├── marathon
    │   ├── maven
    │   ├── mesos
    │   ├── mesos-dns
    │   ├── nginx
    │   ├── python
    │   ├── spark
    │   ├── stars
    │   ├── zeppelin
    │   └── zookeeper
    ├── site.yml
    ├── staging
    ├── webservers.yml
    ├── workers.retry
    └── workers.yml
```

## Running

You'll have a toolkit like this:

```
├── bin
│   ├── backup
│   ├── compose
│   ├── nuke-docker
│   ├── restart
│   ├── run
│   └── stars
```

1. **compose**: Clone Ansible roles to create a playbook. This will be configurable in the future.
```
bin/compose
```
2. **stars**: Deploy the entire system or individual components.
```
cd system
../bin/stars <host-role> <environment>
eg: bin/stars workers staging
eg: bin/stars masters staging
eg: bin/stars site production
```
3. **backup**: Backup apps and tasks from Marathon and Chronos. Will create conf directory in $PWD.
```
bin/backup
```
4. **restart**: Restart services.



