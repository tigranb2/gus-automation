
import concurrent
import os
import json
import time
import sys

from utils.command_util import *
from utils.remote_util import *
from setup_network_delay import setup_delays, get_server_name_to_internal_ip_map
from setup_nodes import setup_nodes


################################################

### PUBLIC FUNCTION AND SCRIPT CALL HANDLER

# this is the primary function to be called if running a single experiment 
# However, users will typically use run_experiments.py instead since that 
# also handles node setup 
def run_experiment(results_extension, config_file_path):
    config_file = open(config_file_path)
    config = json.load(config_file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:

        timestamp = setup_nodes(config, executor, results_extension)

        # results_extension is timestamp; if the function is called as a script we use timestamp for results folder name
        if results_extension is None:
            results_extension = timestamp


        server_names_to_internal_ips = get_server_name_to_internal_ip_map(config)

        # actually running the experiment
        # results_extension is ncessary for naming the experiment
        if config['layered']:
            run_layered_experiment(server_names_to_internal_ips, config, results_extension, executor)
        else:
            run_standard_experiment(server_names_to_internal_ips, config, results_extension, executor)


    config_file.close()

    
# This function can be called as a script to run one single experiment
# python run_experiment_test <config_file>
if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write('Usage: python3 %s <config_file>\n' % sys.argv[0])
        sys.exit(1)

    run_experiment(results_extension=None, config_file_path=sys.argv[1])


###############################################

### HELPER FUNCTIONS

def run_layered_experiment(server_names_to_internal_ips, config, timestamp, executor):
    print("killing machines for safety")
    kill_layered_machines(config, executor)

    print("starting redis servers")
    redis_server_threads = start_redis_servers(config, timestamp, server_names_to_internal_ips)

    print("starting metadata servers")
    master_thread = start_master(config, timestamp)
    server_threads = start_metadata_servers(config, timestamp, server_names_to_internal_ips)
    client_thread = start_clients(config, timestamp, server_names_to_internal_ips)

    print('waiting for client to finish')
    client_thread.wait()

    print("killing master, metadata servers, and redis servers")
    kill_layered_machines(config, executor)

    print("collecting experiment data")
    path_to_client_data = collect_exp_data(config, timestamp, executor)
    # calculate_exp_data(config, path_to_client_data)


def kill_layered_machines(config, executor):
    futures = []

    server_names = config['server_names']
    for i in range(len(server_names)):
        server_url = get_machine_url(config, server_names[i])
        if i < 3:
            futures.append(executor.submit(run_remote_command_sync('killall -9 server', server_url)))
        futures.append(executor.submit(run_remote_command_sync('killall -9 redis-server', server_url)))

    concurrent.futures.wait(futures)


def start_redis_servers(config, timestamp, server_names_to_internal_ips):
    redis_server_threads = []

    redis_servers_started = 0

    for redis_server_name in config['server_names']:
        if redis_servers_started >= config['number_of_replicas']:
            break

        redis_server_url = get_machine_url(config, redis_server_name)
        redis_server_command = get_redis_server_cmd(config, timestamp, server_names_to_internal_ips, redis_server_name)
        redis_server_threads.append(run_remote_command_async(redis_server_command, redis_server_url))

        redis_servers_started += 1

    # I assume there is no way we can detect when the servers are initialized.
    time.sleep(5)
    return redis_server_threads


def start_metadata_servers(config, timestamp, server_names_to_internal_ips):
    metadata_server_threads = []

    metadata_servers_started = 0

    for metadata_server_name in config['server_names']:
        if metadata_servers_started >= 3:
            break

        metadata_server_url = get_machine_url(config, metadata_server_name)
        metadata_server_command = get_server_cmd(config, timestamp, server_names_to_internal_ips, metadata_server_name)
        metadata_server_threads.append(run_remote_command_async(metadata_server_command, metadata_server_url))

        metadata_servers_started += 1

    # I assume there is no way we can detect when the servers are initialized.
    time.sleep(5)
    return metadata_server_threads


def run_standard_experiment(server_names_to_internal_ips, config, timestamp, executor):
    print("killing machines for safety")
    kill_machines(config, executor)

    print("starting machines")
    start_master(config, timestamp)
    start_servers(config, timestamp, server_names_to_internal_ips)
    client_threads = start_clients(config, timestamp, server_names_to_internal_ips)

    if config['replication_protocol'] == "gryff" or config['replication_protocol'] == "epaxos":
        print('waiting for client to finish')
        client_threads.wait()
    else:
        # for multi-client protocols, wait for all clients to finish
        print('waiting for clients to finish')
        _ = [p.wait() for p in client_threads]

    print("killing master and server")
    kill_machines(config, executor)

    print("collecting experiment data")
    path_to_client_data = collect_exp_data(config, timestamp, executor)
    # calculate_exp_data(config, path_to_client_data)


def kill_machines(config, executor):
    futures = []

    master_url = get_machine_url(config, "client")
    futures.append(executor.submit(run_remote_command_sync('killall -9 master', master_url)))
    if config['replication_protocol'] == "epaxos":
        futures.append(executor.submit(run_remote_command_sync('killall -9 clientepaxos', master_url)))

    for server_name in config['server_names']:
        server_url = get_machine_url(config, server_name)
        futures.append(executor.submit(run_remote_command_sync('killall -9 server', server_url)))
        if config['replication_protocol'] != "epaxos":
            if config['replciation_protocol'] == "pineapple" and config['tail_at_scale'] > 1:
                futures.append(executor.submit(run_remote_command_sync('killall -9 clientnew', server_url)))
            else:
                futures.append(executor.submit(run_remote_command_sync('killall -9 client', server_url)))

    concurrent.futures.wait(futures)


def start_master(config, timestamp):
    master_command = get_master_cmd(config, timestamp)
    # The client hosts the master server.
    master_url = get_machine_url(config, "client")
    time.sleep(5)  # wait for master to start

    return run_remote_command_async(master_command, master_url)


def start_servers(config, timestamp, server_names_to_internal_ips):
    server_threads = []

    servers_started = 0

    # start california as leader
    server_url = get_machine_url(config, "california")
    server_command = get_server_cmd(config, timestamp, server_names_to_internal_ips, "california")
    server_threads.append(run_remote_command_async(server_command, server_url))
    servers_started += 1
    time.sleep(5)

    for server_name in config['server_names']:
        if servers_started >= config['number_of_replicas']:
            break
        if server_name == "california":
            continue

        server_url = get_machine_url(config, server_name)
        server_command = get_server_cmd(config, timestamp, server_names_to_internal_ips, server_name)
        server_threads.append(run_remote_command_async(server_command, server_url))

        servers_started += 1


    time.sleep(5)
    return server_threads


def start_clients(config, timestamp, server_names_to_internal_ips):
    client_threads = []

    clients_started = 0
    if config['replication_protocol'] == "gryff" or config['replication_protocol'] == "epaxos":
        client_url = get_machine_url(config, 'client')
        client_command = get_client_cmd(config, timestamp, server_names_to_internal_ips, clients_started)
        return run_remote_command_async(client_command, client_url)
    else:
        for server_name in config['server_names']:
            if clients_started >= config['number_of_replicas']:
                break

            server_url = get_machine_url(config, server_name)
            client_command = get_client_cmd(config, timestamp, server_names_to_internal_ips, clients_started)
            client_threads.append(run_remote_command_async(client_command, server_url))

            clients_started += 1
        return client_threads


def collect_exp_data(config, timestamp, executor):
    download_futures = []
    control_exp_directory = os.path.join(config['base_control_experiment_directory'], timestamp)
    remote_exp_directory = os.path.join(config['base_remote_experiment_directory'], timestamp)

    # Master machine data is in the logs of the first server.
    for server_name in config['server_names']:
        server_url = get_machine_url(config, server_name)
        download_futures.append(executor.submit(copy_remote_directory_to_local,
                                                os.path.join(control_exp_directory, 'server-%s' % server_name),
                                                server_url, remote_exp_directory))

        if config['replication_protocol'] != "gryff" or config['replication_protocol'] != "epaxos":
            # get client data
            download_futures.append(
                executor.submit(copy_remote_directory_to_local, os.path.join(control_exp_directory, 'client'), server_url,
                                remote_exp_directory))

    if config['replication_protocol'] == "gryff" or config['replication_protocol'] == "epaxos":
        client_url = get_machine_url(config, 'client')
        path_to_client_data = os.path.join(control_exp_directory, 'client')
        download_futures.append(
            executor.submit(copy_remote_directory_to_local, os.path.join(control_exp_directory, 'client'), client_url,
                            remote_exp_directory))

    concurrent.futures.wait(download_futures)
    path_to_client_data = os.path.join(control_exp_directory, 'client')
    return path_to_client_data


def calculate_exp_data(config, path_to_client_data):
    client_cdf_analysis_script = os.path.join(config['gus_epaxos_control_src_directory'], "client_metrics.py")
    subprocess.call(["python3.8", client_cdf_analysis_script], cwd=path_to_client_data)
