import pytest
from .zconfig import ZyConfig

def test_read_only_config():
    with pytest.raises(ReadOnlyConfigError):
        conf = ZyConfig._from_dict({'a' : {'b' : 1}})
        conf['a'] = {'b' : 2}
        conf['a']['b'] = 3
        
        conf.a = 3
        conf.a.b = 4

        