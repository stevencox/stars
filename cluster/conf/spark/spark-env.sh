#!/usr/bin/env bash                                                                                                                                                                                                                           

SPARK_LOCAL_IP=$(hostname -i | sed -e "s, ,,g")
export LIBPROCESS_IP=${SPARK_LOCAL_IP}

MESOS_NATIVE_JAVA_LIBRARY=/usr/local/lib/libmesos.so
export MESOS_MASTER=mesos://zk://stars-dc0.edc.renci.org:2181,stars-dc1.edc.renci.org:2181,stars-dc2.edc.renci.org:2181/mesos

export MASTER=$MESOS_MASTER
export SPARK_EXECUTOR_URI=/opt/spark-2.1.0-bin-hadoop2.6.tgz

export SPARK_DAEMON_JAVA_OPTS+=""

echo "Initializing Spark Environment"
source /projects/stars/app/evry/conf/env.sh

export SPARK_HOME=/opt/spark
export PATH=$SPARK_HOME/bin:$PATH
unset HADOOP_CONF_DIR
