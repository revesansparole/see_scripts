"""node definition to interact with SEE platform
"""

from openalea.core import Factory
from openalea.core.interface import *

__name__ = "see"
__alias__ = []
__version__ = '0.0.3'
__license__ = "Cecill-C"
__authors__ = 'Jerome Chopard'
__institutes__ = 'INRIA/CIRAD'
__description__ = 'Nodes to interact with SEE platform'
__url__ = ''

__all__ = []


log = Factory(name="log_to_see",
                   description="",
                   category="",
                   nodemodule="see_client",
                   nodeclass="log_to_see",
                   inputs=(dict(name="user", interface=IStr),
                           dict(name="password", interface=IStr),),
                   outputs=(dict(name="session", interface=None),),
                   )

__all__.append('log')


load_def = Factory(name="load_def",
                   description="",
                   category="",
                   nodemodule="see_client",
                   nodeclass="get_ro_def",
                   inputs=(dict(name="session", interface=None),
                           dict(name="uid", interface=IStr),),
                   outputs=(dict(name="def", interface=IDict),),
                   )

__all__.append('load_def')
