"""Explore recursively a directory tree structure and construct
RO definition files for each Openalea workflow object encountered
"""

from argparse import ArgumentParser
from itertools import chain
import os

from openalea.core.interface import IInterface
from openalea.core.pm_extend import composites, data, get_packages, nodes
from openalea.core.pkgmanager import PackageManager
from openalea.wlformat.convert.wralea import (convert_data_node,
                                              convert_node,
                                              convert_workflow,
                                              get_interface_by_name,
                                              get_node_by_node_desc,
                                              register_interface)

from .see_client import (connect, get_by_name, get_ro_def, get_single_by_name,
                         log_to_see, register_ro, remove_ro)


def oa_pm(root):
    """Create openalea PackageManager and initialize it
    with given directory.

    Args:
        root (str): valid path to a directory

    Returns:
        (PackageManager)
    """
    pm = PackageManager()
    if os.path.exists(os.path.join(root, "src")):
        root = os.path.join(root, "src")

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
                    ros.append((pkgname, idef))

    return ros


def check_fac(session, fac, store, overwrite):
    """Do some checking on existence of RO in SEE database

    Args:
        session (Session): previously opened session with SEEweb
        fac (Factory):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database
                          default False

    Returns:
        (bool): whether RO already exists that corresponds to this fac
    """
    try:
        uid = fac.uid
        if uid in store:
            print("RO with same uid '%s' already exists, DO nothing" % uid)
            return False
        if get_ro_def(uid, session) is not None:
            if overwrite:
                remove_ro(session, uid, False)
            else:
                print("RO with same uid '%s' already exists, DO nothing" % uid)
                return False
    except AttributeError:
        pass

    return True


def export_node(session, nf, store, overwrite):
    """Convert a single node into a RO def.

    Args:
        session (Session): previously opened session with SEEweb
        nf (NodeFactory):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database

    Returns:
        (dict): RO def
    """
    print("exporting node: %s %s" % (nf.package.name, nf.name))
    if not check_fac(session, nf, store, overwrite):
        return None

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
            res = get_by_name('interface', iname, session)
            if len(res) != 1:
                msg = ("Interface '%s' "
                       "used by node '%s:%s' "
                       "is not defined anywhere" % (iname,
                                                    nf.package.name,
                                                    nf.name))
                raise UserWarning(msg)
            else:
                idef = get_ro_def(res[0], session)
                store[idef['id']] = ('data', idef)

    # convert it to wlformat
    return convert_node(nf, store, nf.package.name)


def export_data(session, nf, store, overwrite):
    """Convert a single data node into a RO def.

    Args:
        session (Session): previously opened session with SEEweb
        nf (NodeFactory):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database

    Returns:
        (dict): RO def
    """
    print("exporting node: %s %s" % (nf.package.name, nf.name))
    if not check_fac(session, nf, store, overwrite):
        return None

    for iname in ("any", "IData"):
        idef = get_interface_by_name(store, iname)
        if idef is None:
            # try to find its definition online
            res = get_by_name('interface', iname, session)
            if len(res) != 1:
                msg = ("Interface '%s' "
                       "used by node '%s:%s' "
                       "is not defined anywhere" % (iname,
                                                    nf.package.name,
                                                    nf.name))
                raise UserWarning(msg)
            else:
                idef = get_ro_def(res[0], session)
                store[idef['id']] = ('data', idef)

    # convert it to wlformat
    return convert_data_node(nf, store, nf.package.name)


def extract_nodes(session, pm, store, overwrite=False):
    """Extract all workflow Nodes defined in pm

    Warnings: modify store in place

    Args:
        session (Session): previously opened session with SEEweb
        pm (PackageManager):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database
                          default False

    Returns:
        (list): a list of created ROWorkflowNode objects
    """
    ros = []
    for nf in nodes(pm):
        ndef = export_node(session, nf, store, overwrite)
        if ndef is not None:
            store[ndef['id']] = ("node", ndef)
            ros.append((nf.package.name, ndef))

    for nf in data(pm):
        ndef = export_data(session, nf, store, overwrite)
        if ndef is not None:
            store[ndef['id']] = ("node", ndef)
            ros.append((nf.package.name, ndef))

    for nf in composites(pm):
        if ((nf.inputs is not None and len(nf.inputs) > 0) or
                (nf.outputs is not None and len(nf.outputs) > 0)):
            ndef = export_node(session, nf, store, overwrite)
            if ndef is not None:
                store[ndef['id']] = ("node", ndef)
                ros.append((nf.package.name, ndef))

    return ros


def export_workflow(session, cnf, store, overwrite):
    """Convert a single workflow to RO def

    Args:
        session (Session): previously opened session with SEEweb
        cnf (CompositeNodeFactory):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database

    Returns:
        (dict): RO def
    """
    print("exporting workflow: %s %s" % (cnf.package.name, cnf.name))
    if not check_fac(session, cnf, store, overwrite):
        return None

    # ensure all nodes used by this workflow are in store
    for nid, node_desc in cnf.elt_factory.items():
        ndef = get_node_by_node_desc(store, node_desc)
        if ndef is None:
            # try to find its definition online
            nname = "%s: %s" % node_desc
            res = get_by_name('workflow_node', nname, session)
            if len(res) != 1:
                msg = ("Node '%s' "
                       "used by workflow '%s' "
                       "is not defined anywhere" % (nname, cnf.name))
                raise UserWarning(msg)
            else:
                ndef = get_ro_def(res[0], session)
                store[ndef['id']] = ('node', ndef)

    # import workflow
    return convert_workflow(cnf, store)


def extract_workflows(session, pm, store, overwrite=False):
    """Extract all workflows defined in pm

    Warnings: modify store in place

    Args:
        session (Session): previously opened session with SEEweb
        pm (PackageManager):
        store (dict): previously defined objects
        overwrite (bool): whether to overwrite RO already in database
                          default False

    Returns:
        (list): a list of created ROWorkflow objects
    """
    ros = []
    for cnf in composites(pm):
        wdef = export_workflow(session, cnf, store, overwrite)
        if wdef is not None:
            store[wdef['id']] = ("workflow", wdef)
            ros.append((cnf.package.name, wdef))

    return ros


def main():
    """Analyse arborescence content and extract all openalea objects
    """
    parser = ArgumentParser(description='Wralea converter')

    parser.add_argument('root_dir', nargs='?', default=".",
                        help="Root directory to look for wralea file")

    parser.add_argument('-nw', metavar='no_workflow', dest='no_workflow',
                        action='store_const',
                        const=False, default=True,
                        help='convert everything except workflows')

    parser.add_argument('--overwrite', metavar='overwrite', dest='overwrite',
                        action='store_const',
                        const=True, default=False,
                        help='overwrite nodes with same id in SEE')

    args = parser.parse_args()
    root_dir = args.root_dir
    cvt_workflow = args.no_workflow
    overwrite = args.overwrite

    root_pth = os.path.normpath(os.path.abspath(root_dir))
    if not os.path.exists(root_pth):
        raise UserWarning("need a valid path")

    session = log_to_see("revesansparole", "r")

    pm = oa_pm(root_pth)

    pkgs = get_packages(pm)
    if len(pkgs) == 0:
        return

    store = {}
    rois = extract_interfaces(session, pm, store)
    rons = extract_nodes(session, pm, store, overwrite)
    if cvt_workflow:
        rows = extract_workflows(session, pm, store, overwrite)
    else:
        rows = []

    # register container
    pkg_cont = {}
    for pkgname in pkgs:
        top = None
        for namespace in ('alinea', 'openalea', 'vplants'):
            if namespace in pkgname:
                try:
                    top = get_single_by_name('container', namespace, session)
                except KeyError:
                    top = register_ro(session, 'container',
                                      dict(name=namespace))

        # default to openalea namespace
        if top is None:
            try:
                top = get_single_by_name('container', "openalea", session)
            except KeyError:
                top = register_ro(session, 'container', dict(name="openalea"))

        try:
            pid = get_single_by_name('container', pkgname, session)
        except KeyError:
            pid = register_ro(session, 'container', dict(name=pkgname))
            if top is not None:
                connect(session, top, pid, 'contains')
        pkg_cont[pkgname] = pid

    # register interfaces
    for pkgname, idef in rois:
        uid = register_ro(session, 'interface', idef)
        connect(session, pkg_cont[pkgname], uid, 'contains')

    # register nodes
    for pkgname, ndef in rons:
        uid = register_ro(session, 'workflow_node', ndef)
        connect(session, pkg_cont[pkgname], uid, 'contains')

    # register workflows
    for pkgname, wdef in rows:
        uid = register_ro(session, 'workflow', wdef)
        connect(session, pkg_cont[pkgname], uid, 'contains')


if __name__ == '__main__':
    main()
