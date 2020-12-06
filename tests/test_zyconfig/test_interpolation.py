# Created by tuns at 2019-11-13 11:37:33
import sys
sys.path.append('../../zyconfig/')

from zyconfig import InterpolationError, InterpolationSyntaxError, InterpolationNodeError, \
    InterpolationDepthError, InterpolationMissingError

import pytest
from zyconfig import ZyConfig


@pytest.mark.parametrize('section, subsection, option, expected', [
    # ('tuns', 'profile', 'school', 'hcmus'),
    ('tuns', 'profile', 'name', 'Nguyen Sinh Tu with nick = tuns'),
])
def test_interpolation_get(section, subsection, option, expected):

    value = conf[section][subsection][option]
    print(f'value={value!r} --- expected={expected!r}')
    assert value == expected


@pytest.mark.parametrize('section, subsection, option, ex', [
    ('tuns', 'profile', 'school', InterpolationDepthError),
    ('tuns', 'profile', 'invalid_infer', InterpolationSyntaxError),
    ('tuns', 'profile', 'missing_infer', InterpolationMissingError),
])
def test_interpolation_exception(section, subsection, option, ex):
    with pytest.raises(ex) as error:
        conf[section][subsection][option]

    print(f'ex = {error}')

