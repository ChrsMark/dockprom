import yaml
import argparse

parser = argparse.ArgumentParser(prog='bench-creator')
parser.add_argument('--nodes', help='number of nodes to add', type=int)
parser.add_argument('--interval', help='scrape interval, ie 5s')
parser.add_argument('--max_shards', help='max_shards setting for remote_write', type=int)
parser.add_argument('--max_samples_per_send', help='max_samples_per_send setting for remote_write', type=int)
args = parser.parse_args()

nodes = args.nodes
interval = args.interval
max_shards = args.max_shards
max_samples_per_send = args.max_samples_per_send
remote_endpoint = 'http://35.242.227.62:9201/write'

with open('docker-compose.yml') as file:
    documents = yaml.full_load(file)

    container_name_schema = "nodeexporter{}"
    ports_schema = "{}:9100"
    port = 9100
    nodeexporter = {
        'image': 'prom/node-exporter:v0.18.1',
        'container_name': '',
        'volumes': ['/proc:/host/proc:ro', '/sys:/host/sys:ro', '/:/rootfs:ro'],
        'command': ['--path.procfs=/host/proc', '--path.rootfs=/rootfs', '--path.sysfs=/host/sys', '--collector.filesystem.ignored-mount-points=^/(sys|proc|dev|host|etc)($$|/)'],
        'restart': 'unless-stopped',
        'ports': [],
        'labels': {'org.label-schema.group': 'monitoring'}
    }

    for i in range(nodes):
        ports = ports_schema.format(port+i+1)
        nodeexporter_item = nodeexporter.copy()
        nodeexporter_item["container_name"] = container_name_schema.format(i+1)
        nodeexporter_item["ports"] = [ports]
        nodeexporter_item["labels"]["service_name"] = container_name_schema.format(i+1)
        documents["services"][container_name_schema.format(i+1)] = nodeexporter_item


    print("Services are: " + str(len(documents.get("services"))))
    with open(r'docker-compose-bench.yaml', 'w') as file:
        yaml.dump(documents, file)

with open('prometheus/prometheus.back.yml') as file:
    documents = yaml.full_load(file)
    documents["global"]["scrape_interval"] = interval
    documents["global"]["evaluation_interval"] = interval

    container_name_schema = "nodeexporter{}"
    ports_schema = "{}:9100"
    port = 9100

    for i in range(nodes):
        target = "{}:{}".format(container_name_schema.format(i+1), port+1+i)
        node_job = {
            'job_name': container_name_schema.format(i+1),
            'scrape_interval': interval,
            'static_configs': [{'targets': [target]}]
        }
        documents["scrape_configs"].append(node_job)

    print("Jobs are: " + str(len(documents["scrape_configs"])))
    remote_write = [{
        'url': remote_endpoint,
        "queue_config": {
            "max_shards": max_shards,
            "max_samples_per_send": max_samples_per_send
        }
    }]
    documents["remote_write"] = remote_write
    with open(r'prometheus/prometheus.yml', 'w') as file:
        yaml.dump(documents, file)