# Created by tuns at 30/09/2019

"""zyconfig file parser

A configuration file consistes of sections, lead by [section@subsection] header,
(notice that section separate from subsection by "@" ) and followed by name=value pairs,

zconfigparser readonly configuration when it load from file.

ex:
[section@subsection]
key=value

access : cfg.section.subsection.key (if subsection exists) or
            cfg.section.key

interpolation : keys in same section can refer to each other's values
ex :
[sec_1#subsec_1]
key_1=value_1
[sec_2#subsec_2]
key_2 = ${subsec_1:key_1}/whatever

"""

from __future__ import print_function
import re
from configparser import RawConfigParser
from enum import Enum
from configparser import Error, DuplicateSectionError, DuplicateOptionError, NoSectionError, MissingSectionHeaderError
from collections.abc import MutableMapping
from ast import literal_eval
from typing import Union, Any, Optional, List, Type
import os

__all__ = ["DuplicateOptionError", "DuplicateSectionError", "DuplicateSubsectionError",
           "NoSectionError", "NoSubsectionError", "NoOptionError", "MissingSectionHeaderError",
           "InterpolationDepthError"]
# define object
# Những attr nào có giá trị _UNSET
# là những attr chưa được khởi tạo (dùng cho lazy init)
# Không dùng None vì None có thể là giá trị mặc định khi get()
_UNSET = object()


# define error
class ReadOnlyConfigError(Error):
    """ Raised input config is modified """

    def __init__(self, msg=None):
        default_msg = 'Can not modify read only config'
        if msg:
            default_msg = msg
        Error.__init__(self, default_msg)


class MaxConfigLevelError(Error):
    """ Raised when level of config exceed given threshold"""

    def __init__(self, level, threshold, header):
        default_msg = ('{} exceeded given max level of config, default MAX_LEVEL_CONFIG is {}'
                       .format(level, threshold))
        if header:
            default_msg = ("Level of config header [{!r}] exceeded given max level of config, MAX_LEVEL_CONFIG is {}"
                           .format(header, threshold))
        Error.__init__(self, default_msg)


class NoSubsectionError(Error):
    """ Raised when no Subsection matches requested options """

    def __init__(self, subsection):
        super().__init__('No subsection : {!r}'.format(subsection))


class NoOptionError(Error):

    def __init__(self, section, subsection, option):
        super().__init__(f'No option {option!r} in {section!r}.{subsection!r}.')


class InvalidSubsectionError(Error):
    """ Raised when a name of subsection is DEFAULT_SUBSECT in an input source """

    def __init__(self, subsection):
        msg = ("Invalid subsection name : {!r}".format(subsection))
        Error.__init__(self, msg)


class DuplicateSubsectionError(Error):
    """ Raised when a subsection is repeated in a same section
    and input source"""

    def __init__(self, section, subsection, source=None, lineno=None):
        msg = [repr(subsection), " in section ",
               repr(section), " already exists"]
        if source is not None:
            msg_extended = [" While reading from  ", repr(source)]
            if lineno is not None:
                msg_extended.append(" [line {0:2d}]".format(lineno))
            msg_extended.append("Subsection ")
            msg_extended.extend(msg)
            msg = msg_extended
        else:
            msg.insert(0, "Subsection ")
        Error.__init__(self, "".join(msg))


class InterpolationDepthError(Error):
    def __init__(self, option, rawval, full_key, max_depth):
        msg = (f"Interpolation depth limit exceeded in value substitution: option {option!r} "
               f"in {full_key!r} contains an interpolation key which "
               f"cannot be substituted in {max_depth} steps. Raw value: {rawval!r}")
        self.args = (option, rawval, full_key, max_depth)
        Error.__init__(self, msg)


class InterpolationError(Error):

    def __init__(self, section, subsection, option, msg):
        Error.__init__(self, msg)
        self.section = section
        self.subsection = subsection
        self.option = option
        self.args = (section, subsection, option, msg)


class InterpolationSyntaxError(InterpolationError):
    pass


class InterpolationNodeError(InterpolationError):

    def __init__(self, level: Any):
        super(InterpolationNodeError, self).__init__(None, None, None,
                                                     f"Can't interpolate value for node's level {level!r}")


class InterpolationMissingError(InterpolationError):
    pass


class ConfigLevel(Enum):
    SECTION = 0
    SUBSECTION = 1
    OPTION = 2
    UNKNOW = 3


class ZInterpolation:
    """ ZInterpolation as implemented in the ZConfig """

    # max depth of interpolation
    _MAX_INTERPOLATION_DEPTH = 1
    # regex to match form of interpolation
    _KEYRE = re.compile(r"\$\{([^}]+)\}")

    def __init__(self):
        pass

    def before_get(self, dict_config: Any, raw_value: Any) -> Any:
        """
        :param dict_config:
        :param section:
        :param subsection:
        :param option:
        :return:
        """
        root_config = dict_config.get_root()
        keys = dict_config.get_full_key(raw_value)
        if len(keys) != 3:
            raise InterpolationNodeError(dict_config.cfg_level_type)
        section, subsection, option = keys
        return self._do_interpolation(root_config, section, subsection, option, raw_value)

    def evaluate_type(self, value: Any, value_type: Any = None):
        if value_type is None:
            if not isinstance(value, str):
                return False
        elif not isinstance(value, value_type):
            return False
        return True

    def _do_interpolation(self, root_config: Any,
                          section: str,
                          subsection: str,
                          option: str,
                          raw_value: str) -> Any:

        """based on build-int configparser's interpolation but without recursion"""

        accum = []
        stack = [((section, subsection, option), raw_value)]
        depth = 0

        # print(f'infer value={raw_value}')
        while len(stack) > 0:
            current_state, raw_value = stack.pop()
            current_section, current_subsect, current_option = current_state

            if depth > self._MAX_INTERPOLATION_DEPTH:
                raise InterpolationDepthError(current_option,
                                              section,
                                              f'{section}.{subsection}',
                                              self._MAX_INTERPOLATION_DEPTH)
            rest = raw_value
            seen = False
            # print(f'rest = {rest}')

            while rest:
                # rest is not string type
                if not self.evaluate_type(rest):
                    accum.append(str(rest))
                    break

                p = rest.find("$")
                if p < 0:
                    accum.append(rest)
                    break
                stack.append((current_state, rest[:p]))
                rest = rest[p:]

                # escape value $$
                ch = rest[1:2]
                if ch == '$':
                    stack.append((current_state, ch))
                    rest = rest[2:]

                # process value in {}
                elif ch == '{':
                    m = self._KEYRE.match(rest)
                    if not m:
                        raise InterpolationSyntaxError(current_section, current_subsect, current_option,
                                                       f'bad interpolation at {rest!r}')

                    # case '${section.subsect.option}
                    path = m.group(1)
                    opts = path.split('.')
                    if len(opts) != 3:
                        raise InterpolationSyntaxError(current_section, current_subsect, current_option,
                                                       f'bad interpolation at {rest!r}')

                    # get value
                    ref_section, ref_subsect, ref_option = opts
                    current_state = (ref_section, ref_subsect, ref_option)
                    try:
                        # get raw value
                        value = root_config.get_raw(ref_section) \
                                            .get_raw(ref_subsect) \
                                            .get_raw(ref_option)
                        stack.append((current_state, value))
                        seen = True
                    except KeyError:
                        raise InterpolationMissingError(current_section, current_subsect,
                                                        current_option,
                                                        f"bad interpolation variable reference {rest!r}")
                    rest = rest[m.end():]
                else:
                    raise InterpolationSyntaxError(current_section, current_subsect,
                                                   current_option, f"bad interpolation variable reference {rest!r}")
            if seen:
                depth += 1

        accum.reverse()
        raw_value = ''.join(accum)
        return self.infer_type(raw_value)

    def infer_type(self, raw_value: Any) -> Any:
        try:
            val = literal_eval(raw_value)
        except (ValueError, SyntaxError):
            return str(raw_value)
        return val

    def before_set(self, dict_config, option, raw_value, auto_infer=True):
        escaped_value = raw_value.replace('$$', '')
        escaped_value = self._KEYRE.sub(escaped_value, '')
        if '$' in escaped_value:
            full_key = dict_config.get_full_key(option)
            raise ValueError('Invalid interpolation syntax in %r (key: %s) at position %d' % (raw_value,
                                                                                              full_key,
                                                                                              escaped_value.find('%$')))
        if auto_infer:
            return self.infer_type(raw_value)
        return raw_value


class DictConfig(MutableMapping):
    """ a DictConfig contains data at one level of config
    (ex : sections or subsections) """

    # Default interpolation
    _INTERPOLATION = ZInterpolation()
    # flags
    _READONLY = True
    DO_INTERPOLATION = True

    def __init__(self, contents, config_level_type, parent_node=_UNSET):

        # connect to higher order of config level, ex; subsection -> section
        self.__dict__['_parent'] = parent_node

        if type(config_level_type) == ConfigLevel:
            self.__dict__['cfg_level_type'] = config_level_type
        else:
            self.__dict__['cfg_level_type'] = ConfigLevel.UNKNOW

        self.__dict__['_content'] = {}
        if contents:
            for k, v in contents.items():
                self._setitem(k, v)

    def __dir__(self):
        return self.__dict__['_content'].keys()

    def __setattr__(self, name, value):
        """ setter """
        prop = getattr(self.__class__, name, None)
        if prop and isinstance(prop, property):
            """ class's properties """
            if prop.fset is None:
                raise AttributeError("can't set attribute")
            prop.fset(self, value)
        else:
            self._setitem(name, value)

    def __len__(self):
        return len(self._content)

    def __iter__(self):
        return self._content.__iter__()

    def __delitem__(self, key):
        if DictConfig._READONLY:
            raise ReadOnlyConfigError()
        del self._content[key]

    def __setitem__(self, key, value):
        raise ReadOnlyConfigError()

    def __getitem__(self, key):
        value = self._get(key)
        return value

    def __getattr__(self, key):
        """ get content của config """
        return self._get(key)

    def _setitem(self, key, value):
        """ a private method to set content """
        normalized_key = self.normalize_key(key)
        # if exists
        if normalized_key in self._content:
            full_key = self.get_full_key(normalized_key)
            pre_value = self._content[normalized_key]
            msg = ("Can't set {} to key {!r}, it was set to {}".format(value, full_key, pre_value))
            raise ReadOnlyConfigError(msg=msg)
        # add to content
        if DictConfig.is_primitive(value):
            value = self._INTERPOLATION.before_set(self, key, value)
        elif not isinstance(value, DictConfig):
            raise ValueError(value)
        self.__dict__['_content'][normalized_key] = value

    def _convert_to_boolean(self, value):
        if isinstance(value, DictConfig) and \
                value.lower() not in RawConfigParser.BOOLEAN_STATES:
            raise ValueError("Not a boolean type : {}".format(value))
        return RawConfigParser.BOOLEAN_STATES[value.lower()]

    def get_raw(self, key):
        try:
            normalized_key = self.normalize_key(key)
            value = self._content[normalized_key]
            return value
        except KeyError:
            raise

    def _get(self, key):
        try:
            value = self.get_raw(key)
            if self.cfg_level_type == ConfigLevel.OPTION and \
                    self._INTERPOLATION.evaluate_type(value, str):
                value = self._INTERPOLATION.before_get(self, value)

        except KeyError:
            if self.cfg_level_type == ConfigLevel.SECTION:
                raise NoSectionError(key)
            elif self.cfg_level_type == ConfigLevel.SUBSECTION:
                raise NoSubsectionError(key)
            elif self.cfg_level_type == ConfigLevel.OPTION:
                keys = self.get_full_key(key)
                assert len(keys) == 3
                raise NoOptionError(keys[0], keys[1], keys[2])
            raise
        return value

    def _get_conv(self, key: Any, conv: Type[Union[int, float, str, bool]], default=_UNSET):
        try:
            return conv(self._get(self, key))
        except (NoSectionError, NoSubsectionError, NoOptionError):
            if default != self._UNSET:
                return default
            raise

    def __str__(self):
        return self._content.__str__()

    def __repr__(self):
        return self._content.__repr__()

    def keys(self):
        return self._content.keys()

    def items(self):
        class DictConfigItems:
            def __init__(self, d):
                self.d = d
                self.iter = iter(d)

            def __iter__(self):
                return self

            def __next__(self):
                return self.next()

            def next(self):
                k = next(self.iter)
                v = self.d.get(k)
                kv = (k, v)
                return kv

        return DictConfigItems(self)

    def get(self, key: str, default: Optional[Any] = _UNSET) -> Optional[Any]:
        try:
            return self._get(key)
        except (NoSectionError, NoSubsectionError, NoOptionError, ValueError):
            if default != self._UNSET:
                return default
            raise

    def get_int(self, key, default: Optional[Any] = _UNSET) -> Optional[Any]:
        return self._get_conv(key, int, default)

    def get_boolean(self, key, default: Optional[Any] = _UNSET) -> Optional[Any]:
        return self._get_conv(key, bool, default)

    def get_float(self, *keys, default: Optional[Any] = _UNSET) -> Optional[Any]:
        return self._get(k)
        pass

    def normalize_key(self, key: str) -> str:
        return key.lower()

    @staticmethod
    def format_keys(keys: List[str]) -> str:
        """ format list key => section@sub_section.options """
        if len(keys) == 1:
            full_key = keys[0]
        elif len(keys) > 1:
            full_key = '[{}@{}]'.format(keys[0], keys[1])
            options = '.'.join(keys[2:])
            if options:
                full_key = '.'.join([full_key, options])
        return full_key

    def get_full_key(self, key: str) -> List[str]:
        """ get full key """
        node = self
        keys = [key]
        while node:
            assert isinstance(node, DictConfig)
            if node.parent:
                assert isinstance(node.parent, DictConfig)
                for k, v in node.parent.items():
                    if id(v) == id(node):
                        keys.append(k)
                        break

            node = node.parent

        # reverse list
        return keys[::-1]

    def get_root(self) -> Any:
        node = self
        while node.parent:
            assert isinstance(node.parent, DictConfig)
            node = node.parent

        return node

    def pretty(self) -> str:
        """ print the representation of DictConfig """
        pass

    @staticmethod
    def is_primitive(value: Any) -> bool:
        """ check if input value is primitive type """
        # None is primitive type
        if value is None:
            return True
        if isinstance(value, (bool, float, int, str)):
            return True
        return False

    def _set_parent(self, parent):
        assert isinstance(parent, DictConfig) or parent is None
        self.__dict__['_parent'] = parent

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if self.parent == _UNSET:
            self._set_parent(value)
        else:
            """ can't modify parent node if it was set """
            msg = ("can't set attribute, parent of this DictConfig is set")
            raise AttributeError(msg)


class ZyConfig(object):
    """ utilities funcs to construct config """

    # Chỉ cho phép tối đa ba mức config là sections, subsection, options => value
    MAX_CONFIG_LEVEL = 3
    # Default subsection
    DEFAULT_SUBSECT = "main"
    # Regular expression để split section@subsection header
    _SECT_SPLIT_TMPL = r"\@+"
    # Compiled regular expression for split section, subsect headers
    _SECTSPLITRE = re.compile(_SECT_SPLIT_TMPL)

    @staticmethod
    def _from_configparser(config):
        # type: (dict) -> DictConfig
        """ contruct config tree from config parser """
        if not isinstance(config, RawConfigParser):
            return None

        config_data = {}
        for key in config._sections:
            if key:
                # split section@subsection
                headers = ZyConfig._SECTSPLITRE.split(key)
                headers = [s for s in headers if s]
                if len(headers) >= ZyConfig.MAX_CONFIG_LEVEL:
                    # header contains more than one subsection
                    raise MaxConfigLevelError(headers, ZyConfig.MAX_CONFIG_LEVEL)

                section = headers[0]
                try:
                    subsection = headers[1]
                except IndexError:
                    subsection = None
                # get data
                d = {}
                if section in config_data:
                    d = config_data[section]
                if subsection in d:
                    raise DuplicateSubsectionError(section, subsection)
                # if headers don't contain subsection
                if not subsection:
                    subsection = ZyConfig.DEFAULT_SUBSECT
                if subsection in d:
                    raise DuplicateSectionError(section)
                d[subsection] = config._sections[key]
                config_data[section] = d

        return ZyConfig.from_dict(config_data, 'ROOT', 0)

    @staticmethod
    def from_dict(dict_config, header, depth, parent=None):
        """ recursively construct linked config node from python dict """
        if depth >= ZyConfig.MAX_CONFIG_LEVEL:
            raise MaxConfigLevelError(header, ZyConfig.MAX_CONFIG_LEVEL, header)

        current_dict_config = None
        # store {section : dict_config}
        options_to_values = {}
        for key, d in dict_config.items():
            if isinstance(d, dict):
                # lazy init parent
                options_to_values[key] = ZyConfig.from_dict(d, key, depth + 1)
            else:
                options_to_values[key] = d

        config_level = ConfigLevel.UNKNOW
        try:
            config_level = ConfigLevel(depth)
        except ValueError:
            raise MaxConfigLevelError(depth, ZyConfig.MAX_CONFIG_LEVEL, header)
        # if current dict is first node
        if depth == 0:
            current_dict_config = DictConfig(options_to_values, config_level, parent)
        else:
            current_dict_config = DictConfig(options_to_values, config_level)

        # set parent for child DictConfig
        for k, value in options_to_values.items():
            if isinstance(value, DictConfig):
                try:
                    value.parent = current_dict_config
                except ReadOnlyConfigError:
                    raise
        return current_dict_config

    @staticmethod
    def read(filenames: Union[str, os.PathLike]) -> DictConfig:
        """ read config from file"""
        config = RawConfigParser()
        try:
            config.read(filenames)
        except MissingSectionHeaderError as err:
            raise
        zcfg = ZyConfig._from_configparser(config)
        del config
        return zcfg
