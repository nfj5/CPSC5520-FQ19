"""
CPSC 5520, Seattle University
This is free and unencumbered software released into the public domain.
Collaborated with Pabi
:Authors: Nicholas Jones
:Version: fq19-01
"""

import sys
from enum import Enum
import random
import threading
import socket
import pickle
import hashlib


M = 3  # FIXME: Test environment, normally = hashlib.sha1().digest_size * 8
NODES = 2**M
BUFFER_SIZE = 4096  # socket recv arg
BACKLOG = 100  # socket listen arg
TEST_BASE = 43544  # for testing use port numbers on localhost at TEST_BASE+n


class ModRange(object):
    """
    Range-like object that wraps around 0 at some divisor using modulo arithmetic.

    >>> mr = ModRange(1, 4, 100)
    >>> mr

    >>> 1 in mr and 2 in mr and 4 not in mr
    True
    >>> [i for i in mr]
    [1, 2, 3]
    >>> mr = ModRange(97, 2, 100)
    >>> 0 in mr and 99 in mr and 2 not in mr and 97 in mr
    True
    >>> [i for i in mr]
    [97, 98, 99, 0, 1]
    """

    def __init__(self, start, stop, divisor):
        self.divisor = divisor
        self.start = start % self.divisor
        self.stop = stop % self.divisor
        # we want to use ranges to make things speedy, but if it wraps around the 0 node, we have to use two
        if self.start < self.stop:
            self.intervals = (range(self.start, self.stop),)
        else:
            self.intervals = (range(self.start, self.divisor), range(0, self.stop))

    def __repr__(self):
        """ Something like the interval|node charts in the paper """
        return ''.format(self.start, self.stop, self.divisor)

    def __contains__(self, id):
        """ Is the given id within this finger's interval? """
        for interval in self.intervals:
            if id in interval:
                return True
        return False

    def __len__(self):
        total = 0
        for interval in self.intervals:
            total += len(interval)
        return total

    def __iter__(self):
        return ModRangeIter(self, 0, -1)


class ModRangeIter(object):
    """ Iterator class for ModRange """
    def __init__(self, mr, i, j):
        self.mr, self.i, self.j = mr, i, j

    def __iter__(self):
        return ModRangeIter(self.mr, self.i, self.j)

    def __next__(self):
        if self.j == len(self.mr.intervals[self.i]) - 1:
            if self.i == len(self.mr.intervals) - 1:
                raise StopIteration()
            else:
                self.i += 1
                self.j = 0
        else:
            self.j += 1
        return self.mr.intervals[self.i][self.j]


class FingerEntry(object):
    """
    Row in a finger table.

    >>> fe = FingerEntry(0, 1)
    >>> fe

    >>> fe.node = 1
    >>> fe

    >>> 1 in fe, 2 in fe
    (True, False)
    >>> FingerEntry(0, 2, 3), FingerEntry(0, 3, 0)
    (, )
    >>> FingerEntry(3, 1, 0), FingerEntry(3, 2, 0), FingerEntry(3, 3, 0)
    (, , )
    >>> fe = FingerEntry(3, 3, 0)
    >>> 7 in fe and 0 in fe and 2 in fe and 3 not in fe
    True
    """
    def __init__(self, n, k, node=None):
        if not (0 <= n < NODES and 0 < k <= M):
            raise ValueError('invalid finger entry values')
        self.start = (n + 2**(k-1)) % NODES
        self.next_start = (n + 2**k) % NODES if k < M else n
        self.interval = ModRange(self.start, self.next_start, NODES)
        self.node = node

    def __repr__(self):
        """ Something like the interval|node charts in the paper """
        return ''.format(self.start, self.next_start, self.node)

    def __contains__(self, id):
        """ Is the given id within this finger's interval? """
        return id in self.interval


class ChordNode(object):
    def __init__(self, n):
        self.node = n
        self.finger = [None] + [FingerEntry(n, k) for k in range(1, M+1)]  # indexing starts at 1
        self.predecessor = None
        self.keys = {}

    @property
    def successor(self):
        return self.finger[1].node

    @successor.setter
    def successor(self, id):
        self.finger[1].node = id

    def find_successor(self, id):
        """ Ask this node to find id's successor = successor(predecessor(id))"""
        np = self.find_predecessor(id)
        return self.call_rpc(np, 'successor')

    def find_predecessor(self, id):
        """ Ask this node to find id's predecessor """
    	np = n
        while id not in ModRange(np+1, self.call_rpc(np, 'successor')+1):
            np = self.call_rpc(np, 'closest_preceding_finger', id)
        return np

    def closest_preceding_finger(self, id):
        for i in range(M+1, 1, -1):
            if self.finger[i].node in ModRange(n+1, id):
                return self.finger[i].node
        return self.node

    def call_rpc(self, id, procedure, arguments=None):
        address = self.node_addr(id)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(address)
            sock.sendall(pickle.dumps((procedure, arguments)))
            return pickle.loads(sock.recv(BUFFER_SIZE))

    def node_addr(self, id):
        return TEST_BASE + id

    def listener(self, address):



if __name__ == '__main__':
	if len(sys.argv) != 3:
		print("Usage: python chord_node.py [node_host] [node_port]")
		exit(1)

	address = (sys.argv[1], int(sys.argv[2]))
	node = ChordNode()
