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
kubectl create secret generic sense-agent01-hostcert --from-file=agent-hostcert=certs/fiona.its.hawaii.edu/hostcert.pem -n hawaii-opennsa
kubectl create secret generic sense-agent02-hostcert --from-file=agent-hostcert=certs/prp01.ifa.hawaii.edu/hostcert.pem -n hawaii-opennsa
kubectl create secret generic sense-agent03-hostcert --from-file=agent-hostcert=certs/k8s-dtn-01.uog.edu/hostcert.pem -n hawaii-opennsa

kubectl create secret generic sense-agent01-hostkey --from-file=agent-hostkey=certs/fiona.its.hawaii.edu/hostkey.pem -n hawaii-opennsa
kubectl create secret generic sense-agent02-hostkey --from-file=agent-hostkey=certs/prp01.ifa.hawaii.edu/hostkey.pem -n hawaii-opennsa
kubectl create secret generic sense-agent03-hostkey --from-file=agent-hostkey=certs/k8s-dtn-01.uog.edu/hostkey.pem -n hawaii-opennsa

kubectl create configmap sense-siterm-agent01-yaml --from-file=sense-siterm-agent=dtnrm-agent01.yaml -n hawaii-opennsa
kubectl create configmap sense-siterm-agent02-yaml --from-file=sense-siterm-agent=dtnrm-agent02.yaml -n hawaii-opennsa
kubectl create configmap sense-siterm-agent03-yaml --from-file=sense-siterm-agent=dtnrm-agent03.yaml -n hawaii-opennsa

# deploy site-rm
kubectl apply -f k8s-siterm.yaml -n hawaii-opennsa
