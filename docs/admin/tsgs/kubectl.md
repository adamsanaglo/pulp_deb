# KubeCtl
This document covers some useful kubectl commands, to ensure they're not forgotten as we improve automation.
The easiest way to run these commands is via CloudShell, as kubectl is already installed (from a trusted source).
- For PPE, you should already have standing access
- For Prod, you will have to JiT to subscription `ae06cb0d-47c5-420b-ac59-8e84bef194bb`
- Tux-dev doesn't currently use AKS, so these steps are irrelevant for that environment

## Get Kubectl Creds
In order to use kubectl, you will first need to get credentials.
Luckily, az cli has a convenient method to do this.
```bash
$ az aks get-credentials --resource-group $resourceGroup --name $clusterName
```
|Environment|ResourceGroup|Cluster|
|-----------|-------------|-------|
|PPE|pmc-ppe-rg|pmc-ppe-kube-cluster|
|Prod|pmcprod|pmc-prod-kube-cluster|

## Get Pods
```bash
$ kubectl get pods
NAME                             READY   STATUS    RESTARTS   AGE
api-pod-7cb574d44f-dd25n         2/2     Running   0          10h
api-pod-7cb574d44f-q4mbm         2/2     Running   0          10h
nginx-api-7ff54575f6-4jb6x       1/1     Running   0          10h
nginx-api-7ff54575f6-66jkd       1/1     Running   0          10h
nginx-content-6fdd54c586-k775t   1/1     Running   0          10h
nginx-content-6fdd54c586-qdm6s   1/1     Running   0          10h
pulp-content-6f7775487-7xstq     1/1     Running   0          10h
pulp-content-6f7775487-xv7jw     1/1     Running   0          10h
worker-pod-75889499fd-jbr7w      2/2     Running   0          10h
worker-pod-75889499fd-qkqgr      2/2     Running   0          10h
```

## List Containers in a Pod
Kubectl doesn't give us an easy way to do this, so we have to get creative.
```bash
$ kubectl get pods $podName -o jsonpath='{.spec.containers[*].name}'
```

## Get Logs
```bash
$ kubectl logs -c pmc --since 10h api-pod-7cb574d44f-dd25n
$ kubectl logs -c pulp-api --since 10h api-pod-7cb574d44f-dd25n
```

## Create a Shell/Process in a Container
```bash
$ kubectl exec -it -c ${container} $podName -- /bin/bash
$ kubectl exec -it -c ${container} $podName -- /bin/bash -c $/path/to/command
```
