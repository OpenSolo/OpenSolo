
# Definitions shared between client and server connection modules

# Messages/commands used in connection process

# Network messages are all 68 bytes:
# start size description
#     0    1  CMD_*
#     1    1  SYS_*
#     2    1  cmd_data
#     3    1  locked
#     4   32  sololink version
#    36   32  firmware version (artoo or pixhawk)
#    68       message length

# Messages/commands
CMD_CONN_REQ = 1        # client sends to request connection
CMD_CONN_ACK = 2        # Received to ack a connection request
CMD_USER_RSP = 3        # Internal; user response to connection request
CMD_TIMEOUT  = 4        # Timeout waiting for next message

# return name for command
def cmd_name(cmd):
    if cmd == CMD_CONN_REQ:     return "CMD_CONN_REQ"
    elif cmd == CMD_CONN_ACK:   return "CMD_CONN_ACK"
    elif cmd == CMD_USER_RSP:   return "CMD_USER_RSP"
    elif cmd == CMD_TIMEOUT:    return "CMD_TIMEOUT"
    else:                       return "CMD_UNKNOWN"

# System types that may use the connection protocol
SYS_CONTROLLER = 1      #
SYS_SOLO = 2            #

# return name for system type
def sys_name(sys):
    if sys == SYS_CONTROLLER:   return "SYS_CONTROLLER"
    elif sys == SYS_SOLO:       return "SYS_SOLO"
    elif sys == SYS_APP:        return "SYS_APP"
    else:                       return "SYS_UNKNOWN"

# 'locked' byte in connect_request message
DATA_LOCKED = 1         # sender is locked

# connected state moves from NO to PEND to YES
# network state moves from PEND to either NO or YES
NO = 1
PEND = 2
YES = 3

# all network messages are this long
CONN_MSG_LEN = 68
