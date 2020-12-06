""" Test get values when config was load """
import sys
sys.path.append('../../zyconfig/')
import pytest
from zyconfig import ZyConfig
import logging
logger = logging.getLogger(__name__)

CONF_FILE = '../../conf/env/development/dev.conf.ini'

@pytest.mark.parametrize('input_file, section, subsection, option, expected_type', [
    # file config
    (CONF_FILE, 'math', 'setting', 'arg1', float),
    (CONF_FILE, 'math', 'setting', 'arg2', float),
    (CONF_FILE, 'math', 'setting', 'arg3', float),
])
class TestGetConfig:

    def test_get_value(self, input_file, section, subsection, option, expected_type):
        conf = ZyConfig.read(input_file)
        value = conf[section][subsection][option]
        print(value)
        assert isinstance(value, expected_type)


    def test_get_by_func(self, input_file, section, subsection, option, expected_type):
        conf = ZyConfig.read(input_file)
        conf = getattr(conf, section)
        conf = getattr(conf, subsection)
        value = getattr(conf, option)
        print('key={}, value={}'.format('.'.join([section, subsection, option]), value))
        assert isinstance(value, expected_type)
