import binascii
import socket
from time import time
import pickle
from record import Record


def dump_cache(cache):
    """Сохранение кэша при штатном выключении сервера"""
    with open('cache', 'wb') as cache_file:
        pickle.dump(cache, cache_file)


def load_cache():
    """Загрузка сохраненного кэша"""
    try:
        with open('cache', 'rb+') as cache_file:
            cache = pickle.load(cache_file)
            return cache
    except FileNotFoundError:
        return {}


def clear_cache(last_update, cache):
    """Просмотр и удаление просроенных записей из кэша"""
    now = int(round(time()))
    if now - last_update >= 120:
        for _, value in cache.items():
            for record in value:
                if record.ttl <= now:
                    del record

        for key in cache.keys():
            if cache[key] is None or cache[key] == []:
                cache.pop(key)
    return int(round(time())), cache


def proceed_query(sock, cache):
    """Основной метод обработки запросов"""
    data, addr = sock.recvfrom(4096)
    data = binascii.hexlify(data).decode("utf-8")
    cached_result = get_from_cache(data, cache)

    if cached_result is None:
        print('Fetching data from server...')
        data = data.replace("\n", "").replace(" ", "")
        with socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM) as sock_for_request:
            sock_for_request.settimeout(2)
            try:
                sock_for_request.sendto(binascii.unhexlify(data),
                                        ("195.19.71.253", 53))
                response_from_server, _ = sock_for_request.recvfrom(4096)
                response_from_server = binascii.hexlify(
                    response_from_server).decode("utf-8")
            except:
                result = None
            else:
                parse_response(response_from_server, cache)
                result = response_from_server
    else:
        print('Fetched from cash')
        result = cached_result
    if result is not None:
        sock.sendto(binascii.unhexlify(result), addr)


def parse_response(data, cache):
    """Разбор дополнительных записей и их выгрузка в кэш"""
    header, body = data[:24], data[24:]
    name, offset = get_name(data)
    msg_type = body[offset - 8: offset - 4]
    count_records = [int(header[12:16], 16), int(header[16:20], 16),
                     int(header[20:24], 16)]
    offset = 32 + len(name) * 2
    section = data[24 + offset + 8:]

    for i in count_records:
        record_and_name = parse_record(i, data, section, offset)
        section = section[24 + int(section[20:24], 16) * 2:]

        for record, name in record_and_name:
            if (name, record.msg_type) not in cache.keys:
                cache[(name, msg_type)] = [record_and_name]


def parse_record(count, data, section, offset):
    """Конвертация записи в классовый объект"""
    result = []
    for i in range(count):
        chunks = int(data[offset: offset + 4], 16)
        name, _ = get_part_name("", chunks, data)

        ttl = section[12:20]
        msg_type = section[4:8]

        record_data = section[24:24 + int(section[20:24], 16) * 2]
        result.append((Record(record_data, msg_type, ttl), name))
    return result


def get_part_name(data, chunks, name):
    start_from = int(str(bin(chunks))[4:], 2) * 2
    part_name, offset = get_name(data, start_from)
    if name == "":
        name += part_name
    else:
        name += '.' + part_name
    return name, offset


def get_name(data, start_from=24):
    name = ''
    offset = 0

    while True:
        i = start_from + offset
        chunks = int(data[i:i + 4], 16)

        if chunks >= 49152:
            name, offset = get_part_name(name, chunks, data)
            break

        if not int(data[i:i + 2], 16) == 0:
            break

        name = add_part_name(data, name, i)
        offset += int(data[i:i + 2], 16) * 2 + 2

    return name[:len(name) - 1], offset


def add_part_name(data, name, index):
    for i in range(0, int(data[index:index + 2], 16) * 2, 2):
        part_name = chr(int(data[index + i + 2:index + i + 4], 16))
        name += part_name
    return name + "."


def get_from_cache(data, cache):
    """Выгрузка записи из кэша"""
    header, other_data_before = data[:24], data[24:]
    name, _ = get_name(data)
    msg_type = other_data_before[-8: -4]

    print('Record | {name}, {msg_type}'.format(name=name,
                                               msg_type=msg_type))

    if (name, msg_type) in cache.keys():
        records = []
        for record in cache[(name, msg_type)]:
            format_answer = record.stringify()
            if record.ttl > int(round(time())):
                records.append(format_answer)

        count = len(records)

        if count != 0:
            return (header[:4] + "8180"
                    + header[8:12] + hex(count)[2:].rjust(4, '0')
                    + header[16:] + other_data_before + ''.join(records))
    return None


def start_server():
    """Основной метод сервера"""
    last_cache_update = int(round(time()))
    last_cache_update, cache = clear_cache(last_cache_update, load_cache())
    if cache is not None:
        print('Imported cache from last launch')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('localhost', 53))
    print('Server launched on 127.0.0.1: 53')
    print('-------------------------------------------------------')

    while True:
        try:
            proceed_query(sock, cache)
            last_cache_update, cache = clear_cache(last_cache_update, cache)
            print('-------------------------------------------------------')
        except KeyboardInterrupt:
            answer = -1
            while answer not in ['y', 'n']:
                print('Do you really want to shut down server?[y/n]', end=' ')
                answer = str(input())
            if answer == 'n':
                continue
            if answer == 'y':
                dump_cache(cache)
                exit(0)


if __name__ == '__main__':
    start_server()
