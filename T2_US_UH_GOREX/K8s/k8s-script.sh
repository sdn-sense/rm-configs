#!/bin/bash
### Generate / obtain privkey and cert etc. secret files and place them in K8s folder.

# config for FE
kubectl create secret generic sense-httpdprivkey --from-file=httpdprivkey=privkey.pem -n hawaii-opennsa
kubectl create secret generic sense-httpdcert --from-file=httpdcert=cert.pem -n hawaii-opennsa
kubectl create secret generic sense-hostkey --from-file=hostkey=privkey.pem -n hawaii-opennsa
kubectl create secret generic sense-hostcert --from-file=hostcert=cert.pem -n hawaii-opennsa
kubectl create secret generic sense-httpdfullchain --from-file=httpdfullchain=fullchain.pem -n hawaii-opennsa
kubectl create secret generic sense-environment --from-file=environment=siterm-mariadb -n hawaii-opennsa
kubectl create configmap sense-siterm-fe-yaml --from-file=sense-siterm-fe=dtnrm.yaml -n hawaii-opennsa

# config for Agents
kubectl create secret generic sense-agent-hostcert --from-file=agent-hostcert=cert.pem -n hawaii-opennsa
kubectl create secret generic sense-agent-hostkey --from-file=agent-hostkey=privkey.pem -n hawaii-opennsa
kubectl create configmap sense-siterm-agent01-yaml --from-file=sense-siterm-agent=dtnrm-agent01.yaml -n hawaii-opennsa
kubectl create configmap sense-siterm-agent02-yaml --from-file=sense-siterm-agent=dtnrm-agent02.yaml -n hawaii-opennsa
kubectl create configmap sense-siterm-agent03-yaml --from-file=sense-siterm-agent=dtnrm-agent03.yaml -n hawaii-opennsa

# deploy site-rm
kubectl apply -f k8s-siterm.yaml -n hawaii-opennsa
