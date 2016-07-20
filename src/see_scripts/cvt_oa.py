"""Explore recursively a directory tree structure and construct
RO definition files for each Openalea workflow object encountered
"""

from itertools import chain
import os
from sys import argv

from openalea.core.interface import IInterface
from openalea.core.pm_extend import composites, get_packages, nodes
from openalea.core.pkgmanager import PackageManager
from openalea.wlformat.convert.wralea import (convert_node,
                                              convert_workflow,
                                              get_interface_by_name,
                                              get_node_by_func_desc,
                                              register_interface)

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
                    idef = register_interface(store, name, "unknown")
                    ros.append(idef)

    return ros


def export_node(session, nf, store):
    """Convert a single node into a RO def.

    Args:
        session (Session): previously opened session with SEEweb
        nf (NodeFactory):
        store (dict): previously defined objects

    Returns:
        (dict): RO def
    """
    print("exporting node: %s %s" % (nf.package.name, nf.name))
    try:
        uid = nf.uid
        if get_ro_def(session, uid) is not None:
            print("RO with same uid '%s' already exists, DO nothing" % uid)
            return None
    except AttributeError:
        pass

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

        idef = get_interface_by_name(store, iname)
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
    return convert_node(nf, store, nf.package.name)


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
        ndef = export_node(session, nf, store)
        if ndef is not None:
            store[ndef['id']] = ("node", ndef)
            ros.append(ndef)

    return ros


def export_workflow(session, cnf, store):
    """Convert a single workflow to RO def

    Args:
        session (Session): previously opened session with SEEweb
        cnf (CompositeNodeFactory):
        store (dict): previously defined objects

    Returns:
        (dict): RO def
    """
    print("exporting workflow: %s %s" % (cnf.package.name, cnf.name))
    try:
        uid = cnf.uid
        if get_ro_def(session, uid) is not None:
            print("RO with same uid '%s' already exists, DO nothing" % uid)
            return None
    except AttributeError:
        pass

    # ensure all nodes used by this workflow are in store
    for nid, func_desc in cnf.elt_factory.items():
        ndef = get_node_by_func_desc(store, func_desc)
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
    return convert_workflow(cnf, store)


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
        wdef = export_workflow(session, cnf, store)
        if wdef is not None:
            store[wdef['id']] = ("workflow", wdef)
            ros.append(wdef)

    return ros


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

    session = log_to_see("revesansparole", "r")

    pm = oa_pm(root_pth)

    pkgs = get_packages(pm)
    if len(pkgs) == 1:
        pkgname, = pkgs
    else:
        pkgname = "openalea.%s" % os.path.basename(root_pth)

    store = {}
    rois = extract_interfaces(session, pm, store)
    rons = extract_nodes(session, pm, store)
    rows = extract_workflows(session, pm, store)

    # register container
    res = get_by_name(session, 'container', pkgname)
    if len(res)  == 0:
        pid = register_ro(session, 'container', dict(name=pkgname))
    elif len(res) == 1:
        pid, = res
    else:
        raise UserWarning("already too many packages named '%s'" % pkgname)

    # register interfaces
    for idef in rois:
        uid = register_ro(session, 'interface', idef)
        connect(session, pid, uid, 'contains')

    # register nodes
    for ndef in rons:
        uid = register_ro(session, 'workflow_node', ndef)
        connect(session, pid, uid, 'contains')

    # register workflows
    for wdef in rows:
        uid = register_ro(session, 'workflow', wdef)
        connect(session, pid, uid, 'contains')


if __name__ == '__main__':
    main()
