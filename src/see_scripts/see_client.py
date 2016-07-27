"""Set of python functions to interact with the SEEweb platform.
"""

import json
import requests

seeweb_root = "http://127.0.0.1:6543"
# seeweb_root = "http://194.214.86.135"

seeweb_user_login = "%s/user_login" % seeweb_root
seeweb_connect = "%s/rest/ro/connect" % seeweb_root
seeweb_disconnect = "%s/rest/ro/disconnect" % seeweb_root
seeweb_register = "%s/rest/ro/register" % seeweb_root
seeweb_remove = "%s/rest/ro/remove" % seeweb_root
seeweb_search = "%s/rest/ro/search" % seeweb_root
seeweb_upload = "%s/ro/create" % seeweb_root


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
    res = session.post(seeweb_user_login, data=auth)
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
    query = dict(uid=str(uid))
    ro_def = session.get(seeweb_search, params=query).json()
    return ro_def


def get_ro_data(uid, session=None):
    """Fetch RO data value from SEEweb

    Warnings: TODO

    Args:
        uid (str): unique id for this RO
        session (Session): an opened session,
                           default None for anonymous access

    Returns:
        (None): Actual data value
    """
    if session is None:
        session = requests.session()

    query = dict(uid=str(uid))
    ro_def = session.get(seeweb_search, params=query).json()
    return ro_def


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


def get_single_by_name(session, ro_type, name):
    """Fetch id of unique RO with given name

    Raises: UserWarning if name is not unique
            KeyError if name does not exists

    Args:
        session (Session): an opened session
        ro_type (str): the type of RO to fetch
        name (str): name associated with RO

    Returns:
        (str): id of RO
    """
    query = dict(type=ro_type, name=name)
    res = session.get(seeweb_search, params=query).json()

    if len(res) == 0:
        raise KeyError("No Ro found with name '%s'" % name)

    if len(res) > 1:
        raise UserWarning("Too many ROs share name '%s'" % name)

    return res[0]


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
    data = dict(ro_type=ro_type,
                ro_def=json.dumps(ro_def))

    res = session.post(seeweb_register, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    ans = res.json()
    if ans["status"] != "success":
        raise UserWarning(ans["msg"])

    return ans["res"]


def remove_ro(session, uid, recursive):
    """Remove a RO from platform.

    Args:
        session (Session): previously opened session with SEEweb
        uid (str): unique id for the RO to remove
        recursive (bool): whether to also remove ROs contained inside this RO

    Returns:
        None
    """
    data = dict(uid=uid, recursive=json.dumps(recursive))

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


def search(session, query):
    """Perform a query on SEE platform

    Args:
        session (Session): previously opened session with SEEweb
        query (dict): parameters for query

    Returns:
        (list of id): list of id of RO matching the query
    """
    res = session.get(seeweb_search, params=query)

    if res.status_code != 200:
        raise UserWarning("unable to perform search RO on SEEweb")

    return res.json()
