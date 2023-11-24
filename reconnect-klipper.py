#!/usr/bin/env python3

import json
import urllib.parse
import urllib.request
import urllib.error
import time
import logging
import sys

from typing import Callable
from enum import Enum


class State(Enum):
    PRINTER_READY = "ready"
    PRINTER_STARTUP = "startup"
    PRINTER_SHUTDOWN = "shutdown"
    PRINTER_ERROR = "error"
    PRINTER_UNKNOWN = "unknown"


class PrinterControl:
    _retry_delay = 1  # seconds
    _retry_dont_trust_ready_state_timeout = 15  # seconds
    _retry_wait_for_final_state_timeout = 60*2 # seconds
    _base_url = None
    _state = State.PRINTER_UNKNOWN

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    @staticmethod
    def _request(url, method) -> any:
        req = urllib.request.Request(url, method=method)
        try:
            with urllib.request.urlopen(req) as response:
                data = response.read()
                encoding = response.info().get_content_charset()
        except urllib.error.HTTPError as e:
            data = e.read()
            encoding = e.info().get_content_charset()

        json_data = json.loads(data.decode(encoding))
        return json_data

    def _get_request(self, url_suffix: str) -> any:
        url = urllib.parse.urljoin(self._base_url, url_suffix)
        return self._request(url, method="GET")

    def _post_request(self, url_suffix: str) -> any:
        url = urllib.parse.urljoin(self._base_url, url_suffix)
        return self._request(url, method="POST")

    def _execute_with_retry(self, body_func: Callable[..., bool], retry_func: Callable[[int], None], delay_in_seconds : int, timeout_in_seconds : int) -> bool:
        timeout = time.time() + timeout_in_seconds
        retry = 0
        while True:
            if time.time() >= timeout:
                return False
            if (body_func()):
                return True
            retry += 1
            retry_func(retry)
            time.sleep(delay_in_seconds)

    def _refresh_state(self) -> None:
        response = self._get_request("printer/info")
        if "result" in response and "state" in response["result"]:
            self._state = State(response["result"]["state"].lower())
            logging.debug(f"current state: {self._state}")
        else:
            self._state = State.PRINTER_UNKNOWN
            logging.debug(f"unknown response: {response}")

    @property
    def is_ready(self) -> bool:
        return self._state == State.PRINTER_READY
    
    def wait_for_final_state(self) -> None:
        def body_func() -> bool:
            self._refresh_state(),
            return self._state in (
                    State.PRINTER_READY,
                    State.PRINTER_SHUTDOWN,
                    State.PRINTER_ERROR,
            )
        def retry_func(retryNo) -> None:
            logging.info(f"retry #{retryNo} waiting for final state. Current state {self._state}")
        
        logging.info(f"wait for final state."),
        self._execute_with_retry(
            body_func,
            retry_func,
            self._retry_delay,
            self._retry_wait_for_final_state_timeout)

    def dont_trust_ready_state(self) -> None:
        def body_func() -> bool:
            self._refresh_state()
            return self._state != State.PRINTER_READY
        def retry_func(retryNo) -> None:
            logging.info(f"retry #{retryNo} while don't trust ready state.")

        logging.info("don't trust ready state.")
        self._execute_with_retry(
            body_func,
            retry_func,
            self._retry_delay,
            self._retry_dont_trust_ready_state_timeout)

    def restart_firmware(self) -> None:
        response = self._post_request("printer/firmware_restart")
        logging.info("called firmware")

    def restart(self) -> None:
        response = self._post_request("printer/restart")
        logging.info("called restart")


def wait_for_printer(base_url: str) -> None:
    control = PrinterControl(base_url=base_url)

    logging.info("begin trying to restart klipper")

    control.dont_trust_ready_state()  # when plugging in the usb cable very fast and the state in moonraker is not up to date.
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is already started")
        return

    control.restart_firmware()
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is ready after FIRMWARE_RESTART")
        return

    control.restart()
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is ready after RESTART")
        return
    
    logging.info("failed to restart klipper.")

def is_valid_url(url : str):
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    base_url_arg = sys.argv[1] if (len(sys.argv) > 1) else None
    if (is_valid_url(base_url_arg) == False):
        logging.error(f"Invalid or missing base url parameter '{base_url_arg}'")
        exit(128)
    
    wait_for_printer(base_url=base_url_arg)
