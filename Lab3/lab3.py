"""
CPSC 5520, Seattle University
This is free and unencumbered software released into the public domain.
Collaborated with Pabi and
:Authors: Nicholas Jones
:Version: fq19-01
"""

from datetime import datetime, timedelta
import socket
import sys
import threading
import time
import math

import fxp_bytes
import fxp_bytes_subscriber as fxp_bytes_s
from bellman_ford import BellmanFord

LISTENER_ADDRESS = (socket.gethostbyname(socket.gethostname()), 12345) # start up a listener on port 12345
SUBSCRIPTION_CYCLE = 10 * 60 # ten minutes
MESSAGE_BUFFER = 0.1 # 100ms
QUOTE_TIMEOUT = 1.5 # consider quotes stale after this many seconds
DEFAULT_TRADE_AMT = 100 # the default amount to make a currency exchange with

class Lab3(object):
	
	def __init__(self, provider):
		"""
		:param provider: the address (host, port tuple) of the provider
		"""
		self.provider_address = provider
		self.graph = {}
		
	def listen(self):
		"""
		Binds the listening socket and receives a message, then processes it
		"""
		listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		listener.bind(LISTENER_ADDRESS)
		
		last_time = datetime.now() + (datetime.utcnow() - datetime.now())
		
		while True:
			# wait for a message, unmarshal when one is received
			byte_msg = listener.recv(1024)
			demarshaled = fxp_bytes_s.demarshal_message(byte_msg)
			
			for quote in demarshaled: # process each quote individually
				timestamp = quote["timestamp"]
				diff = (last_time - timestamp).total_seconds()
				
				# if the new message is at least MESSAGE_BUFFER newer than the last message, process it
				if diff < MESSAGE_BUFFER:
					currencies = quote["cross"].split("/")
					self.pr_log("{} {} {}".format(currencies[0], currencies[1], quote["price"]))
					
					# update the graph using the new quote and change last_time to reflect new message
					self.add_to_graph(currencies, quote)
					last_time = quote["timestamp"]
				else:
					self.pr_log("Ignoring out-of-sequence message")
			
			stale = self.cleanup_graph()
			if stale > 0:
				pr_log("Removed {} stale quotes".format(stale))
			
			bf = BellmanFord(self.graph)
			dist, prev, neg_edge = bf.shortest_paths('USD', 1e-12)
			if not neg_edge is None:
				self.print_arbitrage(prev, 'USD')
			
	def add_to_graph(self, currencies, quote):
		"""
		Adds the provided quote to the graph of quotes (along with inverse)
		:param quote: the quote to add to be added to the graph
		"""
		rate = -1 * math.log(quote["price"])
		
		# add the curr1 -> curr2 edge
		if not currencies[0] in self.graph:
			self.graph[currencies[0]] = {}
		
		self.graph[currencies[0]][currencies[1]] = {"timestamp": quote["timestamp"], "price": rate}
		
		# add the curr2 -> curr1 edge (inverse exchange rate)
		if not currencies[1] in self.graph:
			self.graph[currencies[1]] = {}
		
		self.graph[currencies[1]][currencies[0]] = {"timestamp": quote["timestamp"], "price": -1 * rate}
		
	def cleanup_graph(self):
		"""
		Remove any "stale" edges that have been around for longer than QUOTE_TIMEOUT
		"""
		stale_cutoff = datetime.now() - timedelta(seconds=QUOTE_TIMEOUT)
		stale_count = 0
		
		for curr1 in self.graph:
			for curr2 in self.graph[curr1]:
				# remove the quote if it is considered stale
				if self.graph[curr1][curr2]["timestamp"] <= stale_cutoff:
					del self.graph[curr1][curr2]
					stale_count += 1
					
		return stale_count
	
	def print_arbitrage(self, prev, origin, init_value=DEFAULT_TRADE_AMT):
		"""
		Print the arbitrage opportunity step by step
		:param prev: the dictionary of previous locations for each vertex
		:param origin: where we are starting the trade from
		:param init_value: the initial amount of money to exchange (in origin currency)
		"""
		
		# iterate through prev from end to beginning
		steps = [origin]
		last_step = prev[origin]
		
		while not last_step == origin:
			steps.append(last_step)
			last_step = prev[last_step]
		
		# we start at origin so throw that in, then reverse to get forward order
		steps.append(origin)
		steps.reverse()
		
		# print the list of steps in a readable format
		print("From 100 {}".format(origin))
		
		value = init_value
		last = origin
		
		for i in range(1, len(steps)):
			curr = steps[i]
			# convert the negative log back into the exchange rate and update the value
			price = math.exp(-1 * self.graph[last][curr]["price"])
			value *= price
			
			# print the results to the screen and move on to the next step
			print(" = {} {}".format(value, curr))
			last = curr
			
		profit = value - init_value
		print(" > Profit of {} {}".format(profit, origin))
		
	def subscribe(self):
		"""
		Sends the subscription message to the provider every SUBSCRIPTION_CYCLE amount of seconds
		"""
		while True:
			self.pr_log("Sending SUBSCRIBE to {}".format(self.provider_address))
			
			# connect to the socket and send our address information
			with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
				serialized_addr = fxp_bytes_s.serialize_address(LISTENER_ADDRESS)
				sock.sendto(serialized_addr, self.provider_address)
				sock.close()
			
			# wait until the next subscription cycle
			time.sleep(SUBSCRIPTION_CYCLE)
		
	def run(self):
		"""
		Starts up the listener and subscriber threads in that order
		(to ensure that the listener is running when the subscriber sends out data - or close to that)
		"""
		listener_thr = threading.Thread(target=self.listen)
		listener_thr.start()
		
		subscribe_thr = threading.Thread(target=self.subscribe)
		subscribe_thr.start()
	
	def pr_log(self, msg):
		"""
		Print a message with the current timestamp
		:param msg: the message to be printed
		"""
		print("["+str(datetime.now())+"]", msg)
		
if __name__ == "__main__":
	if len(sys.argv) != 3:
		print("Usage: python lab3.py [provider_host] [provider_port]")
		exit(1)
		
	address = (sys.argv[1], int(sys.argv[2]))
	subscriber = Lab3(address)
	subscriber.run()