import os

from nlab.exception import NLabInvalidArgumentType


def _read_conf_value(config, path):
	if isinstance(config, dict):
		paths = path.split(".")
		while paths:
			config = config.get(paths[0], {} if len(paths) > 1 else None)
			paths = paths[1:]
	elif path:
		raise ValueError("Non-dict like can't have path")

	return config


def conf_attr(config, *, path=None, parse_value=None, env=None, default=None, parse_env=None):
	value = default

	if env is not None and os.getenv(env):
		value = os.getenv(env)
		if parse_env is not None:
			value = parse_env(value)
		value = parse_value(value) if parse_value else value
		return value

	conf_value = _read_conf_value(config, path)
	if conf_value is not None:
		value = conf_value

	if parse_value is not None and value is not None:
		try:
			value = parse_value(value)
		except ValueError as e:
			raise NLabInvalidArgumentType(config, path) from e

	return value


def test_conf():
	assert _read_conf_value({"a": {"b": 1}}, "a.b") == 1

	assert conf_attr("1", parse_value=int) == 1
	assert conf_attr({"a": {"b": "1"}}, path="a.b", parse_value=int) == 1
	assert conf_attr({"a": {"b": "1"}}, path="a.c", parse_value=int) is None


if __name__ == "__main__":
	test_conf()
