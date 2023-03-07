from os.path import dirname, abspath, join
import logging

prefect_project_name = 'RAMSIS'


#def get_client(api_key=None):
#    if not api_key:
#        dir_path = dirname(abspath(__file__))
#        api_filename = join(dir_path, '../../api-key-prefect.txt')
#        with open(api_filename, 'r') as ofile:
#            api_key = ofile.read().strip()
#
#    return Client(api_key=api_key)
#
#
#def register_flows(flow, labels, project_name=prefect_project_name):
#    flow_id = flow.register(project_name=project_name, labels=labels)
#    logging.info(f"flow: {flow} has been registered with flow_id: {flow_id}")
#
#
#def register_project(project_name=prefect_project_name):
#    client = get_client()
#    # Will not create project if already exists
#    project_id = client.create_project(project_name)
#    logging.info(f"project {project_name} has been registered with project_id:"
#                 f" {project_id}")
#
# When we no longer want to run a Local agent with streamed
# logs, it would be good to run an
# from prefect.agent.docker import DockerAgent
# DockerAgent(labels=["dev", "staging"]).start()
