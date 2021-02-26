#!/bin/bash
### Run on 180-131.research.maxgigapop.net (a.k.a. master-131)
# config for FE
kubectl create secret generic sense-httpdprivkey --from-file=httpdprivkey=/etc/letsencrypt/live/180-131.research.maxgigapop.net/privkey.pem
kubectl create secret generic sense-httpdcert --from-file=httpdcert=/etc/letsencrypt/live/180-131.research.maxgigapop.net/cert.pem
kubectl create secret generic sense-hostkey --from-file=hostkey=/etc/letsencrypt/live/180-131.research.maxgigapop.net/privkey.pem
kubectl create secret generic sense-hostcert --from-file=hostcert=/etc/letsencrypt/live/180-131.research.maxgigapop.net/cert.pem
kubectl create secret generic sense-httpdfullchain --from-file=httpdfullchain=/etc/letsencrypt/live/180-131.research.maxgigapop.net/fullchain.pem
kubectl create secret generic sense-environment --from-file=environment=/etc/siterm-mariadb
kubectl create configmap sense-siterm-fe-yaml --from-file=sense-siterm-fe=/etc/dtnrm.yaml

# config for Agents
kubectl create secret generic sense-agent-hostcert --from-file=agent-hostcert=/etc/letsencrypt/live/180-131.research.maxgigapop.net/cert.pem
kubectl create secret generic sense-agent-hostkey --from-file=agent-hostkey=/etc/letsencrypt/live/180-131.research.maxgigapop.net/privkey.pem
kubectl create configmap sense-siterm-agent01-yaml --from-file=sense-siterm-agent=/etc/dtnrm-agent01.yaml
kubectl create configmap sense-siterm-agent02-yaml --from-file=sense-siterm-agent=/etc/dtnrm-agent02.yaml

# deploy site-rm
kubectl apply -f k8s-siterm.yaml
