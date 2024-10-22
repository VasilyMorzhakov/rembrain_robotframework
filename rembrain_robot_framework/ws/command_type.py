class WsCommandType:
    PULL = "pull"
    PUSH = "push"
    PUSH_LOOP = "push_loop"
    PING = "ping"
    BIDIRECTIONAL = 'bidirectional'

    ALL_VALUES = (PULL, PUSH, PUSH_LOOP, PING, BIDIRECTIONAL)
