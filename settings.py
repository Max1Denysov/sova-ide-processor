import json
import os
import sys

if os.getenv("NLAB_ARM_DEV") == "1":
    from dotenv import load_dotenv
    sys.path.append(".")
    load_dotenv("env/develop.env", override=True, verbose=True)

if os.getenv("NLAB_ARM_TEST") == "1":
    from dotenv import load_dotenv
    sys.path.append(".")
    load_dotenv("env/testing.env", override=True, verbose=True)

POSTGRES_PREFIX = "NLAB_ARM_PROCESSOR_POSTGRES_"
POSTGRES_USER = os.getenv(POSTGRES_PREFIX + "USER")
POSTGRES_PASSWORD = os.getenv(POSTGRES_PREFIX + "PASSWORD")
POSTGRES_HOST = os.getenv(POSTGRES_PREFIX + "HOST", "localhost")
POSTGRES_DB = os.getenv(POSTGRES_PREFIX + "DB")
POSTGRES_PORT = os.getenv(POSTGRES_PREFIX + "PORT", "5432")

TASK_RUN_TIME_INTERVAL_SEC = 2     # задается в секундах

GATEWAY_URL = os.getenv("NLAB_ARM_GATEWAY_URL")

PROCESSOR_PORT = os.getenv("NLAB_ARM_PROCESSOR_PORT", "5000")

_key_ = json.loads(os.getenv("NLAB_OPENSSH_PRIVATE_KEY"))

ENGINE_AUTH = {
    "root": {
        "private_key": _key_["value"]
    }
}

ENGINE_COMPILER_HOSTS = {
    "sova-engine": {
        "host": os.getenv("NLAB_ARM_COMPILER_HOSTS"),
        "key": "root",
        "user": "root",
        "engine_path": "/usr/local/InfEngine/",
        "exclusive": True,
        "container_name": "",
        "data_path": "/dldata",
    }
}

ENGINE_DEPLOY_HOSTS = json.loads(
    os.getenv("NLAB_ARM_PROCESSOR_DEPLOY_HOSTS", "{}")
)

NLAB_ARM_TEST_TESTCASE_INF_NAME = os.getenv("NLAB_ARM_TEST_TESTCASE_INF_NAME")

NLAB_ARM_ENGINE_SERVICE_HOST = os.getenv("NLAB_ARM_ENGINE_SERVICE_HOST")

SESSION_ID = 1  # TODO номер сессии

HEADERS = {"Content-type": "application/json"}

NLAB_ARM_WS_NOTIFIER_URL = os.getenv("NLAB_ARM_WS_NOTIFIER_URL")
