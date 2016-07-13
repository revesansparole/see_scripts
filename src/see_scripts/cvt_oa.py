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
from openalea.core.pkgmanager import PackageManager
from openalea.wlformat.convert.wralea import (find_wralea_interface,
                                              find_wralea_node,
                                              import_node,
                                              import_workflow,
                                              register_wralea_interface)

seeweb_search = "http://127.0.0.1:6543/rest/ro/search"
seeweb_upload = "http://127.0.0.1:6543/ro/create"


def log_to_see(user, password):
    """Try to log to SEEweb platform

    Args:
        user (str): user id
        password (str): user password

    Returns:
        (Session): opened session if successful
    """
    session = requests.Session()
    auth = {'ok': True, 'user_id': user, 'password': password}
    res = session.post("http://127.0.0.1:6543/user_login", data=auth)
    if res.status_code != 200:
        raise UserWarning("unable to connect to SEEweb")

    return session


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
                    ros.append(('interface', idef))

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
    for pkgname in pm.keys():
        if not pkgname.startswith('#'):
            for name in pm[pkgname].keys():
                nf = pm[pkgname][name]
                if isinstance(nf, NodeFactory):
                    print("exporting node: %s %s" % (pkgname, name))
                    # find all interface used by the node
                    if nf.inputs is None:
                        nf.inputs = []
                    if nf.outputs is None:
                        nf.outputs = []

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
                            query = {'type': 'interface', 'name': iname}
                            res = session.get(seeweb_search,
                                              params=query).json()
                            if len(res) != 1:
                                msg = "Interface '%s' used by node '%s:%s' is not defined anywhere" % (
                                iname, pkgname, name)
                                raise UserWarning(msg)
                            else:
                                query = dict(uid=res[0])
                                idef = session.get(seeweb_search,
                                                   params=query).json()

                                store[idef['id']] = ('data', idef)

                    # convert it to wlformat
                    ndef = import_node(nf, store, pkgname)
                    store[ndef['id']] = ("node", ndef)

                    # add node to ro list
                    ros.append(('workflow_node', ndef))

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
    for pkgname in pm.keys():
        if not pkgname.startswith('#'):
            for name in pm[pkgname].keys():
                cnf = pm[pkgname][name]
                if isinstance(cnf, CompositeNodeFactory):
                    print("exporting workflow: %s %s" % (pkgname, name))
                    # ensure all nodes used by this workflow are in store
                    for nid, func_desc in cnf.elt_factory.items():
                        ndef = find_wralea_node(store, func_desc)
                        if ndef is None:
                            # try to find its definition online
                            nname = "%s: %s" % func_desc
                            query = {'type': 'workflow_node', 'name': nname}
                            res = session.get(seeweb_search,
                                              params=query).json()
                            if len(res) != 1:
                                msg = "Node '%s' used by workflow '%s' is not defined anywhere" % (
                                    nname, name)
                                raise UserWarning(msg)
                            else:
                                query = dict(uid=res[0])
                                ndef = session.get(seeweb_search,
                                                   params=query).json()

                                store[ndef['id']] = ('node', ndef)

                    # import workflow
                    wdef = import_workflow(cnf, store)
                    if wdef is not None:
                        store[wdef['id']] = ("workflow", wdef)
                        # add node to ro list
                        ros.append(('workflow', wdef))

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


def upload_package(session, pth):
    """Upload package on SEEweb

    Args:
        session (Session): previously opened session with SEEweb
        pth (str): path to file

    Returns:
        None
    """
    data = {"submit_upload": True}
    files = {'upload_file': open(pth, 'rb')}

    res = session.post(seeweb_upload, data=data, files=files)
    if res.status_code != 200:
        raise UserWarning("unable to upload package on SEEweb")


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
    ros = extract_interfaces(session, pm, store)
    ros.extend(extract_nodes(session, pm, store))
    ros.extend(extract_workflows(session, pm, store))

    pkg_arch = "%s.zip" % pkgname
    write_package(ros, pkg_arch)
    upload_package(session, pkg_arch)

    if os.path.exists(pkg_arch):
        os.remove(pkg_arch)


if __name__ == '__main__':
    main()
