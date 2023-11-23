import requests
import urllib.parse
import json
import time
import logging
import sys

class PrinterControl:
    PRINTER_READY = "ready"
    PRINTER_STARTUP = "startup"
    PRINTER_SHUTDOWN = "shutdown"
    PRINTER_ERROR = "error"
    PRINTER_UNKNOWN = "unknown"

    __retryDelay = 1 # seconds
    __dontTrustReadyStateTimeout = 30 #seconds
    __baseUrl = None
    __state = PRINTER_UNKNOWN

    def __init__(self, baseUrl : str) -> None:
        self.__baseUrl = baseUrl

    def getRequest(self, urlSuffix : str) -> any:
        url = urllib.parse.urljoin(self.__baseUrl,urlSuffix)
        return requests.get(url=url).json()

    def postRequest(self, urlSuffix : str) -> any:
        url = urllib.parse.urljoin(self.__baseUrl,urlSuffix)
        return requests.post(url=url).json()

    def refreshState(self) -> None:
        response = self.getRequest('printer/info')
        if ('result' in response and 'state' in response['result']):
            self.__state = response['result']['state']
        else:
            logging.debug(f"Unknown response: {response}")
            self.__state = "Unknown"

    def waitForFinalState(self) -> None:
        while True:
            self.refreshState()
            logging.info(f"wait for final state. Current state: {self.__state}")
            if (self.__state == PrinterControl.PRINTER_READY or self.__state == PrinterControl.PRINTER_SHUTDOWN or self.__state == PrinterControl.PRINTER_ERROR):
                break
            time.sleep(self.__retryDelay)

    def isReady(self) -> bool:
        return self.__state == PrinterControl.PRINTER_READY

    def dontTrustReadyState(self) -> None:
        timeout = time.time() + self.__dontTrustReadyStateTimeout   # 1 minutes from now
        while True:
            if time.time() >= timeout:
                break

            self.refreshState()
            if (self.__state != 'ready'):
                break

            logging.info("don't trust ready state.")
            time.sleep(self.__retryDelay)

    def restartFirmware(self) -> None:
        response = self.postRequest('printer/firmware_restart')
        print(response)

    def restart(self) -> None:
        response = self.postRequest('printer/restart')
        print(response)

def waitForPrinter(baseUrl : str) -> None:
    control = PrinterControl(baseUrl=baseUrl)

    control.dontTrustReadyState() #when plugging in the usb cable very fast and the state in moonraker is not up to date.
    control.waitForFinalState()
    if (control.isReady()):
        logging.info("klipper is already started")
        return
    
    control.restart()
    control.waitForFinalState()
    if (control.isReady()):
        logging.info("klipper is ready after RESTART")
        return

    control.restartFirmware()
    control.waitForFinalState()
    if (control.isReady()):
        logging.info("klipper is ready after FIRMWARE_RESTART")
        return
    
    logging.info("failed to restart klipper.")

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    waitForPrinter(baseUrl="http://localhost:7125")