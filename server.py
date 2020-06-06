import binascii
import socket
from time import time
import sys


def start_server():
    cache_check_time = int(round(time()))
    cache = clear_cache(get_cache(), cache_check_time)
    if cache is not None:
        print('Imported cache from last launch')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 53))
    print('Server launched on 127.0.0.1: 53')

    while True:
        try:
            proceed_query(sock, cache)
            cache_check_time = int(round(time()))
            cache = clear_cache(cache, cache_check_time)
        except KeyboardInterrupt:
            answer = -1
            while answer not in ['y', 'n']:
                print('Do you really want to shut down server?[y/n]')
                answer = str(input())
            if answer == 'n':
                continue
            if answer == 'y':
                exit(0)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        # TODO: Написать помощь
        if sys.argv[-1] in ['-h', '--help']:
            with open('help.txt', 'r', encoding='utf-8') as help_text:
                print(help_text.read())
            exit(0)

    start_server()


def get_cache():
    # TODO: Реализовать метод
    pass


def clear_cache():
    # TODO: Реализовать метод
    pass


def proceed_query():
    # TODO: Реализовать метод
    pass
