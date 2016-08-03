"""node definition to interact with SEE platform
"""

from openalea.core import Factory
from openalea.core.interface import *

__name__ = "openalea.see"
__alias__ = []
__version__ = '0.0.3'
__license__ = "Cecill-C"
__authors__ = 'Jerome Chopard'
__institutes__ = 'INRIA/CIRAD'
__description__ = 'Nodes to interact with SEE platform'
__url__ = ''

__all__ = []

log = Factory(uid="cbc464fd4e5011e6bff6d4bed973e64a",
              name="log_to_see",
              description="",
              category="",
              nodemodule="see_client",
              nodeclass="log_to_see_environ",
              inputs=(),
              outputs=(dict(name="session", interface=None),),
              )

__all__.append('log')

load_def = Factory(uid="cbc464fc4e5011e6bff6d4bed973e64a",
                   name="load_def",
                   description="",
                   category="",
                   nodemodule="see_client",
                   nodeclass="get_ro_def",
                   inputs=(dict(name="uid", interface=IStr),
                           dict(name="session", interface=None),),
                   outputs=(dict(name="def", interface=IDict),),
                   )

__all__.append('load_def')

load_data = Factory(uid="7fbd67a4527711e6b255d4bed973e64a",
                    name="load_data",
                    description="",
                    category="",
                    nodemodule="see_client",
                    nodeclass="get_ro_data",
                    inputs=(dict(name="uid", interface=IStr),
                            dict(name="session", interface=None),),
                    outputs=(dict(name="val", interface=None),),
                    )

__all__.append('load_data')
