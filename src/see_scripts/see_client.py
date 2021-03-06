"""Set of python functions to interact with the SEEweb platform.
"""

import json
import os
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


def log_to_see_environ():
    """Attempt to log to SEEweb platform using
    credentials stored in environment variables.

    Notes: needs SEE_user and SEE_pwd to be defined

    Returns:
        (Session): opened session if successful or None
    """
    user = os.environ["SEE_user"]
    pwd = os.environ["SEE_pwd"]
    try:
        return log_to_see(user, pwd)
    except UserWarning:
        return None


def get_ro_def(uid, session=None):
    """Fetch RO definition from SEEweb

    Args:
        uid (str): unique id for this RO
        session (Session): an opened session
                           default None for anonymous access

    Returns:
        (dict): RO definition in json
    """
    if session is None:
        session = requests.session()

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
    return ro_def.get('value')


def get_by_name(ro_type, name, session=None):
    """Fetch RO ids based on their name

    Args:
        ro_type (str): the type of RO to fetch
        name (str): name associated with RO
        session (Session): an opened session,
                           default None for anonymous access

    Returns:
        (list of str): list of RO ids whose name matches
    """
    if session is None:
        session = requests.session()

    query = dict(type=ro_type, name=name)
    res = session.get(seeweb_search, params=query).json()
    return res


def get_single_by_name(ro_type, name, session=None):
    """Fetch id of unique RO with given name

    Raises: UserWarning if name is not unique
            KeyError if name does not exists

    Args:
        ro_type (str): the type of RO to fetch
        name (str): name associated with RO
        session (Session): an opened session,
                           default None for anonymous access

    Returns:
        (str): id of RO
    """
    if session is None:
        session = requests.session()

    query = dict(type=ro_type, name=name)
    res = session.get(seeweb_search, params=query).json()

    if len(res) == 0:
        raise KeyError("No Ro found with name '%s'" % name)

    if len(res) > 1:
        raise UserWarning("Too many ROs share name '%s'" % name)

    return res[0]


def search(query, session=None):
    """Perform a query on SEE platform

    Args:
        query (dict): parameters for query
        session (Session): an opened session,
                           default None for anonymous access

    Returns:
        (list of id): list of id of RO matching the query
    """
    if session is None:
        session = requests.session()

    res = session.get(seeweb_search, params=query)

    if res.status_code != 200:
        raise UserWarning("unable to perform search RO on SEEweb")

    return res.json()


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


def register_data(session, interface, ro_def):
    """Register a new RO data on the platform.

    Args:
        session (Session): previously opened session with SEEweb
        interface (str): interface name, aka data type
        ro_def (dict): json def of RO

    Returns:
        (str): id of registered RO
    """
    # try to localize interface uid
    iid = get_single_by_name('interface', interface, session)

    loc_def = dict(ro_def)

    data = dict(interface=iid,
                ro_def=json.dumps(loc_def))

    res = session.post(seeweb_register, data=data)
    if res.status_code != 200:
        raise UserWarning("unable to register RO on SEEweb")

    ans = res.json()
    if ans["status"] != "success":
        raise UserWarning(ans["msg"])

    return ans["res"]


def register_ro(session, ro_type, ro_def):
    """Register a new RO on the platform.

    Args:
        session (Session): previously opened session with SEEweb
        ro_type (str): type of RO to register
        ro_def (dict): json def of RO

    Returns:
        (str): id of registered RO
    """
    loc_def = dict(ro_def)

    data = dict(ro_type=ro_type,
                ro_def=json.dumps(loc_def))

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
