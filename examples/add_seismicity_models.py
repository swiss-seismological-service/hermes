
from os.path import join, dirname, abspath
import argparse
import json
from ramsis.utils import real_file_path
from ramsis.datamodel import SeismicityModel
from RAMSIS.core.store import Store

DIRPATH = dirname(abspath(__file__))


def create_sm(store, sm_config):

    sm = SeismicityModel(
        name=sm_config["MODEL_NAME"],
        config=sm_config["CONFIG"],
        sfmwid=sm_config["SFMWID"],
        enabled=sm_config["ENABLED"],
        url=sm_config["URL"])

    print(f"Creating new seismicity model: {sm}")
    store.add(sm)


def update_sm(store, existing_sm, sm_config):
    existing_sm.name = sm_config["MODEL_NAME"]
    existing_sm.config = sm_config["CONFIG"]
    existing_sm.sfmwid = sm_config["SFMWID"]
    existing_sm.enabled = sm_config["ENABLED"]
    existing_sm.url = sm_config["URL"]

    print(f"Updating existing seismicity model: {existing_sm}")
    store.add(existing_sm)


def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'db_url', type=str, metavar='URL',
        help=('DB URL indicating the database dialect and connection '
              'arguments.'))
    parser.add_argument(
        '-model_config',
        type=real_file_path,
        default=join(DIRPATH, "config", "model.json"),
        help=("path to a json model configuration "
              "file"))

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_cli()

    store = Store(args.db_url)
    success = store.init_db()

    if success:
        pass
    else:
        raise Exception("DB could not be initialized")

    with open(args.model_config, "r") as model_json:
        config = json.load(model_json)
    seismicity_model_config_list = config["SEISMICITY_MODELS"]

    for sm_config in seismicity_model_config_list:
        existing_sm_model = store.session.query(
            SeismicityModel).filter(
                SeismicityModel.name == sm_config["MODEL_NAME"]).one_or_none()
        if not existing_sm_model:
            create_sm(store, sm_config)
        else:
            update_sm(store, existing_sm_model, sm_config)
    store.save()
    store.close()
    # TODO handle missing models in the config by disabling them.
    # They should not be deleted fully as model runs may exist that require
    # a link to this model.
    # Perhaps delete the model only if there are no associated model runs.
