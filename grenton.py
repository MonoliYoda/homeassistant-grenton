import os
import socket
from binascii import unhexlify
import xml.etree.ElementTree as ET
import re
import json

import asyncio
import struct

from datetime import datetime, timedelta

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from base64 import b64encode, b64decode


# Define TFTP opcodes
RRQ_OPCODE = 1
DATA_OPCODE = 3
ACK_OPCODE = 4
ERROR_OPCODE = 5

OBJECT_TYPES = {
    0: 'clu',
    3: 'd_in',
    4: 'd_out',
    6: 'timer',
    7: 'touch_btn',
    9: 'led',
    12: 'psuvoltage',
    13: 'a_out',
    16: 'scheduler',
    18: 'thermostat',
    20: 'touch_senstemp',
    21: 'touch_senslight',
    23: '1w_temp',
    24: 'shutter',
    29: 'touch_panel',
    31: 'push_notif',
    39: 'sun_clock'
}

TIMEDELTA = 0.1

RGBW_CHANNEL_GET = {
    'r': 3,
    'g': 4,
    'b': 5,
    'w': 15,
}

RGBW_CHANNEL_EXECUTE = {
    'r': 3,
    'g': 4,
    'b': 5,
    'w': 12,
}

THERMO_VALUES_GET = {
    'currentTemp': 14,
    'controlOut': 13,
    'setTemp': 3,
    'on': 6,
    'mode': 8,
    'targetTemp': 12
}

class GrentonClient():
    key = None
    iv = None
    cipher = None
    clu_config = None

    def __init__(self, host,udp_port=1234, base64_key=None, base64_iv=None, debug=False):
        self.host = host
        self.port = udp_port
        self.source_ip = '192.168.1.1'
        if base64_key:
            self.key = b64decode(base64_key)
        if base64_iv:
            self.iv = b64decode(base64_iv)
        self.DEBUG = debug
        if self.key and self.iv:
            self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(5)

        self.objects = []

        self.last_command_time = datetime.now()
        return None

    def __str__(self):
        return 'Hi'

    def id_gen(self):
        return os.urandom(3).hex()

    def load_keys(self, path):
        xml = ET.parse(path).getroot()
        self.key = b64decode(xml.find('ProjectProperties').find('projectCipherKey').find('keyBytes').text)
        self.iv = b64decode(xml.find('ProjectProperties').find('projectCipherKey').find('ivBytes').text)
        self.cipher = AES.new(self.key, AES.MODE_CBC, self.iv)

    def update_keys(self, base64_key, base64_iv):
        self.key = b64decode(base64_key)
        self.iv = b64decode(base64_iv)

    def send_message(self, message):
        if self.DEBUG:
            print(f'Sending message: {message}')
        self.sock.sendto(self.encrypt(message), (self.host, self.port))
        response = None
        try:
            resp, addr = self.sock.recvfrom(1024)
            response = self.decrypt(resp)
            if self.DEBUG:
                print(f'Received response: {response}')
        except socket.timeout:
            print("Timeout: No response received.")
            return False
        return response

    async def send_command(self, commad):
        nowtime = datetime.now()
        if (nowtime - self.last_command_time) < timedelta(seconds=TIMEDELTA):
            await asyncio.sleep(TIMEDELTA)
            # Actually use Threading timer here
        self.last_command_time = datetime.now()
        cmd_id = self.id_gen()
        msg = 'req:' + self.source_ip + f':{cmd_id}:{commad}'
        if self.DEBUG:
            print(f'Sending command: {msg}')
        self.sock.sendto(self.encrypt(msg), (self.host, self.port))
        try:
            resp, addr = self.sock.recvfrom(1024)
            response = self.decrypt(resp)
            if self.DEBUG:
                print(f'Received response: {response}')
            match = re.search(rf'{cmd_id}:(.*)', response)
            if match:
                return match.group(1)
            if self.DEBUG:
                print('Not found the command id, received wrong packet?')
            return False
        except socket.timeout:
            print("Timeout: No response received.")
            return False

    def encrypt(self, string):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded = pad(string.encode(), AES.block_size)
        return cipher.encrypt(padded)

    def decrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(data), AES.block_size).decode()

    async def ping(self):
        return await self.send_command('checkAlive()')

    async def list_modules(self):
        conf = await self.fetch_file_from_tftp('a:\om.lua')
        conf = iter(conf.decode().splitlines())

        modules = []
        for row in conf:
            mod = {}
            if ' = OBJECT:new(' in row and '--' not in row:
                comment = next(conf)
                if '-- NAME' in comment:
                    args = re.findall(r'\((.*?)\)', row)[0].split(', ')
                    name, module_id = re.search(r'(?:NAME_IO |NAME_PERIPHERY |NAME_CLU )(.*)', comment).group(1).split('=')
                    mod['name'] = name
                    mod['id'] = module_id
                    mod['type'] = OBJECT_TYPES[int(args[0])]
                    modules.append(mod)
        if self.DEBUG:
            print(modules)
        self.objects = modules
        return modules

    async def get_clu_id(self):
        conf = await self.fetch_file_from_tftp('a:\CONFIG.JSON')
        return json.loads(conf.decode())['sn']

    async def get_switch_state(self, module_id):
        response = await self.send_command('SYSTEM:fetchValues({{' + module_id + ',0}})')
        state = re.search(r'\{([^{}]*)\}', response).group(1)
        return state == '1'

    async def set_switch_state(self, module_id, state):
        response = await self.send_command(f'{module_id}:set(0, {int(state)})')
        if response == 'nil':
            return True
        return False

    async def get_sensor_value(self, module_id):
        response = await self.send_command('SYSTEM:fetchValues({{' + module_id + ',0}})')
        return re.search(r'\{([^{}]*)\}', response).group(1)

    async def get_led_state(self, module_id, channel):
        msg = "SYSTEM:fetchValues({"
        for i in RGBW_CHANNEL_GET.values():
            msg += f"{{{module_id},{i}}}"
            if i < 15:
                msg += ","
        msg += "})"
        response = await self.send_command(msg)
        response = re.search(r'\{([^{}]*)\}', response).group(1).split(',')
        state = {
            'r': response[0],
            'g': response[1],
            'b': response[2],
            'w': response[3],
            }
        return state[channel]


    async def set_led_value(self, module_id, channel, value, ramp_ms=2000):
        msg = f'{module_id}:execute({RGBW_CHANNEL_EXECUTE[channel]},{value},{ramp_ms})'
        response = await self.send_command(msg)
        if response == 'nil':
            return True
        return False

    async def set_module_value(self, module_id, val_id, value):
        msg = f'{module_id}:set({val_id},{value})'
        response = await self.send_command(msg)
        if response == 'nil':
            return True
        return False

    async def get_thermo_values(self, module_id):
        msg = "SYSTEM:fetchValues({"
        for i in THERMO_VALUES_GET.values():
            msg += f"{{{module_id},{i}}}"
            if i < 15:
                msg += ","
        msg += "})"
        response = await self.send_command(msg)
        response = re.search(r'\{([^{}]*)\}', response).group(1).split(',')
        state = {
            'currentTemp': float(response[0]),
            'controlOut': int(response[1]),
            'setTemp': float(response[2]),
            'on': int(response[3]),
            'mode': int(response[4]),
            'targetTemp': float(response[5])
        }
        return state

    async def set_thermo_away_mode(self, module_id, state):
        command = 6
        if state:
            command = 5
        response = await self.send_command(f"{module_id}:execute({command})")
        if response == 'nil':
            return True
        return False

    async def fetch_file_from_tftp(self, filename):
        # Start TFTP server on the CLU
        resp = self.send_message('req_start_ftp')
        if resp != 'resp:OK':
            return False

        # Set up the socket
        tftp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        tftp.bind(('0.0.0.0', 5683))
        tftp.settimeout(5)

        # Send the RRQ packet to the server
        packet = struct.pack('!H', RRQ_OPCODE) + filename.encode() + b'\0' + b'netascii\0'
        tftp.sendto(packet, (self.host, 69))

        file_data = b''
        # Receive data from the server
        while True:
            response, addr = tftp.recvfrom(516)  # Maximum size for data block in TFTP
            opcode = struct.unpack('!H', response[:2])[0]
            if opcode == DATA_OPCODE:
                block_num = struct.unpack('!H', response[2:4])[0]
                data = response[4:]
                if self.DEBUG:
                    print(f"Received block {block_num}")
                file_data += data
                # Construct and send ACK packet
                ack_packet = struct.pack('!H', ACK_OPCODE) + struct.pack('!H', block_num)
                tftp.sendto(ack_packet, addr)
                if len(response) < 516:
                    break  # End of file
            elif opcode == ERROR_OPCODE:
                error_code = struct.unpack('!H', response[2:4])[0]
                error_message = response[4:].decode()
                print(f"Error {error_code}: {error_message}")
                break
            else:
                print("Unexpected opcode received.")
                break
        tftp.close()
        return file_data