import abc
import logging
import re
from typing import List

from nlab.rpc import ApiError
from nlab.rpc.client import WebClient

logger = logging.getLogger(__name__)


class EngineMessageStatus:

    ERROR = "error"
    WARNING = "warning"


class EngineMessage:
    status = EngineMessageStatus.ERROR
    message = ""

    @abc.abstractmethod
    def to_dict(self):
        pass

    def _to_dict(self):

        return {
            "status": self.status,
            "message": self.message,
        }


class MessageTypes:

    TEMPLATE = "template"


class TemplateMessage(EngineMessage):
    """
    Specified message with specific template context
    """
    template_id = ""
    near_text = ""
    suite_id = ""
    profile_id = ""
    template_meta = {}

    def to_dict(self):

        data = super()._to_dict()
        data.update({
            "type": MessageTypes.TEMPLATE,
            "template_id": self.template_id,
            "suite_id": self.suite_id,
            "profile_id": self.profile_id,
            "near_text": self.near_text,
            "template_meta": self.template_meta,
        })
        return data


class EngineOutput:

    def __init__(self, messages=None):

        self.messages = messages or []


def parse_engine_output(output: str) -> EngineOutput:
    """
    Parses engine output

    :param output:
    :return:
    """

    WAIT_FOR_SECTION = 0
    IN_MESSAGE = 3
    state = WAIT_FOR_SECTION

    messages: List[EngineMessage] = []

    current_message = None

    for line in output.split("\n"):

        cmd = line.lstrip()

        if state == WAIT_FOR_SECTION:
            if cmd.startswith("file:"):
                state = IN_MESSAGE
        elif state == IN_MESSAGE:
            error_m = re.search(r"ERROR: (.*?)$", cmd, flags=re.IGNORECASE)
            if error_m:
                current_message = TemplateMessage()
                current_message.status = EngineMessageStatus.ERROR
                current_message.message = error_m.group(1)

            id_m = re.search(r"Id: ([\w.-]+)$", cmd, flags=re.IGNORECASE)
            if id_m and current_message:
                current_message.template_id = id_m.group(1)

            string_m = re.search(r"STRING: (.*?)$", cmd, flags=re.IGNORECASE)
            if current_message and (string_m or not cmd):
                if string_m:
                    current_message.near_text = string_m.group(1)
                messages.append(current_message)
                current_message = None
                state = IN_MESSAGE

        if cmd.startswith("[WARN]") or cmd.startswith("[FAILED]"):
            if current_message:
                messages.append(current_message)
                current_message = None

    output = EngineOutput(messages=messages)

    return output


def load_client_data(client: WebClient, output: EngineOutput):
    """
    Enrich output messages from given template_id adds parent suite_id
    and profile_id with template meta information

    :param client: web client
    :param output: parsed output messages
    :return:
    """
    template_rpc = client.component("template")
    suite_rpc = client.component("suite")

    for message in output.messages:
        if message.template_id:
            try:
                template_info = template_rpc.fetch(id=message.template_id)
                message.suite_id = template_info["suite_id"]
                message.template_meta = template_info["meta"]
            except ApiError:
                logger.exception(
                    "Can't find suite for template=%s" % message.template_id
                )

            if message.suite_id:
                try:
                    suite_info = suite_rpc.fetch(id=message.suite_id)
                    message.profile_id = suite_info["profile_id"]
                except ApiError:
                    logger.exception(
                        "Can't find profile for suite=%s" % message.suite_id
                    )

    return output
