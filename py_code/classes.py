from datetime import datetime
import sys, posix, time, binascii, socket, select, ssl
import hashlib
import re

class LogLine:
    timestamp: datetime
    maker: str
    model: str
    firmware: str
    firmware_channel: str
    level: int
    topics: str
    dvchost: str
    address: str
    message: str
    raw: str
    msg_src: str

    def __init__(self, rawcefstring: str, src="", delimiter: str = '|'):
        # Parse the raw CEF string
        parts = rawcefstring.split(delimiter)
        if len(parts) < 8:
            raise ValueError("Invalid CEF string format")
        
        self.timestamp = datetime.strptime(parts[0].split(" ")[0], "%Y-%m-%dT%H:%M:%S.%f%z")
        self.maker = parts[1]
        self.model = parts[2]
        self.firmware = parts[3].split(" ")[0]
        self.firmware_channel = parts[3].split(" ")[1].replace("(", "").replace(")", "") if len(parts[3].split(" ")) > 1 else None
        self.level = int(parts[4])
        self.topics = parts[5]
        # Extract the device name
        match = re.search(r'dvchost=([\w\-]+)', parts[7])
        if match:
            self.dvchost = match.group(1)
        else:
            self.dvchost = None
        # Extract the address
        match = re.search(r'dvc=([\d\.]+)', parts[7])
        if match:
            self.address = match.group(1)
        else:
            self.address = None
        # Extract the message
        match = re.search(r'msg=(.*)', parts[7])
        if match:
            self.message = match.group(1)
        else:
            self.message = None
        self.raw = rawcefstring
        self.msg_src = src

    def __str__(self):
        return f"LogLine(timestamp={self.timestamp}, maker={self.maker}, model={self.model}, firmware={self.firmware}, level={self.level}, topics={self.topics}, dvchost={self.dvchost}, address={self.address}, message={self.message})"
