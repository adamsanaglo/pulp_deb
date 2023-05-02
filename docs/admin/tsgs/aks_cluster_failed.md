# AKS Cluster Failed
PMC package ingestion, and some parts of distribution, run in Azure Kubernetes Service (AKS).
In some instances, the AKS cluster can enter a failed state.
This typically does not impact customers directly, but it can block scale up/down operations and cluster upgrades.
This section explains how to get the cluster back to a healthy state.

## Fix the Nodepool
Cluster failure is usually caused by a problem with the nodepool.
A simple step to diagnose/fix this is to issue an operation to "scale" the nodepool to its expected size.
This will either "fix" the issue (by clearing the failed state) or give you more information about what's wrong, so you can fix it.

1. JiT to the production subscription
2. SSH to the pmc-deploy VM (or use CloudShell via Portal)
3. Run the following command to identify the number of nodes currently in the pool
```bash
$ az aks nodepool show --cluster-name pmc-prod-kube-cluster --name nodepool2 -g pmcprod | grep "count"
```
4. Run the following command to scale the cluster to its current size (the count retrieved from the previous command)
```bash
$ az aks scale -g pmcprod -n pmc-prod-kube-cluster -c $count
```
5. If this doesn't succeed, it should tell you what needs to be fixed.
    - One historical example: there were two management policies trying to write to the same tag, resulting in a conflict. One of the policies had to be deleted.
6. Once the cluster is healthy again, be sure to re-enable auto-scale
```bash
$ az aks update --resource-group pmcprod --name pmc-prod-kube-cluster --enable-cluster-autoscaler --min-count 3 --max-count 30
```

## Fix the cluster
Once the nodepool is healthy, you can attempt to fix the cluster with the following command.
Again, this will either succeed, or give you more information fort analysis.
```bash
$ az aks update -g pmcprod -n pmc-prod-kube-cluster
```

## More Help
Unfortunately, the public docs for fixing a cluster's failed state are somewhat lacking.
If you're unable to return the cluster to a healthy state, file an IcM with the AKS team for more support.
- **Service**: Azure Kubernetes Service
- **Team**: RP