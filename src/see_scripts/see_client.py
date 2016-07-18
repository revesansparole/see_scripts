"""Set of python functions to interact with the SEEweb platform.
"""

import requests

seeweb_connect = "http://127.0.0.1:6543/rest/ro/connect"
seeweb_disconnect = "http://127.0.0.1:6543/rest/ro/disconnect"
seeweb_register = "http://127.0.0.1:6543/rest/ro/register"
seeweb_remove = "http://127.0.0.1:6543/rest/ro/remove"
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


def get_ro_def(session, uid):
    """Fetch RO definition from SEEweb

    Args:
        session (Session): an opened session
        uid (str): unique id for this RO

    Returns:
        (dict): RO definition in json
    """
    query = dict(uid=uid)
    idef = session.get(seeweb_search, params=query).json()
    return idef


def get_by_name(session, ro_type, name):
    """Fetch RO ids based on their name

    Args:
        session (Session): an opened session
        ro_type (str): the type of RO to fetch
        name (str): name associated with RO

    Returns:
        (list of str): list of RO ids whose name matches
    """
    query = dict(type=ro_type, name=name)
    res = session.get(seeweb_search, params=query).json()
    return res


def upload_file(session, pth):
    """Upload file on SEEweb

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


def register_ro(session, ro_type, ro_def):
    """Register a new RO on the platform.

    Args:
        session (Session): previously opened session with SEEweb
        ro_type (str): type of RO to register
        ro_def (dict): json def of RO

    Returns:
        (str): id of registered RO
    """
    data = dict(ro_def)
    data["ro_type"] = ro_type

    res = session.post(seeweb_register, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    return res.json()


def remove_ro(session, uid, recursive):
    """Remove a RO from platform.

    Args:
        session (Session): previously opened session with SEEweb
        uid (str): unique id for the RO to remove
        recursive (bool): whether to also remove ROs contained inside this RO

    Returns:
        None
    """
    data = dict(uid=uid, recursive=recursive)

    res = session.post(seeweb_remove, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    return res.json()


def connect(session, src, tgt, link_type):
    """Register a link between two ROs

    Args:
        session (Session): previously opened session with SEEweb
        src (str): id of source RO
        tgt (str): id of target RO
        link_type (str): type of link to create

    Returns:
        (int): id of created link
    """
    data = dict(src=src, tgt=tgt, link_type=link_type)

    res = session.post(seeweb_connect, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    return res.json()


def disconnect(session, src, tgt, link_type):
    """Remove a link between two ROs

    Args:
        session (Session): previously opened session with SEEweb
        src (str): id of source RO
        tgt (str): id of target RO
        link_type (str): type of link to remove

    Returns:
        (int): id of removed link
    """
    data = dict(source=src, target=tgt, link_type=link_type)

    res = session.post(seeweb_disconnect, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    return res.json()
