from time import sleep
from uuid import uuid1


with open("__wralea__.py", 'r') as f:
    txt = f.read()

pattern = "CompositeNodeFactory("
nb = len(pattern)
i = txt.find(pattern)
while i != -1:
    txt = txt[:(i - 1)] + 'CNF(uid="%s",\n' % uuid1().hex + txt[(i + nb):]
    sleep(0.1)
    i = txt.find(pattern)

with open("__wralea__.py", 'w') as f:
    f.write(txt)
