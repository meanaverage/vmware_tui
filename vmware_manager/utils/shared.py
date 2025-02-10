from queue import Queue

# Shared queues and data structures
status_log = Queue(maxsize=1000)  # Keep more messages in memory 