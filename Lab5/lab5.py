"""
CPSC 5520, Seattle University
This is free and unencumbered software released into the public domain.
Collaborated with Pabi
:Authors: Nicholas Jones
:Version: fq19-01
"""

import hashlib
import socket
import time
from time import strftime, gmtime

BUFFER_SIZE = int(2e6)  # bitcoin MAX_SIZE

BTC_HOST = "51.15.95.161"
BTC_PORT = 8333
VERSION = 70015

START_STRING = bytearray.fromhex("f9beb4d9")
HDR_SZ = 24

BLOCK_NUMBER = 2146346 % 600000  # 346346


def run():
	# build the version message
	ver_message = get_version_message()
	ver_packet = build_packet("version", ver_message)

	# build the verack message
	verack_packet = build_packet("verack", "".encode())

	# build the getblocks message
	block_message = get_block_message()
	block_packet = build_packet("getblocks", block_message)

	# put the verack and block packets together
	first_package = ver_packet + verack_packet + block_packet

	for msg in split_message(first_package):
		print("\nSent:")
		print_message(msg)

	# process responses
	first_response = message(first_package)
	for msg in first_response:
		print("\nReceived:")
		print_message(msg)


def split_message(packet):
	"""
	Takes a bytestream and splits it into individual messages
	:param packet: the bytestream to be split
	:return: a list of individual messages
	"""
	curr = 0
	messages = []

	# split the message into individual payloads
	while curr < len(packet):
		payload_size = unmarshal_uint(packet[curr + 16:curr + 20])
		messages.append(packet[curr:curr + HDR_SZ + payload_size])
		curr += payload_size + HDR_SZ

	return messages


def message(packet, wait_for_response=True):
	"""
	Send a message and receive the response
	:param packet: the message to send to the node
	:return: the list of payloads that the node responded with
	"""
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
		sock.connect((BTC_HOST, BTC_PORT))
		sock.sendall(packet)

		if wait_for_response:
			response = sock.recv(BUFFER_SIZE)
			return split_message(response)


def checksum(payload):
	"""
	Double hashes a payload to get a checksum
	:param payload: the payload to hash
	:return: the first four bytes of the resulting hash
	"""
	return hashlib.sha256(hashlib.sha256(payload).digest()).digest()[0:4]


def build_packet(cmd_name, payload):
	"""
	Constructs a Bitcoin message header
	:param cmd_name: the command to send
	:param payload: the actual data of the message
	"""
	command = cmd_name.encode()
	while not len(command) == 12:
		command += '\0'.encode()

	payload_size = uint32_t(len(payload))

	return START_STRING + command + payload_size + checksum(payload) + payload


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
	nonce = uint64_t(0)
	user_agent_bytes = compactsize_t(0)
	start_height = uint32_t(0)
	relay = bool_t(False)

	recv = addr_recv_services + addr_recv + addr_recv_port
	trans = addr_trans_services + addr_trans + addr_trans_port

	return version + services + timestamp + recv + trans + nonce + user_agent_bytes + start_height + relay


def get_block_message():
	"""
	Generates a block request message to send to a node
	:returns: the constructed block message
	"""
	# send inventory message of block header
	# message type: MSG_FILTERED_BLOCK to get Merkle block
	version = uint32_t(VERSION)
	count = compactsize_t(1)
	header_hash = bytearray(32)
	end_hash = bytearray(32)

	return version + count + header_hash + end_hash


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
	elif command == 'getblocks':
		print_blocks_msg(payload)
	elif command == 'inv':
		print("inv")
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


def print_blocks_msg(b):
	"""
	Report the contents of the given bitcoin getblocks message (sans the header)
	:param b: getblocks message contents
	"""

	version, count, header_hash, end_hash = b[:4], b[4:5], b[5:37], b[37:]
	prefix = '  '

	print(prefix + 'GETBLOCKS')
	print(prefix + '-' * 56)
	prefix *= 2
	print('{}{:32} version {}'.format(prefix, version.hex(), unmarshal_int(version)))
	print('{}{:32} count {}'.format(prefix, count.hex(), unmarshal_compactsize(count)[1]))
	print('{}{:32} header hash'.format(prefix, header_hash.hex()[:32]))
	print('{}{:32} end hash'.format(prefix, end_hash.hex()[:32]))


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
