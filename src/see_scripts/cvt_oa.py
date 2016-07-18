"""Explore recursively a directory tree structure and construct
RO definition files for each Openalea workflow object encountered
"""

from itertools import chain
import json
import os
import requests
from sys import argv
from zipfile import ZipFile

from openalea.core.compositenode import CompositeNodeFactory
from openalea.core.interface import IInterface
from openalea.core.node import NodeFactory
from openalea.core.pm_extend import composites, get_packages, nodes
from openalea.core.pkgmanager import PackageManager
from openalea.wlformat.convert.wralea import (find_wralea_interface,
                                              find_wralea_node,
                                              import_node,
                                              import_workflow,
                                              register_wralea_interface)

from .see_client import (connect, get_by_name, get_ro_def,
                         log_to_see, register_ro)


def oa_pm(root):
    """Create openalea PackageManager and initialize it
    with given directory.

    Args:
        root (str): valid path to a directory

    Returns:
        (PackageManager)
    """
    pm = PackageManager()
    pm.init(root, verbose=True)

    return pm


def extract_interfaces(session, pm, store):
    """Extract all interface defined in pm

    Warnings: modify store in place

    Args:
        session (Session): previously opened session with SEEweb
        pm (PackageManager):
        store (dict): previously defined objects

    Returns:
        (list): a list of created ROInterface objects
    """
    del session

    ros = []
    for pkgname in pm.keys():
        if not pkgname.startswith('#'):
            for name in pm[pkgname].keys():
                ii = pm[pkgname][name]
                if isinstance(ii, IInterface):
                    print("exporting interface: %s %s" % (pkgname, name))
                    idef = register_wralea_interface(name, "unknown")
                    store[(pkgname, name)] = idef
                    ros.append(idef)

    return ros


def extract_nodes(session, pm, store):
    """Extract all workflow Nodes defined in pm

    Warnings: modify store in place

    Args:
        session (Session): previously opened session with SEEweb
        pm (PackageManager):
        store (dict): previously defined objects

    Returns:
        (list): a list of created ROWorkflowNode objects
    """
    ros = []
    for nf in nodes(pm):
        print("exporting node: %s %s" % (nf.package.name, nf.name))
        if nf.inputs is None:
            nf.inputs = []
        if nf.outputs is None:
            nf.outputs = []

        # check that all port names are unique
        for i, port in enumerate(nf.inputs):
            if 'name' not in port:
                port['name'] = 'in%d' % i

        pnames = set(port['name'] for port in nf.inputs)
        if len(pnames) < len(nf.inputs):
            raise UserWarning("input names are not unique")

        for i, port in enumerate(nf.outputs):
            if 'name' not in port:
                port['name'] = 'out%d' % i

        pnames = set(port['name'] for port in nf.outputs)
        if len(pnames) < len(nf.outputs):
            raise UserWarning("input names are not unique")

        # find all interface used by the node
        for port in chain(nf.inputs, nf.outputs):
            if port.get('interface') is None:
                port['interface'] = "any"

            iname = str(port['interface'])
            if "(" in iname:
                iname = iname.split("(")[0].strip()
                port['interface'] = iname

            idef = find_wralea_interface(store, iname)
            if idef is None:
                # try to find its definition online
                res = get_by_name(session, 'interface', iname)
                if len(res) != 1:
                    msg = ("Interface '%s' "
                           "used by node '%s:%s' "
                           "is not defined anywhere" % (iname,
                                                        nf.package.name,
                                                        nf.name))
                    raise UserWarning(msg)
                else:
                    idef = get_ro_def(session, res[0])
                    store[idef['id']] = ('data', idef)

        # convert it to wlformat
        ndef = import_node(nf, store, nf.package.name)
        store[ndef['id']] = ("node", ndef)

        # add node to ro list
        ros.append(ndef)

    return ros


def extract_workflows(session, pm, store):
    """Extract all workflows defined in pm

    Warnings: modify store in place

    Args:
        session (Session): previously opened session with SEEweb
        pm (PackageManager):
        store (dict): previously defined objects

    Returns:
        (list): a list of created ROWorkflow objects
    """
    ros = []
    for cnf in composites(pm):
        print("exporting workflow: %s %s" % (cnf.package.name, cnf.name))
        # ensure all nodes used by this workflow are in store
        for nid, func_desc in cnf.elt_factory.items():
            ndef = find_wralea_node(store, func_desc)
            if ndef is None:
                # try to find its definition online
                nname = "%s: %s" % func_desc
                res = get_by_name(session, 'workflow_node', nname)
                if len(res) != 1:
                    msg = ("Node '%s' "
                           "used by workflow '%s' "
                           "is not defined anywhere" % (nname, cnf.name))
                    raise UserWarning(msg)
                else:
                    ndef = get_ro_def(session, res[0])
                    store[ndef['id']] = ('node', ndef)

        # import workflow
        wdef = import_workflow(cnf, store)
        if wdef is not None:
            store[wdef['id']] = ("workflow", wdef)
            # add node to ro list
            ros.append(wdef)

    return ros


def write_package(ros, pth):
    """Write all ROs in list in a zip file

    Args:
        ros (list):
        pth (str): path to created file

    Returns:
        None
    """
    with ZipFile(pth, 'w') as fz:
        for ro_type, ro in ros:
            ro['type'] = ro_type
            fz.writestr("%s.wkf" % ro['id'], json.dumps(ro))


def main():
    """Analyse arborescence content and extract all openalea objects
    """
    if len(argv) > 1:
        root_dir = argv[1]
    else:
        root_dir = "."

    root_pth = os.path.normpath(os.path.abspath(root_dir))
    if not os.path.exists(root_pth):
        raise UserWarning("need a valid path")

    # TODO more advanced managment of pkgname
    pkgname = "openalea.%s" % os.path.basename(root_pth)

    session = log_to_see("revesansparole", "r")

    pm = oa_pm(root_pth)
    store = {}
    rois = extract_interfaces(session, pm, store)
    rons = extract_nodes(session, pm, store)
    rows = extract_workflows(session, pm, store)

    # pkg_arch = "%s.zip" % pkgname
    # write_package(ros, pkg_arch)
    # upload_file(session, pkg_arch)
    #
    # if os.path.exists(pkg_arch):
    #     os.remove(pkg_arch)

    # register container
    pkg = register_ro(session, 'container', dict(name=pkgname))

    # register interfaces
    for idef in rois:
        uid = register_ro(session, 'interface', idef)
        connect(session, pkg, uid, 'contains')

    # register nodes
    for ndef in rons:
        uid = register_ro(session, 'workflow_node', ndef)
        connect(session, pkg, uid, 'contains')

    # register workflows
    for wdef in rows:
        uid = register_ro(session, 'workflow', wdef)
        connect(session, pkg, uid, 'contains')



if __name__ == '__main__':
    main()
