#!/bin/bash
## Run on K8s master node
### Download /etc/dtnrm-agent01.yaml and /etc/dtnrm-agent01.yaml from https://github.com/sdn-sense/rm-configs/blob/master/T3_US_HAWAII/K8s 
### Generate / obtain privkey and cert etc. secret files and place them on the master node under /MASTER_NODE_PATH/.

# config for FE
kubectl create secret generic sense-httpdprivkey --from-file=httpdprivkey=/MASTER_NODE_PATH/privkey.pem -n hawaii-opennsa
kubectl create secret generic sense-httpdcert --from-file=httpdcert=/MASTER_NODE_PATH/cert.pem -n hawaii-opennsa
kubectl create secret generic sense-hostkey --from-file=hostkey=/MASTER_NODE_PATH/privkey.pem -n hawaii-opennsa
kubectl create secret generic sense-hostcert --from-file=hostcert=/MASTER_NODE_PATH/cert.pem -n hawaii-opennsa
kubectl create secret generic sense-httpdfullchain --from-file=httpdfullchain=/MASTER_NODE_PATH/fullchain.pem -n hawaii-opennsa
kubectl create secret generic sense-environment --from-file=environment=/MASTER_NODE_PATH/siterm-mariadb -n hawaii-opennsa
kubectl create configmap sense-siterm-fe-yaml --from-file=sense-siterm-fe=/etc/dtnrm.yaml -n hawaii-opennsa

# config for Agents
kubectl create secret generic sense-agent-hostcert --from-file=agent-hostcert=/MASTER_NODE_PATH/cert.pem -n hawaii-opennsa
kubectl create secret generic sense-agent-hostkey --from-file=agent-hostkey=/MASTER_NODE_PATH/privkey.pem -n hawaii-opennsa
kubectl create configmap sense-siterm-agent01-yaml --from-file=sense-siterm-agent=/etc/dtnrm-agent01.yaml -n hawaii-opennsa

# deploy site-rm
kubectl apply -f k8s-siterm.yaml -n hawaii-opennsa
