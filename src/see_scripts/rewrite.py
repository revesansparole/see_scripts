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

pattern = "DataFactory("
nb = len(pattern)
i = txt.find(pattern)
while i != -1:
    txt = txt[:(i - 1)] + 'DF(uid="%s",\n' % uuid1().hex + txt[(i + nb):]
    sleep(0.1)
    i = txt.find(pattern)

pattern = "Factory("
nb = len(pattern)
i = txt.find(pattern)
while i != -1:
    txt = txt[:(i - 1)] + 'Fa(uid="%s",\n' % uuid1().hex + txt[(i + nb):]
    sleep(0.1)
    i = txt.find(pattern)

with open("__wralea__.py", 'w') as f:
    f.write(txt)
