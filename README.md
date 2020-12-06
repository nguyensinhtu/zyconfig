# zyconfig

zyconfig is lightweight configuration system, based on the idea of [OmegaConf](https://github.com/omry/omegaconf) 's functions
and build-in [configparser](https://docs.python.org/3/library/configparser.html), zconfig provides more utilities
to working with INI configuration file.

## Principles
- "Only the disciplined are truly free" - tephen Covey
- Simple better than complex

## Usages

### Read config files
- read config from single or multiple files
```python
from zyconfig import ZConfig
conf = ZConfig.read('file_paths')
```

### Access value
- access like class's attribute
```ini
[server@nosql_server]
host=0.0.0.0
port = 8000

```
```cmd
>>> conf.server.nosql_server.host
'0.0.0.0'
>> conf.server.nosql_server.port
8000
```

- access like python dict
```cmd
>>> conf['server']['nosql_server']['host']
'0.0.0.0'
```

- access via get value
```python
conf = ZConfig.read('file_paths')

# acess without exception
conf.server.nosql_server.get('port', default='9090')

# don't provide default value will throw exception
conf.server.nosql_server.get('missing_key')

```