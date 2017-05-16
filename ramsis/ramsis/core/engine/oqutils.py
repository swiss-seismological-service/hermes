# -*- encoding: utf-8 -*-
"""
OpenQuake Helpers

Helper functions to manipulate OpenQuake input files.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
import os
import sys
import shutil
from StringIO import StringIO
from lxml import etree


# RAMSIS constants
ramsis_path = os.path.dirname(os.path.realpath(sys.argv[0]))
OQ_RESOURCE_PATH = os.path.join(ramsis_path, 'ramsis', 'resources', 'oq')
PSHA_PATH = os.path.join(OQ_RESOURCE_PATH, 'psha')
# Hazard input file templates
HAZ_JOB_INI = 'job.ini'
HAZ_GMPE_LT = 'gmpe_logic_tree.xml'
HAZ_SOURCE = 'point_source_model.xml'
HAZ_SMLT = 'source_model_logic_tree.xml'
# Risk input file templates
RISK_POE_RESOURCES = {
    'job_def': 'job.ini',
    'exp_model': 'exposure_model.xml',
    'vuln_model': 'struct_vul_model.xml'
}

# OQ specific constants
GR_BRANCH_XPATH = './/{*}logicTreeBranchSet[@uncertaintyType="abGRAbsolute"]'



def lt_branch(branch_id):
    """
    Creates a new logic tree branch

    :param branch_id: branch id
    :type branch_id: str

    :retval: branch element

    """
    return etree.Element('logicTreeBranch', branchID=branch_id)


def gr_branch(branch_id, ab, w):
    """
    Create an (absolute) Gutenberg-Richter branch

    :param branch_id: branch id
    :type branch_id: str
    :param ab: a and b values
    :type ab: tuple
    :param w: model weight
    :type w: float

    :retval: Gutenberg-Richter branch element

    """
    branch = lt_branch(branch_id)
    model = etree.SubElement(branch, 'uncertaintyModel')
    model.text = ' '.join(str(v) for v in ab)
    weight = etree.SubElement(branch, 'uncertaintyWeight')
    weight.text = str(w)
    return branch


def inject_src_params(source_models, tree):
    """
    Inject Gutenberg-Richter source parameters into source logic tree
    definition

    :param source_models: source models (see controller.py)
    :param tree: xml etree with source model definition

    """


def read_xml(path):
    """ parse xml and return tree """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(path, parser)
    return tree


def path_as_stream(path):
    with open(path) as f:
        data = f.read()
        stream = StringIO(data)
    return stream


def hazard_source_model_lt(source_params):
    """
    Return the source model logic tree with source_params injected

    :param source_params: dictionary Gutenberg-Richter a,b values and
            weights per IS forecast model, i.e.
            source_params = {'ETAS': [a, b, w], ...}.
            Note that the sum of all weights must be 1.0

    :return: source model logic tree as stringio

    """
    path = os.path.join(PSHA_PATH, HAZ_SMLT)
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(path, parser)
    gr_branch_set = tree.find(GR_BRANCH_XPATH)
    for child in gr_branch_set:
        gr_branch_set.remove(child)
    for model, params in source_params.items():
        a, b, w = params
        branch = gr_branch(model, (a, b), w)
        gr_branch_set.append(branch)
    return StringIO(etree.tostring(tree))


def hazard_gmpe_lt():
    path = os.path.join(PSHA_PATH, HAZ_GMPE_LT)
    return path_as_stream(path)


def hazard_source():
    path = os.path.join(PSHA_PATH, HAZ_SOURCE)
    return path_as_stream(path)


def hazard_job_ini():
    path = os.path.join(PSHA_PATH, HAZ_JOB_INI)
    return {'job.ini': path_as_stream(path)}


def hazard_input_models(source_parameters):
    input_models = {
        HAZ_SMLT: hazard_source_model_lt(source_parameters),
        HAZ_SOURCE: hazard_source(),
        HAZ_GMPE_LT: hazard_gmpe_lt()
    }
    return input_models


def hazard_input_files(source_parameters, copy_to=None):
    files = hazard_job_ini()
    files.update(hazard_input_models(source_parameters))
    if copy_to:
        for filename, content in files.items():
            with open(os.path.join(copy_to, filename), 'w') as dst:
                shutil.copyfileobj(content, dst)
            content.seek(0)

    return files
