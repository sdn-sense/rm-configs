#!/usr/bin/env python3
import os
import copy
from yaml import safe_load as yload
from yaml import safe_dump as ydump


# STATE - Will Query FE (/<SITENAME>/sitefe/json/frontend/metrics)
# and get all services states of that FE and Agent's registered to it.
STATE_SCRAPE = {'job_name': 'WILLBEREPLACEDBYCODE',
                'scrape_interval': '30s',
                'static_configs': [{'targets': []}],
                'scheme': 'https',
                'metrics_path': 'WILLBEREPLACEDBYCODE',
                'tls_config': {'cert_file': '/etc/prometheus/cert.pem',
                               'key_file': '/etc/prometheus/privkey.pem',
                               'insecure_skip_verify': True},
                'relabel_configs': [{'source_labels': ['__address__'],
                                     'target_label': 'sitename',
                                     'replacement': 'WILLBEREPLACEDBYCODE'}]}

# HTTPS - Will query https endpoint of FE and will check that it returns
# 2XX return code and also check certificate validity
# This uses blackbox exporter and we need to relabel config and use localhost to query
# remote endpoints
HTTPS_SCRAPE = {'job_name': 'WILLBEREPLACEDBYCODE',
                'metrics_path': '/probe',
                'params':{'module': ['http_2xx']},
                'static_configs':[{'targets': []}],
                'relabel_configs':[{'source_labels': ['__address__'],
                                     'target_label': 'sitename',
                                     'replacement': 'WILLBEREPLACEDBYCODE'},
                                    {'source_labels': ['__address__'],
                                     'target_label': '__param_target'},
                                    {'source_labels': ['__param_target'],
                                     'target_label': 'instance'},
                                    {'target_label': '__address__',
                                     'replacement': '127.0.0.1:9115'}]}


# ICMP - Will ping FE endpoint and get RTT
ICMP_SCRAPE = {'job_name': 'WILLBEREPLACEDBYCODE',
                'metrics_path': '/probe',
                'params':{'module': ['icmp']},
                'static_configs':[{'targets': []}],
                'relabel_configs':[{'source_labels': ['__address__'],
                                    'target_label': 'sitename',
                                    'replacement': 'WILLBEREPLACEDBYCODE'},
                                   {'source_labels': ['__address__'],
                                    'target_label': '__param_target'},
                                   {'source_labels': ['__param_target'],
                                    'target_label': 'instance'},
                                   {'target_label': '__address__',
                                    'replacement': '127.0.0.1:9115'}]}

# If Agent or FE has:
# general:
#   node_exporter: <URL>
# It will add that to prometheus config and will scrape node exporter endpoint
NODE_EXPORTER_SCRAPE = {'job_name': 'WILLBEREPLACEDBYCODE',
                        'static_configs': [{'targets': []}],
                        'relabel_configs': [{'source_labels': ['__address__'],
                                             'target_label': 'sitename',
                                             'replacement': 'WILLBEREPLACEDBYCODE'}]}


def loadYamlFile(fname):
    with open(fname, 'r', encoding='utf-8') as fd:
        return yload(fd.read())

class PromModel():
    def __init__(self,):
        self.default = loadYamlFile('default-config.yml')
        self.jobs = []

    def _genName(self, tmpName):
        if tmpName not in self.jobs:
            self.jobs.append(tmpName)
            return tmpName
        for i in range(0,100):
            # Can we have more than 100 DTNs/FEs for single site?
            nName = "%s_%s" % (tmpName, i)
            if nName not in self.jobs:
                self.jobs.append(nName)
                return nName
        return tmpName


    def _addFE(self, dirname):
        confFile = os.path.join(dirname, 'main.yaml')
        if not os.path.isfile(confFile):
            return
        conf = loadYamlFile(confFile)
        webdomain = conf.get('general', {}).get('webdomain', '')
        origwebdomain = webdomain
        if webdomain.startswith('https://'):
            webdomain = webdomain[8:]
        if not webdomain:
            return
        if webdomain.startswith('127.0.0.1'):
            return
        sites = conf.get('general', {}).get('sites', [])
        if not sites:
            return
        for site in sites:
            # 1. Query for State of all Services registered to FE
            tmpEntry = copy.deepcopy(STATE_SCRAPE)
            tmpEntry['job_name'] = self._genName('%s_STATE' % site)
            tmpEntry['static_configs'][0]['targets'].append(webdomain)
            tmpEntry['metrics_path'] = "/%s/sitefe/json/frontend/metrics" % site
            tmpEntry['relabel_configs'][0]['replacement'] = site
            self.default['scrape_configs'].append(tmpEntry)
            # 2. Query Endpoint and get TLS/Certificate information of Service
            tmpEntry = copy.deepcopy(HTTPS_SCRAPE)
            tmpEntry['job_name'] = self._genName('%s_HTTPS' % site)
            tmpEntry['static_configs'][0]['targets'].append(origwebdomain)
            tmpEntry['relabel_configs'][0]['replacement'] = site
            self.default['scrape_configs'].append(tmpEntry)
            # 3. Add ICMP Check for FE
            tmpEntry = copy.deepcopy(ICMP_SCRAPE)
            tmpEntry['job_name'] = self._genName('%s_ICMP' % site)
            tmpEntry['static_configs'][0]['targets'].append(webdomain.split(':')[0])
            tmpEntry['relabel_configs'][0]['replacement'] = site
            self.default['scrape_configs'].append(tmpEntry)
            # 4. Check if agent config has node_exporter defined
            if conf.get('general', {}).get('node_exporter', ''):
                tmpEntry = copy.deepcopy(NODE_EXPORTER_SCRAPE)
                tmpEntry['job_name'] = self._genName('%s_NODE' % site)
                tmpEntry['static_configs'][0]['targets'].append(conf['general']['node_exporter'])
                tmpEntry['relabel_configs'][0]['replacement'] = site
                self.default['scrape_configs'].append(tmpEntry)
        return

    def _addAgent(self, dirname):
        confFile = os.path.join(dirname, 'main.yaml')
        if not os.path.isfile(confFile):
            return
        conf = loadYamlFile(confFile)
        nodeExporter = conf.get('general', {}).get('node_exporter', '')
        site = conf.get('general', {}).get('siteName', '')
        if site and nodeExporter:
            tmpEntry = copy.deepcopy(NODE_EXPORTER_SCRAPE)
            tmpEntry['job_name'] = self._genName('%s_NODE' % site)
            tmpEntry['static_configs'][0]['targets'].append(nodeExporter)
            tmpEntry['relabel_configs'][0]['replacement'] = site
            self.default['scrape_configs'].append(tmpEntry)
        return

    def looper(self, dirname):
        mappingFile = os.path.join(dirname, 'mapping.yaml')
        if not os.path.isfile(mappingFile):
            return
        mapping = loadYamlFile(mappingFile)
        for key, val in mapping.items():
            if val.get('type', '') == 'Agent' and val.get('config', ''):
                tmpD = os.path.join(dirname, val.get('config'))
                self._addAgent(tmpD)
            elif val.get('type', '') == 'FE' and val.get('config', ''):
                tmpD = os.path.join(dirname, val.get('config'))
                self._addFE(tmpD)
        with open('prometheus.yml', 'w') as fd:
            ydump(self.default, fd)
        return

def execute():
    worker = PromModel()
    workdir = "../"
    for dirName in os.listdir(workdir):
        siteConfDir = os.path.join(workdir, dirName)
        worker.looper(siteConfDir)

if __name__ == "__main__":
    execute()

