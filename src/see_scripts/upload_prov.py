import json

from see_client import connect, get_by_name, get_ro_def, log_to_see, register_ro

pth = "../../../prov.wkf"
container = "prov-oc"
session = log_to_see("revesansparole", "r")

# open provenance file
with open(pth, 'r') as f:
    prov = json.load(f)

# check that associated workflow is already registered
uid = prov['workflow']
wdef = get_ro_def(session, uid)
if wdef is None:
    raise UserWarning("The workflow associated to this provenance"
                      "has not been registered")


# check that all data are either local to the file or have been registered
# TODO

# check existence of container
res = get_by_name(session, 'container', container)
if len(res) == 0:
    # create one
    cid = register_ro(session, 'container', dict(name=container))
elif len(res) > 1:
    raise UserWarning("too many containers with this name")
else:
    cid = res[0]

# upload prov on SEEweb
pid = register_ro(session, 'workflow_prov', prov)
connect(session, cid, pid, 'contains')
