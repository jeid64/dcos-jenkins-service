#!/usr/bin/env python3

import logging
from string import Template

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(message)s")


IMPORTS = """
import org.jenkinsci.plugins.mesos.MesosCloud;
import org.jenkinsci.plugins.mesos.MesosSlaveInfo;
import org.apache.mesos.Protos;
import hudson.slaves.NodeProperty;
import jenkins.model.*
import org.jenkinsci.plugins.mesos.MesosSlaveInfo.URI
"""

DOCKER_CONTAINER = """
def containerInfo = new MesosSlaveInfo.ContainerInfo(
                "DOCKER",
                "mesosphere/jenkins-dind:0.7.0-ubuntu",
                true,
                true,
                false,
                true,
                "wrapper.sh",
                new LinkedList<MesosSlaveInfo.Volume>(),
                new LinkedList<MesosSlaveInfo.Parameter>(),
                Protos.ContainerInfo.DockerInfo.Network.BRIDGE.name(),
                new LinkedList<MesosSlaveInfo.PortMapping>(),
                new LinkedList<MesosSlaveInfo.NetworkInfo>()
)
"""

MESOS_SLAVE_INFO_OBJECT = """
def additionalURIs = new LinkedList<URI>()
additionalURIs.add(new URI("file:///etc/docker/docker.tar.gz", false, true))

def mesosSlaveInfo = new MesosSlaveInfo(
        "$labelString",
        $mode,
        "$slaveCpus",
        "$slaveMem",
        "$minExecutors",
        "$maxExecutors",
        "$executorCpus",
        "$diskNeeded",
        "$executorMem",
        "$remoteFSRoot",
        "$idleTerminationMinutes",
        "$slaveAttributes",
        "$jvmArgs",
        "$jnlpArgs",
        "$defaultSlave",
        $containerInfo,
        new LinkedList<URI>(),
        new LinkedList<? extends NodeProperty<?>>()
)
"""

MESOS_SLAVE_INFO_ADD = """
MesosCloud cloud = MesosCloud.get();
cloud.getSlaveInfos().add(mesosSlaveInfo)
cloud.getSlaveInfos().each {
        t ->
            println("Label : " + t.getLabelString())
}
"""

MESOS_SLAVE_INFO_REMOVE = """
MesosCloud cloud = MesosCloud.get();
Iterator<MesosSlaveInfo> it = cloud.getSlaveInfos().iterator()
while(it.hasNext()) {
    MesosSlaveInfo msi = it.next();
    if (msi.getLabelString().equals("$labelString")){
        it.remove()
    }
}
cloud.getSlaveInfos().each {
        t ->
            println("Label : " + t.getLabelString())
}
"""


def add_slave_info(
        labelString,
        service_name,
        slaveCpus="0.1",
        slaveMem="256",
        minExecutors="1",
        maxExecutors="1",
        executorCpus="0.4",
        diskNeeded="0.0",
        executorMem="4096",
        mode="Node.Mode.NORMAL",
        remoteFSRoot="jenkins",
        idleTerminationMinutes="5",
        slaveAttributes="",
        jvmArgs="-Xms16m -XX:+UseConcMarkSweepGC -Djava.net.preferIPv4Stack=true",
        jnlpArgs="-noReconnect",
        defaultSlave="false"
):
    slaveInfo = Template(MESOS_SLAVE_INFO_OBJECT).substitute({
         "labelString": labelString,
         "mode": mode,
         "slaveCpus": slaveCpus,
         "slaveMem": slaveMem,
         "minExecutors": minExecutors,
         "maxExecutors": maxExecutors,
         "executorCpus": executorCpus,
         "diskNeeded": diskNeeded,
         "executorMem": executorMem,
         "remoteFSRoot": remoteFSRoot,
         "idleTerminationMinutes": idleTerminationMinutes,
         "slaveAttributes": slaveAttributes,
         "jvmArgs": jvmArgs,
         "jnlpArgs": jnlpArgs,
         "defaultSlave": defaultSlave,
         "containerInfo": "containerInfo",
    })
    return make_post(
        DOCKER_CONTAINER +
        slaveInfo +
        MESOS_SLAVE_INFO_ADD,
        service_name
    )


def remove_slave_info(labelString, service_name):
    return make_post(
        Template(MESOS_SLAVE_INFO_REMOVE).substitute(
            {
                'labelString': labelString
            }
        ),
        service_name
    )


def make_post(
        post_body,
        service_name
):
    """
    :rtype: requests.Response
    """
    body = IMPORTS + post_body
    log.info('\nMaking request : ========\n{}\n========\n'.format(body))
    '''
    Note: To run locally:
    curl -i -H "Authorization:token=$(dcos config show core.dcos_acs_token)" \
         -k --data-urlencode "script=$(< <path-to-above-script-file>)" \
         https://<dcos-cluster>/service/jenkins/scriptText'
    '''
    import sdk_cmd
    return sdk_cmd.service_request(
        'POST',
        service_name,
        'scriptText',
        log_args=False,
        data={'script': body},
    )
