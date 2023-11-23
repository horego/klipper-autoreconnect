import json
import urllib.parse
import urllib.request
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
    _retryDelay = 1  # seconds
    _dontTrustReadyStateTimeout = 30  # seconds
    _baseUrl = None
    _state = State.PRINTER_UNKNOWN

    def __init__(self, baseUrl: str) -> None:
        self._baseUrl = baseUrl

    def _request(self, url, method) -> any:
        req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req) as response:
            data = response.read()
            json_data = json.loads(data.decode("utf-8"))
            return json_data

    def getRequest(self, urlSuffix: str) -> any:
        url = urllib.parse.urljoin(self._baseUrl, urlSuffix)
        return self._request(url, method="GET")

    def postRequest(self, urlSuffix: str) -> any:
        url = urllib.parse.urljoin(self._baseUrl, urlSuffix)
        return self._request(url, method="POST")

    def refreshState(self) -> None:
        response = self.getRequest("printer/info")
        if "result" in response and "state" in response["result"]:
            self._state = response["result"]["state"]
        else:
            logging.debug(f"Unknown response: {response}")
            self._state = "Unknown"

    def waitForFinalState(self) -> None:
        while True:
            self.refreshState()
            logging.info(f"wait for final state. Current state: {self._state}")
            if self._state in (
                State.PRINTER_READY,
                State.PRINTER_SHUTDOWN,
                State.PRINTER_ERROR,
            ):
                break
            time.sleep(self._retryDelay)

    @property
    def isReady(self) -> bool:
        return self._state == State.PRINTER_READY

    def dontTrustReadyState(self) -> None:
        timeout = time.time() + self._dontTrustReadyStateTimeout  # 1 minutes from now
        while True:
            if time.time() >= timeout:
                break

            self.refreshState()
            if self._state != "ready":
                break

            logging.info("don't trust ready state.")
            time.sleep(self._retryDelay)

    def restartFirmware(self) -> None:
        response = self.postRequest("printer/firmware_restart")
        print(response)

    def restart(self) -> None:
        response = self.postRequest("printer/restart")
        print(response)


def waitForPrinter(baseUrl: str) -> None:
    control = PrinterControl(baseUrl=baseUrl)

    control.dontTrustReadyState()  # when plugging in the usb cable very fast and the state in moonraker is not up to date.
    control.waitForFinalState()
    if control.isReady:
        logging.info("klipper is already started")
        return

    control.restart()
    control.waitForFinalState()
    if control.isReady:
        logging.info("klipper is ready after RESTART")
        return

    control.restartFirmware()
    control.waitForFinalState()
    if control.isReady:
        logging.info("klipper is ready after FIRMWARE_RESTART")
        return

    logging.info("failed to restart klipper.")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    waitForPrinter(baseUrl="http://localhost:7125")
