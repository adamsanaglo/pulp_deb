# Fetching API Logs
These steps explain how to fetch logs for API and other central services.

1. JiT to the production subscription
2. Login to pmc-deploy (or open CloudShell via portal)
3. Run `kubectl get pods` to see a list of all the pods.
    - The pods we're concerned with are those beginning with `api-pod`
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
4. Within each API pod are two containers
    - `pmc` is *our* API (what our publiushers use)
    - `pulp-api` is Pulp's API, which is not exposed to publishers
5. View logs for the relevant container as follows.
You should check the containers in both pods, since publisher requests could land on either container.
The example below uses t he `--since` parameter, to reduce unnecessary output.
```bash
$ kubectl logs -c pmc --since 10h api-pod-7cb574d44f-dd25n
$ kubectl logs -c pulp-api --since 10h api-pod-7cb574d44f-dd25n
```