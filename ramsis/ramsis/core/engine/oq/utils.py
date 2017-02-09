# -*- encoding: utf-8 -*-
"""
OpenQuake Helpers

Helper functions to manipulate OpenQuake input files.

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from lxml import etree

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


def inject_src_params(source_models, path):
    """
    Inject Gutenberg-Richter source parameters into source logic tree
    definition

    :param source_models: source models (see controller.py)
    :param path: path to source logic tree file

    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(path, parser)
    gr_branch_set = tree.find(GR_BRANCH_XPATH)
    for child in gr_branch_set:
        gr_branch_set.remove(child)
    for model, params in source_models.items():
        a, b, w = params
        branch = gr_branch(model, (a, b), w)
        gr_branch_set.append(branch)
    with open(path, 'w') as f:
        tree.write(f, pretty_print=True)
