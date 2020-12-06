import sys
sys.path.append('../../zyconfig/')
import pytest
from zyconfig import ZyConfig, MaxConfigLevelError, MissingSectionHeaderError
import re

UNSET = object()
@pytest.mark.parametrize('_input, section, subsect, option, expected', [
    ({'hello': "None"}, "hello", None, None, None),
    #simple key:value
    ({'hello':'world'}, 'hello', None, None, 'world'),
    #section:subsection:key=value
    ({'greed': {'hello' : 'world'}}, 'greed', None, None, {'hello' : 'world'}),

    ({'greed': {'hello' : 'world'}}, 'greed', 'hello', None, 'world'),

    # more nested section:subsection
    ({'a' : {'b' : "1"}, 'c':{'d': "2"}, 'd': "2"}, 'd',None, None,  2),

    ({'a' : {'b' : "1"}, 'c':{'d': "2"}, 'd': "2"}, 'a', 'b', None, 1),

    ({'a' : {'b' : {'f' : "2"}}, 'c':{'d': "2"}, 'd': "2"}, 'a', 'b', 'f',  2),
])
def test_create_value(_input, section, subsect, option, expected):
    SECTION = section.upper()
    header = "ROOT"
    conf = ZyConfig._from_dict(_input, header, 0)
    value = None
    if section:
        value = conf[section]
    if subsect:
        value = value[subsect]
    if option:
        value = value[option]
    assert value == expected

@pytest.mark.parametrize('input_file, section, subsection, option, expected', [
    # file config
    (CONF_PATH, 'log4z_subsys', 'main', 'enable',  False),

    # file don't exist
    ('/conf/notexsits.ini', None, None, None, None)
])
def test_create_from_file(input_file, section, subsection, option, expected):
    conf = ZyConfig.read(input_file)
    value = None
    if section:
        value = conf[section]
    if subsection:
        value = value[subsection]
    if option:
        value = value[option]
    
    print('value: {}'.format(value))
    print('expected: {}'.format(expected))
    assert expected ==  value

# read from invalid config
@pytest.mark.parametrize('input_file', [
])
def test_create_from_invalid(input_file):
    # with pytest.raises(MissingSectionHeaderError) as err:
        # print(err)

def test_create_raise_invalid_level_ex():
    header = 'ROOT'
    with pytest.raises(MaxConfigLevelError, match=re.escape('a')) as err:
        conf = ZyConfig._from_dict({'a': {'c' : {'d' : {'e': '1'}}}}, header, 0)
        # print(err)

if __name__ == "__main__":
    conf = ZyConfig.read(CONF_PATH)
    print(conf)
    print(conf.log4z_subsys.main.enable)