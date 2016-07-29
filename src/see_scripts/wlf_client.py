"""Set of functions to export workflow related objects, as defined
in openalea.wlformat, to SEE platform.
"""
from itertools import chain

from .see_client import connect, get_ro_def, register_ro, remove_ro


def already_registered(session, ro_def, overwrite):
    """Do some checking on existence of RO in SEE database

    Args:
        session (Session): previously opened session with SEEweb
        ro_def (dict): RO definition
        overwrite (bool): whether to overwrite RO already in database
                          default False

    Returns:
        (bool): whether RO already exists that corresponds to this definition
    """
    try:
        uid = ro_def['id']
        if get_ro_def(uid, session) is not None:
            if overwrite:
                remove_ro(session, uid, False)
            else:
                return True
    except KeyError:
        pass

    return False


def upload_interface(session, idef, cid=None, overwrite=False):
    """Upload a given interface to SEE

    Args:
        session (Session): an opened session
        idef (dict): interface definition
        cid (str): id of container to store RO
                   default None means no container
        overwrite (bool): whether to overwrite RO object already existing
                          on SEE with same id. Default False

    Returns:
        (str): id of RO object created
    """
    if already_registered(session, idef, overwrite):
        raise UserWarning("RO with same id already in SEE platform")

    uid = register_ro(session, 'interface', idef)

    if cid is not None:
        connect(session, cid, uid, 'contains')

    return uid


def upload_node(session, ndef, cid=None, overwrite=False):
    """Upload a given workflow node to SEE

    Args:
        session (Session): an opened session
        ndef (dict): node definition
        cid (str): id of container to store RO
                   default None means no container
        overwrite (bool): whether to overwrite RO object already existing
                          on SEE with same id. Default False

    Returns:
        (str): id of RO object created
    """
    if already_registered(session, ndef, overwrite):
        raise UserWarning("RO with same id already in SEE platform")

    # check that all port names are unique
    pnames = set(port['name'] for port in ndef['inputs'])
    if len(pnames) < len(ndef['inputs']):
        raise UserWarning("input names are not unique")

    pnames = set(port['name'] for port in ndef['outputs'])
    if len(pnames) < len(ndef['outputs']):
        raise UserWarning("output names are not unique")

    # check that all interfaces used by this node are already registered
    # on the platform
    for port in chain(ndef['inputs'], ndef['outputs']):
        iid = port['interface']
        if get_ro_def(iid, session) is None:
            raise UserWarning("Interface '%s' used by the node is "
                              "not registered" % iid)

    # Register node
    uid = register_ro(session, 'workflow_node', ndef)

    if cid is not None:
        connect(session, cid, uid, 'contains')

    return uid


def upload_workflow(session, wdef, cid=None, overwrite=False):
    """Upload a given workflow to SEE

    Args:
        session (Session): an opened session
        wdef (dict): workflow definition
        cid (str): id of container to store RO
                   default None means no container
        overwrite (bool): whether to overwrite RO object already existing
                          on SEE with same id. Default False

    Returns:
        (str): id of RO object created
    """
    if already_registered(session, wdef, overwrite):
        raise UserWarning("RO with same id already in SEE platform")

    # check that all nodes used by this workflow are already registered
    # on the platform
    for node in wdef['nodes']:
        if get_ro_def(node['id'], session) is None:
            raise UserWarning("node '%s' used by workflow is "
                              "not registered" % node['id'])

    # register workflow
    uid = register_ro(session, 'workflow', wdef)

    if cid is not None:
        connect(session, cid, uid, 'contains')

    return uid


def get_data_def(pdef, did):
    for data in pdef['data']:
        if data['id'] == did:
            return data

    raise KeyError("no data recorded with this id")


def upload_prov(session, pdef, cid=None, overwrite=False):
    """Upload a given execution provenance to SEE

    Args:
        session (Session): an opened session
        pdef (dict): provenance definition
        cid (str): id of container to store RO
                   default None means no container
        overwrite (bool): whether to overwrite RO object already existing
                          on SEE with same id. Default False

    Returns:
        (str): id of RO object created
    """
    if already_registered(session, pdef, overwrite):
        raise UserWarning("RO with same id already in SEE platform")

    # check that the associated workflow has been registered on SEE
    wid = pdef['workflow']
    if get_ro_def(wid, session) is None:
        raise UserWarning("Workflow '%s' associated with this provenance "
                          "has not been registered" % wid)

    # check that all input data that correspond to remote data on the platform
    # are actually registered on the platform
    input_data = set()
    for pexec in pdef["executions"]:
        for port in pexec['inputs']:
            if port['data'] is not None:
                input_data.add(port['data'])

    input_ref = set()
    for did in input_data:
        ddata = get_data_def(pdef, did)
        if ddata['type'] == 'ref':
            if get_ro_def(ddata['value'], session) is None:
                raise UserWarning("data '%s' used as input is not registered "
                                  "on SEE" % ddata['value'])
            else:
                input_ref.add(ddata['value'])

    # upload output data as separate ROs
    output_data = set()
    for pexec in pdef["executions"]:
        for port in pexec['outputs']:
            if port['data'] is not None:
                output_data.add(port['data'])

    for i, did in enumerate(output_data):
        ddef = get_data_def(pdef, did)
        # upload object as new data
        rdef = dict(ddef)
        rdef['name'] = "%s_%d" % (pdef['name'], i)
        did = register_ro(session, 'ro', rdef)
        ddef['type'] = "ref"
        ddef['value'] = did
        if cid is not None:
            connect(session, cid, did, 'contains')

    # register provenance
    uid = register_ro(session, 'workflow_prov', pdef)
    # connect prov to data created
    # TODO move it SEE
    for did in input_ref:
        connect(session, uid, did, 'consume')

    for did in output_data:
        connect(session, uid, did, 'produce')

    if cid is not None:
        connect(session, cid, uid, 'contains')

    return uid

