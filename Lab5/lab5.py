"""
CPSC 5520, Seattle University
This is free and unencumbered software released into the public domain.
Collaborated with Pabi
:Authors: Nicholas Jones
:Version: fq19-01
"""

from time import strftime, gmtime

import socket
import time
import random
import struct
import hashlib
import binascii

BTC_HOST = "42.60.217.183"
BTC_PORT = 8333
VERSION = 70015

START_STRING = bytearray.fromhex("f9beb4d9")
HDR_SZ = 24

BLOCK_NUMBER = 2146346 % 600000


def run():
	message = get_version_message()
	# print (len(message))
	header = get_header("version", message)

	complete = header + message

	print_message(complete)


def checksum(payload):
	return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[0:4]


def get_header(cmd_name, payload):
	"""
	Constructs a Bitcoin message header
	:param cmd_name: the command to send
	:param payload: the actual data of the message
	"""
	command = cmd_name.encode()
	while not len(command) == 12:
		command += '\0'.encode()

	payload_size = uint32_t(len(payload))

	return START_STRING + command + bytes(payload_size) + checksum(payload)


def get_version_message():
	"""
	Generates a version message to send to a node
	:returns: the constructed version message
	"""
	version = uint32_t(VERSION)
	services = uint64_t(0)  # 0 = not a full node
	timestamp = uint64_t(int(time.time()))
	addr_recv_services = uint64_t(1)  # 1 = full node
	addr_recv = ipv6_from_ipv4(BTC_HOST)
	addr_recv_port = uint16_t(BTC_PORT)
	addr_trans_services = services
	addr_trans = ipv6_from_ipv4("127.0.0.1")
	addr_trans_port = uint16_t(BTC_PORT)
	nonce = uint64_t(random.randint(20000, 30000))
	user_agent_bytes = '\0'.encode()
	start_height = uint32_t(0)
	relay = '\0'.encode()

	recv = addr_recv_services + addr_recv + addr_recv_port
	trans = addr_trans_services + addr_trans + addr_trans_port

	return version + services + timestamp + recv + trans + nonce + user_agent_bytes + start_height + relay


def compactsize_t(n):
	if n < 252:
		return uint8_t(n)
	if n < 0xffff:
		return uint8_t(0xfd) + uint16_t(n)
	if n < 0xffffffff:
		return uint8_t(0xfe) + uint32_t(n)
	return uint8_t(0xff) + uint64_t(n)


def unmarshal_compactsize(b):
	key = b[0]
	if key == 0xff:
		return b[0:9], unmarshal_uint(b[1:9])
	if key == 0xfe:
		return b[0:5], unmarshal_uint(b[1:5])
	return b[0:1], unmarshal_uint(b[0:1])


def bool_t(flag):
	return uint8_t(1 if flag else 0)


def ipv6_from_ipv4(ipv4_str):
	pchIPv4 = bytearray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0xff, 0xff])
	return pchIPv4 + bytearray((int(x) for x in ipv4_str.split('.')))


def ipv6_to_ipv4(ipv6):
	return '.'.join([str(b) for b in ipv6[12:]])


def uint8_t(n):
	return int(n).to_bytes(1, byteorder='little', signed=False)


def uint16_t(n):
	return int(n).to_bytes(2, byteorder='little', signed=False)


def int32_t(n):
	return int(n).to_bytes(4, byteorder='little', signed=True)


def uint32_t(n):
	return int(n).to_bytes(4, byteorder='little', signed=False)


def int64_t(n):
	return int(n).to_bytes(8, byteorder='little', signed=True)


def uint64_t(n):
	return int(n).to_bytes(8, byteorder='little', signed=False)


def unmarshal_int(b):
	return int.from_bytes(b, byteorder='little', signed=True)


def unmarshal_uint(b):
	return int.from_bytes(b, byteorder='little', signed=False)


def print_message(msg, text=None):
	"""
    Report the contents of the given bitcoin message
    :param msg: bitcoin message including header
    :return: message type
    """
	print('\n{}MESSAGE'.format('' if text is None else (text + ' ')))
	print('({}) {}'.format(len(msg), msg[:60].hex() + ('' if len(msg) < 60 else '...')))
	payload = msg[HDR_SZ:]
	command = print_header(msg[:HDR_SZ], checksum(payload))
	if command == 'version':
		print_version_msg(payload)
	# FIXME print out the payloads of other types of messages, too
	return command


def print_version_msg(b):
	"""
	Report the contents of the given bitcoin version message (sans the header)
	:param payload: version message contents
    """
	# pull out fields
	version, my_services, epoch_time, your_services = b[:4], b[4:12], b[12:20], b[20:28]
	rec_host, rec_port, my_services2, my_host, my_port = b[28:44], b[44:46], b[46:54], b[54:70], b[70:72]
	nonce = b[72:80]
	user_agent_size, uasz = unmarshal_compactsize(b[80:])
	i = 80 + len(user_agent_size)
	user_agent = b[i:i + uasz]
	i += uasz
	start_height, relay = b[i:i + 4], b[i + 4:i + 5]
	extra = b[i + 5:]

	# print report
	prefix = '  '
	print(prefix + 'VERSION')
	print(prefix + '-' * 56)
	prefix *= 2
	print('{}{:32} version {}'.format(prefix, version.hex(), unmarshal_int(version)))
	print('{}{:32} my services'.format(prefix, my_services.hex()))
	time_str = strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(unmarshal_int(epoch_time)))
	print('{}{:32} epoch time {}'.format(prefix, epoch_time.hex(), time_str))
	print('{}{:32} your services'.format(prefix, your_services.hex()))
	print('{}{:32} your host {}'.format(prefix, rec_host.hex(), ipv6_to_ipv4(rec_host)))
	print('{}{:32} your port {}'.format(prefix, rec_port.hex(), unmarshal_uint(rec_port)))
	print('{}{:32} my services (again)'.format(prefix, my_services2.hex()))
	print('{}{:32} my host {}'.format(prefix, my_host.hex(), ipv6_to_ipv4(my_host)))
	print('{}{:32} my port {}'.format(prefix, my_port.hex(), unmarshal_uint(my_port)))
	print('{}{:32} nonce'.format(prefix, nonce.hex()))
	print('{}{:32} user agent size {}'.format(prefix, user_agent_size.hex(), uasz))
	print('{}{:32} user agent \'{}\''.format(prefix, user_agent.hex(), str(user_agent, encoding='utf-8')))
	print('{}{:32} start height {}'.format(prefix, start_height.hex(), unmarshal_uint(start_height)))
	print('{}{:32} relay {}'.format(prefix, relay.hex(), bytes(relay) != b'\0'))
	if len(extra) > 0:
		print('{}{:32} EXTRA!!'.format(prefix, extra.hex()))


def print_header(header, expected_cksum=None):
	"""
    Report the contents of the given bitcoin message header
    :param header: bitcoin message header (bytes or bytearray)
    :param expected_cksum: the expected checksum for this version message, if known
    :return: message type
    """
	magic, command_hex, payload_size, cksum = header[:4], header[4:16], header[16:20], header[20:]
	command = str(bytearray([b for b in command_hex if b != 0]), encoding='utf-8')
	psz = unmarshal_uint(payload_size)
	if expected_cksum is None:
		verified = ''
	elif expected_cksum == cksum:
		verified = '(verified)'
	else:
		verified = '(WRONG!! ' + expected_cksum.hex() + ')'
	prefix = '  '
	print(prefix + 'HEADER')
	print(prefix + '-' * 56)
	prefix *= 2
	print('{}{:32} magic'.format(prefix, magic.hex()))
	print('{}{:32} command: {}'.format(prefix, command_hex.hex(), command))
	print('{}{:32} payload size: {}'.format(prefix, payload_size.hex(), psz))
	print('{}{:32} checksum {}'.format(prefix, cksum.hex(), verified))
	return command


if __name__ == '__main__':
	run()
