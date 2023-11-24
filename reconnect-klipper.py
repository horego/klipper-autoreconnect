#!/usr/bin/env python3
import json
import urllib.parse
import urllib.request
import urllib.error
import time
import logging
import sys

from enum import Enum


class State(Enum):
    PRINTER_READY = "ready"
    PRINTER_STARTUP = "startup"
    PRINTER_SHUTDOWN = "shutdown"
    PRINTER_ERROR = "error"
    PRINTER_UNKNOWN = "unknown"


class PrinterControl:
    _retry_delay = 1  # seconds
    _debounce_time = 30  # seconds
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

    def refresh_state(self) -> None:
        response = self._get_request("printer/info")
        if "result" in response and "state" in response["result"]:
            logging.debug(response["result"]["state"].lower())
            self._state = State(response["result"]["state"].lower())
        else:
            logging.debug(f"Unknown response: {response}")
            self._state = State.PRINTER_UNKNOWN

    def wait_for_final_state(self) -> None:
        while True:
            self.refresh_state()
            logging.info(f"wait for final state. Current state: {self._state}")
            if self._state in (
                State.PRINTER_READY,
                State.PRINTER_SHUTDOWN,
                State.PRINTER_ERROR,
            ):
                break
            time.sleep(self._retry_delay)

    @property
    def is_ready(self) -> bool:
        return self._state == State.PRINTER_READY

    def dont_trust_ready_state(self) -> None:
        timeout = time.time() + self._debounce_time  # 1 minutes from now
        while True:
            if time.time() >= timeout:
                break

            self.refresh_state()
            if self._state != State.PRINTER_READY:
                break

            logging.info("don't trust ready state.")
            time.sleep(self._retry_delay)

    def restart_firmware(self) -> None:
        response = self._post_request("printer/firmware_restart")
        print(response)

    def restart(self) -> None:
        response = self._post_request("printer/restart")
        print(response)


def wait_for_printer(base_url: str) -> None:
    control = PrinterControl(base_url=base_url)

    control.dont_trust_ready_state()  # when plugging in the usb cable very fast and the state in moonraker is not up to date.
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is already started")
        return

    control.restart()
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is ready after RESTART")
        return

    control.restart_firmware()
    control.wait_for_final_state()
    if control.is_ready:
        logging.info("klipper is ready after FIRMWARE_RESTART")
        return

    logging.info("failed to restart klipper.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    wait_for_printer(base_url="http://localhost:7125")
